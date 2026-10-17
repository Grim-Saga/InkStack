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
