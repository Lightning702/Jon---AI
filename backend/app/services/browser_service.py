from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
from datetime import datetime
from queue import Empty, Queue

from app.core.config import DATA_DIR

BROWSER_DIR = DATA_DIR / "browser"
ACTION_TIMEOUT_MS = 15000
CALL_TIMEOUT_S = 25
READ_TEXT_LIMIT = 6000
MAX_ELEMENTS = 60

_SELECTOR_RE = re.compile(r"^([#.\[/]|xpath=|css=|text=|//)|[>:=\"\']")

ELEMENTS_JS = """
() => {
  const items = [];
  const seen = new Set();
  const nodes = document.querySelectorAll(
    'a[href], button, input, select, textarea, [role="button"], [onclick]'
  );
  let i = 0;
  for (const el of nodes) {
    if (items.length >= 60) break;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;
    const style = getComputedStyle(el);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    const tag = el.tagName.toLowerCase();
    const text = (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '')
      .trim().replace(/\\s+/g, ' ').slice(0, 80);
    let selector = '';
    if (el.id) selector = '#' + CSS.escape(el.id);
    else if (el.name) selector = tag + '[name="' + el.name + '"]';
    else {
      const cls = (el.className && typeof el.className === 'string')
        ? el.className.trim().split(/\\s+/).slice(0, 2).map((c) => '.' + CSS.escape(c)).join('')
        : '';
      selector = tag + cls;
      const matches = document.querySelectorAll(selector);
      if (matches.length > 1) {
        let idx = 0;
        for (const m of matches) { if (m === el) break; idx++; }
        selector = selector + ' >> nth=' + idx;
      }
    }
    if (seen.has(selector)) continue;
    seen.add(selector);
    const entry = { tag, text, selector };
    if (tag === 'input') entry.type = el.type || 'text';
    if (tag === 'a') entry.href = (el.getAttribute('href') || '').slice(0, 120);
    items.push(entry);
    i++;
  }
  return items;
}
"""


def _friendly(exc: Exception) -> str:
    text = str(exc)
    if "Timeout" in type(exc).__name__ or "Timeout" in text[:80]:
        return "Zeitüberschreitung (15 s) - das Element oder die Seite hat nicht reagiert."
    if "net::ERR_NAME_NOT_RESOLVED" in text:
        return "Die Adresse wurde nicht gefunden - stimmt die URL?"
    if "net::ERR_INTERNET_DISCONNECTED" in text:
        return "Keine Internetverbindung."
    if "Executable doesn't exist" in text:
        return "Chromium ist noch nicht installiert."
    first = text.splitlines()[0] if text else "Unbekannter Fehler"
    return first[:300]


class BrowserService:
    def __init__(self) -> None:
        self._queue: Queue = Queue()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._installing = False
        self._install_done = False
        self._install_error = ""

    def _ensure_thread(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()

    def _install_chromium(self) -> None:
        with self._lock:
            if self._installing:
                return
            self._installing = True
        try:
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True,
                timeout=900,
            )
            with self._lock:
                self._install_done = result.returncode == 0
                self._install_error = (
                    "" if result.returncode == 0 else result.stderr[-400:]
                )
        except Exception as exc:
            with self._lock:
                self._install_error = str(exc)
        finally:
            with self._lock:
                self._installing = False

    def _run(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            while True:
                try:
                    _op, _args, out = self._queue.get(timeout=60)
                except Empty:
                    return
                out.put(
                    (
                        "err",
                        RuntimeError(
                            "Playwright ist nicht installiert "
                            f"(pip install playwright): {exc}"
                        ),
                    )
                )
        pw = sync_playwright().start()
        state = {"browser": None, "page": None}

        def page():
            if state["browser"] is None or not state["browser"].is_connected():
                state["browser"] = pw.chromium.launch(headless=False)
                state["page"] = None
            if state["page"] is None or state["page"].is_closed():
                state["page"] = state["browser"].new_page()
                state["page"].set_default_timeout(ACTION_TIMEOUT_MS)
            return state["page"]

        def resolve_target(p, target: str):
            target = target.strip()
            if _SELECTOR_RE.search(target):
                loc = p.locator(target).first
                try:
                    if loc.count() > 0:
                        return loc
                except Exception:
                    pass
            by_text = p.get_by_text(target, exact=False).first
            try:
                if by_text.count() > 0:
                    return by_text
            except Exception:
                pass
            by_role = p.get_by_role("button", name=target).first
            try:
                if by_role.count() > 0:
                    return by_role
            except Exception:
                pass
            by_label = p.get_by_label(target).first
            try:
                if by_label.count() > 0:
                    return by_label
            except Exception:
                pass
            raise RuntimeError(
                f"Kein Element gefunden für '{target}'. Rufe browser_read auf "
                "und nutze einen Selektor oder sichtbaren Text aus "
                "interaktive_elemente."
            )

        while True:
            op, args, out = self._queue.get()
            if op == "__quit__":
                break
            try:
                if op == "goto":
                    p = page()
                    p.goto(str(args.get("url", "")), wait_until="domcontentloaded")
                    out.put(("ok", {"titel": p.title(), "url": p.url}))
                elif op == "click":
                    p = page()
                    resolve_target(p, str(args.get("target", ""))).click()
                    p.wait_for_load_state("domcontentloaded")
                    out.put(("ok", {"geklickt": args.get("target"), "url": p.url}))
                elif op == "fill":
                    p = page()
                    loc = resolve_target(p, str(args.get("target", "")))
                    loc.fill(str(args.get("text", "")))
                    if args.get("press_enter"):
                        loc.press("Enter")
                        p.wait_for_load_state("domcontentloaded")
                    out.put(
                        ("ok", {"ausgefuellt": args.get("target"), "url": p.url})
                    )
                elif op == "read":
                    p = page()
                    body = p.locator("body")
                    text = ""
                    try:
                        text = body.inner_text(timeout=5000)
                    except Exception:
                        text = ""
                    text = re.sub(r"\n{3,}", "\n\n", text).strip()[:READ_TEXT_LIMIT]
                    elements = []
                    try:
                        elements = p.evaluate(ELEMENTS_JS)[:MAX_ELEMENTS]
                    except Exception:
                        elements = []
                    out.put(
                        (
                            "ok",
                            {
                                "titel": p.title(),
                                "url": p.url,
                                "sichtbarer_text": text,
                                "interaktive_elemente": elements,
                            },
                        )
                    )
                elif op == "screenshot":
                    p = page()
                    BROWSER_DIR.mkdir(parents=True, exist_ok=True)
                    file = (
                        BROWSER_DIR
                        / f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
                    )
                    p.screenshot(path=str(file))
                    out.put(("ok", {"datei": str(file), "url": p.url}))
                elif op == "back":
                    p = page()
                    p.go_back(wait_until="domcontentloaded")
                    out.put(("ok", {"titel": p.title(), "url": p.url}))
                elif op == "close":
                    if state["browser"] is not None:
                        try:
                            state["browser"].close()
                        except Exception:
                            pass
                    state["browser"] = None
                    state["page"] = None
                    out.put(("ok", {"geschlossen": True}))
                else:
                    out.put(("err", RuntimeError(f"Unbekannte Aktion: {op}")))
            except Exception as exc:
                out.put(("err", exc))

    def call(self, op: str, args: dict) -> str:
        self._ensure_thread()
        out: Queue = Queue()
        self._queue.put((op, args, out))
        try:
            status, result = out.get(timeout=CALL_TIMEOUT_S)
        except Empty:
            return json.dumps(
                {"error": "Zeitüberschreitung - der Browser reagiert nicht."},
                ensure_ascii=False,
            )
        if status == "ok":
            return json.dumps(result, ensure_ascii=False)
        message = _friendly(result)
        if "Chromium ist noch nicht installiert" in message:
            with self._lock:
                installing = self._installing
                error = self._install_error
            if not installing:
                threading.Thread(target=self._install_chromium, daemon=True).start()
                return json.dumps(
                    {
                        "error": "Chromium wird gerade zum ersten Mal installiert "
                        "(einmalig, dauert ein paar Minuten). Sag dem Nutzer "
                        "Bescheid und versuch es danach noch einmal."
                    },
                    ensure_ascii=False,
                )
            if error:
                return json.dumps(
                    {"error": f"Chromium-Installation fehlgeschlagen: {error}"},
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "error": "Chromium wird noch installiert - bitte gleich "
                    "noch einmal versuchen."
                },
                ensure_ascii=False,
            )
        return json.dumps({"error": message}, ensure_ascii=False)


_service: BrowserService | None = None


def get_browser_service() -> BrowserService:
    global _service
    if _service is None:
        _service = BrowserService()
    return _service
