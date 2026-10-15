import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { afterEach, beforeEach } from "@jest/globals";

const originalInkStackHome = process.env.INKSTACK_HOME;
let currentInkStackHome: string | undefined;

beforeEach(async () => {
  currentInkStackHome = await fs.mkdtemp(path.join(os.tmpdir(), "inkstack-sdk-test-"));
  process.env.INKSTACK_HOME = currentInkStackHome;
});

afterEach(async () => {
  const inkstackHomeToDelete = currentInkStackHome;
  currentInkStackHome = undefined;

  if (originalInkStackHome === undefined) {
    delete process.env.INKSTACK_HOME;
  } else {
    process.env.INKSTACK_HOME = originalInkStackHome;
  }

  if (inkstackHomeToDelete) {
    await fs.rm(inkstackHomeToDelete, { recursive: true, force: true });
  }
});
