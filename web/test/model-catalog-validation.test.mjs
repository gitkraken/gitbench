import assert from "node:assert/strict";
import test from "node:test";

import {
  validateModelMetadataCatalog,
  validateModelMetadataOverrides,
} from "../src/lib/model-catalog.ts";
import {
  validCatalogFixture,
  validOverridesFixture,
} from "./fixtures-model-catalog.mjs";

test("catalog and override validation accepts normalized fixtures", () => {
  assert.deepEqual(validateModelMetadataCatalog(validCatalogFixture), validCatalogFixture);
  assert.deepEqual(
    validateModelMetadataOverrides(validOverridesFixture),
    validOverridesFixture,
  );
});

test("catalog validation rejects invalid tri-state and context values", () => {
  const invalidWeight = structuredClone(validCatalogFixture);
  invalidWeight.models["openai/gpt-test"].weightAccess = "maybe";
  assert.throws(() => validateModelMetadataCatalog(invalidWeight), /open, closed/);

  const invalidContext = structuredClone(validCatalogFixture);
  invalidContext.models["openai/gpt-test"].contextWindowTokens = -1;
  assert.throws(() => validateModelMetadataCatalog(invalidContext), /non-negative/);
});

test("catalog validation enforces canonical keys and stable ordering", () => {
  const mismatch = structuredClone(validCatalogFixture);
  mismatch.models["openai/gpt-test"].canonicalId = "openai/other";
  assert.throws(() => validateModelMetadataCatalog(mismatch), /mismatch/);

  const unordered = structuredClone(validCatalogFixture);
  unordered.models = {
    "z/model": { ...unordered.models["openai/gpt-test"], canonicalId: "z/model" },
    "a/model": { ...unordered.models["openai/gpt-test"], canonicalId: "a/model" },
  };
  assert.throws(() => validateModelMetadataCatalog(unordered), /ascending order/);
});

test("override validation rejects invalid reviewed values", () => {
  const invalid = structuredClone(validOverridesFixture);
  invalid.models["openai/gpt-test"].weightAccess = "source-available";
  assert.throws(() => validateModelMetadataOverrides(invalid), /open, closed/);
});

test("committed catalog loads offline without consulting fetch", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = () => {
    throw new Error("network must not be used");
  };
  try {
    const { loadModelMetadataCatalog } = await import("../src/lib/model-catalog.ts");
    const catalog = loadModelMetadataCatalog();
    assert.ok(Object.keys(catalog.models).length > 0);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
