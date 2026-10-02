import base64

import pytest
from fastapi import HTTPException

from app.api import mobile_routes as mobile


def test_metadata_merge_preserves_other_chats(tmp_path, monkeypatch):
    monkeypatch.setattr(mobile, "_state", tmp_path / "state.json")
    mobile.update_state({"chats": {"first": {"pinned": True}}})
    mobile.update_state({"chats": {"second": {"archived": True}}})
    assert mobile.state()["chats"] == {"first": {"pinned": True}, "second": {"archived": True}}
    with pytest.raises(HTTPException):
        mobile.update_state({"credentials": "must-not-store"})


def test_chunked_download_preserves_binary(tmp_path, monkeypatch):
    target = tmp_path / "presentation.pptx"
    raw = bytes(range(256)) * 3800
    target.write_bytes(raw)
    monkeypatch.setattr(mobile, "_file", lambda path: target)
    received = bytearray()
    offset = 0
    while offset < len(raw):
        chunk = mobile.file_chunk(str(target), offset)
        received.extend(base64.b64decode(chunk["data"]))
        offset = chunk["offset"]
    assert received == raw
    with pytest.raises(HTTPException):
        mobile.file_chunk(str(target), -1)


def test_private_files_are_not_previewable(tmp_path, monkeypatch):
    class Room:
        def frei(self, target):
            return False, "Kein Zugriff"

    monkeypatch.setattr(mobile, "get_dateiraum_service", lambda: Room())
    with pytest.raises(HTTPException) as error:
        mobile._file(str(tmp_path / "secret.txt"))
    assert error.value.status_code == 403


def test_upload_rejects_invalid_base64():
    with pytest.raises(HTTPException) as error:
        mobile.upload(mobile.Upload(name="test.txt", data="not base64!"))
    assert error.value.status_code == 400
