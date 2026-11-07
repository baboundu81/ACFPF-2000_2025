// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const window = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../src/acfpf/web/static/js/research_stream.js"), "utf8"),
  { window, TextDecoder, Uint8Array, Set, Error });
const answer = {type:"answer",answer:{status:"answered",answer:"Décision vérifiée.",citations:[]}};
const encode = (event) => JSON.stringify(event)+"\n";
function response(chunks) {
  return {body:new ReadableStream({start(controller) {
    for (const chunk of chunks) controller.enqueue(chunk);
    controller.close();
  }})};
}
const bytes = (s) => new TextEncoder().encode(s);

test("UTF-8 and JSON split across chunks; final line without newline", async () => {
  const payload=bytes(encode({type:"started"})+JSON.stringify(answer));
  const chunks=Array.from(payload, (value)=>new Uint8Array([value]));
  const events=[];
  const result=await window.ACFPFConsumeResearchStream(response(chunks), e=>events.push(e));
  assert.equal(result.answer,"Décision vérifiée.");
  assert.deepEqual(events.map(e=>e.type),["started"]);
});
for (const [name,lines] of [
  ["empty", ""], ["no final", encode({type:"started"})], ["invalid JSON","{broken}"],
  ["unknown event", encode({type:"private_reasoning"})],
  ["duplicate answer", encode(answer)+encode(answer)],
  ["event after answer", encode(answer)+encode({type:"notice"})],
  ["invalid final", encode({type:"answer",answer:{}})],
]) test(`rejects ${name} without publishing an answer`, async () => {
  const events=[];
  await assert.rejects(window.ACFPFConsumeResearchStream(response([bytes(lines)]), e=>events.push(e)));
  assert.equal(events.filter(e=>e.type==="answer").length,0);
});
test("terminal error without newline keeps server diagnostic", async () => {
  const events=[];
  await assert.rejects(window.ACFPFConsumeResearchStream(response([bytes(JSON.stringify({type:"error",message:"Quota atteint"}))]), e=>events.push(e)), /Quota atteint/);
  assert.equal(events[0].type,"error");
});
test("network interruption after progress never becomes a successful answer", async () => {
  const events=[];
  const interrupted={body:new ReadableStream({pull(controller) { controller.error(new Error("connection interrupted")); }})};
  await assert.rejects(window.ACFPFConsumeResearchStream(interrupted,e=>events.push(e)));
  assert.equal(events.length,0);
});
