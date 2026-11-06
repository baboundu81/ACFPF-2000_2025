// SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
class Node {
  constructor(){this.textContent="";this.listeners={};this.dataset={};this.value="";this.disabled=false;}
  addEventListener(name,cb){this.listeners[name]=cb;}
  removeEventListener(name,cb){if(this.listeners[name]===cb)delete this.listeners[name];}
  replaceChildren(){}
}
for(const [file,attribute] of [["versions","versionsDossierId"],["reports","reportsDossierId"],
                              ["votes","votesDossierId"],["amendments","amendmentsDossierId"]]){
 test(`${file} loads only on first opening, not on render or close`,async()=>{
   const panel=new Node();panel.open=false;
   const root=new Node();root.dataset[attribute]="DLR1";root.closest=()=>panel;
   const nodes=new Map();const calls=[];
   const document={querySelector:()=>root,getElementById:(id)=>{
     if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);
   }};
   vm.runInNewContext(fs.readFileSync(path.join(__dirname,`../../src/acfpf/web/static/js/${file}.js`),"utf8"),{
     document,AbortController,URLSearchParams,
     fetch:async(url)=>{calls.push(url);return {ok:true,json:async()=>({available:true,dossier_id:"DLR1",count:0,filtered_count:0,versions:[],reports:[],votes:[],amendments:[]})};}
   });
   assert.equal(calls.length,0);
   panel.listeners.toggle();assert.equal(calls.length,0);
   panel.open=true;panel.listeners.toggle();await new Promise(r=>setImmediate(r));
   assert.equal(calls.length,1);
   assert.equal(panel.listeners.toggle,undefined);
   assert.equal(nodes.get(`${file}-status`).textContent.includes("Impossible"),false);
 });
}
