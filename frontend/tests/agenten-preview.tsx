import React from "react";
import {createRoot} from "react-dom/client";
import {MotionConfig} from "framer-motion";
import MessageBubble, {ChatEntry} from "../src/components/MessageBubble";
import AgentenDock from "../src/components/agenten/AgentenDock";
import AgentTeam from "../src/components/AgentTeam";
import {harnessRequest} from "../src/lib/harness";
import "../src/index.css";

const start = Date.now() / 1000;
const params = new URLSearchParams(location.search);
const versatz = Number(params.get("t") || 0);
const jetzt = () => Date.now() / 1000 - start + versatz;

const teile = [
  {titel: "Wortformen prüfen", auftrag: "Bestimme Kasus und Funktion von puellam", rolle: "latin", rolle_name: "Latein"},
  {titel: "Übersetzung", auftrag: "Übersetze den Satz sinngemäß", rolle: "writing", rolle_name: "Schreiben & Sprache"},
  {titel: "Grammatik erklären", auftrag: "Erkläre den AcI Schritt für Schritt", rolle: "learning", rolle_name: "Lernen & Mathematik"},
];

function lauf() {
  const t = jetzt();
  const status = t < 2 ? "planning" : t < 9 ? "working" : t < 12 ? "verifying" : t < 14 ? "summarizing" : "done";
  return {
    id: "a".repeat(32), aufgabe: "Übersetze „Marcus dicit puellam legere“ und erkläre den AcI", source: "app", status, created_at: start - versatz, updated_at: Date.now() / 1000,
    teile: t < 2 ? [] : teile.map((teil, i) => {
      const fertig = t > 4 + i * 2;
      return {...teil, status: fertig ? "done" : "working", begonnen: start - versatz + 2, dauer: fertig ? 2 + i * 2 : undefined, ergebnis: fertig ? "puellam ist Akkusativ Singular und Subjekt des AcI." : ""};
    }),
    pruefung: t >= 12 ? {ok: true, probleme: [], korrektur: ""} : null,
    antwort: t >= 14 ? "Marcus sagt, dass das Mädchen liest. Der AcI besteht aus puellam (Subjektsakkusativ) und legere (Infinitiv)." : "",
  };
}

function harness() {
  const t = jetzt();
  const status = t < 2 ? "planning" : t < 6 ? "working" : t < 9 ? "waiting_approval" : t < 12 ? "verifying" : t < 15 ? "working" : "done";
  return {
    id: "h1", goal: "Suche im Projekt verbessern und Tests ergänzen", root: "C:\\Projekte\\Beispiel", source: "telegram:42", status, step: 4, companion: false, model: "qwen3-coder",
    steps: t < 2 ? [] : ["Suchfunktion lesen", "Leere Treffer abfangen", "Test ergänzen", "Tests ausführen"], summary: status === "done" ? "Leere Suchanfragen liefern jetzt eine leere Liste. Ein neuer Test deckt den Fall ab; alle Tests bestehen." : "",
    changes: t > 5 ? [{path: "src/search.ts", diff: "- return items;\n+ return query ? items.filter(matches) : [];"}, {path: "tests/search.test.ts", diff: "+ it('leer', () => expect(search('')).toEqual([]));\n+ "}] : [],
    checks: t > 11 ? [{command: "npm test", output: "12 passed", ok: true, exit_code: 0, revision: 2}] : [],
    specialists: t > 3 ? [{role: "Codeprüfung", profil: "coding", question: "Sind Randfälle abgedeckt?", status: t > 7 ? "done" : "working", result: t > 7 ? "Leere Eingaben sind jetzt abgedeckt." : ""}, {role: "Gestaltung", profil: "design", question: "Ist die Leeranzeige verständlich?", status: t > 10 ? "done" : "working"}] : [],
    pending: status === "waiting_approval" ? {id: "f1", notice: "Shellbefehle laufen mit deinen Benutzerrechten.", args: {command: "npm test -- search", cwd: "C:\\Projekte\\Beispiel", timeout: 180}} : null,
    log: [{time: Date.now() / 1000, type: "action", tool: t < 4 ? "read" : t < 6 ? "edit" : "verify", message: t < 4 ? "src/search.ts" : t < 6 ? "src/search.ts" : "npm test"}],
    created_at: start - versatz, updated_at: Date.now() / 1000,
  };
}

window.fetch = async (input) => {
  const url = String(input);
  let data: unknown = {};
  if (url.includes("/agents/live")) data = {teams: [lauf()], harness: [harness()]};
  else if (url.includes("/agents/profiles")) data = [{id: "latin", name: "Latein", focus: ""}, {id: "learning", name: "Lernen & Mathematik", focus: ""}, {id: "coding", name: "Programmierung", focus: ""}, {id: "research", name: "Recherche", focus: ""}, {id: "planning", name: "Alltagsplanung", focus: ""}, {id: "writing", name: "Schreiben & Sprache", focus: ""}, {id: "design", name: "Gestaltung", focus: ""}, {id: "general", name: "Fachanalyse", focus: ""}];
  else if (url.includes("/agents/runs?brief")) data = [{id: "a".repeat(32), aufgabe: lauf().aufgabe, source: "app", status: lauf().status, created_at: start}];
  else if (url.includes("/agents/runs/")) data = lauf();
  else if (url.includes("/harness/tasks/")) data = harness();
  return new Response(JSON.stringify(data), {status: 200, headers: {"Content-Type": "application/json"}});
};

const eintraege: ChatEntry[] = [
  {id: "1", role: "user", content: "Lass dein Fachteam den Satz übersetzen und den AcI erklären."},
  {id: "2", role: "assistant", content: "Ich habe mein Fachteam darauf angesetzt.", tools: [{name: "team", done: true, ok: true}], cards: [{id: "k1", kind: "agenten", data: {id: "a".repeat(32), aufgabe: "Übersetze den Satz"}}]},
  {id: "3", role: "user", content: "Und verbessere bitte die Suche in meinem Projekt."},
  {id: "4", role: "assistant", content: "Der Harness arbeitet im Projekt Beispiel.", tools: [{name: "harness_task", done: true, ok: true}], cards: [{id: "k2", kind: "harness", data: {id: "h1"}}]},
];

const ansicht = params.get("ansicht") || "chat";
if (params.get("hell")) document.documentElement.classList.add("light");
createRoot(document.getElementById("root")!).render(<MotionConfig reducedMotion="never">
  {ansicht === "chat" && <div style={{height: "100vh", overflow: "auto", padding: 24, display: "flex", flexDirection: "column", gap: 16, maxWidth: 820, margin: "0 auto"}}>{eintraege.map(e => <MessageBubble key={e.id} entry={e}/>)}</div>}
  {ansicht === "team" && <div style={{padding: 24, maxWidth: 640, margin: "0 auto", height: "100vh", overflow: "auto"}}><AgentTeam request={harnessRequest}/></div>}
  {ansicht === "dock" && <AgentenDock request={harnessRequest}/>}
</MotionConfig>);
