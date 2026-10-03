import React from "react";
import {createRoot} from "react-dom/client";
import {MotionConfig} from "framer-motion";
import {FunkePage} from "../mobile/Funke";
import "../mobile/style.css";

const params = new URLSearchParams(location.search);
if (params.get("hell")) document.documentElement.dataset.theme = "light"; else document.documentElement.dataset.theme = "dark";
let enabled = false;
let teamStart = 0;
const items = [{id: "2026-10-04:Mittagessen", date: "2026-10-04", meal: "Mittagessen", content: "Schnitzel"}];
const teile = [
  {titel: "Wortformen", auftrag: "Bestimme puellam", rolle: "latin", rolle_name: "Latein"},
  {titel: "Übersetzung", auftrag: "Übersetze den Satz", rolle: "writing", rolle_name: "Schreiben"},
  {titel: "AcI erklären", auftrag: "Erkläre den AcI", rolle: "learning", rolle_name: "Lernen"},
];
function lauf() {
  const t = (Date.now() - teamStart) / 1000;
  const status = t < 1.5 ? "planning" : t < 7 ? "working" : t < 9 ? "verifying" : t < 10.5 ? "summarizing" : "done";
  return {id: "c".repeat(32), aufgabe: "Übersetze Marcus dicit puellam legere", status, created_at: teamStart / 1000, updated_at: Date.now() / 1000, teile: t < 1.5 ? [] : teile.map((x, i) => ({...x, status: t > 3 + i * 1.5 ? "done" : "working", begonnen: teamStart / 1000 + 1.5})), pruefung: t > 9 ? {ok: true, probleme: [], korrektur: ""} : null, antwort: t > 10.5 ? "Marcus sagt, dass das Mädchen liest." : ""};
}
window.JonNative = {post: raw => {
  const request = JSON.parse(raw);
  const emit = (packet: any, delay = 30) => setTimeout(() => window.jonReceive({id: request.id, ...packet}), delay);
  if (request.op === "api") {
    let data: any = {items};
    if (request.path.includes("/agents/profiles")) data = [{id: "latin", name: "Latein", focus: ""}, {id: "planning", name: "Alltagsplanung", focus: ""}, {id: "learning", name: "Lernen & Mathematik", focus: ""}];
    else if (request.path.includes("/agents/runs?brief")) data = [];
    else if (request.path.includes("/agents/runs/")) data = lauf();
    else if (request.method === "DELETE") items.splice(0);
    emit({result: {text: JSON.stringify(data)}});
  }
  else if (request.op === "stream") {
    teamStart = Date.now();
    emit({chunk: {type: "meta", conversation_id: "vorschau"}});
    emit({chunk: {type: "tool", name: "team", status: "running", summary: "Lässt mehrere Agenten arbeiten", card: {kind: "agenten", data: {id: "c".repeat(32), aufgabe: "Übersetze Marcus dicit puellam legere"}}}}, 400);
    emit({chunk: {type: "tool", name: "team", status: "done", ok: true}}, 11000);
    emit({chunk: {type: "content", delta: "Erledigt! Marcus sagt, dass das Mädchen liest. **puellam** ist der Subjektsakkusativ des AcI."}}, 11400);
    emit({chunk: {type: "done"}}, 11600);
    emit({result: {}}, 11700);
  }
  else {if (request.op === "minijon-enable") enabled = request.enabled; emit({result: {enabled, permission: true, running: enabled}});}
}};
const shell: any = {conn: {connected: params.get("offline") ? false : true, paired: true, name: "Deinem Pi", server_id: "preview"}, notify: () => {}, name: "Felix", freigabe: "ask", voice: null};
createRoot(document.getElementById("root")!).render(<MotionConfig reducedMotion="never"><div className="app" style={{position: "relative", height: "100vh", display: "flex", flexDirection: "column"}}><FunkePage shell={shell} back={() => {}}/></div></MotionConfig>);
