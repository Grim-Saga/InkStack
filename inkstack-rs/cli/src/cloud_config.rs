use anyhow::Context;
use anyhow::Result;
use inkstack_app_server::in_process::EmbeddedNetworkPolicy;
use inkstack_cloud_config::cloud_config_bundle_loader_for_storage;
use inkstack_config::CloudConfigBundleLoader;
use inkstack_config::ConfigLoadOptions;
use inkstack_core::config::Config;
use inkstack_core::config::ConfigBuilder;
use inkstack_core::config::ConfigOverrides;
use inkstack_core::config::LoaderOverrides;
use inkstack_core::config::bootstrap_auth_config;
use inkstack_core::config::find_inkstack_home;
use inkstack_core::config::load_config_toml_with_layer_stack;
use inkstack_utils_absolute_path::AbsolutePathBuf;
use inkstack_utils_cli::CliConfigOverrides;

pub(crate) async fn load_config(
    config_overrides: &CliConfigOverrides,
    loader_overrides: LoaderOverrides,
) -> Result<Config> {
    let mut config = config_builder(
        config_overrides,
        loader_overrides,
        ConfigOverrides::default(),
    )
    .await?
    .build()
    .await
    .context("failed to load configuration")?;
    EmbeddedNetworkPolicy::default().activate(&mut config);
    Ok(config)
}

pub(crate) async fn config_builder(
    config_overrides: &CliConfigOverrides,
    loader_overrides: LoaderOverrides,
    harness_overrides: ConfigOverrides,
) -> Result<ConfigBuilder> {
    let network_policy = EmbeddedNetworkPolicy::load(&loader_overrides).await;
    let cli_overrides = config_overrides
        .parse_overrides()
        .map_err(anyhow::Error::msg)?;
    let inkstack_home = find_inkstack_home().context("failed to resolve INKSTACK_HOME")?;
    let cwd = match harness_overrides.cwd.as_deref() {
        Some(cwd) => AbsolutePathBuf::relative_to_current_dir(cwd),
        None => AbsolutePathBuf::current_dir(),
    }
    .context("failed to resolve current directory")?;
    let bootstrap_config = load_config_toml_with_layer_stack(
        inkstack_home.as_path(),
        Some(&cwd),
        cli_overrides.clone(),
        ConfigLoadOptions {
            loader_overrides: loader_overrides.clone(),
            strict_config: false,
            cloud_config_bundle: CloudConfigBundleLoader::default(),
        },
    )
    .await
    .context("failed to load bootstrap configuration")?;
    let cloud_config_bundle = cloud_config_bundle_loader_for_storage(
        network_policy.bind_bootstrap_auth(
            bootstrap_auth_config(inkstack_home.as_path(), &bootstrap_config)
                .context("failed to resolve cloud configuration authentication")?,
        ),
        /*enable_openai_api_key_env*/ false,
    )
    .await
    .context("failed to initialize cloud configuration authentication")?;

    Ok(ConfigBuilder::default()
        .inkstack_home(inkstack_home.to_path_buf())
        .cli_overrides(cli_overrides)
        .loader_overrides(loader_overrides)
        .harness_overrides(harness_overrides)
        .cloud_config_bundle(cloud_config_bundle)
        .fallback_cwd(Some(cwd.to_path_buf())))
}
