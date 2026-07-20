from __future__ import annotations

import json
import math
import threading
from datetime import datetime
from pathlib import Path

from app.core.config import DATA_DIR

STATUS_FILE = DATA_DIR / "mini_jon.json"
SLEEP_GIF = DATA_DIR / "mini_jon_schlaeft.gif"
STATUS_AWAKE = "wach"
STATUS_ASLEEP = "schlaeft"
FRAMES = 14
FRAME_MS = 140
SIZE = 480


class MiniJonService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        try:
            data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("status") in (
                STATUS_AWAKE,
                STATUS_ASLEEP,
            ):
                return {
                    "status": str(data["status"]),
                    "since": str(data.get("since", "")),
                }
        except Exception:
            pass
        return {
            "status": STATUS_AWAKE,
            "since": datetime.now().isoformat(timespec="seconds"),
        }

    def _save(self) -> None:
        try:
            STATUS_FILE.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def status(self) -> dict:
        with self._lock:
            return dict(self._data)

    def is_sleeping(self) -> bool:
        return self.status().get("status") == STATUS_ASLEEP

    def set_status(self, value: str) -> dict:
        norm = str(value or "").strip().lower().replace("ä", "ae")
        if norm in ("schlaeft", "schlafen", "schlaf", "sleep", "sleeping"):
            norm = STATUS_ASLEEP
        elif norm in ("wach", "awake", "auf", "wake"):
            norm = STATUS_AWAKE
        else:
            return {"error": "status muss 'wach' oder 'schlaeft' sein", **self.status()}
        with self._lock:
            if self._data.get("status") != norm:
                self._data = {
                    "status": norm,
                    "since": datetime.now().isoformat(timespec="seconds"),
                }
                self._save()
            return dict(self._data)

    def sleep_animation(self) -> Path | None:
        if SLEEP_GIF.exists() and SLEEP_GIF.stat().st_size > 0:
            return SLEEP_GIF
        try:
            self._render_sleep_gif(SLEEP_GIF)
        except Exception:
            return None
        if SLEEP_GIF.exists() and SLEEP_GIF.stat().st_size > 0:
            return SLEEP_GIF
        return None

    @staticmethod
    def _mix(a: tuple, b: tuple, t: float) -> tuple:
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    @staticmethod
    def _draw_z(draw, x: float, y: float, size: float, color: tuple, width: int) -> None:
        draw.line([(x, y), (x + size, y)], fill=color, width=width)
        draw.line([(x + size, y), (x, y + size)], fill=color, width=width)
        draw.line([(x, y + size), (x + size, y + size)], fill=color, width=width)

    def _render_sleep_gif(self, path: Path) -> None:
        from PIL import Image, ImageDraw

        bg = (16, 16, 22)
        face = (10, 10, 14)
        gold = (212, 175, 55)
        gold_light = (245, 214, 123)
        cx = SIZE // 2
        cy = SIZE // 2 + 30
        frames = []
        for i in range(FRAMES):
            t = i / FRAMES
            breath = math.sin(t * 2 * math.pi)
            r = 150 + breath * 4
            img = Image.new("RGB", (SIZE, SIZE), bg)
            draw = ImageDraw.Draw(img)
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r], fill=face, outline=gold, width=12
            )
            dy = breath * 2
            for ex in (cx - 92, cx + 24):
                draw.arc(
                    [ex, cy - 52 + dy, ex + 68, cy - 4 + dy],
                    start=20,
                    end=160,
                    fill=gold,
                    width=10,
                )
            draw.arc(
                [cx - 26, cy + 48 + dy, cx + 26, cy + 84 + dy],
                start=20,
                end=160,
                fill=gold,
                width=8,
            )
            for n in range(3):
                phase = (t + n * 0.33) % 1.0
                glow = math.sin(phase * math.pi)
                zx = cx + 100 + n * 36 + phase * 26
                zy = cy - 160 - n * 26 - phase * 70
                zs = 16 + n * 8 + phase * 6
                self._draw_z(draw, zx, zy, zs, self._mix(bg, gold_light, glow), 6)
            frames.append(img)
        frames[0].save(
            path,
            save_all=True,
            append_images=frames[1:],
            duration=FRAME_MS,
            loop=0,
            optimize=True,
        )


_service: MiniJonService | None = None


def get_mini_jon_service() -> MiniJonService:
    global _service
    if _service is None:
        _service = MiniJonService()
    return _service
