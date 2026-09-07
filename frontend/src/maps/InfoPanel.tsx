import { useState } from "react";
import { motion } from "framer-motion";
import {
  InfoTarget,
  NewsArticle,
  PlaceInfo,
  formatNewsAge,
  weatherIcon,
} from "../lib/maps";

interface Props {
  target: InfoTarget;
  info: PlaceInfo | null;
  busy: boolean;
  error: string;
  onClose: () => void;
  onReload: () => void;
}

function Thumb({ article }: { article: NewsArticle }) {
  const [broken, setBroken] = useState(false);
  if (article.bild && !broken) {
    return (
      <img
        className="jm-news-thumb"
        src={article.bild}
        alt=""
        loading="lazy"
        referrerPolicy="no-referrer"
        onError={() => setBroken(true)}
      />
    );
  }
  return (
    <div className="jm-news-thumb jm-news-thumb--empty">
      {(article.quelle || "?").slice(0, 1).toUpperCase()}
    </div>
  );
}

function NewsSkeleton() {
  return (
    <div className="jm-news-card" data-skeleton="true">
      <div className="jm-news-thumb jm-news-thumb--empty" />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 7 }}>
        <div className="jm-shimmer" style={{ height: 11, width: "94%" }} />
        <div className="jm-shimmer" style={{ height: 11, width: "72%" }} />
        <div className="jm-shimmer" style={{ height: 9, width: "44%" }} />
      </div>
    </div>
  );
}

export default function InfoPanel({
  target,
  info,
  busy,
  error,
  onClose,
  onReload,
}: Props) {
  const weather = info?.wetter ?? null;
  const news = info?.news ?? [];
  const subtitle =
    target.scope === "land"
      ? "Land"
      : target.land && target.land !== target.name
        ? target.land
        : "Ort";

  return (
    <motion.aside
      className="jm-glass jm-info"
      initial={{ opacity: 0, x: 44, scale: 0.97, filter: "blur(18px)" }}
      animate={{ opacity: 1, x: 0, scale: 1, filter: "blur(0px)" }}
      exit={{ opacity: 0, x: 36, scale: 0.975, filter: "blur(14px)" }}
      transition={{ duration: 0.46, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jm-specular" />
      <div className="jm-info-head">
        <button
          className="jm-dock-btn jm-press"
          style={{ width: 32, height: 32, borderRadius: 999 }}
          onClick={onClose}
          title="Panel schließen"
        >
          ←
        </button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="jm-info-title">{target.name}</div>
          <div className="jm-info-sub">{subtitle}</div>
        </div>
        <button
          className="jm-dock-btn jm-press"
          style={{ width: 32, height: 32, borderRadius: 999 }}
          onClick={onReload}
          disabled={busy}
          title="Neu laden"
        >
          ↻
        </button>
      </div>

      <div className="jm-info-body jm-scroll">
        <div className="jm-info-section">
          <div className="jm-info-label">
            <span>📰</span> Top News
          </div>
          {busy && news.length === 0 && (
            <div className="jm-news-list">
              <NewsSkeleton />
              <NewsSkeleton />
              <NewsSkeleton />
            </div>
          )}
          {!busy && news.length === 0 && (
            <div className="jm-info-empty">
              {error || info?.news_fehler || "Keine Meldungen gefunden."}
            </div>
          )}
          {news.length > 0 && (
            <div className="jm-news-list">
              {news.map((article) => (
                <a
                  key={article.url}
                  className="jm-news-card jm-press"
                  href={article.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  title={article.titel}
                >
                  <Thumb article={article} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="jm-news-title">{article.titel}</div>
                    <div className="jm-news-meta">
                      <span className="jm-news-source">{article.quelle}</span>
                      {article.zeit && (
                        <>
                          <span className="jm-news-dot">·</span>
                          <span>{formatNewsAge(article.zeit)}</span>
                        </>
                      )}
                    </div>
                  </div>
                </a>
              ))}
            </div>
          )}
        </div>

        <div className="jm-info-section">
          <div className="jm-info-label">
            <span>{weatherIcon(weather?.code ?? null, weather?.tag ?? true)}</span>{" "}
            Wetter
          </div>
          {weather ? (
            <div className="jm-glass jm-glass--thin jm-weather">
              <div className="jm-specular" />
              <div className="jm-weather-top">
                <div className="jm-weather-temp">
                  {weather.temperatur == null
                    ? "–"
                    : `${Math.round(weather.temperatur)}°`}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="jm-weather-state">{weather.zustand}</div>
                  <div className="jm-weather-place">
                    {weather.ort || target.name}
                    {target.land && target.land !== weather.ort
                      ? `, ${target.land}`
                      : ""}
                  </div>
                </div>
                <div className="jm-weather-icon">
                  {weatherIcon(weather.code, weather.tag)}
                </div>
              </div>
              <div className="jm-weather-row">
                <span>
                  🌡️ Gefühlt{" "}
                  {weather.gefuehlt == null
                    ? "–"
                    : `${Math.round(weather.gefuehlt)}°`}
                </span>
                <span className="jm-weather-sep" />
                <span>
                  💧 Regen{" "}
                  {weather.regen_prozent == null
                    ? "–"
                    : `${Math.round(weather.regen_prozent)} %`}
                </span>
                <span className="jm-weather-sep" />
                <span>
                  🌬️ Wind{" "}
                  {weather.wind_kmh == null
                    ? "–"
                    : `${Math.round(weather.wind_kmh)} km/h`}
                </span>
              </div>
            </div>
          ) : busy ? (
            <div className="jm-glass jm-glass--thin jm-weather">
              <div className="jm-specular" />
              <div className="jm-weather-top">
                <div className="jm-shimmer" style={{ height: 34, width: 78 }} />
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 7 }}>
                  <div className="jm-shimmer" style={{ height: 12, width: "60%" }} />
                  <div className="jm-shimmer" style={{ height: 10, width: "40%" }} />
                </div>
              </div>
            </div>
          ) : (
            <div className="jm-info-empty">
              {info?.wetter_fehler || "Kein Wetter verfügbar."}
            </div>
          )}
        </div>
      </div>
    </motion.aside>
  );
}
