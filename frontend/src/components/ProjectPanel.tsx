import { useState } from "react";
import {
  JonProject,
  ProjectAnalysis,
  ProjectChanges,
  ProjectDiff,
} from "../lib/api";

interface Props {
  workspace: string;
  project: JonProject | null;
  analysis: ProjectAnalysis | null;
  busy: boolean;
  changes: ProjectChanges | null;
  diff: ProjectDiff | null;
  diffBusy: boolean;
  onAnalyze: () => void;
  onDiff: () => void;
  onNote: (note: string) => void;
}

function bytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export default function ProjectPanel({
  workspace,
  project,
  analysis,
  busy,
  changes,
  diff,
  diffBusy,
  onAnalyze,
  onDiff,
  onNote,
}: Props) {
  const [open, setOpen] = useState(true);
  const [note, setNote] = useState("");
  const [showDiff, setShowDiff] = useState(false);

  if (!workspace) return null;

  return (
    <div className="border-t border-white/10 bg-black/25 flex-none">
      <button
        onClick={() => setOpen((value) => !value)}
        className="w-full flex items-center gap-1.5 px-2.5 py-2 text-[11.5px] text-white/60 hover:text-white/85"
      >
        <span className="text-white/40">{open ? "▾" : "▸"}</span>
        <span className="font-semibold">Projekt</span>
        {analysis && (
          <span className="ml-auto text-[10.5px] text-white/35">
            {analysis.dateien} Dateien
          </span>
        )}
      </button>

      {open && (
        <div className="px-2.5 pb-2.5 max-h-[42vh] overflow-y-auto space-y-2">
          <div className="flex gap-1">
            <button
              onClick={onAnalyze}
              disabled={busy}
              className="flex-1 text-[11px] px-2 py-1 rounded-lg bg-gold/80 text-black font-medium disabled:opacity-40"
            >
              {busy ? "Analysiere …" : "Projekt analysieren"}
            </button>
            <button
              onClick={() => {
                setShowDiff(true);
                onDiff();
              }}
              disabled={diffBusy}
              className="text-[11px] px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 hover:bg-white/10 disabled:opacity-40"
              title="Git Diff anzeigen"
            >
              Git Diff
            </button>
          </div>

          {analysis && (
            <div className="space-y-1.5 text-[11.5px] text-white/65 leading-snug">
              <div className="text-white/80 font-semibold truncate" title={analysis.root}>
                {analysis.name}
              </div>
              <div>
                {analysis.dateien} Dateien · {analysis.ordner} Ordner ·{" "}
                {bytes(analysis.groesse_bytes)}
              </div>
              {analysis.projekttyp.length > 0 && (
                <div>Typ: {analysis.projekttyp.join(", ")}</div>
              )}
              {analysis.sprachen.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {analysis.sprachen.slice(0, 6).map((lang) => (
                    <span
                      key={lang.name}
                      className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 text-[10.5px]"
                    >
                      {lang.name} {lang.dateien}
                    </span>
                  ))}
                </div>
              )}
              {analysis.frameworks.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {analysis.frameworks.map((name) => (
                    <span
                      key={name}
                      className="px-1.5 py-0.5 rounded bg-gold/10 border border-gold/25 text-gold/85 text-[10.5px]"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              )}
              {Object.keys(analysis.skripte).length > 0 && (
                <div className="text-[10.5px] text-white/45">
                  Skripte: {Object.keys(analysis.skripte).slice(0, 6).join(", ")}
                </div>
              )}
              {analysis.git.repo ? (
                <div className="text-[10.5px] text-white/50">
                  🌿 {analysis.git.branch} · {analysis.git.geaendert} geändert
                  {analysis.git.letzter_commit
                    ? ` · ${analysis.git.letzter_commit}`
                    : ""}
                </div>
              ) : (
                <div className="text-[10.5px] text-white/35">Kein Git-Repository</div>
              )}
            </div>
          )}

          {changes && (
            <div className="rounded-lg border border-white/10 bg-black/30 p-2 text-[11px] text-white/65 space-y-1">
              <div className="text-white/80 font-semibold text-[11.5px]">
                Letzte Änderungen
              </div>
              <div>
                Geändert: {changes.anzahl.geaendert} · Erstellt:{" "}
                {changes.anzahl.erstellt} · Gelöscht: {changes.anzahl.geloescht}
              </div>
              {[...changes.geaendert, ...changes.erstellt]
                .slice(0, 8)
                .map((file) => (
                  <div key={file} className="truncate text-[10.5px] text-white/45">
                    {changes.erstellt.includes(file) ? "＋" : "●"} {file}
                  </div>
                ))}
            </div>
          )}

          {showDiff && diff && (
            <div className="rounded-lg border border-white/10 bg-black/40 p-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11.5px] text-white/75 font-semibold">
                  Git Diff
                </span>
                <button
                  onClick={() => setShowDiff(false)}
                  className="text-white/40 hover:text-white/80 text-[12px] leading-none"
                >
                  ×
                </button>
              </div>
              {diff.repo === false ? (
                <div className="text-[11px] text-white/45">
                  {diff.hinweis ?? "Kein Git-Repository."}
                </div>
              ) : diff.fehler ? (
                <div className="text-[11px] text-red-300/80">{diff.fehler}</div>
              ) : (
                <>
                  {diff.stat && (
                    <pre className="text-[10px] text-white/55 whitespace-pre-wrap mb-1">
                      {diff.stat}
                    </pre>
                  )}
                  <pre className="text-[10px] font-mono text-white/70 whitespace-pre-wrap max-h-56 overflow-y-auto">
                    {diff.diff || "Keine Änderungen im Arbeitsverzeichnis."}
                  </pre>
                  {diff.gekuerzt && (
                    <div className="text-[10px] text-white/35 mt-1">
                      Diff gekürzt.
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {project && (
            <div className="space-y-1">
              <div className="flex gap-1">
                <input
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && note.trim()) {
                      onNote(note.trim());
                      setNote("");
                    }
                  }}
                  placeholder="Projekt-Merkposten …"
                  className="flex-1 min-w-0 text-[11px] px-2 py-1 rounded-lg bg-black/40 border border-white/10 text-white/80 outline-none focus:border-gold/40"
                />
                <button
                  onClick={() => {
                    if (!note.trim()) return;
                    onNote(note.trim());
                    setNote("");
                  }}
                  disabled={!note.trim()}
                  className="text-[11px] px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/70 disabled:opacity-40"
                >
                  Merken
                </button>
              </div>
              {(project.notizen ?? []).slice(0, 5).map((entry, index) => (
                <div key={index} className="text-[10.5px] text-white/45 leading-snug">
                  • {entry}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
