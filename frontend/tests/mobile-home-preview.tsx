import React from "react";
import {createRoot} from "react-dom/client";
import {App} from "../mobile/App";
import "../mobile/style.css";
window.JonNative = {post: raw => {
  const r = JSON.parse(raw);
  let result: any = {};
  if (r.op === "ready") result = {connected: true, paired: true, name: "Pi", server_id: "test"};
  if (r.op === "weg") result = {weg: "pi"};
  if (r.op === "freigabe") result = {modus: "ask"};
  if (r.op === "profil") result = {name: ""};
  if (r.op === "kinder") result = {an: false, alter: 10};
  if (r.op === "sprache") result = {code: "de"};
  if (r.op === "apps") result = [];
  if (r.op === "minijon-status") result = {enabled: false, permission: true, running: false};
  if (r.op === "api") {
    let data: any = {};
    if (/conversations|accounts/.test(r.path)) data = [];
    if (r.path.includes("health")) data = {default_provider: "nvidia", default_model: "Jon"};
    if (r.path.includes("memories")) data = {items: []};
    result = {text: JSON.stringify(data)};
  }
  setTimeout(() => window.jonReceive({id:r.id,result}), 20);
}};
createRoot(document.getElementById("root")!).render(<App/>);
