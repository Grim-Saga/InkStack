# Task 16B — security and lint hardening

**PARTIALLY COMPLETE — SECURITY REVIEW PENDING**

Assessment date: 2026-10-18. Approved Option 1 repairs ZIP and the independent
quality gates. Credential storage remains unchanged. Three D-Bus unmaintained
advisories remain blocking; Task 16C requires another review.

Branch: `task-16b/security-and-lint-hardening`, based on Task 16A commit
`afacbdb0a79e311130595bcbd2329c45398f4d67`. Only this task branch is to be pushed
for review. No main merge, release, tag or credential migration is included.

## ZIP repair and dependency graph

The workspace ZIP requirement changes from 2.4.2 to 9.0.5, retaining default
features. RustSec's patched range for RUSTSEC-2026-0367, 0368 and 0369 is
`>=9.0.0`. ZIP 9.0.5 declares Rust 1.88; its newly selected dependencies declare
requirements no higher than 1.89. Actual workspace and release checks use the
repository's Rust 1.95.0 toolchain.

Cargo generated the canonical lockfile using:

```sh
cargo +1.95.0 update --manifest-path inkstack-rs/Cargo.toml -p zip@2.4.2 --precise 9.0.5
cargo +1.95.0 metadata --manifest-path inkstack-rs/Cargo.toml --locked --format-version 1
```

[The complete normalized graph delta](task-16b-dependency-changes.json) records
all added/removed packages, exact versions, sources, checksums and changed edges.
Dependency references are normalized to package identities, so newly necessary
version qualifiers are not mistaken for semantic graph changes.

Removed: arbitrary 1.4.2, bzip2 0.5.2, bzip2-sys 0.1.13+1.0.8,
derive_arbitrary 1.4.2, lzma-rs 0.3.0, lzma-sys 0.1.20, xz2 0.1.7,
zip 2.4.2 and zstd-sys 2.0.16+zstd.1.5.7.

Added: aes 0.9.3, bzip2 0.6.1, cipher 0.5.2, const-oid 0.10.2,
constant_time_eq 0.6.1, cpubits 0.1.1, inout 0.2.4, libbz2-rs-sys 0.2.5,
lzma-rust2 0.22.0, pbkdf2 0.13.0, ppmd-rust 1.5.1, typed-path 0.12.3,
zip 9.0.5, zstd 0.14.3, zstd-safe 8.2.0 and zstd-sys 2.1.2+zstd.1.5.7.
Existing older aes/cipher/zstd packages needed elsewhere remain resolved.
Six retained package identities have changed dependency edges: block-buffer
0.12.0, digest 0.11.3, getrandom 0.3.4, inkstack-core-plugins 0.0.0,
time 0.3.47 and zstd-safe 7.2.4. Retained package checksums/sources are unchanged.

Bazel's Cargo-derived metadata is synchronized. The obsolete native bzip2 module,
its injection and bzip2-sys annotation are removed because bzip2 0.6 uses the Rust
implementation. The zstd-sys MSVC include patch is rebased to 2.1.2: preserve
sibling include paths, use upstream's `target_is_msvc()` helper, and drop the
visibility hunk now implemented upstream. No codec is disabled to avoid fixing
its build metadata.

The new libbz2-rs-sys 0.2.5 LICENSE permits source/binary redistribution subject
to retained source notices, accurate origin/alteration attribution and no author
endorsement. Cargo-deny now approves `bzip2-1.0.6` only for that exact crate
version. This is a reviewed license entry, not an advisory exception or global
license allowance. Upstream source/license remains unmodified; repository
LICENSE and NOTICE remain intact.

## Custom extraction security

The application uses its own ZIP loop rather than `ZipArchive::extract`, so the
crate upgrade alone was insufficient. Extraction now handles the fallible ZIP 9
name API, validates portable paths, rejects archive symlinks/special files,
checks each destination directory with symlink metadata, creates files
exclusively and applies only ordinary permission bits (`mode & 0o777`) through
the open file handle. GitHub root stripping, executable files, empty directories
and `.git` contents remain supported.

Duplicate/pre-existing files and Windows-ambiguous names now fail safely.
Callers use private staging directories; these checks do not claim protection
against a hostile process concurrently replacing ancestor directories.

Six new regression tests exercise genuine ZIP central-directory metadata. The
old implementation produced one pass and five expected security failures. The
repaired implementation passes all six on ZIP 9.0.5/Rust 1.95.0. The complete
startup-sync test selection passes **29 tests**, including those six, GitHub
HTTP/git fallbacks, cleanup and preserving existing snapshots after failure.
Unix symlink and permission tests ran on Linux. No native Windows/macOS runtime
result is claimed.

## Independent quality corrections

- R11: remove a one-comment module placeholder and its orphan snapshot. Git
  history shows that file never contained an executable test since import.
  Existing rmcp-client read-only discovery/metadata and inkstack-mcp connection
  reuse restrictions remain intact. The old snapshot's stronger thread-level
  propagation claim is still unproven (core config sets the flag false); this
  cleanup does not implement that policy or remove executed coverage.
- R12: align the crate-name assertions with the existing InkStack filter,
  explicitly reject `codex_tui`, and retain positive support-crate cases.
- R13: add the 18 exact parameter comments (14 updater-test, four installer),
  with rustfmt wrapping only. Argument values, behavior and assertions are
  unchanged; a normalized token comparison confirms this.
- R14: document narrow dictionary entries for the valid `WRONLY`/`oint`
  identifiers, the RustCrypto `inout` crate name, and use “unparsable” in the Task 11 ledger. Ordinary spelling
  mistakes are still detected by an external negative fixture.

The lint-package setup failure was environmental: missing pinned compiler
components and Dylint tooling. Installed nightly-2026-08-20 rustc-dev, rust-src,
llvm-tools-preview and cargo-dylint/dylint-link 6.1.0. Installing those tools
with stable initially failed because their newly resolved dependencies require
Rust 1.96; installation with the pinned nightly succeeded. No repository
lockfile/toolchain or CI policy was changed to conceal that setup failure.

Before the assertion fix, the stale crate-name assertion failed. Afterward the
exact CI-directory command passes five library tests (including the UI harness
with nine cases) and three binary tests. Python lint wrappers pass six tests.

## Validation

Commands below run from the repository root unless noted. Cargo used an isolated
reflink copy of the prior target cache; the original user cache was not modified.
Verified prebuilt V8 archive/bindings were provided through `RUSTY_V8_ARCHIVE` and
`RUSTY_V8_SRC_BINDING_PATH`; V8 was not rebuilt from source. Test commands retain
`RUST_MIN_STACK=8388608`.

| Command | Observed result |
| --- | --- |
| `RUSTUP_TOOLCHAIN=1.95.0 cargo-deny --manifest-path inkstack-rs/Cargo.toml --locked check` | Exit 1; exactly three unmaintained errors below; bans/licenses/sources pass |
| `cargo +1.95.0 shear --deny-warnings` in `inkstack-rs` (1.11.2) | Pass |
| `cargo +nightly-2026-08-20 test --locked` in `tools/argument-comment-lint` | Five library + three binary tests pass; UI harness nine cases pass |
| `python3 -B -m unittest discover -s tools/argument-comment-lint -p 'test_*.py'` | Six pass |
| `codespell --count --ignore-words .codespellignore --skip ./.git` (2.4.3) | Pass; zero findings |
| Same Codespell command with external ordinary-typo fixture | Exit 65; one finding detected |
| `cargo +nightly-2026-08-20 fmt --manifest-path inkstack-rs/Cargo.toml --all -- --check` | Pass |
| `cargo +1.95.0 check --manifest-path inkstack-rs/Cargo.toml --workspace --locked` | Pass |
| `cargo +1.95.0 check --manifest-path inkstack-rs/Cargo.toml -p inkstack-cli -p inkstack-tui --release --locked` | Pass; existing warnings: app-server one unused mutability, TUI seven dead-code, cloud-tasks two unused imports |
| `cargo +1.95.0 test --manifest-path inkstack-rs/Cargo.toml -p inkstack-core-plugins --lib startup_sync:: --locked` | 29 pass, zero failed/ignored, 455 filtered |
| `cargo +1.95.0 test --manifest-path inkstack-rs/Cargo.toml -p inkstack-app-server-daemon -p inkstack-login -p inkstack-keyring-store --lib --locked` | Exit 101: daemon 93 pass, one unchanged serialization assertion fails; Cargo stops before other packages (see separate auth run) |
| `cargo +1.95.0 test --manifest-path inkstack-rs/Cargo.toml -p inkstack-login -p inkstack-keyring-store --lib --locked` | 204 login + six keyring tests pass, zero failed/ignored |
| `python3 -B -m unittest discover -s .github/scripts -p 'test_*.py'` | 148 pass |
| `python3 -B -m unittest discover -s scripts/install -p 'test_*.py'` | 24 pass; existing Python invalid-escape SyntaxWarning |
| `INKSTACK_REPO_ROOT="$PWD" python3 -B -m unittest discover -s scripts/inkstack_package -p 'test_*.py'` | 32 pass; initial invocation missing required variable failed setup, then corrected |
| Bazel 9.2.0 `mod deps --lockfile_mode=error` | Pass |
| Focused Bazel daemon argument-comment aspect with `--nobuild` | Analysis passes after zstd patch repair; zero actions, not a compiler-lint pass |
| Focused Bazel daemon argument-comment compilation | Pass; daemon inline test target lint marker generated, 9,443 actions |
| `bazel build --lockfile_mode=error --jobs=8 @crates//:zip` | Linux build passes, 419 actions |
| `bazel build --nobuild --lockfile_mode=error --platforms=//:windows_x86_64_gnullvm @crates//:zip` | Windows dependency analysis passes, zero actions; no Windows compiler/runtime claim |

Bazel uses `--output_base=/home/grim/.cache/inkstack-task16b-bazel` and
`--noexperimental_remote_repo_contents_cache`. The exact focused command is:

```sh
bazel build --lockfile_mode=error --config=argument-comment-lint --jobs=8 \
  //inkstack-rs/app-server-daemon:app-server-daemon-unit-tests-bin
```

The daemon failure is
`tests::remote_control_start_output_serializes_inner_output_without_tag`, at
`app-server-daemon/src/lib.rs:1320`: expected `managedInkStackPath` and
`managedInkStackVersion`, actual serde output uses `managedInkstackPath` and
`managedInkstackVersion`. Both the test and serialization source are unchanged
from Task 16A, as are serde/serde_json versions. The baseline suite was not rerun
separately, so this is evidence of an unchanged failing assertion, not a claim
of a separately executed baseline result. The full daemon suite is not green.
All 35 updater/verified-installer tests in that run pass; their assertions remain
unchanged. This spelling/API-contract question is left for review outside the
approved parameter-comment-only correction.

The initial Bazel analysis failed on the obsolete zstd patch; rebasing it fixed
that failure. The later Windows analysis and Linux ZIP build used the corrected
patch and synchronized graph. Native MSVC compilation remains unexecuted; patch
application against pristine zstd-sys 2.1.2 was checked separately.

An independent review attempt could not complete because the reviewer agent
reported an account usage limit. The implementation and preservation diff were
reviewed locally; an independent review pass is not claimed.

## Remaining Cargo-deny findings

Database commit: `999ec89d5d3f10f20be14750ec8c2d8b44e0ac9b`; cargo-deny 0.20.2.

| Advisory | Locked package | Status |
| --- | --- | --- |
| RUSTSEC-2026-0367 | ZIP formerly 2.4.2 | Resolved by 9.0.5 plus custom-loop permission regression |
| RUSTSEC-2026-0368 | ZIP formerly 2.4.2 | Resolved by 9.0.5 plus explicit archive-symlink rejection |
| RUSTSEC-2026-0369 | ZIP formerly 2.4.2 | Resolved by 9.0.5 plus directory checks and file-handle permissions |
| RUSTSEC-2026-0370 | zvariant 4.2.0 | Unresolved, unmaintained |
| RUSTSEC-2026-0371 | zbus_names 3.0.0 | Unresolved, unmaintained |
| RUSTSEC-2026-0372 | zvariant_derive 4.2.0 | Unresolved, unmaintained |

The full check also warns about duplicate versions, yanked spin 0.9.8,
unmatched configured sources/licenses/wrappers and a pre-existing YAML advisory
ignore with no matching package. No advisory ignore is added or altered.
Credential-family package identities, checksums and resolved edges remain
unchanged. The overall security gate remains failed by design until review.

[The separate credential recommendation](task-16b-credential-backend-recommendation.md)
compares upstream zbus 6, reviewed compatibility/security patches and maintained
store alternatives, including migration/API/OS tests. No backend using fastrand
for cryptographic key or IV generation is substituted.

## Preservation and review limits

All eleven pre-existing worktrees retain their recorded HEAD/status and dirty-file
hashes. The Task 16A baseline and the original dirty user lockfile/snapshot are
untouched. The resulting task lockfile has 1,473 packages (previously 1,466),
SHA-256 `bf8a5e33b3c2498e3e5ff2f348fd228fedb13a0332eb3a4830f7a4a69a22df25`.
Credential-family graph equality and unchanged source/config paths were checked
against Task 16A; advisory settings are byte-equivalent after parsing.
GitHub-only executable distribution, legitimate ChatGPT `/backend-api/codex`,
provider/API-key authentication, verified-installer SHA-256 checks, Windows
manifest resources, macOS source/support, LICENSE and NOTICE are preserved.
No runner-group, billing, secrets, SDK-packaging or macOS-build policy change is
included. No full cross-platform matrix, native Windows/macOS credential proof,
release binary publication or Task 16C work was performed.

Local evidence logs are under `/tmp/inkstack-task16b/` with lint-specific logs
under its `quality/` directory. This report distinguishes executed tests from
analysis and unexecuted platform checks; pending D-Bus security review is not a
passing Task 16B claim.

## Correction commits

- `fcde7d5`: patched ZIP, custom extraction and Cargo/Bazel/license synchronization.
- `cc85d73`: orphan module/snapshot cleanup verified by Cargo-shear.
- `a408cc7`: lint assertions and exact updater parameter comments.
- `7a78e52`: Codespell wording and documented valid identifiers.
- The final documentation commit records this report, credential design and
  complete dependency graph delta.
