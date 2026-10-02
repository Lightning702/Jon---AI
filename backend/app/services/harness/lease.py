from __future__ import annotations

import hashlib
import os
from pathlib import Path


class WorkspaceLease:
    def __init__(self, directory: Path, root: str) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        key = hashlib.sha256(os.path.normcase(root).encode("utf-8")).hexdigest()
        self.file = (directory / (key + ".lock")).open("a+b")
        self.file.seek(0, 2)
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise ValueError("Ein anderer Jon-Prozess arbeitet bereits in diesem Ordner.")

    def close(self) -> None:
        if self.file.closed:
            return
        self.file.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(self.file.fileno(), fcntl.LOCK_UN)
        self.file.close()
