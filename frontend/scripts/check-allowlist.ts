// Fails if the UI calls an API path that the /bff allowlist would refuse.
// Run: npm run check:allowlist   (Node strips the types itself)
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { isAllowed } from "../src/lib/api/allowlist.ts";

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : /\.tsx?$/.test(name) ? [path] : [];
  });
}

const calls = new Set<string>();
for (const file of files(fileURLToPath(new URL("../src", import.meta.url)))) {
  for (const match of readFileSync(file, "utf8").matchAll(/api\.(GET|POST|PATCH|PUT|DELETE)\("\/api\/([^"]+)"/g)) {
    calls.add(`${match[1]} ${match[2]}`);
  }
}

let failed = 0;
for (const call of [...calls].sort()) {
  const [method, path] = call.split(" ");
  const segments = path.split("/").map((s) => (s.startsWith("{") ? "x" : s));
  const ok = isAllowed(method, segments);
  if (!ok) failed++;
  console.log(`${ok ? "ok     " : "BLOCKED"} ${call}`);
}
if (failed) {
  console.error(`${failed} call(s) are not in src/lib/api/allowlist.ts`);
  process.exit(1);
}
