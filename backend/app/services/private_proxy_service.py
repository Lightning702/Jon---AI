from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import quote, urlsplit

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
FETCH_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}
MAX_BYTES = 8_000_000
BASE_RE = re.compile(r"<base\b[^>]*>", re.IGNORECASE)
HEAD_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)

INJECT_TEMPLATE = (
    '<base href="__BASE__">'
    "<script>(function(){"
    "function abs(u){try{return new URL(u,document.baseURI).href;}catch(e){return null;}}"
    "function nav(u){var a=abs(u);if(a&&/^https?:/i.test(a))parent.postMessage({jonNav:a},'*');}"
    "document.addEventListener('click',function(e){"
    "var a=e.target&&e.target.closest?e.target.closest('a[href]'):null;"
    "if(!a)return;var h=a.getAttribute('href')||'';"
    "if(h.charAt(0)==='#'||/^javascript:/i.test(h))return;"
    "e.preventDefault();nav(a.href);},true);"
    "document.addEventListener('submit',function(e){"
    "var f=e.target;if(!f||(f.method||'get').toLowerCase()!=='get')return;"
    "e.preventDefault();var q=new URLSearchParams(new FormData(f)).toString();"
    "var base=(f.action||document.baseURI).split('#')[0].split('?')[0];"
    "nav(base+(q?'?'+q:''));},true);"
    "window.open=function(u){nav(u);return null;};"
    "})();</script>"
)


def proxy_target(url: str) -> str:
    return "/api/private/proxy?url=" + quote(url, safe="")


def _blocked(host: str) -> bool:
    host = (host or "").strip().lower().strip("[]")
    if not host:
        return True
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    for info in infos:
        addr = info[4][0].split("%")[0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
            or addr in ("169.254.169.254", "::ffff:169.254.169.254")
        ):
            return True
    return False


def normalize(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if text.startswith("//"):
        return "https:" + text
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", text):
        return text
    return "https://" + text


def _inject(html: str, base: str) -> str:
    html = BASE_RE.sub("", html)
    block = INJECT_TEMPLATE.replace("__BASE__", base.replace('"', "%22"))
    match = HEAD_RE.search(html)
    if match:
        pos = match.end()
        return html[:pos] + block + html[pos:]
    return block + html


async def fetch(url: str) -> tuple[int, bytes, str]:
    target = normalize(url)
    parts = urlsplit(target)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return 400, b"Ungueltige Adresse.", "text/plain; charset=utf-8"
    if _blocked(parts.hostname):
        return (
            403,
            "Diese Adresse ist im privaten Browser gesperrt.".encode("utf-8"),
            "text/plain; charset=utf-8",
        )
    try:
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=25, headers=FETCH_HEADERS
        ) as client:
            response = await client.get(target)
    except Exception:
        return (
            502,
            "Seite nicht erreichbar.".encode("utf-8"),
            "text/plain; charset=utf-8",
        )
    content = response.content[:MAX_BYTES]
    content_type = response.headers.get("content-type", "application/octet-stream")
    if "html" in content_type.lower():
        try:
            html = content.decode(response.encoding or "utf-8", errors="replace")
        except Exception:
            html = content.decode("utf-8", errors="replace")
        html = _inject(html, str(response.url))
        return response.status_code, html.encode("utf-8"), "text/html; charset=utf-8"
    return response.status_code, content, content_type
