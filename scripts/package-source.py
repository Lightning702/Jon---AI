from pathlib import Path
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
entries = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=root).split(b"\0")
output = root / "website" / "jon.zip"
process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
try:
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            if not entry:
                continue
            metadata, raw_name = entry.split(b"\t", 1)
            mode, key, stage = metadata.split()
            name = raw_name.decode("utf-8")
            if stage != b"0" or mode not in {b"100644", b"100755"} or name in {"website/jon.zip", "website/jon-erweiterung.zip", "MEMORY.md"}:
                continue
            if name.startswith(("design/", "artifacts/")) or name.endswith((".env", ".jks", ".keystore")):
                continue
            process.stdin.write(key + b"\n")
            process.stdin.flush()
            header = process.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise RuntimeError("Ungültiger Git-Blob: " + name)
            size = int(header[2])
            content = process.stdout.read(size)
            process.stdout.read(1)
            if len(content) != size:
                raise RuntimeError("Unvollständiger Git-Blob: " + name)
            info = zipfile.ZipInfo("Jon/" + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if mode == b"100755" else 0o100644) << 16
            archive.writestr(info, content)
finally:
    process.stdin.close()
    process.wait()
print(f"{output}: {output.stat().st_size} Bytes")
