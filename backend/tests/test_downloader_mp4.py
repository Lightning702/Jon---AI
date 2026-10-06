from __future__ import annotations

import shutil
import subprocess

import pytest

from app.services.downloader_service import format_for, kompatibel_machen, spuren

ffmpeg_fehlt = pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="ffmpeg fehlt")


def test_mp4_bevorzugt_h264_und_aac_und_faellt_nie_ins_leere():
    for qualitaet in ("best", "1080", "720", "480"):
        format_ = format_for("mp4", qualitaet)
        assert format_.startswith("bv*[vcodec^=avc1]")
        assert "+ba[acodec^=mp4a]" in format_
        assert format_.endswith("/bv*+ba/b")
    assert "[height<=720]" in format_for("mp4", "720") and "height" not in format_for("mp4", "best")
    assert format_for("mp3", "best") == "bestaudio/best"


def erzeugen(ziel, video, audio):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=15:duration=2", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", video, "-c:a", audio, "-shortest", str(ziel)], check=True)


@ffmpeg_fehlt
@pytest.mark.parametrize("name,video,audio", [("vp9.webm", "libvpx-vp9", "libopus"), ("av1.mp4", "libaom-av1", "aac"), ("opus.mkv", "libx264", "libopus")])
def test_nicht_abspielbare_codecs_werden_zu_h264_mp4(tmp_path, name, video, audio):
    quelle = tmp_path / name
    try:
        erzeugen(quelle, video, audio)
    except subprocess.CalledProcessError:
        pytest.skip(f"ffmpeg kann {video} nicht erzeugen")
    meldungen = []
    ziel = kompatibel_machen(quelle, meldungen.append)
    assert ziel.suffix == ".mp4" and ziel.is_file() and not quelle.exists()
    assert spuren(ziel) == {"video": "h264", "audio": "aac"}
    assert meldungen and "MP4" in meldungen[0]


@ffmpeg_fehlt
def test_h264_mit_aac_bleibt_unveraendert(tmp_path):
    quelle = tmp_path / "gut.mp4"
    erzeugen(quelle, "libx264", "aac")
    groesse = quelle.stat().st_size
    assert kompatibel_machen(quelle) == quelle and quelle.stat().st_size == groesse
