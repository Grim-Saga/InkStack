import path from "node:path";

export function inkstackPathOverride() {
  return (
    process.env.INKSTACK_EXECUTABLE ??
    path.join(process.cwd(), "..", "..", "inkstack-rs", "target", "debug", "inkstack")
  );
}
