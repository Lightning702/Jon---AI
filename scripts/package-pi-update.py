from pathlib import Path
import hashlib
import json
import zipfile

root = Path(__file__).resolve().parents[1]
output = root / "artifacts" / "minijon-1.6.0" / "Jon-Pi-Update.zip"
files = {}
for folder, prefix in ((root / "backend/app", "backend/app"), (root / "frontend/dist", "webapp")):
    if not folder.is_dir():
        raise SystemExit(f"Build fehlt: {folder}")
    for path in folder.rglob("*"):
        if not path.is_file() or path.is_symlink() or "__pycache__" in path.parts or path.suffix == ".pyc" or path.name.startswith(".env"):
            continue
        files[prefix + "/" + path.relative_to(folder).as_posix()] = path.read_bytes()
for name in ("backend/requirements.txt", "backend/requirements-pi.txt"):
    files[name] = (root / name).read_bytes()
if "webapp/index.html" not in files:
    raise SystemExit("Web-Oberfläche fehlt.")
for name, content in files.items():
    if name.endswith(".py"):
        compile(content.decode("utf-8-sig"), name, "exec")
manifest = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
    for name, content in files.items():
        archive.writestr(name, content)
    archive.writestr("SHA256.json", json.dumps(manifest, indent=2))
print(f"{output}\n{len(files)} Dateien, {output.stat().st_size} Bytes")
