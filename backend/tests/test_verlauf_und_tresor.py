from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app.services.approval_service import ApprovalService, ToolDeniedError
from app.services.history import budget_chars, shorten_middle, trim_history
from app.services.vault_service import VaultService


@dataclass
class Nachricht:
    role: str
    content: str


def bauen(role: str, content: str) -> Nachricht:
    return Nachricht(role=role, content=content)


def gespraech(runden: int, laenge: int = 400) -> list[Nachricht]:
    verlauf = [Nachricht("system", "Du bist Jon.")]
    for i in range(runden):
        verlauf.append(Nachricht("user", f"Frage {i} " + "x" * laenge))
        verlauf.append(Nachricht("assistant", f"Antwort {i} " + "y" * laenge))
    return verlauf


def gesamtlaenge(nachrichten: list[Nachricht]) -> int:
    return sum(len(n.content) for n in nachrichten)


def test_kurzes_gespraech_bleibt_unveraendert():
    verlauf = gespraech(3)
    ergebnis = trim_history(verlauf, 24000, bauen)
    assert ergebnis.dropped == 0
    assert ergebnis.shortened == 0
    assert [n.content for n in ergebnis.messages] == [n.content for n in verlauf]


def test_langes_gespraech_wird_auf_das_budget_gekuerzt():
    verlauf = gespraech(200)
    ergebnis = trim_history(verlauf, 4000, bauen)
    assert ergebnis.dropped > 0
    assert gesamtlaenge(ergebnis.messages) <= budget_chars(4000) * 1.2


def test_systemanweisung_ueberlebt_die_kuerzung():
    verlauf = gespraech(200)
    ergebnis = trim_history(verlauf, 4000, bauen)
    assert ergebnis.messages[0].role == "system"
    assert ergebnis.messages[0].content == "Du bist Jon."


def test_letzte_nachricht_ueberlebt_die_kuerzung():
    verlauf = gespraech(200)
    verlauf.append(Nachricht("user", "Das ist meine allerletzte Frage"))
    ergebnis = trim_history(verlauf, 4000, bauen)
    assert ergebnis.messages[-1].content == "Das ist meine allerletzte Frage"


def test_gekuerztes_wird_als_zusammenfassung_mitgegeben():
    verlauf = gespraech(200)
    ergebnis = trim_history(verlauf, 4000, bauen)
    zusammenfassung = [
        n for n in ergebnis.messages if n.role == "system" and "gekuerzt" in n.content
    ]
    assert len(zusammenfassung) == 1
    assert "Frage 0" in zusammenfassung[0].content


def test_eine_riesige_nachricht_sprengt_das_budget_nicht():
    verlauf = [
        Nachricht("system", "Du bist Jon."),
        Nachricht("user", "A" * 500_000),
        Nachricht("user", "Und was steht da drin?"),
    ]
    ergebnis = trim_history(verlauf, 4000, bauen)
    assert ergebnis.shortened == 1
    assert gesamtlaenge(ergebnis.messages) < 500_000
    assert ergebnis.messages[-1].content == "Und was steht da drin?"


def test_mitte_kuerzen_behaelt_anfang_und_ende():
    text = "START" + "m" * 5000 + "ENDE"
    kurz = shorten_middle(text, 1000)
    assert kurz.startswith("START")
    assert kurz.endswith("ENDE")
    assert len(kurz) <= 1000


def test_freigabe_wird_erteilt():
    async def ablauf() -> bool:
        dienst = ApprovalService()
        kennung = dienst.create()
        warten = asyncio.create_task(dienst.wait(kennung, timeout=2))
        await asyncio.sleep(0)
        assert dienst.resolve(kennung, True)
        return await warten

    assert asyncio.run(ablauf()) is True


def test_freigabe_wird_verweigert():
    async def ablauf() -> bool:
        dienst = ApprovalService()
        kennung = dienst.create()
        warten = asyncio.create_task(dienst.wait(kennung, timeout=2))
        await asyncio.sleep(0)
        dienst.resolve(kennung, False)
        return await warten

    assert asyncio.run(ablauf()) is False


def test_freigabe_laeuft_ab_und_gilt_als_nein():
    async def ablauf() -> bool:
        dienst = ApprovalService()
        kennung = dienst.create()
        return await dienst.wait(kennung, timeout=0.05)

    assert asyncio.run(ablauf()) is False


def test_unbekannte_freigabe_gilt_als_nein():
    async def ablauf() -> bool:
        dienst = ApprovalService()
        return await dienst.wait("gibtesnicht", timeout=0.05)

    assert asyncio.run(ablauf()) is False


def test_zweite_antwort_auf_dieselbe_freigabe_verpufft():
    async def ablauf() -> bool:
        dienst = ApprovalService()
        kennung = dienst.create()
        warten = asyncio.create_task(dienst.wait(kennung, timeout=2))
        await asyncio.sleep(0)
        dienst.resolve(kennung, True)
        ergebnis = await warten
        assert dienst.resolve(kennung, False) is False
        return ergebnis

    assert asyncio.run(ablauf()) is True


def test_werkzeug_abgelehnt_ist_ein_fehler():
    assert issubclass(ToolDeniedError, RuntimeError)


@pytest.fixture
def tresor(tmp_path, monkeypatch):
    from app.services import vault_service

    monkeypatch.setattr(vault_service, "VAULT_FILE", tmp_path / "vault.dat")
    return VaultService()


def test_tresor_anlegen_und_oeffnen(tresor):
    assert tresor.exists() is False
    assert "error" not in tresor.create("geheim123")
    assert tresor.exists() is True
    tresor.lock()
    assert tresor.status()["unlocked"] is False
    assert "error" not in tresor.unlock("geheim123")
    assert tresor.status()["unlocked"] is True


def test_tresor_weist_falsches_passwort_ab(tresor):
    tresor.create("richtig123")
    tresor.lock()
    assert "error" in tresor.unlock("falsch")
    assert tresor.status()["unlocked"] is False


def test_tresor_zu_kurzes_passwort(tresor):
    assert "error" in tresor.create("ab")


def test_tresor_kein_zweiter_tresor(tresor):
    tresor.create("geheim123")
    assert "error" in tresor.create("nochmal123")


def test_tresor_eintrag_bleibt_nach_neustart(tresor, tmp_path, monkeypatch):
    from app.services import vault_service

    tresor.create("geheim123")
    tresor.add("Mail", "felix", "sehr-geheim")
    tresor.lock()

    monkeypatch.setattr(vault_service, "VAULT_FILE", tmp_path / "vault.dat")
    neu = VaultService()
    assert "error" not in neu.unlock("geheim123")
    eintraege = neu.list()["entries"]
    assert [e["title"] for e in eintraege] == ["Mail"]
    assert neu.reveal(eintraege[0]["id"])["secret"] == "sehr-geheim"


def test_tresor_gibt_ohne_entsperrung_nichts_heraus(tresor):
    tresor.create("geheim123")
    tresor.add("Mail", "felix", "sehr-geheim")
    eintrag = tresor.list()["entries"][0]["id"]
    tresor.lock()
    gesperrt = tresor.list()
    assert gesperrt["locked"] is True
    assert gesperrt["entries"] == []
    assert "error" in tresor.reveal(eintrag)
