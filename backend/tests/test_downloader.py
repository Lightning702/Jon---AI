import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.downloader_service import (
    cookie_load_failed,
    count_cookies,
    format_for,
    friendly_error,
    music_source,
    needs_auth,
    normalize_cookie_text,
    sanitize_filename,
    valid_url,
)

COOKIE_SAMPLE = (
    "# Netscape HTTP Cookie File\n"
    ".youtube.com\tTRUE\t/\tTRUE\t1799999999\tSID\tabc123\n"
    "#HttpOnly_.youtube.com\tTRUE\t/\tTRUE\t1799999999\tHSID\tdef456\n"
)


def test_dateiname_wird_bereinigt():
    assert sanitize_filename('Video: "Test" <1>?|*') == "Video Test 1"
    assert sanitize_filename("   ") == "download"
    assert len(sanitize_filename("x" * 500)) == 120


def test_formatwahl():
    assert format_for("mp3", "best") == "bestaudio/best"
    assert "height<=720" in format_for("mp4", "720")
    assert format_for("mp4", "best").startswith("bestvideo")


def test_fehler_werden_uebersetzt():
    assert "privat" in friendly_error("ERROR: Private video. Sign in.")
    assert "Land" in friendly_error("The uploader has not made this video available in your country")
    assert "existiert nicht mehr" in friendly_error("Video unavailable")
    assert friendly_error("something odd").startswith("Download fehlgeschlagen")


def test_bezahlvideo_verweist_auf_login():
    text = friendly_error("ERROR: [youtube] fXUkxi6AEn0: This video requires payment to watch")
    assert "kostenpflichtig" in text
    assert "youtube-login" in text.lower()


def test_gescheiterter_login_wird_benannt():
    text = friendly_error("This video requires payment to watch", True)
    assert "nicht gereicht" in text
    assert "youtube-login" in text.lower()


def test_login_pflichtige_fehler_werden_erkannt():
    assert needs_auth("This video requires payment to watch")
    assert needs_auth("Sign in to confirm you're not a bot")
    assert needs_auth("Join this channel to get access to members-only content")
    assert not needs_auth("The uploader has not made this video available in your country")
    assert not needs_auth("Video unavailable")


def test_cookie_ladefehler_zaehlt_nicht_als_login_versuch():
    assert cookie_load_failed("could not find firefox cookies database")
    assert cookie_load_failed("unsupported browser: netscape")
    assert not cookie_load_failed("This video requires payment to watch")


def test_cookies_werden_normalisiert():
    normalized = normalize_cookie_text(COOKIE_SAMPLE)
    assert normalized.startswith("# Netscape HTTP Cookie File")
    assert count_cookies(normalized) == 2
    assert "#HttpOnly_.youtube.com" in normalized


def test_cookies_mit_leerzeichen_werden_repariert():
    normalized = normalize_cookie_text(".youtube.com TRUE / TRUE 1799999999 SID abc123")
    assert count_cookies(normalized) == 1
    assert "\t" in normalized


def test_unbrauchbare_cookies_werden_abgelehnt():
    assert normalize_cookie_text("das ist kein cookie file") == ""
    assert normalize_cookie_text("") == ""


def test_musik_links_werden_erkannt():
    assert music_source("https://open.spotify.com/track/abc") == "spotify"
    assert music_source("https://spotify.link/xyz") == "spotify"
    assert music_source("https://music.amazon.de/tracks/B0ABC") == "amazon"
    assert music_source("https://www.youtube.com/watch?v=x") == ""


def test_url_pruefung():
    assert valid_url("https://example.com/v")
    assert not valid_url("ftp://example.com")
    assert not valid_url("kein link")


def test_humanizer_score_erkennt_ki_muster():
    from app.services.humanize_service import score

    robotic = (
        "Darüber hinaus spielt eine entscheidende Rolle die Digitalisierung im Alltag. "
        "Des Weiteren ist es wichtig zu beachten, dass eine Vielzahl von Prozessen läuft. "
        "Darüber hinaus zeigt sich die Bedeutung in der heutigen Zeit sehr deutlich. "
        "Des Weiteren lässt sich zusammenfassend sagen, dass alles von großer Bedeutung ist."
    )
    human = (
        "Gestern hab ich das mal ausprobiert. Lief nicht. Nach zwanzig Minuten und zwei "
        "Kaffees stellte sich raus, dass nur ein Kabel locker war — typisch. Manchmal ist "
        "die Lösung eben peinlich einfach, auch wenn man vorher stundenlang im Handbuch "
        "gewühlt hat. Kurz: erst Kabel prüfen, dann googeln."
    )
    assert score(robotic)["score"] > score(human)["score"]
    assert score(robotic)["phrases"]
