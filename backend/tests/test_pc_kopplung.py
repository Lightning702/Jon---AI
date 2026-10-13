import asyncio

from app.services import pc_kopplung
from app.services.handy_service import get_handy_service


def test_wartender_pc_wird_gemeldet_und_nur_im_heimnetz(monkeypatch):
    async def niemand(_eigene, _zeit=0):
        return []

    monkeypatch.setattr(pc_kopplung, "suchen", niemand)
    daten = asyncio.run(pc_kopplung.verbinden())
    try:
        assert daten["ok"] and daten["heimnetz"] and daten["code"]
        assert "Verbinde meinen PC" in daten["anleitung"]
        anfrage = {"magic": pc_kopplung.MAGIC, "q": "offen", "pc_id": "anderer"}
        antwort = pc_kopplung.antwort_fuer(anfrage, "192.168.1.20")
        assert antwort["code"] == daten["code"]
        assert pc_kopplung.antwort_fuer(anfrage, "8.8.8.8") is None
        eigene = {**anfrage, "pc_id": get_handy_service().kennung()["id"]}
        assert pc_kopplung.antwort_fuer(eigene, "192.168.1.20") is None
        assert pc_kopplung.antwort_fuer({"magic": "anders", "q": "offen"}, "192.168.1.20") is None
    finally:
        pc_kopplung.schliessen()
        get_handy_service().kopplung_abbrechen()
    assert pc_kopplung.antwort_fuer({"magic": pc_kopplung.MAGIC, "q": "offen", "pc_id": "x"}, "192.168.1.20") is None


def test_gefundener_pc_wird_direkt_gekoppelt(monkeypatch):
    async def gefunden(_eigene, _zeit=0):
        return [{"name": "Wohnzimmer-PC", "code": "ABCD2345", "pc_id": "p1", "port": 8756, "host": "192.168.1.30"}, {"name": "Laptop", "code": "WXYZ2345", "pc_id": "p2", "port": 8756, "host": "192.168.1.31"}]

    aufrufe = []

    class Verbund:
        def koppeln(self, code, makler=None, adresse=""):
            aufrufe.append((code, adresse))
            return {"name": "Laptop"}

    import app.services.verbund_service as verbund

    monkeypatch.setattr(pc_kopplung, "suchen", gefunden)
    monkeypatch.setattr(verbund, "get_verbund_service", lambda: Verbund())
    daten = asyncio.run(pc_kopplung.verbinden("laptop"))
    assert daten["fertig"] and daten["jon"] == "Laptop"
    assert aufrufe == [("WXYZ2345", "http://192.168.1.31:8756")]
