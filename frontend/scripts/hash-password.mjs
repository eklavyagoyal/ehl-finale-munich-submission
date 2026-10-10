// Prints a PARALLAX_WEB_USERS entry with a scrypt-hashed password, so no plain password sits in env.
// Usage: node scripts/hash-password.mjs <name>   (the password is read from stdin, not from argv)
import { randomBytes, scryptSync } from "node:crypto";
import { createInterface } from "node:readline";

const name = (process.argv[2] ?? "").trim().toLowerCase();
if (!/^[a-z0-9][a-z0-9_-]{0,31}$/.test(name)) {
  console.error("Usage: node scripts/hash-password.mjs <name>   (lowercase letters, digits, - or _)");
  process.exit(1);
}

const rl = createInterface({ input: process.stdin, output: process.stderr });
rl.question(`Password for ${name}: `, (password) => {
  rl.close();
  if (!password) {
    console.error("Empty password.");
    process.exit(1);
  }
  const salt = randomBytes(16);
  const hash = scryptSync(password, salt, 32);
  console.log(`${name}:scrypt:${salt.toString("hex")}:${hash.toString("hex")}`);
});
