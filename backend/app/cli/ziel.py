from __future__ import annotations

import json
from pathlib import Path

import httpx

from app.cli.kunst import FETT, GRAU, GRUEN, MATT, ROT, TUERKIS, Stift
from app.core.auth import get_token
from app.core.config import get_settings
from app.services.ziel_modus import STOPP, ende_text, get_ziel_modus


class ZielTerminal:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root
        self.stift = Stift()
        self.client: httpx.AsyncClient | None = None
        self.kennung = ""

    async def _verbinden(self) -> None:
        self.client = httpx.AsyncClient(base_url=f"http://127.0.0.1:{get_settings().port}/api", headers={"X-Jon-Token": get_token()}, timeout=30, trust_env=False)
        try:
            antwort = await self.client.get("/goal", timeout=2)
            antwort.raise_for_status()
        except (httpx.TransportError, httpx.HTTPStatusError):
            await self.client.aclose()
            self.client = None
            print(self.stift("Ohne Verbindung zur geöffneten App – ich arbeite hier im Terminal.", GRAU))

    async def _anfrage(self, methode: str, pfad: str, daten: dict | None = None) -> dict:
        antwort = await self.client.request(methode, pfad, json=daten)
        if antwort.is_error:
            try:
                text = antwort.json().get("detail", antwort.text)
            except ValueError:
                text = antwort.text
            raise RuntimeError(str(text))
        return antwort.json()

    async def _ereignisse(self):
        if self.client is None:
            async for ereignis in get_ziel_modus().verfolgen(self.kennung):
                yield ereignis
            return
        async with self.client.stream("GET", f"/goal/{self.kennung}/ereignisse", timeout=httpx.Timeout(30, read=60)) as antwort:
            antwort.raise_for_status()
            async for zeile in antwort.aiter_lines():
                if zeile.startswith("data:"):
                    yield json.loads(zeile[5:])

    async def _stand(self) -> dict:
        if self.client is None:
            return get_ziel_modus().get(self.kennung)
        return await self._anfrage("GET", f"/goal/{self.kennung}")

    async def stoppen(self) -> None:
        if not self.kennung:
            return
        if self.client is None:
            await get_ziel_modus().stoppen(self.kennung)
        else:
            await self._anfrage("POST", f"/goal/{self.kennung}/stopp")

    async def run(self, ziel: str) -> None:
        await self._verbinden()
        try:
            if ziel.strip().casefold() in STOPP or not ziel.strip():
                print(self.stift("So geht's: /goal Baue eine Todo-App mit Login und teste alles. Strg+C hält an.", GRAU))
                return
            daten = {"ziel": ziel, "root": str(self.root or ""), "source": "terminal"}
            try:
                eintrag = get_ziel_modus().starten(ziel, "terminal", daten["root"]) if self.client is None else await self._anfrage("POST", "/goal", daten)
            except (ValueError, RuntimeError) as fehler:
                print(self.stift(str(fehler), ROT))
                return
            self.kennung = eintrag["id"]
            print(self.stift("◆ Ziel: ", TUERKIS, FETT) + eintrag["ziel"])
            print(self.stift("Ich arbeite selbstständig, bis das Ziel erreicht ist. Strg+C hält an.", GRAU))
            try:
                async for ereignis in self._ereignisse():
                    self._zeigen(ereignis)
                    if ereignis.get("art") == "ende":
                        break
            except KeyboardInterrupt:
                await self.stoppen()
                print(self.stift("Angehalten. Was schon fertig ist, bleibt erhalten.", GRAU))
                return
            print()
            print(self.stift(ende_text(await self._stand()), GRUEN if (await self._stand()).get("status") == "erreicht" else GRAU))
        finally:
            if self.client is not None:
                await self.client.aclose()

    def _zeigen(self, ereignis: dict) -> None:
        art = ereignis.get("art")
        if art == "runde":
            print(self.stift(f"\n── Runde {ereignis.get('runde')} ──", TUERKIS, FETT))
        elif art == "schritt":
            typ = ereignis.get("typ")
            text = str(ereignis.get("text") or "").strip()
            if typ == "gedanke" and text:
                print(self.stift("  ∴ " + " ".join(text.split())[-400:], GRAU, MATT))
            elif typ == "notiz" and text:
                print("  › " + text)
            elif typ == "action" and ereignis.get("pfad"):
                print(self.stift("    gespeichert: " + str(ereignis["pfad"]), GRAU))
            elif typ == "action_error" and text:
                print(self.stift("    Problem: " + text[:200], ROT))
            elif typ == "approval_required":
                print(self.stift("    Jon wartet auf eine Freigabe im Harness-Fenster der App.", GRAU))
        elif art == "urteil" and ereignis.get("text"):
            print(self.stift("  ✓ Prüfung: " + str(ereignis["text"]), GRAU))
