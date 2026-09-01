import assert from "node:assert/strict";
import test from "node:test";

import { run } from "../../skills/gitbench-analyze-models/scripts/gitbench.mjs";

function sink() {
  return {
    value: "",
    write(chunk) {
      this.value += chunk;
    },
  };
}

function successFetch(requests) {
  return async (url, options) => {
    requests.push({ url, options });
    return new Response(
      JSON.stringify({
        ok: true,
        source_url: "https://gitbench.dev/",
        data: { campaign_id: null },
      }),
      { status: 200, headers: { "content-type": "application/json" } },
    );
  };
}

async function invoke(argv, options = {}) {
  const stdout = sink();
  const stderr = sink();
  const code = await run(argv, {
    env: {},
    stdout,
    stderr,
    ...options,
  });
  return { code, stdout: stdout.value, stderr: stderr.value };
}

test("all six subcommands send safely encoded v1 GET requests", async () => {
  const cases = [
    ["overview", ["overview", "--limit", "10"]],
    ["models", ["models", "--offset", "0"]],
    [
      "model-results",
      [
        "model-results",
        "--model",
        "provider/model name:high",
        "--tag",
        "spaces & symbols",
      ],
    ],
    ["benchmark", ["benchmark", "--benchmark", "commit messages"]],
    [
      "fixture",
      ["fixture", "--benchmark", "commits", "--fixture", "folder/id"],
    ],
    [
      "rank",
      [
        "rank",
        "--benchmark",
        "commits",
        "--resource-metric",
        "tokens",
        "--strategy",
        "balanced",
      ],
    ],
  ];
  for (const [command, argv] of cases) {
    const requests = [];
    const result = await invoke(argv, { fetchImpl: successFetch(requests) });
    assert.equal(result.code, 0, command);
    assert.equal(result.stderr, "", command);
    assert.equal(JSON.parse(result.stdout).ok, true, command);
    assert.equal(requests.length, 1, command);
    assert.equal(requests[0].url.pathname, `/api/agent/v1/${command}`);
    assert.equal(requests[0].options.method, "GET");
    assert.equal(requests[0].options.headers.accept, "application/json");
  }
});

test("base URL flag overrides environment and environment overrides production", async () => {
  for (const [argv, env, expected] of [
    [
      ["overview", "--base-url", "https://flag.example"],
      { GITBENCH_BASE_URL: "https://env.example" },
      "https://flag.example",
    ],
    [
      ["overview"],
      { GITBENCH_BASE_URL: "https://env.example" },
      "https://env.example",
    ],
    [["overview"], {}, "https://gitbench.dev"],
  ]) {
    const requests = [];
    const result = await invoke(argv, {
      env,
      fetchImpl: successFetch(requests),
    });
    assert.equal(result.code, 0);
    assert.equal(requests[0].url.origin, expected);
  }
});

test("evidence flags stay absent by default and explicit opt-ins are encoded", async () => {
  const requests = [];
  await invoke(["fixture", "--benchmark", "commits", "--fixture", "f-1"], {
    fetchImpl: successFetch(requests),
  });
  assert.equal(
    [...requests[0].url.searchParams.keys()].some((key) =>
      key.startsWith("include_"),
    ),
    false,
  );

  await invoke(
    [
      "fixture",
      "--benchmark",
      "commits",
      "--fixture",
      "f-1",
      "--include-model-output",
      "--include-prompt=false",
      "--evidence-characters",
      "250",
    ],
    { fetchImpl: successFetch(requests) },
  );
  assert.equal(
    requests[1].url.searchParams.get("include_model_output"),
    "true",
  );
  assert.equal(requests[1].url.searchParams.has("include_prompt"), false);
  assert.equal(requests[1].url.searchParams.get("evidence_characters"), "250");
});

test("invalid arguments and unsafe base URLs fail before transport", async () => {
  for (const argv of [
    ["unknown"],
    ["rank"],
    ["overview", "--limit", "0"],
    ["overview", "--extra", "x"],
    ["overview", "--base-url", "file:///tmp/gitbench"],
    ["overview", "--base-url", "https://user:pass@example.test"],
  ]) {
    let fetched = false;
    const result = await invoke(argv, {
      fetchImpl: async () => {
        fetched = true;
      },
    });
    assert.equal(result.code, 2, argv.join(" "));
    assert.equal(result.stdout, "");
    assert.match(result.stderr, /Usage:/);
    assert.equal(fetched, false);
  }
});

test("API failures preserve JSON stdout and add a nonzero diagnostic", async () => {
  const envelope = {
    ok: false,
    source_url: "https://gitbench.dev/benchmarks/missing",
    error: { category: "not_found", message: "Benchmark not found" },
  };
  const result = await invoke(["benchmark", "--benchmark", "missing"], {
    fetchImpl: async () =>
      new Response(JSON.stringify(envelope), {
        status: 404,
        headers: { "content-type": "application/json" },
      }),
  });
  assert.equal(result.code, 1);
  assert.deepEqual(JSON.parse(result.stdout), envelope);
  assert.match(result.stderr, /not_found: Benchmark not found/);
});

test("transport, timeout, and malformed responses fail without fabricated stdout", async () => {
  const transport = await invoke(["overview"], {
    fetchImpl: async () => {
      throw new TypeError("network down");
    },
  });
  assert.equal(transport.code, 1);
  assert.equal(transport.stdout, "");
  assert.match(transport.stderr, /network down/);

  const timeout = await invoke(["overview", "--timeout-ms", "1"], {
    fetchImpl: async (_url, { signal }) =>
      new Promise((_resolve, reject) => {
        signal.addEventListener("abort", () =>
          reject(new DOMException("aborted", "AbortError")),
        );
      }),
  });
  assert.equal(timeout.code, 1);
  assert.equal(timeout.stdout, "");
  assert.match(timeout.stderr, /timed out/);

  const malformed = await invoke(["overview"], {
    fetchImpl: async () => new Response("not json", { status: 502 }),
  });
  assert.equal(malformed.code, 1);
  assert.equal(malformed.stdout, "");
  assert.match(malformed.stderr, /invalid JSON/);
});
