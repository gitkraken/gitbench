#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptDir, "..");
const templatePath = join(scriptDir, "og-card-template.html");
const manifestPath = join(scriptDir, "og-cards.json");
const outputDir = join(webRoot, "public", "og");
const session = process.env.GITBENCH_OG_SESSION || "gitbench-og-build";
const agentBrowserPackage =
  process.env.AGENT_BROWSER_PACKAGE || "agent-browser@0.27.0";
const agentBrowserPrefix = process.env.AGENT_BROWSER_BIN
  ? [process.env.AGENT_BROWSER_BIN]
  : ["npx", "--yes", agentBrowserPackage];
const targetWidth = 1200;
const targetHeight = 630;

function runAgentBrowser(args, { allowFailure = false } = {}) {
  const result = spawnSync(
    agentBrowserPrefix[0],
    [...agentBrowserPrefix.slice(1), "--session", session, ...args],
    {
      cwd: webRoot,
      encoding: "utf8",
      stdio: "pipe",
    },
  );

  if (result.status !== 0 && !allowFailure) {
    const command = [...agentBrowserPrefix, "--session", session, ...args].join(
      " ",
    );
    const output = [result.stdout, result.stderr].filter(Boolean).join("\n");
    throw new Error(`Command failed: ${command}\n${output}`);
  }

  return result;
}

function loadCards() {
  const cards = JSON.parse(readFileSync(manifestPath, "utf8"));
  if (!Array.isArray(cards) || cards.length === 0) {
    throw new Error(`${manifestPath} must contain at least one card.`);
  }

  for (const card of cards) {
    for (const field of [
      "name",
      "file",
      "eyebrow",
      "title",
      "subtitle",
      "stat1",
      "stat2",
      "stat3",
      "panel",
    ]) {
      if (typeof card[field] !== "string" || card[field].length === 0) {
        throw new Error(`Card is missing required string field: ${field}`);
      }
    }
    if (card.file.includes("/") || card.file.includes("\\")) {
      throw new Error(`Card file must be a file name, got: ${card.file}`);
    }
  }

  return cards;
}

function cardUrl(card) {
  const url = new URL(pathToFileURL(templatePath).href);
  for (const key of [
    "eyebrow",
    "title",
    "subtitle",
    "stat1",
    "stat2",
    "stat3",
    "panel",
  ]) {
    url.searchParams.set(key, card[key]);
  }
  return url.href;
}

function assertPngDimensions(filePath) {
  const bytes = readFileSync(filePath);
  const signature = "89504e470d0a1a0a";
  if (bytes.subarray(0, 8).toString("hex") !== signature) {
    throw new Error(`${filePath} is not a PNG file.`);
  }

  const width = bytes.readUInt32BE(16);
  const height = bytes.readUInt32BE(20);
  if (width !== targetWidth || height !== targetHeight) {
    throw new Error(
      `${filePath} is ${width}x${height}; expected ${targetWidth}x${targetHeight}.`,
    );
  }
}

function removeStaleImages(expectedFiles) {
  if (!existsSync(outputDir)) return;
  for (const entry of readdirSync(outputDir)) {
    if (entry.endsWith(".png") && !expectedFiles.has(entry)) {
      rmSync(join(outputDir, entry));
      console.log(`Removed stale OpenGraph image: ${entry}`);
    }
  }
}

if (!existsSync(templatePath)) {
  throw new Error(`Missing OpenGraph template: ${templatePath}`);
}

const cards = loadCards();
const expectedFiles = new Set(cards.map((card) => card.file));
mkdirSync(outputDir, { recursive: true });
removeStaleImages(expectedFiles);

console.log(
  `Generating ${cards.length} OpenGraph images with ${agentBrowserPrefix.join(
    " ",
  )}`,
);

runAgentBrowser(["close"], { allowFailure: true });

try {
  runAgentBrowser(["set", "viewport", String(targetWidth), String(targetHeight)]);

  for (const card of cards) {
    const outputPath = join(outputDir, card.file);
    runAgentBrowser(["open", cardUrl(card)]);
    runAgentBrowser(["screenshot", ".card", outputPath]);
    assertPngDimensions(outputPath);
    console.log(`Wrote ${card.file}`);
  }
} finally {
  runAgentBrowser(["close"], { allowFailure: true });
}

console.log("OpenGraph images are up to date.");
