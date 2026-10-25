from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

THREE = "0.169.0"
ARTEN = ("laufen", "fahren", "fliegen")
AUSSCHLUSS = ("boden", "umland", "ground", "floor", "plane", "himmel", "sky", "jon_kamera")


def dateiname(text: str, ersatz: str = "modell") -> str:
    roh = re.sub(r"[^\w-]+", "_", str(text or "").strip().lower(), flags=re.UNICODE).strip("_")
    return (roh or ersatz)[:40]


def _neueste(ordner: Path, stamm: str, endung: str) -> Path | None:
    kandidaten = [p for p in ordner.glob(f"{stamm}*.{endung}") if p.is_file()]
    if not kandidaten:
        return None
    return max(kandidaten, key=lambda p: p.stat().st_mtime)


def export_skript(ziel: Path) -> str:
    ausschluss = json.dumps(AUSSCHLUSS)
    return (
        "import bpy\n"
        f"_aus = {ausschluss}\n"
        "for _o in bpy.data.objects:\n"
        "    _name = _o.name.lower()\n"
        "    _gross = max(_o.dimensions) if _o.type == 'MESH' else 0.0\n"
        "    _o.select_set(_o.type in ('MESH', 'ARMATURE', 'EMPTY', 'CURVE') and not _name.startswith(tuple(_aus)) and _gross < 400.0)\n"
        f"bpy.ops.export_scene.gltf(filepath={json.dumps(str(ziel))}, export_format='GLB', use_selection=True, export_apply=True)\n"
        "print('JON_EXPORT_OK')\n"
    )


async def modell(auftrag: str, name: str, pfad: str, quelle: str = "harness") -> dict:
    from app.services.blender_service import ZEITGRENZE, get_blender_service

    text = " ".join(str(auftrag or "").split())
    if len(text) < 3:
        return {"error": "Beschreib, welches Modell entstehen soll."}
    ordner = Path(str(pfad or "").strip()) if str(pfad or "").strip() else None
    if ordner is None or not ordner.is_absolute():
        return {"error": "Gib in pfad den Projektordner des Spiels an."}
    stamm = dateiname(name or text[:30])
    dienst = get_blender_service()
    ergebnis = await dienst.szene(
        f"{text}. Es ist ein Spielmodell: steht am Ursprung, die Unterseite liegt auf z=0, "
        "vorne zeigt nach -Y, realistische Groesse in Metern, kraeftige Grundfarben als "
        "Materialien, keine riesigen Boeden oder Hintergruende.",
        projekt=stamm,
        rendern=True,
        export="",
        quelle=quelle,
    )
    if ergebnis.get("error"):
        return ergebnis
    blend = Path(ergebnis["blend"])
    assets = ordner / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    ziel = assets / f"{stamm}.glb"
    lauf = dienst._ausfuehren(export_skript(ziel), blend, ZEITGRENZE)
    if not lauf.get("ok") or not ziel.exists():
        return {"error": lauf.get("fehler") or "Der Export als .glb kam nicht an.", "blend": str(blend)}
    bild = _neueste(blend.parent, blend.stem, "png")
    vorschau = None
    if bild:
        vorschau_ziel = assets / f"{stamm}.png"
        shutil.copy2(bild, vorschau_ziel)
        vorschau = f"assets/{stamm}.png"
    return {
        "ok": True,
        "glb": f"assets/{stamm}.glb",
        "vorschau": vorschau,
        "groesse_kb": round(ziel.stat().st_size / 1024, 1),
        "blend": str(blend),
        "hinweis": (
            f"Laden mit GLTFLoader: new GLTFLoader().load('assets/{stamm}.glb', g => szene.add(g.scene)). "
            "Mit spiel_vorlage bekommst du ein fertiges, spielbares Grundgeruest, das die Modelle laedt."
        ),
    }


def vorlage(pfad: str, titel: str = "", art: str = "laufen", modelle: list | None = None) -> dict:
    ordner = Path(str(pfad or "").strip()) if str(pfad or "").strip() else None
    if ordner is None or not ordner.is_absolute():
        return {"error": "Gib in pfad den Projektordner des Spiels an."}
    art = art if art in ARTEN else "laufen"
    liste = [str(m).replace("\\", "/").lstrip("./") for m in (modelle or []) if str(m).strip()][:12]
    if not liste:
        liste = sorted(p.relative_to(ordner).as_posix() for p in (ordner / "assets").glob("*.glb")) if (ordner / "assets").exists() else []
    ordner.mkdir(parents=True, exist_ok=True)
    titel = " ".join(str(titel or "Mein Spiel").split())[:60] or "Mein Spiel"
    html = SEITE.replace("__TITEL__", titel).replace("__THREE__", THREE)
    js = SPIEL.replace("__MODELLE__", json.dumps(liste)).replace("__ART__", json.dumps(art)).replace("__TITEL__", json.dumps(titel))
    (ordner / "index.html").write_text(html, encoding="utf-8")
    (ordner / "spiel.js").write_text(js, encoding="utf-8")
    return {
        "ok": True,
        "dateien": ["index.html", "spiel.js"],
        "modelle": liste,
        "art": art,
        "hinweis": (
            "Startet ueber die Vorschau des Projekts (eigener kleiner Server, damit die .glb laden). "
            "Das erste Modell ist die Spielfigur, die weiteren stehen als Hindernisse und Deko in der Welt. "
            "Passe spiel.js an: Ziele, Gegner, Level, Sound."
        ),
    }


SEITE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITEL__</title>
<style>
html,body{margin:0;height:100%;overflow:hidden;background:#0b1020;font-family:system-ui,Segoe UI,sans-serif}
#anzeige{position:fixed;top:14px;left:14px;padding:10px 14px;border-radius:12px;background:rgba(8,12,28,.72);color:#f4f1e6;font-size:15px;line-height:1.5}
#anzeige b{color:#f4c542}
#meldung{position:fixed;inset:0;display:grid;place-items:center;pointer-events:none;color:#fff;font-size:42px;font-weight:800;text-shadow:0 4px 24px rgba(0,0,0,.6)}
#hilfe{position:fixed;bottom:12px;left:50%;transform:translateX(-50%);color:rgba(255,255,255,.75);font-size:13px;background:rgba(8,12,28,.55);padding:6px 12px;border-radius:999px}
</style>
<script type="importmap">{"imports":{"three":"https://unpkg.com/three@__THREE__/build/three.module.js","three/addons/":"https://unpkg.com/three@__THREE__/examples/jsm/"}}</script>
</head>
<body>
<div id="anzeige"></div>
<div id="meldung"></div>
<div id="hilfe"></div>
<script type="module" src="spiel.js"></script>
</body>
</html>
"""

SPIEL = """import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const MODELLE = __MODELLE__;
const ART = __ART__;
const TITEL = __TITEL__;

const leinwand = new THREE.WebGLRenderer({ antialias: true });
leinwand.setPixelRatio(Math.min(devicePixelRatio, 2));
leinwand.setSize(innerWidth, innerHeight);
leinwand.shadowMap.enabled = true;
leinwand.shadowMap.type = THREE.PCFSoftShadowMap;
leinwand.toneMapping = THREE.ACESFilmicToneMapping;
document.body.appendChild(leinwand.domElement);

const szene = new THREE.Scene();
szene.background = new THREE.Color(0x9fc7ea);
szene.fog = new THREE.Fog(0x9fc7ea, 120, 520);
const kamera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.1, 2000);

szene.add(new THREE.HemisphereLight(0xdcecff, 0x4a5a3a, 1.1));
const sonne = new THREE.DirectionalLight(0xfff1dc, 2.4);
sonne.position.set(60, 90, 40);
sonne.castShadow = true;
sonne.shadow.mapSize.set(2048, 2048);
Object.assign(sonne.shadow.camera, { left: -90, right: 90, top: 90, bottom: -90, far: 400 });
szene.add(sonne, sonne.target);

const boden = new THREE.Mesh(new THREE.PlaneGeometry(1200, 1200, 60, 60), new THREE.MeshStandardMaterial({ color: 0x6aa84f, roughness: 0.95 }));
boden.rotation.x = -Math.PI / 2;
boden.receiveShadow = true;
szene.add(boden);

const zufall = (() => { let s = 1337; return () => ((s = (s * 16807) % 2147483647) / 2147483647); })();
for (let i = 0; i < 70; i++) {
  const baum = new THREE.Group();
  const stamm = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.5, 3, 7), new THREE.MeshStandardMaterial({ color: 0x6b4a2b }));
  stamm.position.y = 1.5;
  const krone = new THREE.Mesh(new THREE.ConeGeometry(2.6, 6, 8), new THREE.MeshStandardMaterial({ color: 0x2f7d3b, flatShading: true }));
  krone.position.y = 5.5;
  stamm.castShadow = krone.castShadow = true;
  baum.add(stamm, krone);
  const w = zufall() * Math.PI * 2;
  const r = 40 + zufall() * 260;
  baum.position.set(Math.cos(w) * r, 0, Math.sin(w) * r);
  szene.add(baum);
}

const spieler = new THREE.Group();
szene.add(spieler);
const ersatz = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.8, 1.2), new THREE.MeshStandardMaterial({ color: 0xf4c542 }));
ersatz.position.y = 0.9;
ersatz.castShadow = true;
spieler.add(ersatz);

const hindernisse = [];
const lader = new GLTFLoader();
function schattenAn(objekt) {
  objekt.traverse((t) => { if (t.isMesh) { t.castShadow = true; t.receiveShadow = true; } });
}
function aufBoden(objekt, zielGroesse) {
  const kiste = new THREE.Box3().setFromObject(objekt);
  const groesse = kiste.getSize(new THREE.Vector3());
  const mass = zielGroesse ? zielGroesse / Math.max(groesse.x, groesse.y, groesse.z, 0.001) : 1;
  objekt.scale.multiplyScalar(mass);
  const neu = new THREE.Box3().setFromObject(objekt);
  objekt.position.y -= neu.min.y;
  return neu.getSize(new THREE.Vector3());
}
MODELLE.forEach((pfad, i) => {
  lader.load(pfad, (gltf) => {
    const modell = gltf.scene;
    schattenAn(modell);
    if (i === 0) {
      spieler.remove(ersatz);
      aufBoden(modell, ART === "fahren" ? 4.5 : ART === "fliegen" ? 9 : 1.9);
      spieler.add(modell);
      return;
    }
    for (let k = 0; k < 6; k++) {
      const kopie = modell.clone();
      const groesse = aufBoden(kopie, 0);
      const w = zufall() * Math.PI * 2;
      const r = 25 + zufall() * 160;
      kopie.position.x = Math.cos(w) * r;
      kopie.position.z = Math.sin(w) * r;
      kopie.rotation.y = zufall() * Math.PI * 2;
      szene.add(kopie);
      hindernisse.push({ objekt: kopie, radius: Math.max(groesse.x, groesse.z) * 0.5 });
    }
  }, undefined, () => meldung("Modell " + pfad + " fehlt", 2.5));
});

const sterne = [];
const sternForm = new THREE.TorusGeometry(0.8, 0.25, 10, 24);
const sternStoff = new THREE.MeshStandardMaterial({ color: 0xffd34d, emissive: 0x8a6400, metalness: 0.6, roughness: 0.3 });
for (let i = 0; i < 15; i++) {
  const stern = new THREE.Mesh(sternForm, sternStoff);
  const w = (i / 15) * Math.PI * 2;
  const r = 30 + (i % 5) * 28;
  stern.position.set(Math.cos(w) * r, ART === "fliegen" ? 12 + (i % 4) * 8 : 1.6, Math.sin(w) * r);
  stern.castShadow = true;
  szene.add(stern);
  sterne.push(stern);
}

const tasten = new Set();
addEventListener("keydown", (e) => { tasten.add(e.code); if (e.code === "KeyR") neu(); });
addEventListener("keyup", (e) => tasten.delete(e.code));
addEventListener("resize", () => { kamera.aspect = innerWidth / innerHeight; kamera.updateProjectionMatrix(); leinwand.setSize(innerWidth, innerHeight); });

const zustand = { tempo: 0, gier: 0, hoehe: 0, fallen: 0, punkte: 0, zeit: 0, fertig: false };
const anzeige = document.getElementById("anzeige");
const meldungFeld = document.getElementById("meldung");
document.getElementById("hilfe").textContent =
  ART === "fahren" ? "W/S Gas und Bremse · A/D lenken · R neu" : ART === "fliegen" ? "W/S schneller/langsamer · A/D drehen · Leertaste/Shift hoch/runter · R neu" : "W/A/S/D laufen · Shift rennen · Leertaste springen · R neu";
let meldungBis = 0;
function meldung(text, dauer) { meldungFeld.textContent = text; meldungBis = performance.now() + dauer * 1000; }
function neu() {
  Object.assign(zustand, { tempo: 0, gier: 0, hoehe: ART === "fliegen" ? 15 : 0, fallen: 0, punkte: 0, zeit: 0, fertig: false });
  spieler.position.set(0, zustand.hoehe, 0);
  sterne.forEach((s) => (s.visible = true));
  meldung(TITEL, 1.5);
}
neu();

function bewegen(dt) {
  const vor = (tasten.has("KeyW") || tasten.has("ArrowUp") ? 1 : 0) - (tasten.has("KeyS") || tasten.has("ArrowDown") ? 1 : 0);
  const seite = (tasten.has("KeyA") || tasten.has("ArrowLeft") ? 1 : 0) - (tasten.has("KeyD") || tasten.has("ArrowRight") ? 1 : 0);
  if (ART === "fahren") {
    zustand.tempo += vor * (vor > 0 ? 18 : 30) * dt;
    zustand.tempo -= Math.sign(zustand.tempo) * Math.min(Math.abs(zustand.tempo), (2 + Math.abs(zustand.tempo) * 0.25) * dt);
    zustand.tempo = THREE.MathUtils.clamp(zustand.tempo, -10, 42);
    zustand.gier += seite * dt * Math.min(1.6, Math.abs(zustand.tempo) / 8) * Math.sign(zustand.tempo || 1);
  } else if (ART === "fliegen") {
    zustand.tempo = THREE.MathUtils.clamp(zustand.tempo + vor * 12 * dt, 8, 60);
    zustand.gier += seite * dt * 0.9;
    zustand.hoehe = Math.max(2, zustand.hoehe + ((tasten.has("Space") ? 1 : 0) - (tasten.has("ShiftLeft") ? 1 : 0)) * 14 * dt);
  } else {
    const ziel = vor * (tasten.has("ShiftLeft") ? 11 : 6);
    zustand.tempo += (ziel - zustand.tempo) * Math.min(1, dt * 8);
    zustand.gier += seite * dt * 2.4;
    if (tasten.has("Space") && zustand.hoehe <= 0.001) zustand.fallen = 7;
    zustand.fallen -= 20 * dt;
    zustand.hoehe = Math.max(0, zustand.hoehe + zustand.fallen * dt);
  }
  const alt = spieler.position.clone();
  spieler.position.x += Math.sin(zustand.gier) * zustand.tempo * dt;
  spieler.position.z += Math.cos(zustand.gier) * zustand.tempo * dt;
  spieler.position.y = zustand.hoehe;
  for (const h of hindernisse) {
    const d = Math.hypot(spieler.position.x - h.objekt.position.x, spieler.position.z - h.objekt.position.z);
    if (d < h.radius + 1 && spieler.position.y < 4) {
      spieler.position.x = alt.x;
      spieler.position.z = alt.z;
      zustand.tempo *= -0.3;
    }
  }
  spieler.rotation.y = zustand.gier + Math.PI;
}

function kameraFuehren(dt) {
  const hinten = ART === "fliegen" ? 22 : ART === "fahren" ? 11 : 7;
  const hoch = ART === "fliegen" ? 7 : ART === "fahren" ? 4.5 : 3.2;
  const wunsch = new THREE.Vector3(spieler.position.x - Math.sin(zustand.gier) * hinten, spieler.position.y + hoch, spieler.position.z - Math.cos(zustand.gier) * hinten);
  kamera.position.lerp(wunsch, 1 - Math.exp(-dt * 5));
  kamera.lookAt(spieler.position.x, spieler.position.y + 1.4, spieler.position.z);
  sonne.position.set(spieler.position.x + 60, 90, spieler.position.z + 40);
  sonne.target.position.copy(spieler.position);
}

let letzte = performance.now();
function bild(nun) {
  const dt = Math.min(0.05, (nun - letzte) / 1000);
  letzte = nun;
  if (!zustand.fertig) {
    zustand.zeit += dt;
    bewegen(dt);
  }
  for (const s of sterne) {
    if (!s.visible) continue;
    s.rotation.y += dt * 2;
    if (s.position.distanceTo(spieler.position.clone().setY(spieler.position.y + 1)) < 2.6) {
      s.visible = false;
      zustand.punkte += 1;
      if (zustand.punkte === sterne.length) {
        zustand.fertig = true;
        meldung("Geschafft in " + zustand.zeit.toFixed(1) + " s", 99);
      }
    }
  }
  kameraFuehren(dt);
  anzeige.innerHTML = "<b>" + TITEL + "</b><br>Sterne " + zustand.punkte + " / " + sterne.length + "<br>Zeit " + zustand.zeit.toFixed(1) + " s";
  if (nun > meldungBis && !zustand.fertig) meldungFeld.textContent = "";
  leinwand.render(szene, kamera);
  requestAnimationFrame(bild);
}
requestAnimationFrame(bild);
"""
