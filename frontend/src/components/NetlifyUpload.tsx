import { useEffect, useState } from "react";
import {
  NetlifyDeployResult,
  NetlifySite,
  NetlifyStatus,
  netlifyDeploy,
  netlifySetSite,
  netlifySetToken,
  netlifySites,
  netlifyStatus,
} from "../lib/api";

interface Props {
  onClose: () => void;
}

export default function NetlifyUpload({ onClose }: Props) {
  const [status, setStatus] = useState<NetlifyStatus | null>(null);
  const [sites, setSites] = useState<NetlifySite[]>([]);
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [result, setResult] = useState<NetlifyDeployResult | null>(null);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [pickSite, setPickSite] = useState(false);

  const refresh = async () => {
    try {
      const s = await netlifyStatus();
      setStatus(s);
      if (s.token_set && !s.site_id) void loadSites();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const loadSites = async () => {
    try {
      setSites(await netlifySites());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const saveToken = async () => {
    if (busy || !token.trim()) return;
    setBusy(true);
    setError("");
    try {
      await netlifySetToken(token.trim());
      setToken("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const chooseSite = async (site: NetlifySite) => {
    setBusy(true);
    setError("");
    try {
      setStatus(await netlifySetSite(site));
      setPickSite(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async () => {
    setBusy(true);
    setError("");
    try {
      await netlifySetToken("");
      setSites([]);
      setResult(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const deploy = async () => {
    if (deploying) return;
    setDeploying(true);
    setError("");
    setResult(null);
    try {
      setResult(await netlifyDeploy());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setDeploying(false);
    }
  };

  const ready = !!status?.token_set && !!status?.site_id;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="glass rounded-2xl border border-white/15 w-[560px] max-w-[95vw] max-h-[92vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-5 h-14 border-b border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-xl">🌐</span>
            <span className="text-[14px] text-white/90">Website hochladen</span>
            <span className="text-[11px] text-white/35">
              Jon lädt nur die Website hoch (~1 MB) — fertig in Sekunden
            </span>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full border border-white/10 bg-white/5 text-white/50 hover:text-white/90 transition"
          >
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {!status && !error && (
            <div className="text-[12px] text-white/40">Lade …</div>
          )}

          {status && !status.token_set && (
            <div className="space-y-3">
              <div className="text-[13px] text-white/80">
                Einmalig verbinden: Erstelle auf{" "}
                <a
                  href="https://app.netlify.com/user/applications#personal-access-tokens"
                  target="_blank"
                  rel="noreferrer"
                  className="text-gold underline"
                >
                  app.netlify.com/user/applications
                </a>{" "}
                einen „Personal Access Token" und füge ihn hier ein.
              </div>
              <div className="flex gap-2">
                <input
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && void saveToken()}
                  placeholder="Netlify-Token einfügen …"
                  type="password"
                  className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[13px] text-white/90 placeholder-white/25 outline-none focus:border-gold/40"
                />
                <button
                  onClick={() => void saveToken()}
                  disabled={busy || !token.trim()}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-gold-light to-gold-dark text-black font-semibold text-[12px] disabled:opacity-40 hover:brightness-110 transition"
                >
                  {busy ? "Prüfe …" : "Verbinden"}
                </button>
              </div>
              <div className="text-[11px] text-white/35">
                Der Token wird nur lokal bei Jon gespeichert.
              </div>
            </div>
          )}

          {status && status.token_set && (!status.site_id || pickSite) && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-[13px] text-white/80">Wähle deine Website:</div>
                <button
                  onClick={() => void loadSites()}
                  className="text-[11px] text-white/40 hover:text-gold transition"
                >
                  ↻ Neu laden
                </button>
              </div>
              {sites.length === 0 && (
                <div className="text-[12px] text-white/40">
                  Keine Websites gefunden. Lade die Liste neu oder lege die Website einmal
                  bei Netlify an.
                </div>
              )}
              {sites.map((site) => (
                <button
                  key={site.id}
                  onClick={() => void chooseSite(site)}
                  disabled={busy}
                  className="w-full text-left px-3 py-2.5 rounded-xl border border-white/10 bg-white/5 hover:border-gold/40 hover:bg-gold/10 transition"
                >
                  <div className="text-[13px] text-white/90">{site.name}</div>
                  <div className="text-[11px] text-white/40">{site.url}</div>
                </button>
              ))}
              {pickSite && (
                <button
                  onClick={() => setPickSite(false)}
                  className="text-[11px] text-white/40 hover:text-white/70 transition"
                >
                  Abbrechen
                </button>
              )}
            </div>
          )}

          {ready && !pickSite && (
            <div className="space-y-4">
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragOver(false);
                  void deploy();
                }}
                onClick={() => void deploy()}
                className={`cursor-pointer rounded-2xl border-2 border-dashed px-6 py-10 text-center transition ${
                  dragOver
                    ? "border-gold bg-gold/15"
                    : "border-white/20 bg-white/5 hover:border-gold/50 hover:bg-gold/5"
                }`}
              >
                {deploying ? (
                  <div className="space-y-2">
                    <div className="text-3xl animate-bounce">🚀</div>
                    <div className="text-[13px] text-gold">
                      Lade hoch … Jon packt die Website und schickt sie zu Netlify.
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="text-3xl">📁</div>
                    <div className="text-[14px] text-white/90 font-medium">
                      Zieh deinen kompletten Jon-Ordner hier rein
                    </div>
                    <div className="text-[12px] text-white/40">
                      oder klick einfach — Jon nimmt die Dateien direkt von der
                      Festplatte, baut jon.zip frisch und lädt nur die Website hoch
                    </div>
                  </div>
                )}
              </div>

              {result && (
                <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 space-y-1">
                  <div className="text-[13px] text-emerald-300 font-medium">
                    ✅ Website ist live!
                  </div>
                  <div className="text-[12px] text-white/70">
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-gold underline"
                    >
                      {result.url}
                    </a>
                  </div>
                  <div className="text-[11px] text-white/40">
                    {result.dauer}s · {result.zip_kb} KB hochgeladen
                    {result.jon_zip_dateien > 0 &&
                      ` · jon.zip mit ${result.jon_zip_dateien} Dateien neu gebaut`}
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between text-[11px] text-white/35">
                <div>
                  Website: <span className="text-white/60">{status?.site_name}</span>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setPickSite(true);
                      void loadSites();
                    }}
                    className="hover:text-gold transition"
                  >
                    Website wechseln
                  </button>
                  <button onClick={() => void disconnect()} className="hover:text-red-300 transition">
                    Trennen
                  </button>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-[12px] text-red-300">
              {error}
            </div>
          )}
        </div>

        <div className="px-5 py-2 border-t border-white/10 text-[11px] text-white/30">
          Früher wurde beim Drag&Drop auf netlify.com der ganze Ordner (über 1 GB) in den
          Browser geladen — deshalb dauerte es 15 Minuten. Hier passiert das nicht.
        </div>
      </div>
    </div>
  );
}
