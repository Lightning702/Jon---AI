import { motion } from "framer-motion";

interface Props {
  bearing: number;
  pitch: number;
  is3d: boolean;
  isGlobe: boolean;
  isEarth: boolean;
  layersOpen: boolean;
  onZoom: (delta: number) => void;
  onResetNorth: () => void;
  onToggle3d: () => void;
  onToggleGlobe: () => void;
  onToggleEarth: () => void;
  onLayers: () => void;
  onLocate: () => void;
  onExplore: () => void;
  onStreet: () => void;
}

export default function ControlDock({
  bearing,
  pitch,
  is3d,
  isGlobe,
  isEarth,
  layersOpen,
  onZoom,
  onResetNorth,
  onToggle3d,
  onToggleGlobe,
  onToggleEarth,
  onLayers,
  onLocate,
  onExplore,
  onStreet,
}: Props) {
  return (
    <motion.div
      className="jm-scroll"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        maxHeight: "calc(100vh - 150px)",
        overflowY: "auto",
        paddingRight: 2,
      }}
      initial={{ opacity: 0, x: 22, filter: "blur(12px)" }}
      animate={{ opacity: 1, x: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.5, delay: 0.05, ease: [0.22, 1, 0.36, 1] }}
    >
      <div className="jm-glass jm-glass--chrome jm-dock">
        <div className="jm-specular" />
        <button
          className="jm-dock-btn"
          onClick={() => onZoom(1)}
          title="Hineinzoomen"
        >
          ＋
        </button>
        <button
          className="jm-dock-btn"
          onClick={() => onZoom(-1)}
          title="Herauszoomen"
        >
          －
        </button>
        <div className="jm-dock-sep" />
        <button
          className="jm-dock-btn jm-compass"
          onClick={onResetNorth}
          title={`Nach Norden ausrichten (${Math.round(bearing)}°)`}
        >
          <span
            className="jm-compass-needle"
            style={{ transform: `rotate(${-bearing}deg)` }}
          />
        </button>
      </div>

      <div className="jm-glass jm-glass--chrome jm-dock">
        <div className="jm-specular" />
        <button
          className="jm-dock-btn"
          data-active={is3d}
          onClick={onToggle3d}
          title={is3d ? "Zurück auf 2D" : "3D einschalten"}
          style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.04em" }}
        >
          {is3d ? "3D" : "2D"}
        </button>
        <button
          className="jm-dock-btn"
          data-active={isGlobe}
          onClick={onToggleGlobe}
          title={isGlobe ? "Zurück zur Karte" : "Globus-Ansicht"}
        >
          {isGlobe ? "🗺️" : "🌍"}
        </button>
        <button
          className="jm-dock-btn"
          data-active={isEarth}
          onClick={onToggleEarth}
          title={
            isEarth
              ? "Erde-Ansicht aus"
              : "Erde: Satellit, echtes Gelände und 3D-Gebäude zusammen"
          }
        >
          🌎
        </button>
        <div className="jm-dock-sep" />
        <button
          className="jm-dock-btn"
          data-active={layersOpen}
          onClick={onLayers}
          title="Ebenen"
        >
          ▦
        </button>
      </div>

      <div className="jm-glass jm-glass--chrome jm-dock">
        <div className="jm-specular" />
        <button
          className="jm-dock-btn"
          onClick={onStreet}
          title="Street Exploration an dieser Stelle"
        >
          👁️
        </button>
        <button
          className="jm-dock-btn"
          onClick={onExplore}
          title="Abheben und die Welt im Flugzeug erkunden"
        >
          ✈️
        </button>
        <div className="jm-dock-sep" />
        <button className="jm-dock-btn" onClick={onLocate} title="Mein Standort">
          ◎
        </button>
      </div>

      <div
        className="jm-glass jm-glass--thin"
        style={{
          padding: "7px 11px",
          borderRadius: 14,
          fontSize: 10,
          textAlign: "center",
          color: "var(--jm-text-faint)",
        }}
        title="Neigung der Karte"
      >
        {Math.round(pitch)}°
      </div>
    </motion.div>
  );
}
