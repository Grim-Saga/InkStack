export type InkStackConfigValue = string | number | boolean | InkStackConfigValue[] | InkStackConfigObject;

export type InkStackConfigObject = { [key: string]: InkStackConfigValue };

export type InkStackOptions = {
  inkstackPathOverride?: string;
  baseUrl?: string;
  apiKey?: string;
  /**
   * Additional `--config key=value` overrides to pass to the InkStack CLI.
   *
   * Provide a JSON object and the SDK will flatten it into dotted paths and
   * serialize values as TOML literals so they are compatible with the CLI's
   * `--config` parsing.
   */
  config?: InkStackConfigObject;
  /**
   * Raw `--config key=value` overrides to pass unchanged to the InkStack CLI after
   * structured configuration and before SDK-managed or thread-specific overrides.
   */
  configOverrides?: string[];
  /**
   * Environment variables passed to the InkStack CLI process. When provided, the SDK
   * will not inherit variables from `process.env`.
   */
  env?: Record<string, string>;
};
