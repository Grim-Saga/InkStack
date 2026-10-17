# Authentication

InkStack supports two ways to authenticate with OpenAI models:

- **Sign in with ChatGPT** — select **Sign in with ChatGPT** in the TUI to use your
  ChatGPT Plus, Pro, Business, Edu, or Enterprise plan. Credentials are stored after
  login and refreshed automatically.
- **OpenAI API key** — set the `OPENAI_API_KEY` environment variable, or pass a key
  explicitly with `inkstack login --with-api-key` (the command reads the key from
  stdin, e.g. `printenv OPENAI_API_KEY | inkstack login --with-api-key`).
  Environment-key authentication is enabled for `inkstack exec`; for the
  interactive TUI, sign in explicitly to save the key. The onboarding form can
  prefill it from `OPENAI_API_KEY`.

InkStack is an agentic harness, not an AI model provider: it does not issue its own
API keys, and no `INKSTACK_API_KEY` variable is recognized.

Other model providers (for example NVIDIA NIM or Amazon Bedrock) use their own
provider-specific credentials; see each provider's documentation for the
environment variables it expects.
