# Task 16A — Foundational CI repairs

Base: `7bc23ac72d0d14ba8a56c007cc8c61633b6ac494`, verified against GitHub main
before work started. Work was isolated on `task-16a/ci-foundation-repairs`.
Only audit findings R1, R4, R5, and R8 are addressed here.

## Changes and commit boundaries

| Finding | Commit | Correction |
|---|---|---|
| R1 | `a9e0de9` | Grant `contents: read` and `actions: read` on the postmerge V8 reusable call only. Other postmerge jobs retain their inherited defaults. |
| R4 | `8ff6718` | Canonicalize Cargo.lock package/dependency ordering and pass `--locked` in the shared benchmark recipe. |
| R5 | `1bd9db0` | Exempt only the exact deny-probe declaration in the named CLI policy test; add adversarial scanner tests. |
| R8 | `87abf14` | Rename the existing manifest to the filename already required by Cargo and Bazel, with no byte changes. Add source/manifest consistency checks. |
| R5 review hardening | `3776b26` | Ignore Rust comments and literals when identifying the test scope; match balanced code braces and reject declarations inside comments/literals. |

The additional R5 commit addresses an important finding from a fresh read-only
review. Keeping that fix separate preserves the earlier commit boundaries.
No dependency upgrades or application Rust implementation changes are included.

## Permission validation

GitHub rejected the original run before any jobs existed because the nested V8
build requested `actions: read`, while its caller allowed `actions: none`.
The caller now explicitly permits the child's required read-only scopes.
The grant is job-specific: neither the workflow root nor the sibling
`rust-ci-full`/results jobs acquire a new permission mapping.

- The new regression failed before the grant and passes afterward (2 tests).
- All 24 workflow YAML files parse; local reusable paths and job `needs` resolve.
- Semantic caller/callee inspection confirms all explicit V8 child requests fit
  the caller's grant, including `contents: read` for Windows source jobs.
- actionlint 1.7.12 passes the changed postmerge workflow and V8 callee.
- Full actionlint reports the same four diagnostics on the base and this branch:
  three object-valued `runs-on` expressions in rust-release-windows.yml and
  `queue` under concurrency in rust-release.yml. These unrelated diagnostics
  were not repaired here.

These are local contract and syntax checks, not proof of GitHub's live workflow
acceptance. Postmerge is triggered only by main pushes. No main push, temporary
workflow, dispatch, or V8 build was used to obtain scheduler validation. That
validation remains for an authorized integration run.

## Cargo.lock serialization proof

Pinned Cargo 1.95.0 reproduced the audited canonical bytes using the benchmark
unit graph, before any compilation. `RUSTC_BOOTSTRAP=1` was used only to expose
Cargo's diagnostic `-Z unstable-options --unit-graph`; it is not committed or
used for CI compilation. Actual benchmark runs use stable Cargo normally.

| Property | Result |
|---|---|
| Packages compared | 1,466 |
| Committed input SHA-256 | `0413a2dbfdb35784405d00123308265472ba02b009420a9092646372eb5d3c71` |
| Canonical SHA-256 | `63f34b3a72a8314b22b45472cd0ada594875d50db92ddafe3d5beedfb6363277` |
| Package identities, versions, sources, checksums, dependency edges | Equal |
| Additional TOML metadata | Equal |
| Two consecutive locked benchmark runs | Passed; hash unchanged after each |

The canonical hash also matches the user's preserved modified lockfile; that
file was read for verification and was never written by this task.
The benchmark change retains the clean-worktree guard unchanged.

The comparison normalizes only package order and dependency order. Every other
value is compared, so dependency upgrades cannot pass as serialization changes:

```python
import pathlib
import subprocess
import tomllib

base = subprocess.check_output([
    "git", "show",
    "7bc23ac72d0d14ba8a56c007cc8c61633b6ac494:inkstack-rs/Cargo.lock",
])
current = pathlib.Path("inkstack-rs/Cargo.lock").read_bytes()

def normalized(raw):
    doc = tomllib.loads(raw.decode())
    for package in doc["package"]:
        if "dependencies" in package:
            package["dependencies"].sort()
    doc["package"].sort(key=lambda p: (p["name"], p["version"], p.get("source", "")))
    return doc

assert normalized(base) == normalized(current)
```

## Updater scanner boundaries

The original 127-test GitHub-script suite failed only because rustfmt moved
`releases.openai.com` below the declaration marker. The earlier same-line
exception also accepted forbidden URLs next to marker comments.

The scanner now recognizes only the exact three-host literal declaration in
`cli/src/main.rs`, in the named application-network-policy test inside the
`cfg(test)` module. It accepts single-line, wrapped, and expanded arrays, but
exempts only that declaration's character span. It scans all remaining text.
It is deliberately a narrow source guard, not a general Rust parser: altered
hosts/types/expressions or unsupported syntax fail closed.

Adversarial coverage rejects all four forbidden distribution URL families in
production, marker-comment bypasses, same-line trailing URLs, URLs before and
after the fixture, production declarations with the same name, changed
initializers, wrong files/functions, absent test configuration, and malformed
initializers. The fresh reviewer additionally demonstrated forged scope
headers in a block comment. Seven failing subcases were reproduced before the
lexical fix; block comments, nested comments, raw strings, and declaration
decoys are now rejected. Positive coverage retains real scopes containing
comments, escaped strings, character literals, raw strings, and lifetimes.

The final focused updater suite passes 20 tests. The actual CLI network-denial
assertions and verified installer implementation, including SHA-256 checking,
remain byte-identical to the base.

## Windows manifest and resource contract

The tracked manifest still had its old filename while BUILD.bazel and build.rs
already requested `inkstack-windows-sandbox-setup.manifest`. A `git mv` repairs
that mismatch without changing those linker definitions or the manifest data.

- Both new manifest consistency/security tests failed on the missing file
  before the rename and pass afterward.
- Original and renamed bytes match exactly, SHA-256
  `14b210c3cc998be496d7511a8900321cdf603a1510cf4423b25648023085b7cb`.
- XML retains `requestedExecutionLevel level="asInvoker" uiAccess="false"`.
- Compiled build.rs was invoked with MSVC and GNU LLVM target metadata; emitted
  arguments still target the setup binary only and request manifest embedding
  with the expected manifest path.
- Bazel 9.2.0 focused `--nobuild` analysis and an actual resource-target build
  both passed with `--lockfile_mode=error`.
- The actual Bazel `.res` output was decoded: numeric `RT_MANIFEST` type 24,
  resource ID 1, and a payload identical to the original manifest. Independent
  system llvm-rc compilation produced the same verified resource contract.

No Windows executable was linked or run. Native Windows verification, including
`setup_helper_embeds_as_invoker_manifest`, remains necessary on an available
Windows runner. No helper or Windows check was disabled.

## Local validation

| Check | Result |
|---|---|
| GitHub scripts, baseline | 127 tests; one expected updater scanner failure |
| GitHub scripts, final | 148 passed |
| Focused updater scanner/integration guards | 20 passed |
| Postmerge permission regressions | 2 passed |
| Windows manifest regressions | 2 passed |
| Standalone installer tests | 24 passed |
| Package builder tests | 32 passed |
| `just bench-smoke`, twice, Cargo 1.95.0 | Both passed; four image cases each; lockfile stable |
| `cargo +1.95.0 check -p inkstack-utils-image --locked --offline` | Passed |
| Nightly-2026-08-20 workspace Rust formatting check | Passed |
| Ruff 0.15.13 lint and formatting for the four changed Python files | Passed |
| All workflow YAML files/local call graph | Passed |
| Changed caller and V8 callee actionlint | Passed |
| Full actionlint versus base | Same four inherited diagnostics noted above |
| Focused Bazel resource analysis/build and binary resource checks | Passed |
| Cargo.lock normalized graph comparison | Equal, 1,466 packages |
| Attribution and security implementation preservation | LICENSE, NOTICE, CLI and verified installer bytes unchanged |
| Diff whitespace check | Passed |

Representative commands, from repository root unless noted:

```sh
python3 -B -m unittest discover -s .github/scripts -p 'test_*.py'
python3 -B -m unittest discover -s scripts/install -p 'test_*.py'
INKSTACK_REPO_ROOT="$PWD" python3 -B -m unittest discover -s scripts/inkstack_package -p 'test_*.py'
RUSTUP_TOOLCHAIN=1.95.0 just bench-smoke
cargo +1.95.0 check --manifest-path inkstack-rs/Cargo.toml -p inkstack-utils-image --locked --offline
# From inkstack-rs:
cargo +nightly-2026-08-20 fmt -- --config imports_granularity=Item --config reorder_imports=false --check
# With Bazel output paths directed outside the repository:
bazel build --lockfile_mode=error //inkstack-rs/windows-sandbox-rs:inkstack-windows-sandbox-setup-manifest-resource
```

Build outputs and logs were kept outside user worktrees. No V8 compilation,
full Bazel matrix, whole-workspace application build, or whole Rust runtime
suite was performed. Rust daemon updater runtime tests were not rerun; the
relevant shell installer/package suites, source guards, and byte-preservation
checks above cover the unchanged runtime paths within this task's scope.

## Remaining gates and preservation

The other audited failures remain out of scope: runner availability and billing,
Python locks/default runtime distribution, broad Ruff drift, musl execution
platforms, Cargo-deny advisories, cargo-shear, stale lint-package expectations,
missing argument comments, spelling, and Linux lint duration. They prevent a
claim that the full CI matrix or release process is green.

All ten pre-existing worktrees, their heads, dirty files, and untracked files
were preserved. Historical branches are retained. Authentication, ChatGPT
backend routes, GitHub-only distribution, release infrastructure, upstream
attribution, installer SHA-256 verification, and the CI clean-worktree guard
remain intact. No repository settings, runner configuration, tags, releases,
main updates, or external publishers were changed.

Only the requested task branch is to be pushed, without force. Integration
must wait for independent review and a separate authorization.
