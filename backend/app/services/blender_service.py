from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from app.core.fehler import leise
from app.services.dateiindex_service import get_dateiindex_service, karte
from app.services.dateiraum_service import get_dateiraum_service, saeubern

ZEITGRENZE = 600
RENDER_GRENZE = 1200
MAX_VERSUCHE = 3

FORMATE = {
    "fbx": "export_scene.fbx",
    "obj": "wm.obj_export",
    "glb": "export_scene.gltf",
    "gltf": "export_scene.gltf",
    "stl": "wm.stl_export",
}

WINDOWS_ORTE = (
    r"C:\Program Files\Blender Foundation",
    r"C:\Program Files (x86)\Blender Foundation",
)

MAC_ORTE = ("/Applications/Blender.app/Contents/MacOS/Blender",)

LINUX_ORTE = ("/usr/bin/blender", "/usr/local/bin/blender", "/snap/bin/blender")

SKRIPT_SYSTEM = (
    "Du schreibst Python-Skripte fuer Blender (bpy). Antworte AUSSCHLIESSLICH mit dem "
    "Skript, ohne Erklaerung und ohne Code-Zaun.\n"
    "Regeln:\n"
    "- Beginne mit 'import bpy' und, wenn noetig, 'import math' oder 'import random'.\n"
    "- Die Szene ist bereits leer. Baue nur auf, was verlangt ist.\n"
    "- Setze immer eine Kamera und mindestens eine Lichtquelle, sodass ein Render "
    "etwas zeigt. Richte die Kamera so aus, dass das Motiv formatfuellend im Bild ist.\n"
    "- Benutze nur stabile bpy-Operatoren aus Blender 3.x/4.x.\n"
    "- Materialien setzt du ueber bpy.data.materials.new und use_nodes mit dem "
    "Principled BSDF; Eingaenge sprichst du ueber ihren Namen an "
    "(z.B. inputs['Base Color'], inputs['Metallic'], inputs['Roughness']).\n"
    "- Kein bpy.ops.wm.save_as_mainfile, kein Render, kein Export - das macht Jon.\n"
    "- Keine Addons, die nicht standardmaessig aktiv sind.\n"
    "- Kein Zugriff auf Dateien, kein Netzwerk, kein os/subprocess/sys."
)

REPARATUR_SYSTEM = (
    "Du reparierst ein fehlgeschlagenes Blender-Python-Skript. Du bekommst das Skript "
    "und die Fehlermeldung. Antworte AUSSCHLIESSLICH mit dem korrigierten vollstaendigen "
    "Skript, ohne Erklaerung und ohne Code-Zaun. Aendere genau das, was den Fehler "
    "ausloest, und behalte die Absicht bei."
)

VERBOTEN = re.compile(
    r"\b(import\s+(os|sys|subprocess|socket|shutil|requests|urllib)"
    r"|from\s+(os|sys|subprocess|socket|shutil|requests|urllib)\s+import"
    r"|__import__|eval\s*\(|exec\s*\(|open\s*\()",
)

KOPF = """import bpy

for _block in list(bpy.data.objects):
    bpy.data.objects.remove(_block, do_unlink=True)
for _sammlung in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
    for _eintrag in list(_sammlung):
        _sammlung.remove(_eintrag)
"""

FUSS = """
import bpy as _bpy

if _bpy.context.scene.camera is None:
    _kamera_daten = _bpy.data.cameras.new("JonKamera")
    _kamera = _bpy.data.objects.new("JonKamera", _kamera_daten)
    _bpy.context.collection.objects.link(_kamera)
    _kamera.location = (7.0, -7.0, 5.0)
    _kamera.rotation_euler = (1.1, 0.0, 0.785)
    _bpy.context.scene.camera = _kamera

if not [o for o in _bpy.data.objects if o.type == "LIGHT"]:
    _licht_daten = _bpy.data.lights.new("JonLicht", type="AREA")
    _licht_daten.energy = 900.0
    _licht_daten.size = 6.0
    _licht = _bpy.data.objects.new("JonLicht", _licht_daten)
    _bpy.context.collection.objects.link(_licht)
    _licht.location = (5.0, -5.0, 8.0)

_bpy.ops.wm.save_as_mainfile(filepath=__JON_BLEND__)
print("JON_OK objekte=%d" % len(_bpy.data.objects))
"""

RENDER_SKRIPT = """
import bpy as _bpy

_szene = _bpy.context.scene
_szene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [
    e.bl_idname for e in _bpy.types.RenderEngine.__subclasses__()
] else _szene.render.engine
_szene.render.image_settings.file_format = "PNG"
_szene.render.filepath = __JON_BILD__
_szene.render.resolution_x = __JON_BREITE__
_szene.render.resolution_y = __JON_HOEHE__
_szene.render.resolution_percentage = 100
_bpy.ops.render.render(write_still=True)
print("JON_RENDER_OK")
"""


def _fehlerzeilen(text: str, grenze: int = 700) -> str:
    zeilen = [z for z in str(text or "").splitlines() if z.strip()]
    wichtig = [
        z
        for z in zeilen
        if "Error" in z or "error" in z or "Traceback" in z or z.startswith("  ")
    ]
    return "\n".join(wichtig or zeilen[-12:])[:grenze]


class BlenderService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pfad: str | None = None
        self._version = ""

    def _suchen(self) -> str:
        gefunden = shutil.which("blender")
        if gefunden:
            return gefunden
        eigene = ""
        try:
            from app.services.settings_service import get_settings_service

            eigene = str(get_settings_service().get().get("blender_pfad", "") or "")
        except Exception as fehler:
            leise(fehler, "services/blender_service")
        if eigene and Path(eigene).exists():
            return eigene
        if sys.platform == "win32":
            for ort in WINDOWS_ORTE:
                basis = Path(ort)
                if not basis.is_dir():
                    continue
                kandidaten = sorted(basis.glob("Blender*/blender.exe"), reverse=True)
                if kandidaten:
                    return str(kandidaten[0])
        elif sys.platform == "darwin":
            for ort in MAC_ORTE:
                if Path(ort).exists():
                    return ort
        else:
            for ort in LINUX_ORTE:
                if Path(ort).exists():
                    return ort
        return ""

    def gefunden(self, neu: bool = False) -> dict:
        with self._lock:
            if self._pfad is None or neu:
                self._pfad = self._suchen()
                self._version = ""
            pfad = self._pfad
        if not pfad:
            return {
                "da": False,
                "hinweis": (
                    "Blender ist auf diesem Rechner nicht zu finden. Lade es bei "
                    "blender.org, oder trage den Pfad in den Einstellungen unter "
                    "blender_pfad ein."
                ),
            }
        if not self._version:
            try:
                lauf = subprocess.run(
                    [pfad, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=40,
                    encoding="utf-8",
                    errors="replace",
                )
                erste = (lauf.stdout or "").strip().splitlines()
                self._version = erste[0].strip() if erste else "Blender"
            except Exception as fehler:
                leise(fehler, "services/blender_service")
                self._version = "Blender"
        return {"da": True, "pfad": pfad, "version": self._version}

    def _ordner(self, projekt: str, wunsch: str) -> dict:
        if wunsch.strip():
            return get_dateiraum_service().zielordner(wunsch)
        basis = get_dateiraum_service().ordner("Blender")
        ziel = basis / saeubern(projekt or "Szene", "Szene")
        ziel.mkdir(parents=True, exist_ok=True)
        return {"pfad": str(ziel)}

    def _ausfuehren(self, skript: str, blend: Path | None, grenze: int) -> dict:
        stand = self.gefunden()
        if not stand["da"]:
            return {"ok": False, "fehler": stand["hinweis"], "fehlt": True}
        temp = get_dateiraum_service().ordner("Temp")
        datei = temp / f"jon-blender-{int(time.time() * 1000)}.py"
        datei.write_text(skript, encoding="utf-8")
        befehl = [stand["pfad"], "--background"]
        if blend is not None and blend.exists():
            befehl.append(str(blend))
        befehl += ["--factory-startup", "--python", str(datei)]
        umgebung = dict(os.environ)
        umgebung["PYTHONIOENCODING"] = "utf-8"
        try:
            lauf = subprocess.run(
                befehl,
                capture_output=True,
                text=True,
                timeout=grenze,
                encoding="utf-8",
                errors="replace",
                env=umgebung,
            )
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "fehler": f"Blender hat laenger als {grenze} Sekunden gebraucht.",
            }
        except Exception as exc:
            return {"ok": False, "fehler": f"Blender liess sich nicht starten: {exc}"}
        finally:
            try:
                datei.unlink()
            except OSError:
                pass
        ausgabe = (lauf.stdout or "") + "\n" + (lauf.stderr or "")
        erfolg = lauf.returncode == 0 and "Error:" not in ausgabe and "Traceback" not in ausgabe
        return {
            "ok": erfolg,
            "code": lauf.returncode,
            "ausgabe": ausgabe[-4000:],
            "fehler": "" if erfolg else _fehlerzeilen(ausgabe),
        }

    @staticmethod
    def _pruefen(skript: str) -> str:
        if VERBOTEN.search(skript or ""):
            return (
                "Das erzeugte Skript wollte auf Dateien, System oder Netzwerk "
                "zugreifen. Das lasse ich in Blender nicht zu."
            )
        if "bpy" not in (skript or ""):
            return "Das erzeugte Skript benutzt bpy gar nicht."
        return ""

    @staticmethod
    def _saeubern(roh: str) -> str:
        text = str(roh or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"```\s*$", "", text).strip()
        return text

    async def _skript_bauen(self, auftrag: str, fehler: str = "", vorher: str = "") -> str:
        from app.services.llm import complete

        if fehler and vorher:
            eingabe = f"Skript:\n{vorher[:4000]}\n\nFehler:\n{fehler[:800]}"
            return self._saeubern(
                await complete(REPARATUR_SYSTEM, eingabe, max_tokens=1800, temperature=0.2)
            )
        return self._saeubern(
            await complete(SKRIPT_SYSTEM, auftrag, max_tokens=1800, temperature=0.4)
        )

    async def szene(
        self,
        auftrag: str,
        projekt: str = "",
        wunsch: str = "",
        rendern: bool = True,
        export: str = "",
        quelle: str = "app",
    ) -> dict:
        sauber = " ".join(str(auftrag or "").split())[:400]
        if len(sauber) < 3:
            return {"error": "Was soll in der Szene entstehen?"}
        stand = self.gefunden()
        if not stand["da"]:
            return {"error": stand["hinweis"]}
        ordner = self._ordner(projekt or sauber[:40], wunsch)
        if ordner.get("error"):
            return ordner
        basis = Path(ordner["pfad"])
        name = saeubern(projekt or sauber[:40], "Szene")
        blend = get_dateiraum_service().eindeutig(basis, f"{name}.blend")
        protokoll: list[dict] = []
        skript = ""
        fehlertext = ""
        for versuch in range(1, MAX_VERSUCHE + 1):
            try:
                skript = await self._skript_bauen(sauber, fehlertext, skript)
            except Exception as exc:
                return {"error": f"Das Skript liess sich nicht erzeugen: {exc}"}
            einwand = self._pruefen(skript)
            if einwand:
                protokoll.append({"versuch": versuch, "ok": False, "fehler": einwand})
                fehlertext = einwand
                continue
            ganz = (
                KOPF
                + "\n"
                + skript
                + "\n"
                + FUSS.replace("__JON_BLEND__", json.dumps(str(blend)))
            )
            ergebnis = self._ausfuehren(ganz, None, ZEITGRENZE)
            protokoll.append(
                {
                    "versuch": versuch,
                    "ok": ergebnis["ok"],
                    "fehler": ergebnis.get("fehler", "")[:400],
                }
            )
            if ergebnis["ok"] and blend.exists():
                break
            if ergebnis.get("fehlt"):
                return {"error": ergebnis["fehler"]}
            fehlertext = ergebnis.get("fehler", "") or "Blender hat nichts gespeichert."
        else:
            return {
                "error": (
                    f"Blender ist nach {MAX_VERSUCHE} Versuchen nicht durchgelaufen. "
                    f"Letzter Fehler: {fehlertext[:300]}"
                ),
                "protokoll": protokoll,
            }
        dateien = [
            get_dateiindex_service().karte_und_merken(
                blend, name, sauber, projekt, "", quelle
            )
        ]
        bild = None
        if rendern:
            gerendert = self.rendern(blend, projekt=projekt, quelle=quelle)
            if gerendert.get("datei"):
                bild = gerendert["datei"]
                dateien.append(bild)
        ausgefuehrt = []
        for format_ in [f.strip() for f in str(export or "").split(",") if f.strip()]:
            aus = self.exportieren(blend, format_, projekt=projekt, quelle=quelle)
            if aus.get("datei"):
                dateien.append(aus["datei"])
                ausgefuehrt.append(format_)
            elif aus.get("error"):
                ausgefuehrt.append(f"{format_}: {aus['error']}")
        return {
            "ok": True,
            "auftrag": sauber,
            "blend": str(blend),
            "ordner": str(basis),
            "versuche": len(protokoll),
            "protokoll": protokoll,
            "render": bild,
            "export": ausgefuehrt,
            "dateien": dateien,
            "skript": skript[:2000],
        }

    def rendern(
        self,
        blend: str | Path,
        breite: int = 1280,
        hoehe: int = 720,
        projekt: str = "",
        quelle: str = "app",
    ) -> dict:
        datei = Path(blend)
        if not datei.exists():
            return {"error": f"Die Blender-Datei {datei.name} gibt es nicht."}
        ziel = get_dateiraum_service().eindeutig(datei.parent, f"{datei.stem}.png")
        skript = (
            RENDER_SKRIPT.replace("__JON_BILD__", json.dumps(str(ziel)))
            .replace("__JON_BREITE__", str(max(64, min(4096, int(breite)))))
            .replace("__JON_HOEHE__", str(max(64, min(4096, int(hoehe)))))
        )
        ergebnis = self._ausfuehren(skript, datei, RENDER_GRENZE)
        if not ergebnis["ok"] or not ziel.exists():
            return {
                "error": ergebnis.get("fehler") or "Der Render hat kein Bild erzeugt."
            }
        return {
            "ok": True,
            "datei": get_dateiindex_service().karte_und_merken(
                ziel, f"Render {datei.stem}", "", projekt, "", quelle
            ),
        }

    def exportieren(
        self,
        blend: str | Path,
        format_: str,
        projekt: str = "",
        quelle: str = "app",
    ) -> dict:
        datei = Path(blend)
        if not datei.exists():
            return {"error": f"Die Blender-Datei {datei.name} gibt es nicht."}
        endung = str(format_ or "").lower().lstrip(".")
        operator = FORMATE.get(endung)
        if not operator:
            return {
                "error": f"Format .{endung} kenne ich nicht.",
                "moeglich": sorted(FORMATE),
            }
        ziel = get_dateiraum_service().eindeutig(datei.parent, f"{datei.stem}.{endung}")
        zusatz = ""
        if endung in ("glb", "gltf"):
            zusatz = (
                f", export_format={json.dumps('GLB' if endung == 'glb' else 'GLTF_SEPARATE')}"
            )
        skript = (
            "import bpy as _bpy\n"
            "for _o in _bpy.data.objects:\n"
            "    _o.select_set(True)\n"
            f"_bpy.ops.{operator}(filepath={json.dumps(str(ziel))}{zusatz})\n"
            'print("JON_EXPORT_OK")\n'
        )
        ergebnis = self._ausfuehren(skript, datei, ZEITGRENZE)
        if not ergebnis["ok"] or not ziel.exists():
            return {
                "error": ergebnis.get("fehler") or f"Der Export nach .{endung} kam nicht an."
            }
        return {
            "ok": True,
            "datei": get_dateiindex_service().karte_und_merken(
                ziel, f"{datei.stem} als {endung.upper()}", "", projekt, "", quelle
            ),
        }

    async def skript_laufen(
        self, blend: str | Path, skript: str, quelle: str = "app"
    ) -> dict:
        einwand = self._pruefen(skript)
        if einwand:
            return {"error": einwand}
        datei = Path(blend)
        ergebnis = self._ausfuehren(
            skript + f"\nimport bpy as _b\n_b.ops.wm.save_mainfile()\n",
            datei if datei.exists() else None,
            ZEITGRENZE,
        )
        if not ergebnis["ok"]:
            return {"error": ergebnis.get("fehler") or "Blender meldete einen Fehler."}
        return {
            "ok": True,
            "datei": karte(datei) if datei.exists() else None,
            "ausgabe": ergebnis["ausgabe"][-600:],
        }

    def oeffnen(self, blend: str | Path) -> dict:
        stand = self.gefunden()
        if not stand["da"]:
            return {"error": stand["hinweis"]}
        datei = Path(blend)
        if not datei.exists():
            return {"error": f"Die Blender-Datei {datei.name} gibt es nicht."}
        try:
            subprocess.Popen([stand["pfad"], str(datei)])
        except Exception as exc:
            return {"error": f"Blender liess sich nicht oeffnen: {exc}"}
        return {"ok": True, "pfad": str(datei)}


_service: BlenderService | None = None


def get_blender_service() -> BlenderService:
    global _service
    if _service is None:
        _service = BlenderService()
    return _service
