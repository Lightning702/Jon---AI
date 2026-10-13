import pytest

from app.services.fenster_wechsel import _ohne_browser, wunsch


@pytest.mark.parametrize("text,erwartet", [
    ("wechsle den Tab zu Claude", ("Claude", True)),
    ("wechsle den tab zuu claude", ("claude", True)),
    ("Wechsel zu YouTube", ("YouTube", False)),
    ("geh zum Tab mit Gmail", ("Gmail", True)),
    ("Jon, spring zu Spotify", ("Spotify", False)),
    ("zeig mir das Fenster von Discord", ("Discord", False)),
    ("kannst du bitte zum Tab mit YouTube wechseln", ("YouTube", True)),
    ("wechsle zu tab 3", ("3", True)),
    ("wechsel zum Fenster wo Spotify läuft", ("Spotify", False)),
    ("switch to claude", ("claude", False)),
])
def test_wechsel_wird_erkannt(text, erwartet):
    assert wunsch(text) == erwartet


@pytest.mark.parametrize("text", [
    "wechsle das Modell",
    "zeig mir das Wetter",
    "öffne YouTube",
    "wechsle zum Dunkelmodus",
    "wechsle die Stimme zu Funke",
    "Wechsle bitte das Thema, ich will über etwas ganz anderes reden und dir eine lange Geschichte erzählen",
])
def test_kein_wechsel(text):
    assert wunsch(text) is None


def test_browsername_wird_entfernt():
    assert _ohne_browser("Neue Unterhaltung - Claude - Google Chrome") == "Neue Unterhaltung - Claude"
    assert _ohne_browser("YouTube - Persönlich – Microsoft​ Edge") == "YouTube - Persönlich"
