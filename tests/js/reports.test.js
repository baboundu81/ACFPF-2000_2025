// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const script = fs.readFileSync(
  path.join(__dirname, "../../src/acfpf/web/static/js/reports.js"), "utf8",
);

class Node {
  constructor(tag = "div") {
    this.tag = tag;
    this.children = [];
    this.listeners = {};
    this.hidden = false;
    this.disabled = false;
    this.textContent = "";
    this.dataset = {};
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  click() { if (this.listeners.click) return this.listeners.click(); }
}

async function settle() {
  await new Promise((resolve) => setImmediate(resolve));
}

function setup(handler) {
  const ids = new Map();
  for (const id of ["reports-list", "reports-count", "reports-status", "reports-more"]) {
    ids.set(id, new Node());
  }
  const root = new Node();
  root.dataset.reportsDossierId = "DLR1";
  const calls = [];
  const document = {
    querySelector: (selector) => selector === "[data-reports-dossier-id]" ? root : null,
    getElementById: (id) => ids.get(id),
    createElement: (tag) => new Node(tag),
  };
  const fetch = async (url, options) => {
    calls.push(String(url));
    assert.equal(options.headers.Accept, "application/json");
    return handler(String(url));
  };
  vm.runInNewContext(script, { document, fetch, URLSearchParams });
  return { ids, calls };
}

const report = {
  uid: "RAPPANR5L17B0912", title: "Rapport <script>injection</script>",
  origin: "Assemblée nationale", provenance: "Commission",
  publication_date: "2025-02-05", dossier_url: "https://www.assemblee-nationale.fr/",
  html_lookup_supported: true,
};

test("reports viewer paginates and fetches HTML on click only", async () => {
  const { ids, calls } = setup((url) => {
    if (url.includes("/text")) return {
      ok: true, json: async () => ({
        dossier_id: "DLR1", uid: report.uid,
        text: "<script>should be literal</script>", sha256: "a".repeat(64),
        retrieved_at: "2026-11-05T15:00:00Z",
        url: "https://www.assemblee-nationale.fr/dyn/opendata/RAPPANR5L17B0912.html",
      }),
    };
    return {
      ok: true, json: async () => ({ available: true, count: 1, reports: [report] }),
    };
  });
  await settle();
  const list = ids.get("reports-list");
  assert.equal(list.children.length, 1);
  assert.equal(list.children[0].children[0].textContent, report.title);
  assert.equal(calls.length, 1);
  assert.equal(ids.get("reports-more").hidden, true);
  const card = list.children[0];
  const button = card.children.find((item) => item.tag === "button");
  const panel = card.children.find((item) => item.tag === "div");
  assert.equal(panel.hidden, true);
  button.click();
  await settle();
  assert.equal(calls.length, 2);
  assert.equal(panel.dataset.loaded, "1");
  assert(panel.children.some((item) => item.textContent === "<script>should be literal</script>"));
  button.click();
  assert.equal(panel.hidden, true);
  assert.equal(calls.length, 2);
});

test("unverified Senate report offers no Assembly HTML fetch", async () => {
  const { ids, calls } = setup(async () => ({
    ok: true, json: async () => ({
      available: true, count: 1, reports: [{
        ...report, uid: "RAPPSNR5S499B0016", html_lookup_supported: false,
      }],
    }),
  }));
  await settle();
  const card = ids.get("reports-list").children[0];
  assert.equal(card.children.some((item) => item.tag === "button"), false);
  assert.equal(calls.length, 1);
});

test("source outage is reported rather than rendering fictitious reports", async () => {
  const { ids } = setup(async () => ({
    ok: false, json: async () => ({ message: "Source indisponible" }),
  }));
  await settle();
  assert.equal(ids.get("reports-list").children.length, 0);
  assert.match(ids.get("reports-status").textContent, /indisponible/i);
});
