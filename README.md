# InkStack

**InkStack** is a terminal coding agent, a community fork of [OpenAI's Codex CLI](https://github.com/openai/codex), rebranded for independent experimentation and extension.

> **Attribution:** InkStack is derived from [openai/codex](https://github.com/openai/codex), which is &copy; OpenAI and licensed under the [Apache License 2.0](LICENSE). The original `NOTICE` file is preserved unmodified, and no claim is made over OpenAI's technology. InkStack is an independent, non-commercial open-source project and is not affiliated with or endorsed by OpenAI.

## What this is

Everything Codex CLI does, under a new name: the full agentic coding loop, the terminal UI, sandboxing, MCP support, skills, the app server, and the SDKs. The rebrand covers the product surface (binary name, config directory, environment variables, user-facing strings, docs). The model and auth layer is intentionally untouched.

## Quickstart

### Build from source

You need a Rust toolchain (see `inkstack-rs/rust-toolchain.toml`):

```shell
cargo build --release --manifest-path inkstack-rs/Cargo.toml --bin inkstack
```

The binary is `inkstack`. Run it to get started.

### Model access

Run `inkstack` and select **Sign in with ChatGPT** to use your ChatGPT Plus, Pro, Business, Edu, or Enterprise plan. To use OpenAI API-key authentication instead, set `OPENAI_API_KEY`. InkStack does not issue its own API keys. Users of other model providers should configure their provider's own credentials. See [docs/authentication.md](./docs/authentication.md).

### Config

InkStack keeps its state in `~/.inkstack` (override with `INKSTACK_HOME`). See [docs/config.md](./docs/config.md).

## Docs

- [Getting started](./docs/getting-started.md)
- [Authentication](./docs/authentication.md)
- [Config reference](./docs/config.md)
- [Contributing](./docs/contributing.md)
- [Installing & building](./docs/install.md)

Much of the [upstream Codex documentation](https://developers.openai.com/codex) still applies, since the underlying engine is unchanged.

## License

Licensed under the [Apache License 2.0](LICENSE). See also [NOTICE](NOTICE) for upstream attribution.
