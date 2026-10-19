# Task 16B — credential dependency recommendation

Assessment date: 2026-10-18. This is a follow-up design recommendation, not an
implemented migration. The approved Task 16B scope is ZIP security and independent
quality repairs; credential dependencies remain unchanged. RUSTSEC-2026-0370,
RUSTSEC-2026-0371 and RUSTSEC-2026-0372 remain unresolved. Do not add advisory
exceptions or remove macOS support to make the gate pass.

## Recommendation and alternatives

Prefer an upstream-supported zbus 6 port that preserves the existing credential
contract. If none is released, separately review a narrowly scoped, pinned
compatibility patch before considering a broader keyring migration. No such patch
has been implemented or approved by this assessment. Substantial authentication
or credential-storage redesign requires the user's separate approval.

Crates.io metadata and published source manifests were checked on the assessment
date. The latest stable versions checked were keyring 4.2.0, secret-service 5.2.0,
dbus-secret-service 4.1.0, zbus-secret-service-keyring-store 1.0.1 and zbus 6.0.0.

| Route | Evidence and decision |
| --- | --- |
| Upstream zbus 6 support | Preferred destination. The standalone wire/name crates moved into zbus 6; zbus 5 still retains the retired families. zbus 6.0.0 requires Rust 1.89, within the pinned 1.95.0 toolchain. Updating the TUI's direct screen-reader dependency alone cannot remove the credential dependency path. |
| Reviewed compatibility patch retaining keyring 3 | Potentially bounded: port the Secret Service integration and its dependency constraints to zbus 6 while preserving the existing `Entry` API, identity and error behavior. A Cargo version override alone cannot bridge incompatible APIs or the existing major-version requirements. Require a pinned source revision, reviewed diff, reproducible lockfile and an explicit maintenance/upstreaming plan. |
| keyring 4 / separate store ecosystem | A maintained alternative to evaluate, not a sufficient advisory fix by itself. keyring 4.2.0 uses keyring-core and separate platform stores; its default `v1` feature selects the zbus Secret Service store. Store 1.0.1 requires secret-service 5 and zbus 5; secret-service 5.2.0 also requires zbus 5. Migration would additionally require reviewing builder initialization, credential API, native errors and platform store identity. It still needs a zbus 6-compatible store. |
| keyring 3 synchronous backend | Same keyring API and shared `SsCredential` identity code could limit migration scope, but reject unmodified dbus-secret-service 4.1.0: its DH private-key and AES-IV generation uses noncryptographic `fastrand`. A reviewed security patch replacing both with a cryptographic OS-backed RNG could be evaluated separately; it also introduces libdbus packaging and timeout/error compatibility work. Switching to its OpenSSL feature does not fix the shared DH generator. |

Official references: [RustSec 0370](https://rustsec.org/advisories/RUSTSEC-2026-0370.html),
[0371](https://rustsec.org/advisories/RUSTSEC-2026-0371.html),
[0372](https://rustsec.org/advisories/RUSTSEC-2026-0372.html), and the
[zbus upstream retirement/release follow-up](https://github.com/z-galaxy/zbus/issues/2043).
Published manifests: [keyring 4.2.0](https://docs.rs/crate/keyring/4.2.0/source/Cargo.toml),
[secret-service 5.2.0](https://docs.rs/crate/secret-service/5.2.0/source/Cargo.toml),
[store 1.0.1](https://docs.rs/crate/zbus-secret-service-keyring-store/1.0.1/source/Cargo.toml),
[zbus 6.0.0](https://docs.rs/crate/zbus/6.0.0/source/Cargo.toml).

## Contract that a replacement must preserve

Linux keyring 3.6.3 uses `service`, `username`, `target=default` and
`application=rust-keyring` attributes. Lookup matches service/username/target,
with a legacy no-target fallback in the default collection. Preserve collection
selection, duplicate/ambiguous handling, UTF-8 password encoding, update/delete
semantics and durable storage. Preserve application service/account derivation,
serialized token formats, home-scoped secrets, resolved-backend pinning and the
existing rules for file fallback. Do not silently interpret provider errors as
missing credentials. The existing persistent builder actually constructs
`SsCredential`; its name does not establish a kernel-cache guarantee.

See the published [keyring 3 Secret Service implementation](https://docs.rs/crate/keyring/3.6.3/source/src/secret_service.rs)
and [persistent builder](https://docs.rs/crate/keyring/3.6.3/source/src/keyutils_persistent.rs).
Both Linux feature declarations in `keyring-store` and `rmcp-client` must remain
consistent: upstream rejects enabling sync and async Secret Service together.

With `crypto-rust`, the current backend requests a DH-encrypted Secret Service
session. Preserve cryptographic randomness for private keys and IVs, encrypted
session negotiation, and failure on unsupported encryption rather than silent
plaintext fallback. This is local D-Bus transport encryption; OAuth HTTP/TLS and
at-rest encryption remain separate contracts. Existing secret-service 4.0.0 uses
`OsRng`; the dbus-secret-service 4.1.0 shared generator uses `fastrand::Rng`.
[fastrand explicitly disclaims cryptographic security](https://docs.rs/fastrand/2.3.0/fastrand/).
The [dbus-secret-service session source](https://docs.rs/crate/dbus-secret-service/4.1.0/source/src/session.rs)
shows the private-key generator and IV generator. This is a source-based rejection,
not a claim of a published advisory or demonstrated credential exploit.

Native error compatibility is part of the API. Keep `Locked` → `WouldBlock`,
`Unavailable` → `NotConnected`, typed I/O kinds where available, and ambiguous
errors as `Other`. Libdbus retains D-Bus error names but loses the old typed I/O
source: map only reviewed names, never human-readable messages. Preserve error
payload redaction and cause-chain safety. The alternative's two-second method
timeout also differs operationally; its prompt wait is effectively unbounded
(one year), as the old prompt completion wait is unbounded. Existing blocking
store APIs and async callers' blocking-task boundaries must remain sound.

## Platform behavior and security boundary

| Platform | Existing backend and compatibility requirement |
| --- | --- |
| Linux | `linux-native-async-persistent` with keyring 3.6.3/secret-service 4; credentials are Secret Service items selected by the attributes above. Encrypted D-Bus sessions protect transferred secrets; collection unlock, prompts, access control and encryption at rest depend on the actual provider. A zbus 6 patch should retain those contracts without changing item identity. |
| Windows | `windows-native` uses Windows Credential Manager through keyring 3.6.3. The default target name is `username.service` (an explicit target overrides it), with generic credentials and enterprise persistence. Preserve that derivation, credential type/persistence and error mapping. An isolated Linux dependency patch should leave this feature and backend untouched. A keyring 4 store must prove access to old entries and equivalent OS access controls before adoption. |
| macOS | `apple-native` uses Keychain generic passwords via security-framework; service/account identify the item, with the selected keychain domain determining lookup (default User/login keychain). Preserve domain selection, prompts/access controls, item identity and native errors. An isolated Linux patch should leave this path untouched; keyring 4 needs seeded Keychain proof. |

These OS stores delegate protection at rest and authorization to the provider or
operating system; this assessment does not establish a universal at-rest cipher
or equivalent policy across all three systems. Replacing a transport library
cannot justify stronger claims. Native behavior and migration tests on Windows
and macOS have not been executed as part of Task 16B.
Published native implementations: [Windows](https://docs.rs/crate/keyring/3.6.3/source/src/windows.rs),
[macOS](https://docs.rs/crate/keyring/3.6.3/source/src/macos.rs).

## Required proof before adoption

1. Use a disposable provider and synthetic secrets to seed credentials with the
   old backend, then read/update/delete them with the candidate. Check restart
   persistence, old-client rollback where supported, no duplicate creation,
   missing entries, legacy no-target entries, conflicting entries, Unicode and
   separate service/account/home identities. Do not use personal credentials.
2. Verify secure RNG usage, encrypted-session success and negotiation failure,
   locked/unlocked stores, prompt dismissal, provider disconnect, absent session
   bus and slow-provider timeout behavior. A mocked keyring alone cannot prove
   transport or seeded migration compatibility.
3. Run native-error and redaction tests plus OAuth/secrets regressions for login,
   refresh, logout, persistence failure, backend pinning and file-fallback policy.
   Include known and unknown D-Bus names and misleading error messages.
4. Retain and verify Linux, macOS and Windows backends. For any keyring 4 route,
   test seeded platform credentials and native error conversion on all three OSes;
   a Linux build cannot prove Keychain or Windows Credential Manager compatibility.
5. Check reproducible dependency/features across supported targets, packaging and
   native linkage, the screen reader, and the repository's required quality gates.
   Run cargo-deny without advisory exceptions and show that all three retired
   families disappear from the resolved dependency graph before claiming repair.

This document changes no dependency, credential implementation or authentication
behavior. The three D-Bus findings remain visible until a separately reviewed
route satisfies these conditions.
