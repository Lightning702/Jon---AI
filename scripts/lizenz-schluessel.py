from __future__ import annotations

import base64
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    schluessel = Ed25519PrivateKey.generate()
    privat = base64.b64encode(schluessel.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())).decode()
    oeffentlich = base64.b64encode(schluessel.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "jon-lizenz-schluessel.txt"
    ziel.write_text(f"JON_LIZENZ_SCHLUESSEL (nur in Netlify eintragen, geheim halten):\n{privat}\n\nOEFFENTLICH (in backend/app/services/premium.py eintragen):\n{oeffentlich}\n", encoding="utf-8")
    try:
        ziel.chmod(0o600)
    except OSError:
        pass
    print(f"Neues Schlüsselpaar gespeichert in {ziel}")
    print(f"Öffentlicher Schlüssel: {oeffentlich}")
    print("Den privaten Schlüssel niemals ins Git oder in die App legen.")


if __name__ == "__main__":
    main()
