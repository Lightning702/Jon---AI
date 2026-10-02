from pathlib import Path
import json
import os
import secrets
import socket
import subprocess
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
exe = root / "backend/dist/jon-backend/jon-backend.exe"
model = exe.parent / "_internal/assets/models/whisper-base/model.bin"
if not exe.is_file() or not model.is_file():
    raise SystemExit("Backend oder mitgeliefertes Sprachmodell fehlt.")
with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
directory = root / "artifacts" / ("release-check-" + time.strftime("%Y%m%d-%H%M%S"))
directory.mkdir(parents=True)
token = secrets.token_urlsafe(32)
env = dict(os.environ, JON_DATA_DIR=str(directory / "data"), PORT=str(port), HOST="127.0.0.1", JON_TOKEN=token, JON_LAN="0", JON_ZEIT_STUMM="1", JON_SCHLUESSELSPEICHER="datei")
url = f"http://127.0.0.1:{port}/api"

def request(path, data=None, raw=False):
    headers = {"X-Jon-Token": token}
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    value = urllib.request.Request(url + path, data=data, headers=headers)
    with urllib.request.urlopen(value, timeout=20) as response:
        content = response.read()
    return content if raw else json.loads(content)


def wait_job(key):
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        value = request("/media/jobs/" + key)
        if value["status"] in {"done", "failed", "cancelled", "interrupted"}:
            if value["status"] != "done":
                raise RuntimeError(value.get("error") or value["status"])
            return value
        time.sleep(1)
    raise RuntimeError("Zeitlimit beim Medienauftrag.")


with (directory / "backend.log").open("wb") as log:
    process = subprocess.Popen([str(exe)], cwd=exe.parent, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try:
        deadline = time.monotonic() + 80
        while True:
            if process.poll() is not None:
                raise RuntimeError("Paket-Backend konnte nicht starten. " + str(directory / "backend.log"))
            try:
                health = request("/health")
                break
            except Exception:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Paket-Backend antwortet nicht.")
                time.sleep(1)
        print("Packaged backend healthy", health.get("version", ""), flush=True)
        speech = request("/media/jobs", {"kind": "speech", "text": "Am Sonntag gibt es Schnitzel zum Mittagessen. Dies ist der letzte Satz der Aufnahme."})
        wait_job(speech["id"])
        audio = request(f'/media/jobs/{speech["id"]}/files/audio.mp3', raw=True)
        print("Packaged text-to-speech:", len(audio), "bytes", flush=True)
        upload = request("/media/uploads?name=release-test.mp3", audio)
        job = request("/media/jobs", {"kind": "transcribe", "upload_id": upload["id"]})
        result = wait_job(job["id"])
        full = request(f'/media/jobs/{job["id"]}/files/transkript.txt', raw=True).decode("utf-8")
        if "sonntag" not in full.lower() or "letzte" not in full.lower():
            raise RuntimeError("Transkript unvollständig: " + full)
        print("Packaged speech-to-text:", full, flush=True)
        assert request("/agents/profiles")
        assert isinstance(request("/harness/tasks?brief=true"), list)
        print("Release smoke passed", flush=True)
    finally:
        process.terminate()
        try:
            process.wait(8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
