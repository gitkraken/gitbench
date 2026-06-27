import assert from "node:assert/strict";
import test from "node:test";
import { inflateSync } from "fflate";

import {
  base64UrlDecodeBytes,
  decodeReportViewState,
  encodeReportViewState,
  resolveReportViewState,
} from "../src/lib/report-url-state.ts";

const textDecoder = new TextDecoder();

function groups(count) {
  return Array.from({ length: count }, (_, index) => ({
    id: `provider/model-${index}`,
    provider: "provider",
    baseModel: `model-${index}`,
    efforts: [
      { modelName: `provider/model-${index}:high` },
      { modelName: `provider/model-${index}:high__json_schema` },
    ],
  }));
}

function forceCompressed(state, modelGroups, options = {}) {
  const encoded = encodeReportViewState(state, modelGroups, {
    availableOutputModes: ["text", "json_schema"],
    maxReadableLength: 1,
    ...options,
  });
  assert.match(encoded, /^s=gb1\./);
  return encoded;
}

function compressedBytes(encoded) {
  return base64UrlDecodeBytes(encoded.slice("s=gb1.".length));
}

test("compressed report state round trips include, exclude, all, and omitted default output mode", () => {
  const modelGroups = groups(5);

  const include = forceCompressed(
    {
      selectedGroups: ["provider/model-1", "provider/model-3"],
      outputMode: "text",
    },
    modelGroups
  );
  assert.deepEqual(
    resolveReportViewState(include, modelGroups, {
      availableOutputModes: ["text", "json_schema"],
    }),
    {
      selectedGroups: ["provider/model-1", "provider/model-3"],
      outputMode: "text",
      source: "url",
      selectionKind: "include",
      errors: [],
    }
  );

  const exclude = forceCompressed(
    {
      selectedGroups: [
        "provider/model-0",
        "provider/model-1",
        "provider/model-2",
        "provider/model-3",
      ],
      outputMode: "json_schema",
    },
    modelGroups
  );
  assert.deepEqual(
    resolveReportViewState(exclude, modelGroups, {
      availableOutputModes: ["text", "json_schema"],
    }).selectedGroups,
    [
      "provider/model-0",
      "provider/model-1",
      "provider/model-2",
      "provider/model-3",
    ]
  );

  const all = forceCompressed(
    {
      selectedGroups: modelGroups.map((group) => group.id),
      outputMode: "both",
    },
    modelGroups
  );
  const payload = JSON.parse(textDecoder.decode(inflateSync(compressedBytes(all))));
  assert.equal(payload.k, "a");
  assert.equal(payload.o, undefined);
  assert.deepEqual(
    resolveReportViewState(all, modelGroups, {
      availableOutputModes: ["text", "json_schema"],
    }).selectedGroups,
    modelGroups.map((group) => group.id)
  );
});

test("compressed transport stores deflated bytes, not raw JSON base64", () => {
  const modelGroups = groups(2);
  const encoded = forceCompressed(
    {
      selectedGroups: ["provider/model-0"],
      outputMode: "text",
    },
    modelGroups
  );

  const bytes = compressedBytes(encoded);
  assert.notEqual(textDecoder.decode(bytes).trimStart()[0], "{");
  const inflated = JSON.parse(textDecoder.decode(inflateSync(bytes)));
  assert.equal(inflated.v, 1);
  assert.equal(inflated.k, "i");
});

test("invalid, stale, and unavailable URL state falls back without throwing", () => {
  const modelGroups = groups(3);
  const defaultOptions = {
    defaultSelectedGroups: ["provider/model-2"],
    availableOutputModes: ["text", "json_schema"],
  };

  assert.deepEqual(
    resolveReportViewState(
      "m=provider%2Fmodel-1,missing&mode=bogus",
      modelGroups,
      defaultOptions
    ),
    {
      selectedGroups: ["provider/model-1"],
      outputMode: "both",
      source: "url",
      selectionKind: "include",
      errors: [
        {
          code: "invalid-output-mode",
          message: 'Invalid output mode "bogus".',
        },
      ],
    }
  );

  assert.deepEqual(
    resolveReportViewState("m=missing", modelGroups, defaultOptions)
      .selectedGroups,
    ["provider/model-2"]
  );

  const corrupt = resolveReportViewState(
    "s=gb1.YWJj",
    modelGroups,
    defaultOptions
  );
  assert.deepEqual(corrupt.selectedGroups, ["provider/model-2"]);
  assert.equal(corrupt.outputMode, "both");
  assert.equal(corrupt.source, "default");
  assert.equal(corrupt.errors[0].code, "inflate-failed");

  const unsupported = resolveReportViewState(
    "s=gb2.YWJj",
    modelGroups,
    defaultOptions
  );
  assert.deepEqual(unsupported.selectedGroups, ["provider/model-2"]);
  assert.equal(unsupported.errors[0].code, "unsupported-codec");

  const unavailableMode = resolveReportViewState(
    "models=all&mode=json_schema",
    modelGroups,
    { availableOutputModes: ["text"] }
  );
  assert.equal(unavailableMode.outputMode, "text");
  assert.equal(unavailableMode.errors[0].code, "unavailable-output-mode");
});

test("encoder minimizes readable include, exclude, and all selections", () => {
  const modelGroups = groups(5);
  const options = {
    availableOutputModes: ["text", "json_schema"],
    maxReadableLength: 5000,
  };

  assert.equal(
    encodeReportViewState(
      {
        selectedGroups: ["provider/model-0", "provider/model-1"],
        outputMode: "both",
      },
      modelGroups,
      options
    ),
    "m=provider%2Fmodel-0,provider%2Fmodel-1"
  );

  assert.equal(
    encodeReportViewState(
      {
        selectedGroups: [
          "provider/model-0",
          "provider/model-1",
          "provider/model-2",
          "provider/model-3",
        ],
        outputMode: "both",
      },
      modelGroups,
      options
    ),
    "x=provider%2Fmodel-4"
  );

  assert.equal(
    encodeReportViewState(
      {
        selectedGroups: modelGroups.map((group) => group.id),
        outputMode: "both",
      },
      modelGroups,
      options
    ),
    "models=all"
  );

  assert.equal(
    encodeReportViewState(
      {
        selectedGroups: [],
        outputMode: "both",
      },
      modelGroups,
      options
    ),
    "models=none"
  );
});

test("empty selections round trip through readable and compressed URL state", () => {
  const modelGroups = groups(3);

  assert.deepEqual(
    resolveReportViewState("models=none", modelGroups, {
      availableOutputModes: ["text", "json_schema"],
    }).selectedGroups,
    []
  );

  const compressed = forceCompressed(
    {
      selectedGroups: [],
      outputMode: "both",
    },
    modelGroups
  );
  assert.deepEqual(
    resolveReportViewState(compressed, modelGroups, {
      availableOutputModes: ["text", "json_schema"],
    }).selectedGroups,
    []
  );
});

test("legacy with parameter maps model effort aliases to provider/base-model groups", () => {
  const modelGroups = groups(3);

  assert.deepEqual(
    resolveReportViewState("with=provider%2Fmodel-1%3Ahigh", modelGroups)
      .selectedGroups,
    ["provider/model-1"]
  );
  assert.deepEqual(
    resolveReportViewState("with=model-1%23high", modelGroups).selectedGroups,
    ["provider/model-1"]
  );
  assert.deepEqual(
    resolveReportViewState("with=model-2", modelGroups).selectedGroups,
    ["provider/model-2"]
  );
  assert.deepEqual(
    resolveReportViewState(
      "m=provider%2Fmodel-0&with=provider%2Fmodel-1%3Ahigh",
      modelGroups
    ),
    {
      selectedGroups: ["provider/model-0"],
      outputMode: "both",
      source: "url",
      selectionKind: "include",
      errors: [],
    }
  );
  assert.equal(
    decodeReportViewState("with=provider%2Fmodel-1%3Ahigh")?.source,
    "legacy"
  );
});
