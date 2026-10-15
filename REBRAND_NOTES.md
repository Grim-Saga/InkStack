# InkStack rebrand notes

InkStack is a fork of [openai/codex](https://github.com/openai/codex) (Apache-2.0).
This file documents what the rebrand changed, what it deliberately left alone,
and what still needs a human decision.

## Renamed (product surface)

- Binary `codex` -> `inkstack` (`inkstack-rs/cli`, `[[bin]] name`)
- All Rust crates `codex-*` -> `inkstack-*` (160 packages), lib targets
  `codex_*` -> `inkstack_*`, `use` paths updated throughout
- Directories: `codex-rs/` -> `inkstack-rs/`, `codex-cli/` -> `inkstack-cli/`,
  `codex-home` etc. -> `inkstack-*`, `sdk/python/src/openai_codex` -> `sdk/python/src/inkstack`
- Config home `~/.codex` -> `~/.inkstack`, env `CODEX_HOME` -> `INKSTACK_HOME`
- Env vars `CODEX_*` -> `INKSTACK_*` (incl. `CODEX_API_KEY` -> `INKSTACK_API_KEY`;
  note `OPENAI_API_KEY` is still honored as a fallback)
- npm `@openai/codex` -> `inkstack` (bin `inkstack`), TS SDK -> `inkstack-sdk`,
  Python SDK `openai-codex` -> `inkstack` (class `Codex` -> `InkStack`)
- macOS bundle id `com.openai.codex` -> `com.inkstack.inkstack` (change to your
  own reverse-DNS when you have one)
- Plugin manifest dir `.codex-plugin` -> `.inkstack-plugin`
- Insta snapshot files `codex_*__*.snap` -> `inkstack_*__*.snap`
- README rewritten with fork attribution; upstream end-of-support announcement
  removed from `announcement_tip.toml`
- Lockfiles updated: `Cargo.lock`, `pnpm-lock.yaml`

## Deliberately kept (OpenAI service references)

These are functional identifiers for OpenAI's services. Renaming them would
break auth, model calls, or builds:

- Auth layer untouched: ChatGPT sign-in flow, OAuth client IDs
  (`codex_chatgpt_*`), token URLs, `OPENAI_API_KEY`, keyring storage logic
- Model IDs: `gpt-5.x-codex*`, `gpt-live-1-codex`, etc.
- Protocol strings: `x-codex-*` headers, `codex_app`/`codex_apps` MCP namespaces,
  `codex-curated` marketplace, `codex_turn_event` analytics, `codex_tui` /
  `codex_app` product client IDs, `<codex_delegation>` tags
- `openai_models` module (it models OpenAI's API types), `openai` provider ID
- Functional URLs: `api.openai.com`, `chatgpt.com/*`, `releases.openai.com`,
  `openai-oss-forks` cargo git patches (build breaks without them)
- `LICENSE`, `NOTICE` preserved unmodified; `CHANGELOG.md` kept as history
- `third_party/` and `vendor/` excluded entirely

## Repo wiring (done 2026-10-15)

The InkStack repo is https://github.com/Grim-Saga/InkStack. Wired in:

- `repository.url` in `inkstack-cli/package.json`,
  `sdk/typescript/package.json`, `inkstack-rs/responses-api-proxy/npm/package.json`
- `project.urls` in both Python `pyproject.toml` files
- `REPO_URL` build metadata in `.bazelrc`
- Clone URL in `docs/install.md`; doc links in `sdk/python/README.md`,
  `sdk/python/docs/getting-started.md`, `inkstack-rs/config.md`
- Issue templates (discussions link, contributing link, npm package link)
- Self-updater endpoints now point at the InkStack repo:
  `api.github.com/repos/Grim-Saga/InkStack/releases/latest` (both TUI and
  `doctor`), npm registry `https://registry.npmjs.org/inkstack`, and the
  user-facing "Update available!" notices link to the InkStack repo/releases

## TODO for the human

- [ ] Cut InkStack releases: until the repo has releases, the updater will
      find nothing (graceful 404) and `npm install -g inkstack` won't resolve
- [ ] The *installer* (`scripts/install/install.sh`, `install.ps1`) still
      downloads from `releases.openai.com/codex` with a GitHub fallback to
      `openai/codex` releases; repoint at InkStack's own release artifacts
      once they exist
- [ ] The Homebrew cask check still queries `formulae.brew.sh/api/cask/codex.json`;
      only matters if you ship an `inkstack` cask
- [ ] `.github/workflows/cla.yml` now points at your repo's `docs/CLA.md`,
      and the CLA text has been rewritten as an InkStack draft (license grant
      to Grim-Saga instead of OpenAI, Inc.; upstream California governing-law
      clause dropped). Review the draft before merging outside contributions;
      alternatively drop the CLA workflow or switch to DCO for lighter terms
- [ ] Regenerate `sdk/python/uv.lock`, `sdk/python-runtime/uv.lock`,
      `scripts/uv.lock` with `uv lock` (they still pin upstream artifacts)
- [ ] `third_party/voice` packaging scripts still produce `codex` packages;
      rebrand when you cut InkStack releases
- [ ] No Rust toolchain was available in this environment, so this rebrand is
      verified by static consistency checks only (all crate/dep/bin/lib
      references resolve, no stray product branding). Run `cargo check` /
      `cargo test` locally before trusting it fully.

## Follow-up fixes (2026-10-15)

A background audit found the rebrand had renamed import specifiers and
package declarations but missed renaming six files/directories, leaving
broken references. Fixed by renaming, no content changes:

- `sdk/typescript/src/codex.ts` -> `sdk/typescript/src/inkstack.ts`
  (imported as `./inkstack` by `src/index.ts`)
- `sdk/typescript/src/codexOptions.ts` -> `sdk/typescript/src/inkstackOptions.ts`
  (imported as `./inkstackOptions` by `index.ts`, `inkstack.ts`, `exec.ts`,
  `thread.ts`)
- `sdk/typescript/tests/codexExecSpy.ts` -> `tests/inkstackExecSpy.ts`
  (imported as `./inkstackExecSpy` by `run.test.ts`)
- `sdk/typescript/tests/testCodex.ts` -> `tests/testInkStack.ts`
  (imported as `./testInkStack` by `abort/run/runStreamed.test.ts`)
- `sdk/typescript/tests/setupCodexHome.ts` -> `tests/setupInkStackHome.ts`
  (referenced by `jest.config.cjs` `setupFilesAfterEach`)
- `sdk/python-runtime/src/codex_cli_bin/` -> `src/inkstack_cli_bin/`
  (declared as `src/inkstack_cli_bin` in `pyproject.toml` wheel config)

Verified after the fix: every relative import in `sdk/typescript/src` and
`tests` resolves, the jest setup file exists, and the python-runtime wheel
package directory matches its `pyproject.toml`.
