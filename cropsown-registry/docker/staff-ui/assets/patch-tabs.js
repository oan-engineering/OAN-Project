#!/usr/bin/env node
/*
 * Show every register tab.
 *
 * The portal renders only the first five tabs and pushes the rest into a "More"
 * dropdown:
 *
 *     k = S.slice(0, 5), A = S.slice(5)        // S = the tab list
 *
 * The crop sown register has six tabs, so Crop Production ended up hidden. The
 * limit is compiled into the bundle, so it is rewritten here. The surrounding
 * code already handles an empty overflow list, so the "More" button simply
 * stops rendering once nothing spills over.
 *
 * Exits non-zero if the expression is not found in at least two bundles, so a
 * base-image change fails the build instead of silently reverting to five tabs.
 */
const fs = require("fs");
const path = require("path");

const ROOT = "/app/.next";
const LIMIT = 20;
// name = list.slice(0,5), other = list.slice(5)
const PATTERN = /([A-Za-z_$][\w$]*)=([A-Za-z_$][\w$]*)\.slice\(0,5\),([A-Za-z_$][\w$]*)=\2\.slice\(5\)/g;

function* walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(full);
    else if (entry.name.endsWith(".js")) yield full;
  }
}

let patched = 0;
for (const file of walk(ROOT)) {
  const before = fs.readFileSync(file, "utf8");
  if (!before.includes(".slice(0,5)")) continue;
  const after = before.replace(
    PATTERN,
    (_m, a, list, b) => `${a}=${list}.slice(0,${LIMIT}),${b}=${list}.slice(${LIMIT})`
  );
  if (after !== before) {
    fs.writeFileSync(file, after);
    patched += 1;
    console.log("  patched " + file.replace(ROOT + "/", ""));
  }
}

if (patched < 2) {
  console.error(
    `tab-limit patch matched ${patched} bundle(s), expected at least 2 — ` +
      "the base image layout changed, so tabs would silently fall back to five"
  );
  process.exit(1);
}
console.log(`raised the visible tab limit to ${LIMIT} in ${patched} bundle(s)`);
