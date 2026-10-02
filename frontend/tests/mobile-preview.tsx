import React from "react";
import {createRoot} from "react-dom/client";
import {MiniJonPage} from "../mobile/MiniJon";
import "../mobile/style.css";
let enabled = false;
const items = [{id: "2026-10-04:Mittagessen", date: "2026-10-04", meal: "Mittagessen", content: "Schnitzel"}];
window.JonNative = {post: raw => {
  const request = JSON.parse(raw);
  const emit = (packet: any) => setTimeout(() => window.jonReceive({id: request.id, ...packet}), 30);
  if (request.op === "api") {
    let data: any = {items};
    if (request.path.includes("/agents/profiles")) data = [{id: "latin", name: "Latein", activity: "learning", focus: "Grammatik und Übersetzung"}, {id: "planning", name: "Planen", activity: "planning", focus: "Aufgaben und Termine"}];
    else if (request.path.includes("/agents/runs") && request.method === "GET") data = [];
    else if (request.method === "DELETE") items.splice(0);
    emit({result: {text: JSON.stringify(data)}});
  }
  else if (request.op === "stream") {emit({chunk: {type: "meta", conversation_id: "preview"}}); emit({chunk: {type: "content", delta: "Am Sonntag, dem 04.10.2026, gibt es Schnitzel zum Mittagessen. Das hast du mir so gesagt."}}); emit({chunk: {type: "done"}}); emit({result: {}});}
  else {if (request.op === "minijon-enable") enabled = request.enabled; emit({result: {enabled, permission: true, running: enabled}});}
}};
const shell: any = {conn: {connected: true, paired: true, name: "Deinem Pi", server_id: "preview"}, notify: () => {}};
createRoot(document.getElementById("root")!).render(<MiniJonPage shell={shell} back={() => {}}/>);
