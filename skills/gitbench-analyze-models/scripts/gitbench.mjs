#!/usr/bin/env node

import process from "node:process";
import { pathToFileURL } from "node:url";

const DEFAULT_BASE_URL = "https://gitbench.dev";
const DEFAULT_TIMEOUT_MS = 15_000;

const commandOptions = {
  overview: ["offset", "limit"],
  models: ["offset", "limit"],
  "model-results": [
    "model",
    "benchmark",
    "difficulty",
    "tag",
    "output-mode",
    "include-model-output",
    "evidence-characters",
    "offset",
    "limit",
  ],
  benchmark: ["benchmark", "offset", "limit"],
  fixture: [
    "benchmark",
    "fixture",
    "include-prompt",
    "include-expected",
    "include-model-output",
    "include-structured-output",
    "evidence-characters",
    "offset",
    "limit",
  ],
  rank: [
    "benchmark",
    "resource-metric",
    "strategy",
    "output-mode",
    "minimum-quality",
    "offset",
    "limit",
  ],
};

const requiredOptions = {
  "model-results": ["model"],
  benchmark: ["benchmark"],
  fixture: ["benchmark", "fixture"],
  rank: ["benchmark"],
};

const booleanOptions = new Set([
  "include-prompt",
  "include-expected",
  "include-model-output",
  "include-structured-output",
]);

const integerOptions = new Set([
  "offset",
  "limit",
  "evidence-characters",
  "timeout-ms",
]);

function usage() {
  return `Usage: gitbench.mjs <command> [options]

Commands: overview, models, model-results, benchmark, fixture, rank
Global options:
  --base-url <http(s) origin>  Override GITBENCH_BASE_URL and production
  --timeout-ms <integer>      Request timeout (default: 15000)
  --help                      Show this help

Run with a command and --help for its accepted options.`;
}

function commandUsage(command) {
  const options = commandOptions[command] ?? [];
  return `${command} options: ${options.map((option) => `--${option}`).join(", ")}`;
}

function parseArguments(argv) {
  const [command, ...tokens] = argv;
  if (!command || command === "--help" || command === "-h") {
    return { help: true };
  }
  if (!Object.hasOwn(commandOptions, command)) {
    throw new Error(`Unknown command: ${command}`);
  }

  const allowed = new Set([
    ...commandOptions[command],
    "base-url",
    "timeout-ms",
    "help",
  ]);
  const values = {};
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];
    if (!token.startsWith("--")) {
      throw new Error(`Unexpected positional argument: ${token}`);
    }
    const equals = token.indexOf("=");
    const key = token.slice(2, equals === -1 ? undefined : equals);
    if (!allowed.has(key)) {
      throw new Error(`Unsupported option for ${command}: --${key}`);
    }
    if (Object.hasOwn(values, key)) {
      throw new Error(`Option may only be supplied once: --${key}`);
    }
    if (key === "help") return { help: true, command };
    if (booleanOptions.has(key)) {
      if (equals !== -1) {
        const raw = token.slice(equals + 1);
        if (raw !== "true" && raw !== "false") {
          throw new Error(`--${key} must be true or false`);
        }
        values[key] = raw === "true";
      } else {
        values[key] = true;
      }
      continue;
    }
    const value =
      equals === -1 ? tokens[(index += 1)] : token.slice(equals + 1);
    if (!value || value.startsWith("--")) {
      throw new Error(`--${key} requires a value`);
    }
    if (integerOptions.has(key)) {
      if (!/^\d+$/.test(value) || (Number(value) < 1 && key !== "offset")) {
        throw new Error(
          `--${key} must be ${key === "offset" ? "a non-negative" : "a positive"} integer`,
        );
      }
      values[key] = Number(value);
    } else {
      values[key] = value;
    }
  }

  for (const key of requiredOptions[command] ?? []) {
    if (!values[key]) throw new Error(`--${key} is required for ${command}`);
  }
  return { command, values };
}

function normalizeBaseUrl(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`Invalid GitBench base URL: ${value}`);
  }
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    (url.pathname !== "/" && url.pathname !== "")
  ) {
    throw new Error(
      "GitBench base URL must be an http(s) origin without credentials, path, query, or fragment",
    );
  }
  return url.origin;
}

export async function run(
  argv,
  {
    env = process.env,
    fetchImpl = globalThis.fetch,
    stdout = process.stdout,
    stderr = process.stderr,
  } = {},
) {
  let parsed;
  try {
    parsed = parseArguments(argv);
    if (parsed.help) {
      stdout.write(
        `${parsed.command ? commandUsage(parsed.command) : usage()}\n`,
      );
      return 0;
    }
    const baseUrl = normalizeBaseUrl(
      parsed.values["base-url"] ?? env.GITBENCH_BASE_URL ?? DEFAULT_BASE_URL,
    );
    const timeoutMs = parsed.values["timeout-ms"] ?? DEFAULT_TIMEOUT_MS;
    const url = new URL(`/api/agent/v1/${parsed.command}`, baseUrl);
    for (const [key, value] of Object.entries(parsed.values)) {
      if (key === "base-url" || key === "timeout-ms" || value === false)
        continue;
      url.searchParams.set(key.replaceAll("-", "_"), String(value));
    }

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetchImpl(url, {
        method: "GET",
        headers: { accept: "application/json" },
        signal: controller.signal,
      });
    } catch (error) {
      const diagnostic = controller.signal.aborted
        ? `GitBench request timed out after ${timeoutMs}ms`
        : `GitBench request failed: ${error instanceof Error ? error.message : String(error)}`;
      stderr.write(`${diagnostic}\n`);
      return 1;
    } finally {
      clearTimeout(timeout);
    }

    let body;
    try {
      body = await response.json();
    } catch {
      stderr.write(
        `GitBench API returned invalid JSON (HTTP ${response.status})\n`,
      );
      return 1;
    }
    if (
      typeof body !== "object" ||
      body === null ||
      typeof body.ok !== "boolean"
    ) {
      stderr.write(
        `GitBench API returned an invalid envelope (HTTP ${response.status})\n`,
      );
      return 1;
    }

    stdout.write(`${JSON.stringify(body, null, 2)}\n`);
    if (!response.ok || !body.ok) {
      const category = body.error?.category ?? "request_failure";
      const message = body.error?.message ?? `HTTP ${response.status}`;
      stderr.write(`GitBench API ${category}: ${message}\n`);
      return 1;
    }
    return 0;
  } catch (error) {
    stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    stderr.write(`${usage()}\n`);
    return 2;
  }
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exitCode = await run(process.argv.slice(2));
}
