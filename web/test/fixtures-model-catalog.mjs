export const validCatalogFixture = {
  schemaVersion: 1,
  fetchedAt: "2026-07-16T00:00:00.000Z",
  models: {
    "openai/gpt-test": {
      canonicalId: "openai/gpt-test",
      contextWindowTokens: 200000,
      weightAccess: "closed",
      openRouterId: "openai/gpt-test",
      huggingFaceId: null,
      provenance: {
        contextWindowTokens: "openrouter",
        weightAccess: "override",
      },
      fetchedAt: "2026-07-16T00:00:00.000Z",
    },
  },
};

export const validOverridesFixture = {
  schemaVersion: 1,
  aliases: { "openai/gpt-old": "openai/gpt-renamed" },
  models: {
    "openai/gpt-test": {
      weightAccess: "closed",
      note: "Reviewed provider-hosted model.",
    },
  },
};
