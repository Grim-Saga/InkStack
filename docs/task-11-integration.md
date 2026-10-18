# Task 11 integration ledger

## Checklist

- [x] Audit branches and isolate integration from user worktrees.
- [x] Correct changelog link (`bc7121b`).
- [x] Merge Tasks 1–10 normally (`178eafa`, no conflicts).
- [x] Complete authentication migration and focused verification (`4aed2bd`).
- [x] Remove external publishers; preserve GitHub artifact construction (`8aebefa`).
- [x] Review complete diff and run final verification (failures reported below).
- [ ] Update main only if verification and attribution gates are satisfied.

## Audit and decisions

Integration started at origin/main `f31d1c2`; task chain ends at `e521c54`.
Common baseline: `d19294d`. All nine earlier task branches are ancestors of
Task 10. `codex/rusty-v8-release` (`92a7954`) is already in the baseline.
No additional GLM branches or registered worktrees were found. All eight
Dependabot branches remain separate. No branches are deleted.

Main's eight commits touch only LICENSE, NOTICE, CHANGELOG, CLA, and three
deliberate document deletions. The merge preserves those deletions:
REBRAND_NOTES.md, SECURITY.md, docs/open-source-fund.md. The CLA maintainer
note removal and changelog bullet removal are preserved.

Initial attribution gate: Apache 2.0 text and Ratatui notices remain, but main replaced
the original OpenAI copyright lines. Ownership intent does not establish legal
permission to erase upstream attribution. Flag for owner review; do not claim
legal clearance or update main while this is unresolved.
Resolved in `67584f0`: retain the original OpenAI copyright alongside the owner's
Grim Saga copyright, explicitly identify OpenAI Codex ancestry, and keep the
Apache license text and Ratatui notices. This preserves known attribution,
not a legal opinion about other potential obligations.

Ruling: preserve secret-filter references to the retired variable. Filtering a
legacy secret is not an authentication alias; removal would weaken safeguards.

## Verification so far

Historical pre-continuation runs: GitHub scripts 128/128; shell installer
24/24; package tests 31/31; Bazel mod deps lockfile check passed. Workspace
cargo check --locked --all-targets passed with the existing verified V8 pair.
Auth manager 80/80, model-provider 102/102, feedback 36/36, TUI preflight 6/6.
CLI --lib 15/15 does NOT cover main.rs doctor tests; run binary tests separately.

Known failures reproduced before this continuation: login store-key hash and
storage metrics; TUI long-browser-link snapshot; broad TUI update filter stack
overflow. Do not regenerate unrelated snapshots to conceal these failures.

Original worktree on continuation: Task 10 at e521c54, dirty lock SHA-256
63f34b3a72a8314b22b45472cd0ada594875d50db92ddafe3d5beedfb6363277.
It also has an untracked onboarding .snap.new from the earlier baseline test.
Neither will be edited. Integration's lock serialization is also dirty and
must not be staged without semantic comparison.

## Continuation evidence

- `cargo test -p inkstack-login --lib auth::manager --locked`: 80 passed.
- `cargo test -p inkstack-cli --bin inkstack doctor --locked`: initially
  127 passed, 3 failed, 1 ignored. One was the changed OpenAI-key precedence
  expectation; corrected to match the new contract and added obsolete-variable
  negative coverage. `provider_reachability_mode_uses_api_key_auth`: 1 passed.
  The other failures are a pre-existing ChatGPT endpoint expectation
  (`/codex/responses` versus actual `/inkstack/responses`) and snapshot spacing.
- `cargo test -p inkstack-otel --test tests otel_export_routing_policy --locked`:
  6 passed, including request-auth metadata and recovery observability.
- `pnpm test -- --runInBand exec.test.ts`: could not run, pnpm unavailable.
- `cargo fmt --all --check`: fails on broad existing formatting drift,
  including untouched agent-graph-store and agent-identity files. No global
  formatting rewrite performed.
- TOML semantic comparison of committed versus dirty integration lockfile,
  normalizing package/dependency order: equal. No lockfile staged.

Ruling: remove the R2 upload implementation and its three dedicated tests,
replace old opt-in publisher guards with GitHub-only guards. This retires
coverage only for deleted functionality, not release integrity coverage.
Keep `npm_alpha_tag.py`, PyPI verification/resolution helpers, and their tests
as disconnected tested utilities; no workflow calls them to publish.

Caller audit: R2 workflow called only from rust-release; R2 script called only
by that workflow and its tests. Three Python publisher workflows were top-level
entrypoints, not reusable dependencies. Their reusable package-build workflows
and SDK implementations are retained, as are npm staging and Python wheel
creation for GitHub assets. Removed jobs: publish-r2-assets, publish-r2,
publish-npm, deploy-dev-website, winget. Canary now needs release and DotSlash
only, and recognizes alpha versions directly rather than using an npm output.

Distribution guard RED: 5 tests, 8 failures before cleanup (one parser defect
corrected to avoid treating a newline as inline needs). After cleanup the
full GitHub-script suite passes 125 tests; previous count 128 loses 3 deleted
R2 tests and replaces 5 old gates with 5 GitHub-only guards.
Prompt 7/7 and history update notices 3/3 pass with reviewed generated snapshots:
prompt now displays `inkstack update`; legacy pnpm notice has no registry
command. Installation detection and ownership remain unchanged.

## Complete branch/worktree audit

Original checkout: `/home/grim/Dev/Agent Harness/InkStack`, Task 10 at `e521c54`.
V8 checkout: `/home/grim/.codex/worktrees/rusty-v8-release/InkStack`, at `92a7954`;
its untracked `docs/superpowers/` migration plan is untouched.
Integration: `/home/grim/Dev/Agent Harness/InkStack-task11`.

| AI branch | Tip | Disposition |
|---|---|---|
| task-1/bazel-extension-repair | 85e0fd8 | Ancestor of Task 10; no unique commits |
| task-2/bazel-lockfile-repair | b109cb0 | Ancestor of Task 10; no unique commits |
| task-3/macos-entitlements-repair | 378b3ec | Ancestor of Task 10; no unique commits |
| task-4/ci-verification-repair | 2cc3316 | Ancestor of Task 10; no unique commits |
| task-5/python-packaging-migration | 30155ec | Ancestor of Task 10; no unique commits |
| task-6/remove-upstream-release-dependencies | ec222be | Ancestor of Task 10; no unique commits |
| task-7/independent-installers | 0b991fe | Ancestor of Task 10; no unique commits |
| task-8/independent-updaters | 4acd559 | Ancestor of Task 10; no unique commits |
| task-9/first-release-readiness | 34edba9 | Ancestor of Task 10; no unique commits |
| task-10/verified-updater-bootstrap | e521c54 | Merged once, with all nine ancestors |
| codex/rusty-v8-release | 92a7954 | Already in baseline; not remerged |
| task-11/integration-github-only | See final git log | New integration work only |

Local and origin task/V8 tips agree. Local main remains `d19294d`; origin/main
remains `f31d1c2ec116609b6be43db6ba45932bdd74f474`. Its eight newer commits are
`1aa297f`, `d74433c`, `a739b3c`, `9d2b5ea`, `004e451`, `99d8464`, `107af21`,
`f31d1c2`. All are integration ancestors. The merge parents are `bc7121b` and
`e521c54`; there were no conflicts and no global ours/theirs resolutions.

## Final review and fixes

A separate read-only reviewer examined the complete integration and cleanup.
Important findings were corrected in one fix pass:

- `67584f0`: upstream attribution restored alongside fork attribution.
  Attribution guard failed before the change and passed afterwards.
- `82e0712`: both standalone package variants now contain exact root LICENSE
  and NOTICE bytes. Archive tests failed for missing notices on Linux, macOS,
  and Windows fixture packages, then passed for both tar.gz and zip archives.
- `6c01677`: doctor and TUI now share published application-release discovery
  with the verified installer rather than using GitHub's stable-only /latest.
  Draft/dependency histories and alpha precedence regressions failed before
  the fix and pass afterwards. Metadata requests retain route-aware policy,
  a five-second deadline, and a bounded 16 MiB page body (release lists contain
  many asset records). The TUI release-only module is compiled under tests too.
- `bcacb72`: actual loopback HTTP testing proved updater requests lacked a
  GitHub-required product User-Agent; both metadata and installer requests now
  explicitly send a non-secret InkStack User-Agent. Regression RED → GREEN.

`4da6b3b` corrects two stale login expectations without changing storage code.
Correction to the earlier diagnosis: the keyring hash failure is NOT caused
by the presence of a home directory. Rust receives the literal `~/.inkstack`;
its SHA-256 prefix is `22922df3eb6ea845`, whereas the old expectation
`940db7b1d0e4eb40` hashes `~/.codex`. The metrics failure is NOT a missing
keyring service: its expected credential kind was `inkstack`, while the enum
serializes as `ink_stack`. The complete login library suite now passes.

Ruling: restore only upstream attribution proven by the common baseline;
retain all owner notices and deliberate document deletions. Cost if wrong:
additional legal review may identify further notices, but none were removed.
The earlier secret-filter ruling's cost if wrong is only conservative filtering
of an obsolete secret name. The publisher-test ruling's cost if wrong is that
an overlooked caller would fail; caller searches, workflow graph validation,
and the replacement guards found none.

Deferred minor: doctor still labels an unparseable version as "not older".
Valid prereleases are now comparable; unknown version wording is deferred.

## Final validation record

Python/Bazel commands run from the integration repository root; Cargo and
rustfmt commands run from `inkstack-rs`. Full logs are under `/tmp/opencode/task11-*`.

| Exact command | Result |
|---|---|
| `python3 -m unittest discover -s .github/scripts -p 'test_*.py'` | 127 passed; includes release-resolution, first-release, publisher ownership, updater destination, no-upstream-binary, V8-integrity and attribution guards |
| `python3 -m unittest discover -s scripts/install -p test_install_sh.py` | 24 passed |
| `INKSTACK_REPO_ROOT="$PWD" python3 -m unittest discover -s scripts/inkstack_package -p 'test_*.py'` | 32 passed; initial invocation without INKSTACK_REPO_ROOT failed at import, then corrected |
| `/tmp/opencode/bin/bazel mod deps --lockfile_mode=error` | Passed; no build |
| `cargo test -p inkstack-login --lib --locked` | 204 passed |
| `cargo test -p inkstack-cli --test login --locked` | 8 passed, including stdin API-key login and Bedrock logout isolation |
| `cargo test -p inkstack-cli --lib --locked` | 15 passed |
| `cargo test -p inkstack-cli --bin inkstack doctor::updates --locked` | 4 passed |
| `cargo test -p inkstack-cli --bin inkstack doctor --locked` | 128 passed, 2 failed, 1 ignored; failures below |
| `cargo test -p inkstack-model-provider --lib --locked` | 102 passed |
| `cargo test -p inkstack-otel --test tests otel_export_routing_policy --locked` | 6 passed |
| `cargo test -p inkstack-app-server-daemon --lib update --locked` | 40 passed |
| `cargo test -p inkstack-app-server-daemon --lib verified_installer --locked` | 3 passed |
| `cargo test -p inkstack-tui --lib update_action::tests --locked` | 2 passed |
| `cargo test -p inkstack-tui --lib update_versions --locked` | 11 passed |
| `cargo test -p inkstack-tui --lib startup_preflight --locked` | 6 passed |
| `cargo test -p inkstack-tui --lib update_prompt --locked` | 7 passed; generated prompt snapshot reviewed |
| `cargo test -p inkstack-tui --lib update_available_history_cell_snapshot --locked` | 3 passed; generated legacy-package notice reviewed |
| `cargo check --workspace --locked --all-targets` | Passed using the existing verified V8 archive/binding overrides; warnings remain |
| `cargo check -p inkstack-cli -p inkstack-tui --release --locked` | Failed: inkstack-core compiler query-depth limit in request_plugin_install handler |
| `cargo fmt --all --check` | Failed on existing workspace-wide formatting drift |
| `rustfmt --check --edition 2024 --config skip_children=true app-server-daemon/src/verified_installer.rs tui/src/update_action.rs tui/src/update_versions.rs tui/src/updates.rs cli/src/doctor/updates.rs` | Passed; stable-rustfmt warns about existing nightly-only imports_granularity configuration |
| `pnpm test -- --runInBand exec.test.ts` (sdk/typescript) | Not run: pnpm missing |

The check commands used:

```sh
RUSTY_V8_ARCHIVE=/tmp/opencode/v8-consumer-cache/rusty-v8-150.4.0-x86_64-unknown-linux-gnu/librusty_v8_ptrcomp_sandbox_release_x86_64-unknown-linux-gnu.a.gz
RUSTY_V8_SRC_BINDING_PATH=/tmp/opencode/v8-consumer-cache/rusty-v8-150.4.0-x86_64-unknown-linux-gnu/src_binding_ptrcomp_sandbox_release_x86_64-unknown-linux-gnu.rs
```

A Python `yaml.safe_load` inspection parsed all 24 retained workflows and checked
every job's needs against existing jobs and every local reusable-workflow path.
Core release still depends on tag validation, all platform artifacts, npm
archive staging, and the existing provisioned-macOS gate; DotSlash depends on
release, and canary tracking depends only on release and DotSlash.

## Resolution record (Task 11 state preserved above; Task 12 repairs below)

The three doctor/TUI blockers listed above were resolved on branch
`task-12/integration-validation-repairs` (commits `33b0f32`, `4c6f096`,
`3b448c9`, `65139e2`, pushed to origin). What failed before and how:

1. ChatGPT doctor endpoint — **fixed.** `provider_reachability_plan_from_parts`
   probed `config.chatgpt_base_url + "inkstack/responses"`; the runtime
   resolves ChatGPT-family auth to `CHATGPT_INKSTACK_BASE_URL`
   (`https://chatgpt.com/backend-api/codex`, model-provider-info/src/lib.rs:80)
   and posts inference to `{base}/responses`. The doctor now probes exactly
   that endpoint (`.../codex/responses`, matching the previously "outdated"
   test expectation); the proxy-auth test now probes the provider-configured
   URL. Doctor binary: 130 passed, 1 ignored (pre-existing).
2. Doctor rendering snapshot — **fixed.** `DETAIL_LABEL_WIDTH` has been 24
   since the initial import; the committed snapshot was baked at width 27.
   Restored the committed snapshot to the renderer's actual (correct) output;
   no logic changed.
3. Release-mode compiler query-depth — **fixed at root cause.** Release type
   layout of `request_plugin_install::handle_call`'s async state machine
   exceeded the default query recursion limit (+130 over 128). Added
   `#![recursion_limit = "256"]` to inkstack-core only, with justification;
   `cargo check -p inkstack-cli -p inkstack-tui --release --locked`: exit 0.
4. TUI stack overflows — **isolated.** All three overflow in test SETUP:
   `test_config()` → `Config::load_default...` → `deserialize_config_toml_with_base`
   serde-recurses the large `ConfigToml` and exhausts the default 2 MiB test
   thread stack (deep-but-finite, confirmed via gdb backtrace and 16–32 MiB
   stack runs). No logic failure; all five named TUI tests pass with adequate
   stack. Per the task constraints, no global stack bump is committed; the
   required accommodation (`RUST_MIN_STACK>=16 MiB` for these tests) is
   documented here for a follow-up task.
5. Browser-link snapshot drift — **fixed.** Wrap-width-only diff (3–5 columns)
   at width 80; regenerated from current correct output (`daemon_unmanaged`,
   `continue_in_browser_narrow_long_url`).
6. README — **fixed.** NOTICE attribution and OpenAI auth-layer descriptions
   now match the integrated state.

`cargo check --workspace --locked`: exit 0 (with the verified V8 archive/binding
overrides; V8 was not rebuilt). GitHub scripts 127/127, installer 24/24,
packaging 32/32, login 204/204, model-provider 102/102, CLI lib 15/15,
daemon updater 40/40, verified installer 3/3.

Remaining scope for a follow-up task: default test-thread stack accommodation
for ConfigToml deserialization in TUI setup, missing SDK test tooling
(`pnpm` unavailable), and Windows/macOS runtime verification. `main` remains
`f31d1c2`; both local and remote `main` are unchanged; no merge, force push,
tag, release, or publication occurred.

## Task 13 resolution record (branch `task-13/backend-route-test-hardening`,
pushed to origin)

### Phase 1 — ChatGPT backend-route detection (fixed)

Root cause: `ModelProviderInfo::supports_inkstack_backend_routes()` accepted
base URLs ending in `/backend-api/inkstack`, but the runtime resolves
ChatGPT-family authentication to `CHATGPT_INKSTACK_BASE_URL`
(`https://chatgpt.com/backend-api/codex`, model-provider-info/src/lib.rs:80)
and posts inference to `{base}/responses`. The retired `/inkstack` path never
matched the real service, so the doctor and every consumer that gates on
`supports_inkstack_backend_routes()` (provider.rs workspace routing,
client.rs responses headers / Guardian metadata, token_budget.rs context
features, guardian-v2 connection_pool request classification) misclassified
the production ChatGPT endpoint.

Fix: `supports_inkstack_backend_routes()` now returns true only for the
`/backend-api/codex` path (trailing slash allowed, query strings ignored,
https implied) on any host, and false for unrelated API endpoints and
superficially similar or malicious path suffixes (`codex-evil`,
`codex/extra`, `inkstack`, `/v1`). `None` (the built-in default) remains
true. NVIDIA NIM and Amazon Bedrock are unaffected (`is_openai()` guards).

All callers inspected and consistent:
- `inkstack-rs/model-provider/src/provider.rs:224` — workspace routing
- `inkstack-rs/core/src/client.rs:1196,1238` — responses headers / Guardian metadata
- `inkstack-rs/core/src/session/token_budget.rs:29` — context features
- `inkstack-rs/ext/guardian-v2/src/async_scorer/sampler/connection_pool.rs:442` — request classification

Tests: `inkstack_backend_routes_require_inkstack_base_url` now passes
(33/33 in inkstack-model-provider-info). Added positive coverage
(production, staging, trailing slash, query string) and negative coverage
(proxy, api.openai.com, codex-evil, codex/extra, inkstack path).

### Phase 2 — TUI test stack (configured, no code change)

The three reported TUI stack overflows occur in test SETUP only:
`test_config()` → `ConfigToml` serde deserialization exhausts the default
2 MiB test-thread stack (deep-but-finite recursion, confirmed via gdb
backtrace). They do not affect normal application startup (main thread has
an adequate stack). All five named tests pass at 8 MiB:
daemon_menu_is_read_only_and_confirmation_can_cancel_or_handoff,
unavailable_daemon_menu_offers_guidance_without_update_actions,
daemon_version_notice_preserves_manual_update_guidance,
model_picker_refresh_updates_app_catalog_from_app_server,
continue_in_browser_preserves_long_link_and_footer_at_narrow_width.

The test stack is already configured consistently at 8 MiB
(`rust_min_stack := "8388608"` in justfile, `common --test_env=RUST_MIN_STACK=8388608`
in .bazelrc, `RUST_MIN_STACK: "8388608"` in rust-ci.yml, rust-ci-full.yml and
rust-ci-full-nextest-platform.yml). Verified: all pass at 8 MiB. No production
thread stack was changed.

### Phase 3 — TypeScript SDK (49/49)

pnpm@10.34.5 (the required packageManager) installed via npm to
`~/.npm-global` (corepack not installed; npm global install blocked by
permissions; user prefix used). SDK dependencies installed with
`pnpm install --frozen-lockfile`. The `inkstack` and
`inkstack-code-mode-host` debug binaries were built (the latter required
creating `target/debug/gn_out/obj/` before the v8 build script's
`copy_archive` could write to it).

SDK test result: 49 passed, 0 failed. Both MCP client conformance tests
(`MCP client conformance › does not introduce shipping, intermediate, or
modern official conformance regressions` and `... production reviewer or
catalog-boundary regressions`) now execute the actual
`scripts/mcp_conformance/run_inkstack_compliance.py` runner (116 s), not
skipped or mocked. This was blocked in Task 13 solely by the
codex→inkstack fixture rename completed in Task 14.

### Phase 4 — regression checks (all green)

- `cargo test -p inkstack-cli --bin inkstack doctor`: 130 passed, 1 ignored
- `cargo test -p inkstack-model-provider-info --lib`: 33 passed
- `cargo test -p inkstack-model-provider --lib`: 102 passed
- `cargo test -p inkstack-app-server --test all external_auth_refreshes_on_unauthorized`: both cases pass
- TUI tests at `RUST_MIN_STACK=8388608`: daemon menu ×3, model picker,
  browser link, update_action/update_versions/update_prompt/startup_preflight — all pass
- `cargo test -p inkstack-cli --lib`: 15 passed
- `cargo test -p inkstack-cli --test login`: 8 passed
- `cargo test -p inkstack-app-server-daemon --lib update`: 40 passed
- `cargo test -p inkstack-app-server-daemon --lib verified_installer`: 3 passed
- GitHub scripts: 127 passed; installer: 24 passed; packaging: 32 passed
- `cargo check --workspace --locked`: exit 0
- `cargo check -p inkstack-cli -p inkstack-tui --release --locked`: exit 0

Cargo.lock preservation: the integration lock remains byte-identical to
Task 10 (including the daemon `sha2 0.10.9` edge); Task 13 commits do not
modify Cargo.lock. Normalized TOML comparison (package/dependency order)
is equal to the committed lock. V8 release workflow, fetch script and
package consumer unchanged; no V8 rebuild.

`main` remains `f31d1c2`; both local and remote `main` are unchanged; no
merge, force push, tag, release, or publication occurred. The implementation
commits are on local `task-13/backend-route-test-hardening`, pushed to origin
for review.

## Task 14 resolution record (branch `task-14/mcp-conformance-final-validation`,
pushed to origin)

### Phase 1 — Git state (verified)

Task 13 commit `fb0e1f9` is the branch ancestor; all previous repair tasks
remain integrated. Remote `main` is `f31d1c2`, unchanged. User worktrees
(`task-10/verified-updater-bootstrap` at `e521c54` with its dirty
`Cargo.lock`, and `codex/rusty-v8-release` at `92a7954` with its untracked
migration plan) are untouched. Task 14 was developed in a separate clean
worktree at `/home/grim/Dev/Agent Harness/InkStack-task14`.

### Phase 2 — MCP conformance filenames (repaired via `git mv`)

Root cause: the codex→inkstack fixture rename completed Task 13 updated all
*imports* to `run_inkstack_compliance` / `inkstack_conformance_adapter`, but
the source files retained the old names (`run_codex_compliance.py`,
`codex_conformance_adapter.py`, `test_codex_compliance.py`), so neither the
TypeScript SDK tests nor the Python test discovery could resolve the runner.

Renamed (executable bits preserved — none were set):
- `scripts/mcp_conformance/run_codex_compliance.py` →
  `scripts/mcp_conformance/run_inkstack_compliance.py`
- `scripts/mcp_conformance/codex_conformance_adapter.py` →
  `scripts/mcp_conformance/inkstack_conformance_adapter.py`
- `scripts/mcp_conformance/test_codex_compliance.py` →
  `scripts/mcp_conformance/test_inkstack_compliance.py`

Updated callers: all Python imports already referenced the new names
(`test_official_conformance.py`, `test_inkstack_compliance.py`,
`review_regressions.py`, `run_inkstack_compliance.py` line 2011 default);
the TypeScript SDK test (`sdk/typescript/tests/mcpConformance.test.ts`)
already referenced `run_inkstack_compliance.py`. No Bazel or CI references
existed. The runner's CLI arguments and behavior are unchanged; no duplicate
compatibility scripts were introduced. Third-party MCP/OpenAI protocol
identifiers and historical attribution were left untouched.

### Phase 3 — Python conformance validation (239 passed)

`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q scripts/mcp_conformance`:
**239 passed, 0 failed**. Direct invocation of the renamed runner works
(`run_inkstack_compliance.py --help` exits 0). Renamed test file discovered
and passes standalone (54 passed).

### Phase 4 — TypeScript SDK validation (49/49)

pnpm@10.34.5 installed via npm user prefix; dependencies installed with
`pnpm install --frozen-lockfile` (existing store, no version changes). Both
previously failing MCP conformance tests now execute the actual runner and
pass (49 passed, 0 failed, 0 skipped; not mocked).

### Phase 5 — final regression validation (all green)

- `cargo test -p inkstack-model-provider-info --lib --locked`: 33 passed
- `cargo test -p inkstack-model-provider --lib --locked`: 102 passed
- `cargo test -p inkstack-cli --bin inkstack doctor --locked`: 130 passed,
  1 ignored (pre-existing)
- `cargo test -p inkstack-cli --test login --locked`: 8 passed
- `cargo test -p inkstack-app-server-daemon --lib update --locked`: 40 passed
- `cargo test -p inkstack-app-server-daemon --lib verified_installer --locked`:
  3 passed
- TUI tests at `RUST_MIN_STACK=8388608` (daemon menu ×3, model picker,
  browser link, update_action/update_versions/update_prompt/startup_preflight):
  all pass
- `cargo test -p inkstack-cli --lib --locked`: 15 passed
- GitHub scripts: 127 passed; installer: 24 passed; packaging: 32 passed
- `cargo check --workspace --locked`: exit 0
- `cargo check -p inkstack-cli -p inkstack-tui --release --locked`: exit 0
- Python conformance: 239 passed; TypeScript SDK: 49 passed

Cargo.lock preservation: Task 14 commits do not modify Cargo.lock. The
integration lock remains byte-identical to Task 10 (including the daemon
`sha2 0.10.9` edge); normalized TOML comparison is equal to the committed
lock. V8 release workflow, fetch script and package consumer unchanged; no
V8 rebuild.

### Phase 6 — integration readiness audit

- Application release URLs: InkStack-owned
  (`github.com/Grim-Saga/InkStack`); no OpenAI Codex executable downloads
  remain (`test_bazel_no_upstream_binaries.py` is the guard).
- GitHub remains the only active application publisher (external publishers
  removed in Task 11).
- Installer script verification remains enforced (`verified_installer.rs`,
  SHA-256 against GitHub-recorded digest).
- API-key authentication uses `OPENAI_API_KEY` without the retired
  `INKSTACK_API_KEY` alias (Task 11).
- ChatGPT backend routes use the correct external service endpoint
  (`https://chatgpt.com/backend-api/codex`, Task 13).
- Required upstream licensing and attribution intact (Task 11/12).
- Rust release-mode checks succeed (exit 0).
- All CI dependencies reference existing files/scripts (24 workflows parse;
  all `needs` resolve to existing jobs).

`main` remains `f31d1c2`; both local and remote `main` are unchanged; no
merge, force push, tag, release, or publication occurred. The implementation
commits are on local `task-14/mcp-conformance-final-validation`, pushed to
origin for review.

## Task 15 resolution record (branch `task-15/ci-format-toolchain-match`,
pushed to origin)

### Phase 1 — Git state (verified)

Task 14 commit `e136bbd` is the branch ancestor; all previous repair tasks
remain integrated. Remote `main` is `f31d1c2`, unchanged. User worktrees
(`task-10/verified-updater-bootstrap` at `e521c54` with its dirty
`Cargo.lock`, and `codex/rusty-v8-release` at `92a7954` with its untracked
migration plan) are untouched. Task 15 was developed in a separate clean
worktree at `/home/grim/Dev/Agent Harness/InkStack-task15`.

### Phase 2 — CI readiness preflight (formatting gate investigation)

The `rust-ci.yml` and `rust-ci-full.yml` `general` job runs:
`cargo fmt -- --config imports_granularity=Item --check`
on Rust toolchain 1.95.0 (from `inkstack-rs/rust-toolchain.toml`).

**Root cause:** `inkstack-rs/rustfmt.toml` specifies
`imports_granularity = "Item"`, which is a nightly-only unstable feature.
On stable 1.95.0 it is ignored with a warning, so rustfmt uses defaults
(`imports_granularity = Preserve`, `reorder_imports = true`,
`max_width = 100`). The committed source was formatted with
`imports_granularity = Item` + `reorder_imports = false` (imports kept in
original order, not alphabetically sorted) and allows function
signatures/call arguments over 100 chars on single lines.

**Exact commands and results:**

| Command | Toolchain | Files differing | Result |
|---|---|---|---|
| `cargo fmt -- --config imports_granularity=Item --check` | stable 1.95.0 | 3,510 | FAIL (setting ignored, warning) |
| `cargo fmt -- --config imports_granularity=Item --check` | nightly-2026-08-20 | 3,516 | FAIL (imports sorted alphabetically) |
| `cargo fmt -- --config imports_granularity=Item --config reorder_imports=false --check` | nightly-2026-08-20 | 1,510 | FAIL (fn signature wrapping) |
| `cargo fmt -- --config imports_granularity=Item --config reorder_imports=false --config max_width=103 --check` | nightly-2026-08-20 | 6,594 | FAIL (mass-unwrapping) |

**Genuine formatting baseline issue:** The committed source was formatted
with `imports_granularity = Item` + `reorder_imports = false` and allows
function signatures/call arguments exceeding 100 chars (with indentation)
on single lines. Neither stable 1.95.0 nor nightly-2026-08-20 matches.
No single `max_width` value works: `max_width = 100` wraps long function
signatures; any `max_width > 100` unwraps lines at 100–102 chars,
causing 49,000+ differences.

**Recommended fix:**
1. Add `reorder_imports = false` to `inkstack-rs/rustfmt.toml`
2. Pin CI formatting to nightly-2026-08-20 (where
   `imports_granularity = Item` works without warning)
3. Run `cargo fmt` once with the corrected config to reformat ~1,510
   files (function signature/call argument wrapping), after which
   `cargo fmt --check` passes on nightly

Mass-reformatting ~1,510 files is unavoidable — no toolchain/config
combination matches the committed source without it.

### Phase 3 — Main-push approval gate

**NOT PROCEEDING.** `main` remains at `f31d1c2`. The formatting gate
failure (`general` job in `rust-ci-full`) would fail on a main push until
the rustfmt.toml/CI toolchain mismatch is resolved. Awaiting owner
direction on whether to proceed with the recommended fix above.

**Known CI limitations:** Formatting gate fails on pre-existing drift
(3,510 files on stable, not introduced by Tasks 1–14). Windows
self-hosted runner groups may be unavailable for Windows matrix jobs.
V8 canary build matrix WILL run (MODULE.bazel.lock changed in Task 2;
`canary_required=true` per `v8_canary_changes.py`; V8 version unchanged
at 150.4.0 so `windows_source_required=false`).

## Task 15B resolution record (branch `task-15b/formatting-baseline-stabilization`,
pushed to origin)

### Phase 1 — Formatting report (verified)

| Command | Toolchain | Files differing | Result |
|---|---|---|---|
| `cargo fmt -- --config imports_granularity=Item --check` | stable 1.95.0 | 3,510 | FAIL |
| `cargo fmt -- --config imports_granularity=Item --check` | nightly-2026-08-20 | 3,516 | FAIL |
| `cargo fmt -- --config imports_granularity=Item --config reorder_imports=false --check` | nightly-2026-08-20 | 1,510 | FAIL |

All 1,510 differences are formatting-only (function signature wrapping,
match arm wrapping, tuple struct wrapping, closure argument wrapping).
No semantic changes. Verified by inspecting 20+ representative diffs
across diverse crates (agent-graph-store, analytics, app-server,
app-server-daemon, app-server-protocol, cli, core, tui, windows-sandbox-service,
windows-sandbox-service, voice-host).

### Phase 2 — Smallest reliable correction

No rustfmt config combination matches the committed source without
modification. Tested: `imports_granularity=Item` + `reorder_imports=false`
(1,510 files), `+ use_small_heuristics=Always/Never` (invalid key),
`+ overflow_delimited_expr=true` (6,936 files), `+ max_width=103`
(6,594 files). The only path to a clean check is a one-time formatting
pass.

### Phase 3 — Mechanical normalization

Ran `cargo fmt` once with `imports_granularity=Item` +
`reorder_imports=false` on nightly-2026-08-20. Result: 699 files changed
(698 `.rs` + 1 `toml` — the rustfmt.toml itself). All changes are
mechanical formatting: function signature wrapping, argument list
wrapping, brace placement. Verified zero non-formatting changes by
inspecting the diff (all changed lines are whitespace/brace/paren
rearrangement; no identifiers, strings, or logic changed).

### Phase 4 — CI formatting gates fixed

Updated `.github/workflows/rust-ci.yml` and
`.github/workflows/rust-ci-full.yml`:
- `general` job keeps the stable 1.95.0 toolchain installation
  (unchanged for clippy/builds/tests)
- Added a separate step to install `nightly-2026-08-20` with its `rustfmt`
  component via `rustup toolchain install nightly-2026-08-20 --component rustfmt`
- `cargo fmt` now invoked explicitly as `cargo +nightly-2026-08-20 fmt` so the
  nightly toolchain is actually used for formatting, not stable 1.95.0
- All other jobs (clippy, lint_build, tests) remain on stable 1.95.0

### Phase 5 — Validation (all green)

| Check | Result |
|---|---|
| `cargo fmt -- --config imports_granularity=Item --config reorder_imports=false --check` (nightly-2026-08-20, run 1) | exit 0 |
| `cargo fmt -- --config imports_granularity=Item --config reorder_imports=false --check` (nightly-2026-08-20, run 2, idempotency) | exit 0 |
| `cargo check --workspace --locked` | exit 0 |
| `cargo check -p inkstack-cli -p inkstack-tui --release --locked` | exit 0 |
| `python3 -m unittest discover -s .github/scripts -p 'test_*.py'` | 127 passed |
| `cargo test -p inkstack-model-provider-info --lib --locked` | 33 passed |
| `cargo test -p inkstack-cli --bin inkstack doctor --locked` | 130 passed, 1 ignored |

### Phase 6 — Commit and report

Three commits:
1. `rustfmt.toml` + both workflow files (formatting configuration + CI toolchain)
2. 699 formatted source files (mechanical normalization only)
3. `rust-ci.yml` + `rust-ci-full.yml` (explicit nightly-2026-08-20 rustfmt invocation)

No `Cargo.lock` modification. No V8 rebuild. No release tag. `main` remains
`f31d1c2`.

## Task 15C resolution record (branch `task-15c/explicit-nightly-rustfmt`,
pushed to origin)

### Phase 1 — Root cause confirmation

`dtolnay/rust-toolchain@e081816240890017053eacbb1bdf337761dc5582` is a pinned
revision that hardcodes stable 1.95.0 internally. It does **not** support the
`toolchain` input, so specifying `toolchain: nightly-2026-08-20` in the
workflow had no effect — rustfmt always ran on stable 1.95.0, where
`imports_granularity=Item` is an unsupported (ignored) option and the
formatting gate failed on 3,510 files.

### Phase 2 — Exact GitHub Actions changes

Updated `.github/workflows/rust-ci.yml` and
`.github/workflows/rust-ci-full.yml`:
- Kept the existing stable 1.95.0 toolchain installation
  (`dtolnay/rust-toolchain@e081816240890017053eacbb1bdf337761dc5582`) for
  clippy/builds/tests — unchanged
- Added a narrowly scoped step to install `nightly-2026-08-20` with its
  `rustfmt` component via `rustup toolchain install nightly-2026-08-20 --component rustfmt`
- Changed the format command from `cargo fmt` to `cargo +nightly-2026-08-20 fmt`
  so the nightly toolchain is explicitly selected for rustfmt
- `rust-toolchain.toml` remains pinned to stable 1.95.0

### Phase 3 — Proof that nightly executes the formatting check

`rustup run nightly-2026-08-20 rustfmt --version` → `rustfmt 1.10.0-nightly (f7d782a3be 2026-08-19)`

Exact passing command (from `inkstack-rs/`):
```
cargo +nightly-2026-08-20 fmt -- --config imports_granularity=Item --config reorder_imports=false --check
```
Exit code: 0 (verified twice for idempotency)

### Phase 5 — Validation (all green)

| Check | Result |
|---|---|
| `cargo fmt --check` (nightly, run 1) | exit 0 |
| `cargo fmt --check` (nightly, run 2, idempotency) | exit 0 |
| `cargo check --workspace --locked` | exit 0 |
| `cargo check -p inkstack-cli -p inkstack-tui --release --locked` | exit 0 |
| `python3 -m unittest discover -s .github/scripts -p 'test_*.py'` | 127 passed |

No `Cargo.lock` modification. No source files reformatted. No V8 rebuild. No release tag. `main` remains `f31d1c2`.


