import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE = os.path.join(ROOT, "website")
JON_ZIP = os.path.join(WEBSITE, "jon.zip")
OUT = os.path.join(ROOT, "netlify-upload.zip")


def baue_jon_zip():
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    dateien = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    dateien = [f for f in dateien if f and f != "MEMORY.md" and f != "website/jon.zip"]
    with zipfile.ZipFile(JON_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("Jon/"), "")
        for f in sorted(dateien):
            quelle = os.path.join(ROOT, f.replace("/", os.sep))
            ziel = "Jon/" + f
            with open(quelle, "rb") as fh:
                daten = fh.read()
            if f.endswith(".sh"):
                daten = daten.replace(b"\r\n", b"\n")
                info = zipfile.ZipInfo(ziel)
                info.external_attr = 0o755 << 16
                z.writestr(info, daten, zipfile.ZIP_DEFLATED)
            else:
                z.write(quelle, ziel)
    return len(dateien)


def baue_netlify_zip():
    anzahl = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for ordner, _, dateien in os.walk(WEBSITE):
            for name in dateien:
                quelle = os.path.join(ordner, name)
                ziel = os.path.relpath(quelle, WEBSITE).replace(os.sep, "/")
                z.write(quelle, ziel)
                anzahl += 1
    return anzahl


def main():
    if not os.path.isdir(WEBSITE):
        print("FEHLER: website-Ordner nicht gefunden.")
        return 1
    try:
        n = baue_jon_zip()
        print(f"website/jon.zip neu gebaut ({n} Dateien).")
    except Exception as e:
        print(f"Warnung: jon.zip nicht neu gebaut ({e}) - nehme die vorhandene Datei.")
    anzahl = baue_netlify_zip()
    groesse = os.path.getsize(OUT) / 1024 / 1024
    print(f"netlify-upload.zip fertig: {anzahl} Dateien, {groesse:.2f} MB")
    print("")
    print("So laedst du hoch (dauert nur Sekunden):")
    print("  Bestehende Website: app.netlify.com -> deine Website -> Deploys ->")
    print("  netlify-upload.zip auf die Flaeche ziehen.")
    print("  Neue Website: app.netlify.com/drop -> Zip drauf ziehen.")
    print("WICHTIG: Nie mehr den ganzen Jon-Ordner hochladen - der enthaelt ueber 1 GB")
    print("(backend/dist, node_modules), deshalb dauerte es 15 Minuten und brach ab.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
