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
from app.services.blender_bausteine import BAUSTEINE, GLANZ, PRUEFUNG
from app.services.blender_bauwerke import BAUWERKE
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
    "- Die Szene ist leer. Einheiten sind Meter, z zeigt nach oben, der Boden liegt bei "
    "z=0. Stelle alles auf den Boden (nichts schwebt, nichts steckt im Boden) und halte "
    "echte Groessen ein: Tuer 2.1 m, Stockwerk 2.8 m, Tisch 0.75 m, Stuhlsitz 0.45 m, "
    "Auto 4.3 m. Baue mit Liebe zum Detail: Materialien, Proportionen, eine stimmige "
    "Umgebung.\n"
    "- Halte das Skript kurz (hoechstens etwa 150 Zeilen): Schleifen, Hilfsfunktionen und "
    "vor allem Jons fertige Bausteine. Ein abgeschnittenes Skript ist wertlos.\n"
    "- Fertige Bausteine, schon definiert, einfach aufrufen:\n"
    "  Umgebung: jon_himmel(zeit='tag'|'morgen'|'abend'|'nacht'|'bewoelkt') setzt Himmel "
    "und Sonne. jon_boden(art='gras'|'asphalt'|'pflaster'|'sand'|'schnee'|'wasser'|'erde'|"
    "'beton'|'holz'|'fliesen', groesse=160). jon_studio(farbe=(r, g, b)) baut NACH dem "
    "Motiv eine Fotostudio-Hohlkehle mit drei Lichtern, ideal fuer einzelne Objekte.\n"
    "  Gebaeude und Landschaft: jon_haus(breite=9, tiefe=7, stockwerke=1, dach='sattel'|"
    "'flach', wandfarbe, dachfarbe, ort=(x, y, 0), drehung=0, kamin=True, "
    "fensterlaeden=False) mit eingelassenen Fenstern, Haustuer, Stufe, Vordach, "
    "Ziegeldach und Regenrinne, Vorderseite zeigt nach -y. jon_baum(ort, hoehe=6, "
    "art='laub'|'nadel'). jon_wald(anzahl=30, flaeche=(40, 40), mitte=(x, y, 0), "
    "frei=[(x, y, radius)]). jon_stadt(bloecke=4, hoehe=(9, 60), blick='schraeg'|"
    "'strasse') baut eine ganze Stadt mit Strassen, Zebrastreifen, Hochhaeusern, "
    "Baeumen, Laternen, Autos und Kamera. jon_auto(ort, drehung, farbe). "
    "jon_laterne(ort, drehung).\n"
    "  Innenraeume: jon_raum(breite=6, tiefe=5, hoehe=2.7, wandfarbe, boden='holz'|"
    "'fliesen'|'teppich'|'beton', fenster='hinten'|'links'|'rechts'|None) baut Boden, drei "
    "Waende mit Fenster, Deckenlicht und stellt die Kamera schon richtig an die offene "
    "Vorderseite. Der Raum reicht von x=-breite/2 bis breite/2 und von y=-tiefe/2 (offen, "
    "Kamera) bis y=tiefe/2 (Rueckwand). Moebel stehen mit ort=(x, y, 0) auf dem Boden, "
    "drehung in Grad: 0 heisst Vorderseite zur Kamera (-y), 90 nach +x, -90 nach -x, 180 "
    "nach +y. Moebel an der Rueckwand brauchen KEINE Drehung: jon_sofa(ort=(0, tiefe/2 - "
    "0.55, 0)), jon_kueche(ort=(0, tiefe/2 - 0.32, 0)); an der linken Wand drehung=90, an "
    "der rechten drehung=-90. Moebel an einer Wand dreht Jon zur Sicherheit zum Raum, Bilder "
    "haengt er an die naechste Wand. Die Kueche kommt an eine Wand ohne Fenster. Moebel: "
    "jon_sofa(farbe, breite=2.2), jon_sessel, jon_tisch(breite, tiefe, hoehe), "
    "jon_couchtisch, jon_stuhl, jon_bett, jon_schrank, jon_regal(buecher=True), "
    "jon_kueche(breite=3), jon_fernseher(zoll=55), jon_teppich(groesse=(2.4, 1.7)), "
    "jon_pflanze(groesse=1), jon_lampe(art='steh'|'tisch'|'decke'; Tischlampe mit "
    "ort=(x, y, tischhoehe), Haengelampe mit ort=(x, y, raumhoehe)), jon_bild(ort=(x, y, z)) "
    "fuer ein Bild an der Wand.\n"
    "  Uhren: jon_uhr(durchmesser=0.6, uhrzeit=(10, 10, 32), ziffern='roemisch'|"
    "'arabisch'|'striche', stil='wand'|'wecker', gehaeusefarbe, zifferblattfarbe, ort, glas=False) "
    "mit Gehaeuse, Minutenstrichen, Ziffern, Zeigern und Kamera. Steht die Uhr allein "
    "in der Szene, haengt Jon sie an eine Wand (den Wecker auf einen Tisch) und setzt Licht.\n"
    "  Weltraum: jon_sternenhimmel(), jon_schwarzes_loch(groesse=1, neigung=9, "
    "scheibenfarbe, leuchten=6) mit Akkretionsscheibe, Photonenring, gelinster Scheibe "
    "und Kamera, jon_planet(radius, farbe, ort, ringe=False, atmosphaere=True), "
    "jon_sonne(radius, ort), jon_galaxie(arme=2, sterne=5000, radius=6).\n"
    "  Materialien: jon_material(name, farbe, metall=0, rau=0.5, leuchten=0), "
    "jon_leuchtmaterial(name, farbe, staerke), jon_holz(name, farbe, dielen=False), "
    "jon_putz(name, farbe), jon_ziegel(name, farbe), jon_dachziegel(name, farbe), "
    "jon_stoff(name, farbe), jon_glas(name, farbe, deckkraft=0.12), jon_metall(name, "
    "farbe, rau), jon_fliesen(name, farbe), jon_fassade(name, wandfarbe, glasfarbe).\n"
    "  Eigene Formen: bau = JonBau('Name'); bau.quader(mitte, (breite, tiefe, hoehe), "
    "material, drehung=(rx, ry, rz)); bau.zylinder(mitte, radius, hoehe, material, "
    "oben=None, drehung=(rx, ry, rz)); bau.kugel(mitte, radius, material, streckung=(sx, "
    "sy, sz)); objekt = bau.fertig(ort=(x, y, z), drehung=0, fase=0.01). Alle Teile werden "
    "ein Objekt mit sauberen Kanten; Winkel in Grad.\n"
    "- Kamera: jon_kamera(richtung=(x, y, z), brennweite=50, objekte=None) setzt sie aus "
    "der Richtung (vom Motiv zur Kamera) formatfuellend. Fuer Gebaeude passt "
    "richtung=(1, -1.3, 0.45) mit brennweite=35. Stelle Baeume und Deko seitlich oder "
    "hinter das Motiv, nie zwischen Kamera und Motiv. jon_raum, jon_stadt, jon_uhr und "
    "jon_schwarzes_loch setzen die Kamera selbst, danach kein jon_kamera mehr. Ohne Aufruf "
    "prueft Jon am Ende, ob alles im Bild ist. jon_kamera_fest() verhindert jede Korrektur.\n"
    "- Licht: jon_himmel setzt Sonne und Himmel; fehlt Licht ganz, setzt Jon eines.\n"
    "- Eigene Materialien: bpy.data.materials.new, use_nodes, Principled BSDF mit den "
    "Blender-4-Namen inputs['Base Color'], inputs['Metallic'], inputs['Roughness'], "
    "inputs['Alpha'], inputs['Emission Color'], inputs['Emission Strength'].\n"
    "- Beispiel: import bpy / jon_himmel('abend') / jon_boden('gras') / "
    "jon_haus(stockwerke=2) / jon_baum((-9, 5, 0)) / jon_kamera(richtung=(1, -1.3, 0.42), "
    "brennweite=35)\n"
    "- Kein bpy.ops.wm.save_as_mainfile, kein Render, kein Export und keine Einstellungen "
    "an Render-Engine oder Farbmanagement - das macht Jon.\n"
    "- Keine Addons, die nicht standardmaessig aktiv sind.\n"
    "- Kein Zugriff auf Dateien, kein Netzwerk, kein os/subprocess/sys."
)

REPARATUR_SYSTEM = (
    "Du reparierst ein fehlgeschlagenes Blender-Python-Skript. Du bekommst das Skript "
    "und die Fehlermeldung. Antworte AUSSCHLIESSLICH mit dem korrigierten vollstaendigen "
    "Skript, ohne Erklaerung und ohne Code-Zaun. Aendere genau das, was den Fehler "
    "ausloest, und behalte die Absicht bei. Zeilennummern beziehen sich auf das Skript. "
    "Jons Bausteine (alle Funktionen jon_..., die Klasse JonBau) sind bereits definiert, "
    "lass ihre Aufrufe stehen. Blender 4: Principled-Eingaenge heissen 'Specular IOR "
    "Level', 'Emission Color', 'Transmission Weight', 'Coat Weight', 'Subsurface Weight', "
    "'Sheen Weight'; scene.eevee.use_bloom, use_ssr, use_gtao und mesh.use_auto_smooth gibt "
    "es nicht mehr."
)

KUERZER = (
    "\n\nWICHTIG: Dein letztes Skript war zu lang und wurde mitten im Code abgeschnitten. "
    "Schreibe es neu und deutlich kuerzer, hoechstens 120 Zeilen, mit Schleifen und Jons "
    "Bausteinen."
)

ALTE_EINGAENGE = {
    "Specular": "Specular IOR Level",
    "Subsurface": "Subsurface Weight",
    "Transmission": "Transmission Weight",
    "Clearcoat": "Coat Weight",
    "Clearcoat Roughness": "Coat Roughness",
    "Clearcoat Normal": "Coat Normal",
    "Sheen": "Sheen Weight",
    "Emission": "Emission Color",
}

ALTE_NAMEN = re.compile(
    r"inputs\[(['\"])(" + "|".join(sorted(map(re.escape, ALTE_EINGAENGE), key=len, reverse=True)) + r")\1\]"
)

WACKELIG = re.compile(
    r"^(?P<einzug>[ \t]*)(?P<befehl>[A-Za-z_][\w.\[\]'\"]*\.(?:eevee\.\w+|shadow_method|"
    r"blend_method|show_transparent_back|use_screen_refraction|use_auto_smooth|"
    r"auto_smooth_angle|render\.engine|view_transform|look|use_ssr\w*)\s*=[^=].*)$",
    re.MULTILINE,
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
""" + BAUSTEINE + BAUWERKE

FUSS = "\nimport bpy\n" + PRUEFUNG + """
bpy.ops.wm.save_as_mainfile(filepath=__JON_BLEND__)
print("JON_OK objekte=%d" % len(bpy.data.objects))
"""

RENDER_SKRIPT = "import bpy\nimport math\n" + GLANZ + """
_szene = bpy.context.scene
for _maschine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        _szene.render.engine = _maschine
        break
    except TypeError:
        continue
for _ansicht in ("AgX", "Filmic"):
    try:
        _szene.view_settings.view_transform = _ansicht
        break
    except TypeError:
        continue
for _blick in ("AgX - Medium High Contrast", "Medium High Contrast"):
    try:
        _szene.view_settings.look = _blick
        break
    except TypeError:
        continue
for _schalter in ("use_raytracing", "use_gtao", "use_ssr", "use_ssr_refraction", "use_soft_shadows"):
    if hasattr(_szene.eevee, _schalter):
        setattr(_szene.eevee, _schalter, True)
print("JON_GLANZ=%s" % _jon_glanz(_szene))
_bpy = bpy
_szene.render.image_settings.file_format = "PNG"
_szene.render.filepath = __JON_BILD__
_szene.render.resolution_x = __JON_BREITE__
_szene.render.resolution_y = __JON_HOEHE__
_szene.render.resolution_percentage = 100
_bpy.ops.render.render(write_still=True)
print("JON_RENDER_OK")
"""


def _fehlerzeilen(text: str, grenze: int = 700, versatz: int = 0) -> str:
    def umrechnen(treffer: re.Match) -> str:
        nummer = int(treffer.group(1))
        if versatz and nummer > versatz:
            return f"Skript, Zeile {nummer - versatz}"
        return "Jons Bausteine" if versatz else f"Zeile {nummer}"

    text = re.sub(r'File "[^"]*jon-blender-[^"]*", line (\d+)', umrechnen, str(text or ""))
    zeilen = [z for z in text.splitlines() if z.strip()]
    wichtig = [
        z
        for z in zeilen
        if "Error" in z or "error" in z or "Traceback" in z or z.startswith("  ")
    ]
    return "\n".join(wichtig or zeilen[-12:])[-grenze:]


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
            if self._pfad is None or neu or not self._pfad or not Path(self._pfad).exists():
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

    def _ausfuehren(
        self, skript: str, blend: Path | None, grenze: int, versatz: int = 0
    ) -> dict:
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
            "fehler": "" if erfolg else _fehlerzeilen(ausgabe, versatz=versatz),
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

    def _anpassen(self, skript: str) -> str:
        treffer = re.search(r"(\d+)\.(\d+)", self._version or "")
        if treffer is None or int(treffer.group(1)) >= 4:
            skript = ALTE_NAMEN.sub(
                lambda t: f"inputs[{t.group(1)}{ALTE_EINGAENGE[t.group(2)]}{t.group(1)}]", skript
            )
        def absichern(treffer: re.Match) -> str:
            befehl = treffer.group("befehl").rstrip()
            offen = sum(befehl.count(z) for z in "([{") - sum(befehl.count(z) for z in ")]}")
            if offen or befehl.endswith(("\\", ":")):
                return treffer.group(0)
            einzug = treffer.group("einzug")
            return f"{einzug}try: {befehl}\n{einzug}except Exception: pass"

        return WACKELIG.sub(absichern, skript)

    @staticmethod
    def _syntax(skript: str) -> tuple[str, bool]:
        try:
            compile(skript, "skript", "exec")
        except SyntaxError as fehler:
            zeilen = skript.splitlines()
            nummer = int(fehler.lineno or 0)
            meldung = str(fehler.msg or "")
            abgeschnitten = nummer >= len(zeilen) - 3 and any(
                wort in meldung
                for wort in ("never closed", "EOF", "unterminated", "expected an indented block", "was not closed")
            )
            zeile = zeilen[nummer - 1].strip() if 0 < nummer <= len(zeilen) else ""
            return f"SyntaxError: {meldung} (Skript, Zeile {nummer})" + (f"\n    {zeile}" if zeile else ""), abgeschnitten
        return "", False

    @staticmethod
    def _saeubern(roh: str) -> str:
        text = str(roh or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"```\s*$", "", text).strip()
        return text

    async def _skript_bauen(
        self, auftrag: str, fehler: str = "", vorher: str = "", kuerzer: bool = False
    ) -> str:
        from app.services.llm import complete

        if fehler and vorher and not kuerzer:
            eingabe = f"Skript:\n{vorher[:24000]}\n\nFehler:\n{fehler[-1200:]}"
            return self._saeubern(
                await complete(REPARATUR_SYSTEM, eingabe, max_tokens=9000, temperature=0.2)
            )
        return self._saeubern(
            await complete(
                SKRIPT_SYSTEM,
                auftrag + (KUERZER if kuerzer else ""),
                max_tokens=9000,
                temperature=0.4,
            )
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
        sauber = " ".join(str(auftrag or "").split())[:1500]
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
        kuerzer = False
        versatz = KOPF.count("\n") + 1
        for versuch in range(1, MAX_VERSUCHE + 1):
            try:
                skript = await self._skript_bauen(sauber, fehlertext, skript, kuerzer)
            except Exception as exc:
                return {"error": f"Das Skript liess sich nicht erzeugen: {exc}"}
            einwand = self._pruefen(skript)
            if einwand:
                protokoll.append({"versuch": versuch, "ok": False, "fehler": einwand})
                fehlertext = einwand
                continue
            skript = self._anpassen(skript)
            fehlertext, kuerzer = self._syntax(skript)
            if fehlertext:
                protokoll.append(
                    {
                        "versuch": versuch,
                        "ok": False,
                        "fehler": ("Skript abgeschnitten. " if kuerzer else "") + fehlertext[:400],
                    }
                )
                continue
            ganz = (
                KOPF
                + "\n"
                + skript
                + "\n"
                + FUSS.replace("__JON_BLEND__", json.dumps(str(blend)))
            )
            ergebnis = self._ausfuehren(ganz, None, ZEITGRENZE, versatz)
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
            "import bpy\n" + BAUSTEINE + BAUWERKE + "\n" + skript + "\nimport bpy as _b\n_b.ops.wm.save_mainfile()\n",
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
