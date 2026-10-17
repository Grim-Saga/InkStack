//! Verified installer-script resolution shared by the daemon updater and the CLI.
//!
//! Every consumer must resolve the installer script from a published
//! InkStack application release and verify the downloaded bytes against the
//! SHA-256 digest GitHub records for that release asset before executing
//! anything. The digest check establishes consistency with GitHub's release
//! metadata at fetch time; it is not a signature, and a repository owner can
//! replace release assets, so the comparison must happen on the exact bytes
//! that are about to be executed — never on a prior fetch.

use anyhow::Context;
use anyhow::Result;
use inkstack_http_client::ClientRouteClass;
use inkstack_http_client::RouteAwareClientPool;

pub(crate) const INKSTACK_RELEASES_API_URL: &str =
    "https://api.github.com/repos/Grim-Saga/InkStack";
pub(crate) const INKSTACK_RELEASES_DOWNLOAD_URL: &str =
    "https://github.com/Grim-Saga/InkStack/releases/download";
#[cfg(unix)]
pub(crate) const INSTALLER_ASSET_NAME: &str = "install.sh";
#[cfg(windows)]
pub(crate) const INSTALLER_ASSET_NAME: &str = "install.ps1";

/// The on-disk name of the staged installer script.
pub fn installer_file_name() -> &'static str {
    INSTALLER_ASSET_NAME
}

pub(crate) const RELEASES_PER_PAGE: usize = 100;
const RELEASE_SCAN_MAX_PAGES: usize = 10;

#[derive(Debug)]
pub(crate) struct ResolvedInstaller {
    pub tag: String,
    /// The hex-encoded SHA-256 digest GitHub recorded for the asset.
    pub sha256: String,
    /// The exact download URL of the installer asset on that release.
    pub url: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum InstallerResponse {
    Success(Vec<u8>),
    Unsuccessful { status: u16 },
}

/// HTTP boundary used to download release metadata and installer assets.
///
/// Implementations must issue a GET for the supplied URL, return exact
/// response bytes for a successful status, and report a non-success status
/// without buffering its response body.
pub(crate) trait InstallerHttp: Send + Sync {
    fn get<'a>(
        &'a self,
        url: &'a str,
    ) -> impl std::future::Future<Output = Result<InstallerResponse>> + Send + 'a;
}

impl InstallerHttp for RouteAwareClientPool {
    async fn get(&self, url: &str) -> Result<InstallerResponse> {
        let response = RouteAwareClientPool::get(self, url)
            .send()
            .await
            .context("failed to fetch standalone InkStack updater")?;
        if !response.status().is_success() {
            return Ok(InstallerResponse::Unsuccessful {
                status: response.status().as_u16(),
            });
        }
        let body = response
            .bytes()
            .await
            .context("failed to read standalone InkStack updater")?
            .to_vec();
        Ok(InstallerResponse::Success(body))
    }
}

/// Builds an HTTP pool for installer resolution using the CLI's factory.
pub fn installer_http_pool(
    factory: inkstack_http_client::HttpClientFactory,
) -> RouteAwareClientPool {
    RouteAwareClientPool::new_without_request_logging(factory, ClientRouteClass::Other)
}

/// Resolves the installer script of the most recently published InkStack
/// application release, together with the digest GitHub recorded for it.
///
/// Mirrors the standalone installers' resolution contract: only a
/// `rust-v<version>` tag counts as an application release. The V8
/// dependency releases (`rusty-v8-v*`) and every other release type are
/// skipped, so no consumer can ever bootstrap from a non-application
/// release, and a repository without application releases yet fails
/// cleanly without disturbing the managed installation.
pub(crate) async fn resolve_installer_release(
    http: &impl InstallerHttp,
) -> Result<ResolvedInstaller> {
    for page in 1..=RELEASE_SCAN_MAX_PAGES {
        let list_url = format!(
            "{INKSTACK_RELEASES_API_URL}/releases?per_page={RELEASES_PER_PAGE}&page={page}"
        );
        let body = match http.get(&list_url).await? {
            InstallerResponse::Success(body) => body,
            InstallerResponse::Unsuccessful { status } => {
                anyhow::bail!("standalone InkStack updater request failed with status {status}")
            }
        };
        let releases: serde_json::Value =
            serde_json::from_slice(&body).context("could not parse the InkStack release list")?;
        let releases = releases
            .as_array()
            .context("InkStack release list was not an array")?;
        for release in releases {
            let Some(tag) = release["tag_name"].as_str() else {
                continue;
            };
            if !is_application_release_tag(tag) {
                continue;
            }
            let Some(asset) = release["assets"].as_array().and_then(|assets| {
                assets
                    .iter()
                    .find(|asset| asset["name"].as_str() == Some(INSTALLER_ASSET_NAME))
            }) else {
                continue;
            };
            let Some(digest) = asset["digest"].as_str() else {
                anyhow::bail!(
                    "InkStack release {tag} does not publish a digest for {INSTALLER_ASSET_NAME}"
                )
            };
            let Some(sha256) = parse_sha256_digest(digest) else {
                anyhow::bail!(
                    "InkStack release {tag} publishes an invalid digest for {INSTALLER_ASSET_NAME}"
                )
            };
            return Ok(ResolvedInstaller {
                tag: tag.to_string(),
                sha256,
                url: format!("{INKSTACK_RELEASES_DOWNLOAD_URL}/{tag}/{INSTALLER_ASSET_NAME}"),
            });
        }
        if releases.len() < RELEASES_PER_PAGE {
            break;
        }
    }
    anyhow::bail!(
        "no compatible InkStack application release is available yet; \
         publish an InkStack application release (rust-v tag with installer \
         assets) and retry the update"
    )
}

/// Downloads the installer script of the selected application release and
/// verifies its bytes against the digest GitHub recorded for the asset
/// before returning them. Empty or truncated responses are rejected.
pub(crate) async fn fetch_verified_installer_script(http: &impl InstallerHttp) -> Result<Vec<u8>> {
    let resolved = resolve_installer_release(http).await?;
    let body = match http.get(&resolved.url).await? {
        InstallerResponse::Success(body) => body,
        InstallerResponse::Unsuccessful { status } => {
            anyhow::bail!("standalone InkStack updater request failed with status {status}")
        }
    };
    verify_installer_bytes(&body, &resolved)?;
    Ok(body)
}

/// The `pub` entry point for the CLI's standalone update bootstrap.
pub async fn fetch_installer_script(http: &RouteAwareClientPool) -> Result<Vec<u8>> {
    fetch_verified_installer_script(http).await
}

pub(crate) fn verify_installer_bytes(body: &[u8], resolved: &ResolvedInstaller) -> Result<()> {
    if body.is_empty() {
        anyhow::bail!(
            "the InkStack installer asset {} from {} was empty",
            INSTALLER_ASSET_NAME,
            resolved.tag
        );
    }
    let actual = hex_sha256(body);
    if actual != resolved.sha256 {
        anyhow::bail!(
            "the downloaded InkStack installer from {} did not match the digest \
             GitHub recorded for the release asset: expected sha256:{}, got sha256:{actual}",
            resolved.tag,
            resolved.sha256
        );
    }
    Ok(())
}

fn parse_sha256_digest(digest: &str) -> Option<String> {
    let hex = digest.strip_prefix("sha256:")?;
    if hex.len() != 64 || !hex.bytes().all(|b| b.is_ascii_hexdigit()) {
        return None;
    }
    Some(hex.to_ascii_lowercase())
}

fn hex_sha256(bytes: &[u8]) -> String {
    use sha2::Digest;
    let digest = sha2::Sha256::digest(bytes);
    let mut encoded = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write;
        let _ = write!(encoded, "{byte:02x}");
    }
    encoded
}

/// Matches the application release tag contract shared with the standalone
/// installers: `rust-vMAJOR.MINOR.PATCH` with an optional `-alpha[.N[.M]]`
/// or `-beta[.N]` prerelease suffix. V8 dependency releases such as
/// `rusty-v8-v150.4.0` never match.
pub(crate) fn is_application_release_tag(tag: &str) -> bool {
    fn numeric(part: &str) -> bool {
        !part.is_empty() && part.bytes().all(|byte| byte.is_ascii_digit())
    }
    let Some(version) = tag.strip_prefix("rust-v") else {
        return false;
    };
    let (core, suffix) = match version.split_once('-') {
        Some((core, suffix)) => (core, suffix),
        None => (version, ""),
    };
    let numbers: Vec<&str> = core.split('.').collect();
    if numbers.len() != 3 || numbers.iter().any(|part| !numeric(part)) {
        return false;
    }
    if suffix.is_empty() {
        return true;
    }
    let mut suffix_parts = suffix.split('.');
    match suffix_parts.next() {
        Some("alpha") => {
            let rest: Vec<&str> = suffix_parts.collect();
            rest.len() <= 2 && rest.iter().all(|part| numeric(part))
        }
        Some("beta") => {
            let rest: Vec<&str> = suffix_parts.collect();
            rest.len() <= 1 && rest.iter().all(|part| numeric(part))
        }
        _ => false,
    }
}
