import assert from "node:assert/strict";
import test from "node:test";

import {
  availableModelPresets,
  defaultModelGroupSelection,
} from "../src/lib/model-selector-state.ts";
import {
  encodeReportViewState,
  resolveReportViewState,
} from "../src/lib/report-url-state.ts";

const groups = ["provider/a", "provider/b", "provider/c"];
const groupObjects = groups.map((id) => ({ id }));
const presets = [
  {
    id: "top-performers",
    label: "Top Performers",
    description: "Top",
    modelGroupIds: ["provider/a", "provider/missing", "provider/b"],
  },
  {
    id: "open-weights",
    label: "Open Weights",
    description: "Open",
    modelGroupIds: ["provider/c"],
  },
];

test("preset membership intersects available groups and exact active state ignores order", () => {
  const available = availableModelPresets(presets, groups, ["provider/b", "provider/a"]);
  assert.deepEqual(available[0].availableIds, ["provider/a", "provider/b"]);
  assert.equal(available[0].active, true);
  assert.equal(available[1].active, false);

  const customized = availableModelPresets(presets, groups, ["provider/a"]);
  assert.equal(customized[0].active, false);
});

test("Top Performers is the default only when URL model state is absent", () => {
  const defaults = defaultModelGroupSelection({ model_presets: presets }, groups);
  assert.deepEqual(defaults, ["provider/a", "provider/b"]);
  assert.deepEqual(
    resolveReportViewState("", groupObjects, { defaultSelectedGroups: defaults })
      .selectedGroups,
    defaults,
  );
  assert.deepEqual(
    resolveReportViewState("m=provider%2Fc", groupObjects, {
      defaultSelectedGroups: defaults,
    }).selectedGroups,
    ["provider/c"],
  );
  assert.deepEqual(
    resolveReportViewState("models=none", groupObjects, {
      defaultSelectedGroups: defaults,
    }).selectedGroups,
    [],
  );
});

test("applied presets encode concrete IDs and post-preset edits are custom", () => {
  const applied = ["provider/a", "provider/b"];
  assert.equal(
    encodeReportViewState({ selectedGroups: applied }, groupObjects),
    "x=provider%2Fc",
  );
  const customized = availableModelPresets(presets, groups, ["provider/a"]);
  assert.equal(customized.every((preset) => !preset.active), true);
});
