# Config JSON Schema

We generate a JSON Schema for `~/.inkstack/config.toml` from the `ConfigToml` type
and commit it at `inkstack-rs/core/config.schema.json` for editor integration.

When you change any fields included in `ConfigToml` (or nested config types),
regenerate the schema:

```
just write-config-schema
```
