from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.maps.base import (
    MapsError,
    Place,
    RouteOption,
    RouteStep,
    format_distance,
    format_duration,
)
from app.services.maps.nominatim import haversine_m
from app.services.maps.osrm import PROFILES, _step_text
from app.services.maps.overpass import CATEGORIES, category_list, resolve_category
from app.services.maps.styles import PALETTES, _recolor, _vector_source
from app.services.maps.transitous import decode_polyline
from app.services.maps.valhalla import decode_polyline6


def test_kategorie_erkennung():
    assert resolve_category("Restaurants in der Nähe") == "restaurant"
    assert resolve_category("cafes") == "cafe"
    assert resolve_category("Tankstelle") == "tankstelle"
    assert resolve_category("Salzburg Hauptbahnhof") == ""
    assert resolve_category("Eiffelturm") == ""
    assert resolve_category("Berlin") == ""


def test_kategorie_liste_vollstaendig():
    liste = category_list()
    assert len(liste) == len(CATEGORIES)
    assert all(eintrag["icon"] and eintrag["label"] for eintrag in liste)


def test_entfernung_und_dauer_formatierung():
    assert format_distance(120) == "120 m"
    assert format_distance(1500) == "1,5 km"
    assert format_distance(250000) == "250 km"
    assert format_duration(30) == "unter 1 Minute"
    assert format_duration(600) == "10 Minuten"
    assert format_duration(3600) == "1 Stunde"
    assert format_duration(5400) == "1 h 30 min"


def test_haversine_kennt_echte_distanz():
    salzburg = (47.8095, 13.0550)
    muenchen = (48.1372, 11.5756)
    meter = haversine_m(*salzburg, *muenchen)
    assert 110_000 < meter < 130_000


def test_polyline_dekodierung():
    grob = decode_polyline("_p~iF~ps|U_ulLnnqC", precision=5)
    assert len(grob) == 2
    assert round(grob[0][1], 1) == 38.5
    assert round(grob[0][0], 1) == -120.2
    assert round(grob[1][1], 1) == 40.7
    fein = decode_polyline6("_p~iF~ps|U_ulLnnqC")
    assert len(fein) == 2
    assert round(fein[0][1] * 10, 1) == round(grob[0][1], 1)
    assert round(fein[0][0] * 10, 1) == round(grob[0][0], 1)


def test_osrm_profile_und_anweisungen():
    assert PROFILES["auto"] == "driving"
    text = _step_text(
        {"name": "Hauptstraße", "maneuver": {"type": "turn", "modifier": "left"}}
    )
    assert "links" in text and "Hauptstraße" in text
    assert _step_text({"maneuver": {"type": "arrive"}}) == "Ziel erreicht"
    kreisel = _step_text(
        {"name": "Ring", "maneuver": {"type": "roundabout", "exit": 2}}
    )
    assert "Kreisverkehr" in kreisel and "2. Ausfahrt" in kreisel


def test_style_recolor_faerbt_ebenen_um():
    dunkel = PALETTES["dark"]
    wasser = _recolor(
        {"id": "water", "type": "fill", "source-layer": "water", "paint": {"fill-color": "#aaddff"}},
        dunkel,
    )
    assert wasser["paint"]["fill-color"] == dunkel["water"]
    hintergrund = _recolor({"id": "background", "type": "background", "paint": {}}, dunkel)
    assert hintergrund["paint"]["background-color"] == dunkel["background"]
    beschriftung = _recolor(
        {"id": "place-city", "type": "symbol", "paint": {"text-color": "#000"}}, dunkel
    )
    assert beschriftung["paint"]["text-color"] == dunkel["text"]
    gebaeude = _recolor(
        {"id": "building", "type": "fill", "source-layer": "building", "paint": {"fill-color": "#fff"}},
        dunkel,
    )
    assert gebaeude["paint"]["fill-color"] == dunkel["building"]


def test_style_findet_vektorquelle():
    style = {"sources": {"raster": {"type": "raster"}, "openmaptiles": {"type": "vector"}}}
    assert _vector_source(style) == "openmaptiles"
    assert _vector_source({"sources": {}}) == ""


def test_place_und_route_serialisierung():
    ort = Place(id="x", name="Test", label="Teststadt", lat=48.0, lon=11.0)
    daten = ort.to_dict()
    assert daten["lat"] == 48.0 and daten["kind"] == "ort"
    route = RouteOption(
        id="r1",
        mode="auto",
        distance_m=1000.0,
        duration_s=600.0,
        geometry=[[11.0, 48.0], [11.1, 48.1]],
        steps=[RouteStep(text="Start", distance_m=0.0, duration_s=0.0)],
    )
    roh = route.to_dict()
    assert roh["steps"][0]["text"] == "Start"
    assert len(roh["geometry"]) == 2


def test_router_kette_bevorzugt_valhalla_fuer_fuss(monkeypatch):
    monkeypatch.setenv("JON_MAPS_TEST", "1")
    from app.services.maps.service import MapsService

    service = MapsService()
    assert [r.name for r in service._chain("auto")][0] == "osrm"
    fuss = [r.name for r in service._chain("fuss")]
    assert fuss and fuss[0] == "valhalla"
    assert "osrm" not in fuss


def test_maps_tool_liefert_kartenpayload(monkeypatch):
    from app.services.maps import service as service_module

    async def fake_answer(action, args):
        return {
            "aktion": action,
            "karte": {"center": {"lat": 48.0, "lon": 11.0}, "marker": []},
            "text": "ok",
        }

    class FakeService:
        answer = staticmethod(fake_answer)

    monkeypatch.setattr(service_module, "_service", FakeService())
    from app.services.tools import ToolBox

    ergebnis = json.loads(
        asyncio.run(ToolBox().execute("maps", {"action": "suche", "query": "Test"}))
    )
    assert ergebnis["aktion"] == "suche"
    assert ergebnis["karte"]["center"]["lat"] == 48.0


def test_chat_karte_nur_fuer_kartentools():
    from app.services.chat_service import card_payload

    treffer = card_payload("maps", json.dumps({"aktion": "suche", "karte": {}}))
    assert treffer is not None and treffer["kind"] == "maps"
    assert card_payload("web_search", json.dumps({"x": 1})) is None
    assert card_payload("maps", json.dumps({"error": "kaputt"})) is None
    assert card_payload("maps", "kein json") is None
    lernen = card_payload(
        "deep_learning", json.dumps({"gestartet": True, "task": {"id": "abc"}})
    )
    assert lernen is not None and lernen["data"]["id"] == "abc"


def test_standort_wird_gespeichert_und_bevorzugt(tmp_path, monkeypatch):
    import app.services.settings_service as settings_service

    monkeypatch.setattr(settings_service, "SETTINGS_FILE", tmp_path / "s.json")
    dienst = settings_service.SettingsService()
    monkeypatch.setattr(settings_service, "_service", dienst)

    from app.services.maps.service import MapsService

    service = MapsService()

    async def fake_reverse(lat, lon):
        return Place(
            id="x", name="Mirabellgarten", label="Salzburg", lat=lat, lon=lon
        )

    service.reverse = fake_reverse

    assert service._stored_home() is None

    gespeichert = asyncio.run(service.set_home(47.8095, 13.0550, "geraet"))
    assert gespeichert["name"] == "Mirabellgarten"
    assert gespeichert["quelle"] == "geraet"

    stored = service._stored_home()
    assert stored is not None
    assert stored[0] == (47.8095, 13.0550)
    assert stored[2] == "geraet"

    frisch = MapsService()
    frisch.reverse = fake_reverse
    assert asyncio.run(frisch.home()) == (47.8095, 13.0550)
    details = asyncio.run(frisch.home_details())
    assert details["name"] == "Mirabellgarten"
    assert details["quelle"] == "geraet"


def test_standort_lehnt_unsinnige_koordinaten_ab(tmp_path, monkeypatch):
    import app.services.settings_service as settings_service

    monkeypatch.setattr(settings_service, "SETTINGS_FILE", tmp_path / "s.json")
    monkeypatch.setattr(settings_service, "_service", settings_service.SettingsService())

    from app.services.maps.service import MapsService

    service = MapsService()
    for lat, lon in ((91.0, 0.0), (0.0, 181.0), (-90.5, 10.0)):
        try:
            asyncio.run(service.set_home(lat, lon))
        except MapsError:
            continue
        raise AssertionError(f"{lat},{lon} haette abgelehnt werden muessen")


def test_home_schema_prueft_quelle():
    from pydantic import ValidationError

    from app.schemas import MapsHomeIn

    assert MapsHomeIn(lat=48.0, lon=11.0).source == "geraet"
    assert MapsHomeIn(lat=48.0, lon=11.0, source="karte").source == "karte"
    try:
        MapsHomeIn(lat=48.0, lon=11.0, source="erfunden")
    except ValidationError:
        return
    raise AssertionError("unbekannte Quelle haette abgelehnt werden muessen")
