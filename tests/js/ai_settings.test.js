// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
// Copyright (C) 2026 ACFPF contributors

const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { test } = require("node:test");
const vm = require("node:vm");

const script = readFileSync("src/acfpf/web/static/js/ai_settings.js", "utf8");

function element(properties = {}) {
  const handlers = {};
  return {
    ...properties,
    addEventListener(type, handler) { handlers[type] = handler; },
    dispatch(type, event = {}) { handlers[type](event); },
  };
}

test("drop selects a file for native submission without reading the key", () => {
  const button = { textContent: "Activer l’IA" };
  const file = { name: "key.txt", text() { assert.fail("Credential must not be read in JS"); } };
  const input = element({ files: [] });
  Object.defineProperty(input, "value", {
    set(value) {
      assert.equal(value, "");
      this.files = [];
    },
  });
  const zone = element({ classList: { remove() {} } });
  const status = {};
  const elements = {
    "ai-settings-form": element({ querySelector: () => button }),
    "ai-provider": element(),
    "ai-model-name": {},
    "key-drop-zone": zone,
    "ai-key-file": input,
    "key-file-status": status,
  };
  vm.runInNewContext(script, {
    document: { getElementById: (id) => elements[id] },
    window: element(),
  });

  let prevented = false;
  zone.dispatch("drop", {
    dataTransfer: { files: [file] },
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
  assert.deepEqual(input.files, [file]);
  assert.equal(status.hidden, false);

  zone.dispatch("drop", {
    dataTransfer: { files: [file, file] },
    preventDefault() {},
  });
  assert.deepEqual(input.files, []);
  assert.match(status.textContent, /un seul fichier/);
});
