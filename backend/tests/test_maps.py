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
from app.services.maps.overpass import (
    CATEGORIES,
    OverpassProvider,
    category_list,
    detect_category,
    resolve_category,
    split_query,
    wants_nearby,
)
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


def test_trip_sammelt_alle_stationen_der_reihe_nach():
    from app.services.maps.service import MapsService

    service = MapsService()
    eingaben = service._station_inputs(
        {
            "from": "hier",
            "via": ["Muenchen"],
            "stops": ["Prag", "Wien"],
            "to": "Berlin",
        }
    )
    assert eingaben == ["hier", "Muenchen", "Prag", "Wien", "Berlin"]
    assert service._station_inputs({"stops": ["Prag", "Berlin"]}) == [
        "hier",
        "Prag",
        "Berlin",
    ]
    assert service._station_inputs({"to": ["Prag", "Berlin"]}) == [
        "hier",
        "Prag",
        "Berlin",
    ]
    assert service._station_inputs({"to": ""}) == ["hier"]


def test_trip_faltet_doppelte_stationen_zusammen():
    from app.services.maps.service import MapsService

    orte = {
        "hier": (47.8095, 13.0550),
        "salzburg": (47.8096, 13.0551),
        "prag": (50.0755, 14.4378),
        "berlin": (52.5200, 13.4050),
    }
    service = MapsService()

    async def fake_resolve(value, near=None):
        key = str(value).lower()
        lat, lon = orte[key]
        return Place(id=key, name=key.title(), label=key, lat=lat, lon=lon)

    service.resolve_point = fake_resolve

    stationen = asyncio.run(
        service._resolve_stations(
            {"from": "hier", "stops": ["salzburg", "prag", "berlin"]}, None
        )
    )
    assert [ort.name for ort in stationen] == ["Hier", "Prag", "Berlin"]

    try:
        asyncio.run(service._resolve_stations({"from": "hier"}, None))
    except MapsError:
        return
    raise AssertionError("ein einzelner Ort ist noch kein Trip")


def test_trip_text_listet_jeden_abschnitt():
    from app.services.maps.service import MapsService

    service = MapsService()
    stationen = [
        Place(id="a", name="Salzburg", label="", lat=47.8, lon=13.0),
        Place(id="b", name="Prag", label="", lat=50.0, lon=14.4),
        Place(id="c", name="Berlin", label="", lat=52.5, lon=13.4),
    ]
    route = RouteOption(
        id="r",
        mode="auto",
        distance_m=700_000.0,
        duration_s=25_200.0,
        geometry=[],
        legs=[
            {"distanz_m": 400_000.0, "dauer_s": 14_400.0, "zusammenfassung": ""},
            {"distanz_m": 300_000.0, "dauer_s": 10_800.0, "zusammenfassung": ""},
        ],
    )
    abschnitte = service._legs(stationen, route)
    assert [(leg["von"], leg["nach"]) for leg in abschnitte] == [
        ("Salzburg", "Prag"),
        ("Prag", "Berlin"),
    ]
    text = service._trip_text(stationen, "auto", [route], abschnitte)
    assert "Salzburg → Prag → Berlin" in text
    assert "1. Salzburg → Prag" in text
    assert "2. Prag → Berlin" in text
    assert "400 km" in text

    ohne_legs = service._legs(stationen, None)
    assert len(ohne_legs) == 2
    assert ohne_legs[0]["distanz_m"] == 0.0


def test_filter_und_marken_werden_erkannt():
    assert split_query("nächster Supermarkt") == ("supermarkt", "")
    assert split_query("zum nächsten Supermarkt") == ("supermarkt", "")
    assert split_query("Supermarkt in meiner Nähe") == ("supermarkt", "")
    assert split_query("Apotheken in der Nähe") == ("apotheke", "")
    assert split_query("Interspar in meiner Nähe") == ("supermarkt", "Interspar")
    assert split_query("Hofer Supermarkt") == ("supermarkt", "Hofer")
    assert split_query("dm drogerie") == ("drogerie", "dm")
    assert split_query("Berlin") == ("", "Berlin")
    assert split_query("Hauptstraße 5, Wien") == ("", "Hauptstraße 5, Wien")
    assert wants_nearby("Tankstelle in der Nähe")
    assert wants_nearby("die nächste Apotheke")
    assert not wants_nearby("Salzburg Hauptbahnhof")


def test_overpass_filtert_nach_kategorie_und_name():
    provider = OverpassProvider()
    kategorie = provider._query("apotheke", 47.8, 13.05, 2500)
    assert '["amenity"="pharmacy"]' in kategorie
    assert "around:2500,47.8,13.05" in kategorie
    marke = provider._name_query("Interspar", "supermarkt", 47.8, 13.05, 5000)
    assert '["name"~"Interspar",i]' in marke
    assert "supermarket" in marke
    frei = provider._name_query("Sacher", "", 47.8, 13.05, 5000)
    assert '["shop"]' in frei and '["amenity"]' in frei
    assert detect_category({"shop": "supermarket"}) == "supermarkt"
    assert detect_category({"amenity": "pharmacy"}) == "apotheke"
    assert detect_category({"shop": "hardware"}) == "geschaeft"
    assert detect_category({"highway": "residential"}) == ""


class _FakePlaces:
    name = "fake"

    def __init__(self, treffer):
        self.treffer = treffer
        self.aufrufe = []

    async def nearby(self, category, lat, lon, radius_m=1500, limit=20):
        self.aufrufe.append((category, radius_m))
        return [
            ort
            for ort in self.treffer
            if str(ort.extra.get("kategorie")) == category
        ][:limit]

    async def named(self, name, lat, lon, radius_m=5000, category="", limit=20):
        self.aufrufe.append((f"{category}:{name}", radius_m))
        gesucht = name.lower()
        return [
            ort
            for ort in self.treffer
            if gesucht in ort.name.lower()
            and (not category or str(ort.extra.get("kategorie")) == category)
        ][:limit]


def _maerkte():
    return [
        Place(
            id="osm:n:1",
            name="Billa",
            label="Getreidegasse 1",
            lat=47.8100,
            lon=13.0560,
            kind="poi",
            category="Supermärkte",
            distance_m=180.0,
            extra={"kategorie": "supermarkt", "icon": "🛒"},
        ),
        Place(
            id="osm:n:2",
            name="Interspar",
            label="Alpenstraße 107",
            lat=47.8150,
            lon=13.0600,
            kind="poi",
            category="Supermärkte",
            distance_m=900.0,
            extra={"kategorie": "supermarkt", "icon": "🛒"},
        ),
        Place(
            id="osm:n:3",
            name="Hofer",
            label="Bahnhofstraße 3",
            lat=47.8200,
            lon=13.0700,
            kind="poi",
            category="Supermärkte",
            distance_m=1600.0,
            extra={"kategorie": "supermarkt", "icon": "🛒"},
        ),
    ]


def _service_mit_orten(orte):
    from app.services.maps.service import MapsService

    service = MapsService()
    service._places = _FakePlaces(orte)

    async def fake_home():
        return (47.8095, 13.0550)

    async def fake_reverse(lat, lon):
        return Place(
            id="standort", name="Mein Standort", label="Salzburg", lat=lat, lon=lon
        )

    async def fake_route(points, mode="auto", alternatives=True):
        return [
            RouteOption(
                id="r1",
                mode=mode,
                distance_m=1200.0,
                duration_s=420.0,
                geometry=[[p[1], p[0]] for p in points],
                steps=[RouteStep(text="Ziel erreicht", distance_m=0.0, duration_s=0.0)],
                legs=[{"distanz_m": 1200.0, "dauer_s": 420.0, "zusammenfassung": ""}],
            )
        ]

    service.home = fake_home
    service.reverse = fake_reverse
    service.route = fake_route
    return service


def test_route_zum_naechsten_supermarkt():
    service = _service_mit_orten(_maerkte())
    ergebnis = asyncio.run(
        service.answer(
            "route", {"from": "hier", "to": "nächster Supermarkt", "mode": "auto"}
        )
    )
    assert ergebnis["filter"] == "supermarkt"
    assert ergebnis["start"]["name"] == "Mein Standort"
    assert ergebnis["ziel"]["name"] == "Billa"
    assert [ort["name"] for ort in ergebnis["ziel_optionen"]] == ["Interspar", "Hofer"]
    assert "Auch in der Nähe" in ergebnis["text"]


def test_route_zur_marke_in_der_naehe():
    service = _service_mit_orten(_maerkte())
    ergebnis = asyncio.run(
        service.answer(
            "route", {"from": "hier", "to": "Interspar in meiner Nähe", "mode": "auto"}
        )
    )
    assert ergebnis["ziel"]["name"] == "Interspar"
    assert ergebnis["filter"] == "supermarkt"
    assert ergebnis["ziel_optionen"] == []


def test_umgebung_nennt_filter_und_label():
    service = _service_mit_orten(_maerkte())
    ergebnis = asyncio.run(
        service.answer("umgebung", {"category": "Supermärkte in meiner Nähe"})
    )
    assert ergebnis["filter"] == "supermarkt"
    assert ergebnis["kategorie"] == "Supermärkte"
    assert [ort["name"] for ort in ergebnis["treffer"]] == [
        "Billa",
        "Interspar",
        "Hofer",
    ]
    assert ergebnis["karte"]["marker"]


def test_umgebungssuche_weitet_den_radius_aus():
    service = _service_mit_orten([])
    ergebnis = asyncio.run(service.answer("umgebung", {"category": "apotheke"}))
    assert ergebnis["treffer"] == []
    assert [radius for _, radius in service._places.aufrufe] == [2500, 10000, 25000]


def test_maps_tool_beschreibt_alle_filter():
    from app.services.tools import ToolBox

    schema = [
        eintrag
        for eintrag in ToolBox()._all_tools()
        if eintrag["function"]["name"] == "maps"
    ][0]
    text = schema["function"]["description"]
    for key in ("supermarkt", "apotheke", "restaurant", "tankstelle"):
        assert key in text
    assert "Interspar" in text
