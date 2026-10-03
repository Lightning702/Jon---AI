import React from "react";
import {createRoot} from "react-dom/client";
import HarnessWorkspace from "../src/components/HarnessWorkspace";
import "../src/index.css";
const task = {id: "preview", goal: "Suche im Projekt verbessern", root: "C:\\Projekte\\Beispiel", source: "app", companion: true, model: "qwen3-coder", created_at: Date.now() / 1000 - 42, updated_at: Date.now() / 1000, status: "waiting_approval", step: 4, steps: ["Suchfunktion prüfen", "Leere Treffer abfangen", "Tests ausführen"], summary: "", changes: [{path: "src/search.ts", diff: "- return items;\n+ return items.filter(matchesQuery);"}], checks: [], specialists: [{role: "Codeprüfung", profil: "coding", question: "Ist die Behandlung leerer Eingaben korrekt?", status: "done", result: "Leere Eingaben liefern alle Einträge. Die Prüfung gehört in den bestehenden Suchtest."}], pending: {id: "approval-preview", notice: "Lokaler Testlauf im gewählten Projekt.", args: {command: "npm test", cwd: "C:\\Projekte\\Beispiel", timeout: 180}}, log: [{time: Date.now() / 1000, type: "running_command", tool: "", message: "npm test"}]};
window.fetch = async (input, init) => {
  const url = String(input);
  let data: unknown = {};
  if (url.includes("/tools")) data = {gruppen: [], skills: []};
  else if (url.endsWith("/projects")) data = [{id: "project", root: task.root, name: "Beispiel"}];
  else if (url.includes("/harness/project")) data = {root: task.root};
  else if (url.includes("/mini-jon/agent")) data = {config: {screen_enabled: false, screen_auto: false, privacy: false}, state: {}, destination: {local: true, available: true, model: "Vision", provider: "ollama", identity: "local"}};
  else if (url.includes("approve")) {task.status = "working"; task.pending = null as any; data = task;}
  else if (url.includes("cancel")) {task.status = "cancelled"; data = task;}
  else if (url.includes("/tasks/preview")) data = task;
  else if (url.includes("/settings")) data = {model: "qwen3-coder"};
  else if (url.includes("/harness/tasks")) data = [task];
  return new Response(JSON.stringify(data), {status: 200, headers: {"Content-Type": "application/json"}});
};
createRoot(document.getElementById("root")!).render(<><p style={{position: "fixed", top: 8, left: 16, color: "#aaa", fontSize: 12}}>UI-Prüfung mit Beispieldaten · keine echten Befehle</p><HarnessWorkspace onClose={() => {}} initialTask={new URLSearchParams(location.search).get("leer") ? undefined : "preview"}/></>);
