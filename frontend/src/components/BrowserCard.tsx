import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import "../maps/glass.css";
import {
  BrowserStatus,
  BrowserTaskDaten,
  confirmBrowserAction,
  getBrowserStatus,
  stopBrowser,
} from "../lib/api";
import type { MapsTheme } from "../lib/maps";
import { useT } from "../hooks/useT";

interface Props {
  data: BrowserTaskDaten;
}

function readTheme(): MapsTheme {
  return document.documentElement.classList.contains("light") ? "light" : "dark";
}

const RISIKO_FARBE: Record<string, string> = {
  niedrig: "var(--jm-text-soft)",
  mittel: "rgb(var(--jm-gold))",
  hoch: "#ff6b6b",
};

const STATUS_SCHLUESSEL: Record<string, string> = {
  bereit: "br_ready",
  plant: "br_planning",
  laeuft: "br_working",
  wartet_auf_bestaetigung: "br_waiting",
  fertig: "br_done",
  fehler: "br_error",
};

export default function BrowserCard({ data }: Props) {
  const [status, setStatus] = useState<BrowserStatus | null>(null);
  const [nachladen, setNachladen] = useState(0);
  const [busy, setBusy] = useState(false);
  const [entschieden, setEntschieden] = useState<"ja" | "nein" | null>(null);
  const { t } = useT();

  useEffect(() => {
    let alive = true;
    let timer = 0;
    let versuche = 0;
    const arbeitet = (wert: BrowserStatus | null) =>
      !!wert &&
      (wert.zustand?.status === "laeuft" ||
        wert.zustand?.status === "plant" ||
        wert.zustand?.status === "wartet_auf_bestaetigung" ||
        !!wert.bestaetigung);
    const laden = async () => {
      const wert = await getBrowserStatus();
      if (!alive) return;
      setStatus(wert);
      versuche += 1;
      if (arbeitet(wert) && versuche < 240) {
        timer = window.setTimeout(laden, 2500);
      }
    };
    void laden();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [nachladen]);

  const zustand = status?.zustand;
  const offen = status?.bestaetigung;
  const gate = data.bestaetigung;
  const token = offen?.token ?? gate?.token ?? "";
  const zusammenfassung = offen?.zusammenfassung ?? gate?.zusammenfassung ?? "";
  const wartet =
    !!token && !!zusammenfassung && entschieden === null && !offen?.verbraucht;
  const plan = data.plan;
  const schritte = plan?.schritte ?? [];
  const aktuell = zustand?.plan_schritt || plan?.aktueller_schritt || 0;

  const entscheiden = async (erlaubt: boolean) => {
    if (!token) return;
    setBusy(true);
    const ok = await confirmBrowserAction(token, erlaubt);
    setBusy(false);
    if (ok) setEntschieden(erlaubt ? "ja" : "nein");
  };

  return (
    <motion.div
      className="jm-root"
      data-jm-theme={readTheme()}
      style={{ height: "auto", marginTop: 4 }}
      initial={{ opacity: 0, y: 12, filter: "blur(10px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.44, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jm-glass" style={{ borderRadius: 20, overflow: "hidden" }}>
        <div className="jm-specular" />
        {zustand?.status === "laeuft" && <div className="jm-sheen-sweep" />}

        <div style={{ padding: "13px 15px 11px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
            <span
              className="jm-brand-mark"
              style={{ width: 22, height: 22, fontSize: 11 }}
            >
              🌐
            </span>
            <span
              className="jm-title"
              style={{ flex: 1, fontSize: 10.5, letterSpacing: "0.14em" }}
            >
              {t("br_title")}
            </span>
            <span
              className="jm-chip"
              style={{ cursor: "default", padding: "4px 10px", fontSize: 10.5 }}
              data-active={zustand?.status === "laeuft"}
            >
              {data.dry_run
                ? t("br_dryrun")
                : t(
                    (STATUS_SCHLUESSEL[zustand?.status ?? ""] ??
                      "br_done") as never
                  )}
            </span>
          </div>

          <div style={{ fontSize: 14.5, fontWeight: 620, marginTop: 9 }}>
            {plan?.ziel || data.auftrag}
          </div>

          <div
            style={{
              display: "flex",
              gap: 14,
              marginTop: 8,
              fontSize: 11.5,
              color: "var(--jm-text-soft)",
              flexWrap: "wrap",
            }}
          >
            {typeof data.schritte === "number" && (
              <span>🖱️ {t("br_actions", { n: data.schritte })}</span>
            )}
            {plan && (
              <span style={{ color: RISIKO_FARBE[plan.risiko] }}>
                ⚠️ {t("br_risk", { level: plan.risiko })}
              </span>
            )}
            {data.abbruch && <span>⏹️ {data.abbruch}</span>}
            {zustand?.letzte_aktion && zustand.status === "laeuft" && (
              <span>⚙️ {zustand.letzte_aktion}</span>
            )}
            <button
              onClick={() => setNachladen((wert) => wert + 1)}
              aria-label={t("br_refresh")}
              style={{
                background: "none",
                border: "none",
                padding: 0,
                cursor: "pointer",
                color: "var(--jm-text-faint)",
                font: "inherit",
              }}
            >
              ↻ {t("br_refresh")}
            </button>
          </div>

          {(zustand?.url || data.url) && (
            <div
              style={{
                marginTop: 8,
                fontSize: 11.5,
                color: "var(--jm-text-faint)",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {zustand?.titel || data.titel || ""} · {zustand?.url || data.url}
            </div>
          )}

          {schritte.length > 0 && (
            <div style={{ marginTop: 11, display: "grid", gap: 5 }}>
              {schritte.map((schritt) => {
                const fertig = schritt.id < aktuell;
                const laeuft = schritt.id === aktuell;
                return (
                  <div
                    key={schritt.id}
                    style={{
                      display: "flex",
                      gap: 8,
                      fontSize: 12,
                      lineHeight: 1.45,
                      opacity: fertig ? 0.55 : 1,
                    }}
                  >
                    <span style={{ flex: "0 0 auto", width: 16 }}>
                      {fertig ? "✅" : laeuft ? "▶️" : "○"}
                    </span>
                    <span style={{ flex: 1, minWidth: 0 }}>
                      {schritt.beschreibung}
                      {schritt.bestaetigung_noetig && (
                        <span
                          style={{
                            marginLeft: 6,
                            fontSize: 10.5,
                            color: RISIKO_FARBE.hoch,
                          }}
                        >
                          {t("br_confirm_needed")}
                        </span>
                      )}
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {data.hinweis && (
            <div
              style={{
                marginTop: 10,
                fontSize: 11.5,
                color: "var(--jm-text-faint)",
              }}
            >
              {data.hinweis}
            </div>
          )}
        </div>

        {wartet && (
          <>
            <div style={{ height: 1, background: "var(--jm-hairline)" }} />
            <div style={{ padding: "11px 15px 13px" }} role="group" aria-live="polite">
              <div
                style={{
                  fontSize: 11,
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  color: RISIKO_FARBE.hoch,
                  marginBottom: 6,
                }}
              >
                {t("br_confirm_needed")}
              </div>
              <pre
                style={{
                  margin: 0,
                  fontSize: 12,
                  lineHeight: 1.55,
                  whiteSpace: "pre-wrap",
                  fontFamily: "inherit",
                  color: "var(--jm-text)",
                }}
              >
                {zusammenfassung}
              </pre>
              <div style={{ display: "flex", gap: 7, marginTop: 11 }}>
                <button
                  className="jm-chip"
                  data-active="true"
                  disabled={busy}
                  onClick={() => void entscheiden(true)}
                >
                  ✅ {t("br_confirm")}
                </button>
                <button
                  className="jm-chip"
                  disabled={busy}
                  onClick={() => void entscheiden(false)}
                >
                  ✖️ {t("br_cancel")}
                </button>
              </div>
            </div>
          </>
        )}

        {entschieden && (
          <div
            style={{
              padding: "10px 15px 12px",
              fontSize: 12,
              color: "var(--jm-text-soft)",
            }}
          >
            {entschieden === "ja" ? t("br_released") : t("br_denied")}
          </div>
        )}

        {(status?.protokoll?.length ?? 0) > 0 && (
          <>
            <div style={{ height: 1, background: "var(--jm-hairline)" }} />
            <div className="jm-scroll" style={{ maxHeight: 132, padding: "8px 10px" }}>
              {status!.protokoll.slice(-14).map((zeile, index) => (
                <div
                  key={`${zeile.zeit}-${index}`}
                  className="jm-log-line"
                  style={{ fontSize: 11 }}
                >
                  <span style={{ minWidth: 0, flex: 1 }}>
                    <span style={{ fontWeight: 550 }}>{zeile.aktion}</span>{" "}
                    <span style={{ color: "var(--jm-text-faint)" }}>
                      {zeile.detail}
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </>
        )}

        {zustand?.aktiv && (
          <>
            <div style={{ height: 1, background: "var(--jm-hairline)" }} />
            <div style={{ display: "flex", gap: 7, padding: "10px 12px 12px" }}>
              <div style={{ flex: 1 }} />
              <button
                className="jm-chip"
                onClick={() => {
                  void stopBrowser().then(() => getBrowserStatus().then(setStatus));
                }}
              >
                ⏹️ {t("br_close_browser")}
              </button>
            </div>
          </>
        )}
      </div>
    </motion.div>
  );
}
