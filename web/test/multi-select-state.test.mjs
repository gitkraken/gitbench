import assert from "node:assert/strict";
import test from "node:test";

import {
  clearMultiSelectValues,
  filterMultiSelectOptions,
  selectAllMultiSelectValues,
  toggleMultiSelectValue,
} from "../src/lib/multi-select-state.ts";

const options = [
  { value: "openai/a", label: "Alpha", keywords: ["closed", "200K"] },
  { value: "other/b", label: "Beta", keywords: ["open", "1M"] },
];

test("multi-select search includes values, labels, and metadata keywords", () => {
  assert.deepEqual(filterMultiSelectOptions(options, "alpha"), [options[0]]);
  assert.deepEqual(filterMultiSelectOptions(options, "OPENAI"), [options[0]]);
  assert.deepEqual(filterMultiSelectOptions(options, "1m"), [options[1]]);
});

test("multi-select toggles individual values and supports select-all/clear inputs", () => {
  assert.deepEqual(toggleMultiSelectValue([], "openai/a"), ["openai/a"]);
  assert.deepEqual(
    toggleMultiSelectValue(["openai/a", "other/b"], "openai/a"),
    ["other/b"],
  );
  assert.deepEqual(selectAllMultiSelectValues(options), ["openai/a", "other/b"]);
  assert.deepEqual(clearMultiSelectValues(), []);
});
