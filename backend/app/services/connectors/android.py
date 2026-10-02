from __future__ import annotations

import time
from typing import Any

from app.services.connectors.basis import Connector, Werkzeug
from app.services.handy_service import RECHTE_NAMEN, HandyFehler, get_handy_service

_INT = {"type": "integer"}

_GERAET = {
    "type": "string",
    "description": (
        "Name oder Kennung des Handys. Weglassen, wenn nur ein Handy gekoppelt ist."
    ),
}

HINWEIS_ANDROID = (
    "Am Handy fehlt die passende Android-Berechtigung. Der Nutzer erteilt sie in der "
    "Jon-App unter Verbinder."
)


def _app_kennung(geraet: dict, wunsch: str) -> str:
    wunsch = wunsch.strip()
    if not wunsch:
        return ""
    zustand = geraet.get("zustand") or {}
    apps = zustand.get("apps") or (zustand.get("bildschirmzeit") or {}).get("apps") or []
    einfach = "".join(zeichen for zeichen in wunsch.lower() if zeichen.isalnum())
    for app in apps if isinstance(apps, list) else []:
        if not isinstance(app, dict):
            continue
        kennung = str(app.get("id") or "")
        name = "".join(zeichen for zeichen in str(app.get("name") or "").lower() if zeichen.isalnum())
        if wunsch == kennung or (einfach and einfach == name):
            return kennung
    if wunsch in ("whatsapp", "tiktok", "amazon"):
        return wunsch
    return ""


class AndroidConnector(Connector):
    id = "android"
    name = "Android"

    def _dienst(self):
        return get_handy_service()

    def bereit(self) -> bool:
        return bool(self._dienst().geraete())

    def geraete(self) -> list[dict]:
        return self._dienst().geraete()

    def _mit_recht(self, recht: str) -> list[dict]:
        dienst = self._dienst()
        passend = []
        for geraet in dienst.geraete():
            if not dienst.recht_erlaubt(geraet["id"], recht):
                continue
            if not dienst.faehig(geraet["id"], recht):
                continue
            passend.append(geraet)
        return passend

    def _alle_werkzeuge(self) -> list[Werkzeug]:
        return [
            Werkzeug(name="android_app_open", beschreibung="Öffnet auf dem Android-Handy eine der dort freigegebenen Apps, zum Beispiel WhatsApp, TikTok, Amazon Music oder YouTube. Keine Nachrichten versenden.",
                eigenschaften={"device": _GERAET, "app": {"type": "string", "description": "Name oder Kennung der App, zum Beispiel WhatsApp oder com.google.android.youtube."}}, pflicht=["app"], recht="apps", kurz="App am Handy öffnen"),
            Werkzeug(name="android_amazon_music", beschreibung="Steuert Amazon Music auf dem Android-Handy: öffnen, Play, Pause, nächster oder vorheriger Titel.",
                eigenschaften={"device": _GERAET, "action": {"type": "string", "enum": ["oeffnen", "play", "pause", "next", "previous", "status"]}}, pflicht=["action"], recht="musik", kurz="Musik am Handy steuern"),
            Werkzeug(
                name="android_announce",
                beschreibung=(
                    "Schickt eine Durchsage an ein Jon Gerät: Der Text erscheint gross auf "
                    "dem Handy und wird laut vorgelesen, zum Beispiel 'Essen ist fertig'. "
                    "Das Gerät meldet zurück, wenn die Durchsage gelesen wurde."
                ),
                eigenschaften={
                    "device": _GERAET,
                    "text": {"type": "string", "description": "Die Durchsage, kurz und freundlich."},
                    "speak": {"type": "boolean", "description": "Laut vorlesen, Standard ja."},
                },
                pflicht=["text"],
                stufe="standard",
                recht="durchsage",
                kurz="Schickt eine Durchsage aufs Handy.",
            ),
            Werkzeug(
                name="android_ring",
                beschreibung=(
                    "Lässt ein Jon Gerät laut klingeln, auch wenn es stumm ist, damit man es "
                    "wiederfindet. Standard 30 Sekunden."
                ),
                eigenschaften={
                    "device": _GERAET,
                    "seconds": {"type": "integer", "description": "5 bis 120 Sekunden, Standard 30."},
                },
                pflicht=[],
                stufe="standard",
                recht="klingeln",
                kurz="Lässt das Handy klingeln.",
            ),
            Werkzeug(
                name="android_screen_time",
                beschreibung=(
                    "Bildschirmzeit am Jon Gerät. action=status zeigt die heutige Nutzung pro "
                    "App, Limits, Schlafenszeit und Pause. action=pause sperrt alle freigegebenen "
                    "Apps für minutes Minuten. action=pause_end hebt die Pause auf. "
                    "action=limit setzt für app ein Tageslimit von minutes Minuten (0 = unbegrenzt). "
                    "action=extra gibt app für minutes Minuten frei, auch wenn das Limit erreicht ist."
                ),
                eigenschaften={
                    "device": _GERAET,
                    "action": {"type": "string", "enum": ["status", "pause", "pause_end", "limit", "extra"]},
                    "minutes": _INT,
                    "app": {"type": "string", "description": "Kennung der App aus dem Status, zum Beispiel whatsapp oder com.google.android.youtube."},
                },
                pflicht=["action"],
                stufe="standard",
                recht="regeln",
                kurz="Bildschirmzeit am Handy.",
            ),
            Werkzeug(
                name="android_devices",
                beschreibung=(
                    "Listet die mit Jon gekoppelten Android-Geraete mit Online-Status, "
                    "Akku und freigegebenen Funktionen."
                ),
                eigenschaften={},
                pflicht=[],
                stufe="standard",
                recht="status",
                kurz="Zeigt die gekoppelten Handys.",
            ),
            Werkzeug(
                name="android_device_status",
                beschreibung=(
                    "Fragt den Zustand eines gekoppelten Handys ab: Name, Online-Status, "
                    "Akku, Ladezustand, Verbindungsart, Android-Version und letzter Kontakt."
                ),
                eigenschaften={"device": _GERAET},
                pflicht=[],
                stufe="standard",
                recht="status",
                kurz="Fragt den Zustand des Handys ab.",
            ),
            Werkzeug(
                name="android_battery_status",
                beschreibung="Fragt Akkustand und Ladezustand eines gekoppelten Handys ab.",
                eigenschaften={"device": _GERAET},
                pflicht=[],
                stufe="standard",
                recht="status",
                kurz="Fragt den Akku des Handys ab.",
            ),
            Werkzeug(
                name="android_notifications_list",
                beschreibung=(
                    "Liest die aktuellen Benachrichtigungen vom Handy, sofern der Nutzer "
                    "den Zugriff in Jon und in Android freigegeben hat."
                ),
                eigenschaften={
                    "device": _GERAET,
                    "limit": {
                        "type": "integer",
                        "description": "Wie viele Benachrichtigungen hoechstens (Vorgabe 20).",
                    },
                },
                pflicht=[],
                stufe="persoenlich",
                recht="hinweise",
                kurz="Liest die Benachrichtigungen vom Handy.",
            ),
            Werkzeug(
                name="android_files_list",
                beschreibung=(
                    "Listet Dateien in einem freigegebenen Ordner auf dem Handy "
                    "(Vorgabe: der Jon-Ordner in den Downloads)."
                ),
                eigenschaften={
                    "device": _GERAET,
                    "folder": {
                        "type": "string",
                        "description": (
                            "Ordner auf dem Handy: jon, downloads, bilder, filme, "
                            "musik oder dokumente."
                        ),
                    },
                },
                pflicht=[],
                stufe="standard",
                recht="dateien",
                kurz="Listet Dateien auf dem Handy.",
            ),
            Werkzeug(
                name="android_files_send",
                beschreibung=(
                    "Schickt eine vorhandene Datei vom PC auf das Handy. Nimm dieses "
                    "Werkzeug immer, wenn der Nutzer sagt: schick das aufs Handy, "
                    "schick mir die Datei/das Bild/die PDF, ueberspiel das. Den Pfad "
                    "findest du im Gespraech - Anhaenge stehen als „Diese Datei liegt "
                    "auf dem PC unter: ...\". Mach dafuer niemals ein neues Foto."
                ),
                eigenschaften={
                    "path": {"type": "string", "description": "Voller Pfad der Datei auf dem PC."},
                    "device": _GERAET,
                },
                pflicht=["path"],
                stufe="standard",
                recht="dateien",
                kurz="Schickt eine Datei aufs Handy.",
            ),
            Werkzeug(
                name="android_files_receive",
                beschreibung=(
                    "Holt eine Datei vom Handy auf den PC. Der Pfad stammt aus "
                    "android_files_list."
                ),
                eigenschaften={
                    "path": {"type": "string", "description": "Pfad der Datei auf dem Handy."},
                    "device": _GERAET,
                },
                pflicht=["path"],
                stufe="standard",
                recht="dateien",
                kurz="Holt eine Datei vom Handy.",
            ),
            Werkzeug(
                name="android_clipboard_send",
                beschreibung=(
                    "Legt einen Text in die Zwischenablage des Handys. Android erlaubt "
                    "kein Mitlesen der Zwischenablage im Hintergrund, deshalb nur senden."
                ),
                eigenschaften={
                    "text": {"type": "string", "description": "Der Text fuer die Zwischenablage."},
                    "device": _GERAET,
                },
                pflicht=["text"],
                stufe="persoenlich",
                recht="zwischenablage",
                kurz="Legt Text in die Zwischenablage des Handys.",
            ),
            Werkzeug(
                name="android_location_get",
                beschreibung=(
                    "Fragt den aktuellen Standort des Handys ab. Nur mit ausdruecklicher "
                    "Freigabe in Jon und in Android."
                ),
                eigenschaften={"device": _GERAET},
                pflicht=[],
                stufe="persoenlich",
                recht="standort",
                kurz="Fragt den Standort des Handys ab.",
            ),
            Werkzeug(
                name="android_contacts_search",
                beschreibung="Sucht in den Kontakten des Handys nach einem Namen.",
                eigenschaften={
                    "query": {"type": "string", "description": "Name oder Teil davon."},
                    "device": _GERAET,
                    "limit": _INT,
                },
                pflicht=["query"],
                stufe="persoenlich",
                recht="kontakte",
                kurz="Sucht in den Kontakten des Handys.",
            ),
            Werkzeug(
                name="android_camera_request_photo",
                beschreibung=(
                    "Nimmt mit der Kamera des Handys ein NEUES Foto auf und legt es auf "
                    "dem PC ab. Nur nehmen, wenn der Nutzer wirklich eine neue Aufnahme "
                    "will (fotografier, mach ein Bild, zeig mir was die Kamera sieht). "
                    "Niemals, wenn er eine vorhandene Datei verschicken will. Braucht "
                    "keine Bestaetigung am Handy; camera=vorne fuer die Selfie-Kamera."
                ),
                eigenschaften={
                    "camera": {
                        "type": "string",
                        "description": "hinten (Standard) oder vorne",
                    },
                    "device": _GERAET,
                },
                pflicht=[],
                stufe="sensibel",
                recht="kamera",
                kurz="Macht sofort ein Foto mit dem Handy.",
            ),
        ]

    def werkzeuge(self) -> list[Werkzeug]:
        if not self.bereit():
            return []
        sichtbar = []
        for werkzeug in self._alle_werkzeuge():
            if not werkzeug.recht or self._mit_recht(werkzeug.recht):
                sichtbar.append(werkzeug)
                continue
            sichtbar.append(
                Werkzeug(
                    name=werkzeug.name,
                    beschreibung=(
                        f"GESPERRT: {werkzeug.beschreibung} Der Nutzer hat "
                        f"„{RECHTE_NAMEN.get(werkzeug.recht, werkzeug.recht)}“ für sein "
                        "Handy noch nicht freigegeben. Ruf das Werkzeug trotzdem auf, "
                        "wenn er es verlangt - du bekommst dann den genauen Hinweis, "
                        "was er einschalten muss."
                    ),
                    eigenschaften=werkzeug.eigenschaften,
                    pflicht=werkzeug.pflicht,
                    stufe=werkzeug.stufe,
                    recht=werkzeug.recht,
                    kurz=werkzeug.kurz,
                    frei=False,
                )
            )
        return sichtbar

    def kann(self, name: str) -> bool:
        return any(werkzeug.name == name for werkzeug in self._alle_werkzeuge())

    def kurztexte(self) -> dict[str, str]:
        return {werkzeug.name: werkzeug.kurz for werkzeug in self._alle_werkzeuge()}

    def _waehlen(self, args: dict[str, Any], recht: str) -> dict:
        dienst = self._dienst()
        alle = dienst.geraete()
        if not alle:
            raise HandyFehler(
                "Es ist kein Handy gekoppelt. Das geht in Jon unter Einstellungen -> "
                "Verbindungen -> Geraete."
            )
        wunsch = str(args.get("device") or args.get("geraet") or "").strip().lower()
        if wunsch:
            treffer = [
                geraet
                for geraet in alle
                if geraet["id"].lower() == wunsch
                or wunsch in str(geraet.get("name", "")).lower()
            ]
            if not treffer:
                namen = ", ".join(geraet.get("name", geraet["id"]) for geraet in alle)
                raise HandyFehler(f"Kein Handy passt zu „{args.get('device')}“. Da sind: {namen}")
        else:
            treffer = alle
        passend = [geraet for geraet in treffer if dienst.recht_erlaubt(geraet["id"], recht)]
        if not passend:
            name = RECHTE_NAMEN.get(recht, recht)
            raise HandyFehler(
                f"„{name}“ ist für dieses Handy noch nicht freigegeben. Der Nutzer "
                "schaltet das in Jon unter 🧰 Werkzeuge -> 📱 Handy & Geräte mit dem "
                f"Schalter „{name}“ frei. Sag ihm genau das."
            )
        online = [geraet for geraet in passend if geraet.get("online")]
        auswahl = online or passend
        if len(auswahl) > 1 and not wunsch:
            namen = ", ".join(geraet.get("name", geraet["id"]) for geraet in auswahl)
            raise HandyFehler(
                f"Es sind mehrere Handys gekoppelt: {namen}. Sag dazu, welches gemeint ist."
            )
        return auswahl[0]

    async def _auftrag(
        self,
        geraet: dict,
        op: str,
        recht: str,
        daten: dict | None = None,
        wartezeit: float = 45.0,
    ) -> dict:
        dienst = self._dienst()
        if recht and not dienst.faehig(geraet["id"], recht):
            raise HandyFehler(HINWEIS_ANDROID)
        antwort = await dienst.auftrag(geraet["id"], op, daten, wartezeit=wartezeit)
        if not antwort.get("ok"):
            raise HandyFehler(antwort.get("fehler") or "Das Handy konnte das nicht ausfuehren.")
        ergebnis = dict(antwort.get("daten") or {})
        ergebnis["geraet"] = geraet.get("name", geraet["id"])
        return ergebnis

    async def ausfuehren(self, name: str, args: dict[str, Any]) -> dict:
        try:
            return await self._ausfuehren(name, args)
        except HandyFehler as exc:
            return {"error": str(exc)}

    async def _ausfuehren(self, name: str, args: dict[str, Any]) -> dict:
        dienst = self._dienst()
        if name in ("android_app_open", "android_amazon_music"):
            from app.services.geraete_funktionen import HANDY_KONTEXT
            gebunden = HANDY_KONTEXT.get()
            if gebunden:
                args = {**args, "device": gebunden}
            recht = "apps" if name == "android_app_open" else "musik"
            geraet = self._waehlen(args, recht)
            if not dienst.faehig(geraet["id"], recht):
                raise HandyFehler("Die Handy-App unterstützt diese Funktion noch nicht oder die Berechtigung fehlt.")
            if name == "android_app_open":
                wunsch = str(args.get("app", "")).strip()[:120]
                if not wunsch:
                    raise HandyFehler("Welche App soll ich öffnen?")
                app = _app_kennung(geraet, wunsch)
                if not app:
                    raise HandyFehler(f"„{wunsch}“ ist auf dem Handy nicht freigegeben.")
                return await dienst.auftrag(geraet["id"], "app-oeffnen", {"app": app})
            aktion = str(args.get("action", ""))
            if aktion not in ("oeffnen", "play", "pause", "next", "previous", "status"):
                raise HandyFehler("Unbekannte Musikaktion.")
            return await dienst.auftrag(geraet["id"], "musik", {"aktion": aktion})
        if name in ("android_announce", "android_ring", "android_screen_time"):
            return await self._eltern(name, args)
        if name == "android_devices":
            return {"geraete": [self._kurzsicht(geraet) for geraet in dienst.geraete()]}
        if name in ("android_device_status", "android_battery_status"):
            geraet = self._waehlen(args, "status")
            return await self._status(geraet, name == "android_battery_status")
        if name == "android_notifications_list":
            geraet = self._waehlen(args, "hinweise")
            try:
                grenze = int(args.get("limit") or 20)
            except (TypeError, ValueError):
                grenze = 20
            return await self._auftrag(
                geraet,
                "hinweise",
                "hinweise",
                {"limit": max(1, min(grenze, 60))},
            )
        if name == "android_files_list":
            geraet = self._waehlen(args, "dateien")
            return await self._auftrag(
                geraet,
                "dateien",
                "dateien",
                {"ordner": str(args.get("folder") or args.get("ordner") or "jon")},
            )
        if name == "android_files_send":
            return await self._senden(args)
        if name == "android_files_receive":
            geraet = self._waehlen(args, "dateien")
            pfad = str(args.get("path") or args.get("pfad") or "").strip()
            if not pfad:
                raise HandyFehler("Ohne Pfad weiss das Handy nicht, welche Datei gemeint ist.")
            return await self._auftrag(
                geraet,
                "datei-senden",
                "dateien",
                {"pfad": pfad},
                wartezeit=300.0,
            )
        if name == "android_clipboard_send":
            geraet = self._waehlen(args, "zwischenablage")
            text = str(args.get("text") or "")
            if not text:
                raise HandyFehler("Ohne Text gibt es nichts zu kopieren.")
            return await self._auftrag(
                geraet,
                "zwischenablage",
                "zwischenablage",
                {"text": text[:20000]},
            )
        if name == "android_location_get":
            geraet = self._waehlen(args, "standort")
            return await self._auftrag(geraet, "ort", "standort", {}, wartezeit=60.0)
        if name == "android_contacts_search":
            geraet = self._waehlen(args, "kontakte")
            suche = str(args.get("query") or args.get("suche") or "").strip()
            if not suche:
                raise HandyFehler("Ohne Suchbegriff findet das Handy keinen Kontakt.")
            try:
                grenze = int(args.get("limit") or 10)
            except (TypeError, ValueError):
                grenze = 10
            return await self._auftrag(
                geraet,
                "kontakte",
                "kontakte",
                {"suche": suche, "limit": max(1, min(grenze, 40))},
            )
        if name == "android_camera_request_photo":
            geraet = self._waehlen(args, "kamera")
            kamera = str(args.get("camera") or "hinten").strip().lower()
            return await self._auftrag(
                geraet,
                "foto",
                "kamera",
                {"kamera": "vorne" if kamera.startswith("v") else "hinten"},
                wartezeit=120.0,
            )
        raise HandyFehler(f"Der Android-Connector kennt {name} nicht.")

    async def _eltern(self, name: str, args: dict[str, Any]) -> dict:
        from app.services.geraete_funktionen import HANDY_KONTEXT

        if HANDY_KONTEXT.get():
            raise HandyFehler("Das geht nur von Jon am PC oder Pi aus, nicht vom Gerät selbst.")
        dienst = self._dienst()
        recht = {"android_announce": "durchsage", "android_ring": "klingeln"}.get(name, "regeln")
        geraet = self._waehlen(args, recht)
        geraet_name = geraet.get("name", geraet["id"])
        if name == "android_announce":
            ergebnis = await dienst.durchsage(geraet["id"], str(args.get("text") or ""), args.get("speak", True) is not False)
            return {**ergebnis, "geraet": geraet_name}
        if name == "android_ring":
            ergebnis = await dienst.klingeln(geraet["id"], args.get("seconds") or 30)
            return {**ergebnis, "geraet": geraet_name}
        aktion = str(args.get("action") or "status").strip().lower()
        if aktion == "status":
            stand = dict(dienst.zustand(geraet["id"])["zustand"]).get("bildschirmzeit")
            if geraet.get("online"):
                try:
                    frisch = await self._auftrag(geraet, "zustand", "status", {}, wartezeit=25.0)
                    stand = frisch.get("bildschirmzeit") or stand
                except HandyFehler:
                    pass
            if not stand:
                return {"geraet": geraet_name, "hinweis": "Das Gerät hat noch keine Bildschirmzeit gemeldet."}
            return {"geraet": geraet_name, "bildschirmzeit": stand}
        try:
            minuten = int(args.get("minutes") or 0)
        except (TypeError, ValueError):
            minuten = 0
        if aktion == "pause":
            stand = await dienst.regeln_setzen(geraet["id"], {"pause_minuten": minuten or 30})
        elif aktion == "pause_end":
            stand = await dienst.regeln_setzen(geraet["id"], {"pause_minuten": 0})
        elif aktion in ("limit", "extra"):
            app = _app_kennung(geraet, str(args.get("app") or ""))
            if not app:
                raise HandyFehler("Für diese Aktion brauche ich eine freigegebene App vom Handy.")
            if aktion == "limit":
                stand = await dienst.regeln_setzen(geraet["id"], {"limits": {app: minuten}})
            else:
                stand = await dienst.regeln_setzen(geraet["id"], {"extra": {app: minuten or 30}})
        else:
            raise HandyFehler("Unbekannte Aktion für die Bildschirmzeit.")
        return {"geraet": geraet_name, "bildschirmzeit": stand}

    def _kurzsicht(self, geraet: dict) -> dict:
        zustand = geraet.get("zustand") or {}
        rechte = geraet.get("rechte") or {}
        return {
            "id": geraet["id"],
            "name": geraet.get("name", ""),
            "plattform": geraet.get("plattform", ""),
            "online": bool(geraet.get("online")),
            "akku": zustand.get("akku"),
            "laedt": zustand.get("laedt"),
            "verbindung": zustand.get("netz"),
            "letzter_kontakt": self._wann(geraet.get("gesehen")),
            "freigaben": sorted(name for name, wert in rechte.items() if wert),
        }

    async def _status(self, geraet: dict, nur_akku: bool) -> dict:
        dienst = self._dienst()
        frisch: dict | None = None
        fehler = ""
        if geraet.get("online"):
            try:
                frisch = await self._auftrag(geraet, "zustand", "status", {}, wartezeit=25.0)
            except HandyFehler as exc:
                fehler = str(exc)
        gespeichert = dienst.zustand(geraet["id"])
        zustand = frisch or dict(gespeichert["zustand"])
        zustand.pop("geraet", None)
        antwort = {
            "name": geraet.get("name", ""),
            "online": bool(geraet.get("online")),
            "akku": zustand.get("akku"),
            "laedt": bool(zustand.get("laedt")),
        }
        if not nur_akku:
            antwort.update(
                {
                    "verbindung": zustand.get("netz") or "unbekannt",
                    "android": zustand.get("android") or geraet.get("plattform", ""),
                    "modell": zustand.get("modell") or "",
                    "speicher_frei": zustand.get("speicher_frei"),
                    "letzter_kontakt": self._wann(geraet.get("gesehen")),
                    "freigaben": sorted(
                        name for name, wert in (geraet.get("rechte") or {}).items() if wert
                    ),
                }
            )
        if frisch is None:
            antwort["hinweis"] = fehler or (
                "Das Handy meldet sich gerade nicht. Die Werte stammen vom letzten Kontakt."
            )
            antwort["stand"] = self._wann(gespeichert["zeit"])
        return antwort

    async def _senden(self, args: dict[str, Any]) -> dict:
        dienst = self._dienst()
        geraet = self._waehlen(args, "dateien")
        pfad = str(args.get("path") or args.get("pfad") or "").strip()
        if not pfad:
            raise HandyFehler("Ohne Pfad weiss Jon nicht, welche Datei gemeint ist.")
        karte = dienst.datei_bereitstellen(geraet["id"], pfad)
        ergebnis = await self._auftrag(
            geraet,
            "datei",
            "dateien",
            karte,
            wartezeit=300.0,
        )
        ergebnis.setdefault("name", karte["name"])
        ergebnis.setdefault("groesse", karte["groesse"])
        return ergebnis

    def _wann(self, zeitpunkt: Any) -> str:
        try:
            wert = float(zeitpunkt or 0)
        except (TypeError, ValueError):
            return "unbekannt"
        if wert <= 0:
            return "unbekannt"
        abstand = time.time() - wert
        if abstand < 90:
            return "gerade eben"
        if abstand < 3600:
            return f"vor {int(abstand // 60)} Minuten"
        if abstand < 86400:
            return f"vor {int(abstand // 3600)} Stunden"
        return time.strftime("%d.%m.%Y %H:%M", time.localtime(wert))
