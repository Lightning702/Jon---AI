from __future__ import annotations

import email
import email.utils
import imaplib
import re
import smtplib
import urllib.request
from datetime import date, datetime, timedelta
from email.header import decode_header
from email.mime.text import MIMEText

from app.services.settings_service import get_settings_service


def _decode(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for text, charset in decode_header(value):
        if isinstance(text, bytes):
            parts.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(text)
    return "".join(parts).strip()


def _body_text(message: email.message.Message) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
        for part in message.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode(
                        part.get_content_charset() or "utf-8", errors="replace"
                    )
                    return re.sub(r"<[^>]+>", " ", html)
        return ""
    payload = message.get_payload(decode=True)
    if payload:
        return payload.decode(
            message.get_content_charset() or "utf-8", errors="replace"
        )
    return ""


class MailService:
    def _cfg(self) -> dict:
        return get_settings_service().get()

    def _imap(self) -> imaplib.IMAP4_SSL:
        cfg = self._cfg()
        host = str(cfg.get("mail_imap_host", "")).strip()
        user = str(cfg.get("mail_imap_user", "")).strip()
        password = str(cfg.get("mail_imap_password", "")).strip()
        if not host or not user or not password:
            raise RuntimeError(
                "E-Mail ist nicht eingerichtet. Trage IMAP-Server, Adresse und "
                "Passwort im Zahnrad-Menue unter 'Verbindungen' ein."
            )
        conn = imaplib.IMAP4_SSL(host, timeout=15)
        conn.login(user, password)
        return conn

    def check_mail(self, limit: int = 10) -> dict:
        conn = self._imap()
        try:
            conn.select("INBOX", readonly=True)
            status, data = conn.search(None, "UNSEEN")
            ids = data[0].split() if status == "OK" and data and data[0] else []
            mails = []
            for mail_id in list(reversed(ids))[: max(1, min(int(limit), 25))]:
                status, msg_data = conn.fetch(
                    mail_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
                )
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                header = email.message_from_bytes(msg_data[0][1])
                mails.append(
                    {
                        "id": mail_id.decode(),
                        "von": _decode(header.get("From")),
                        "betreff": _decode(header.get("Subject")),
                        "datum": _decode(header.get("Date")),
                    }
                )
            return {"ungelesen": len(ids), "mails": mails}
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def read_mail(self, mail_id: str) -> dict:
        conn = self._imap()
        try:
            conn.select("INBOX", readonly=True)
            status, msg_data = conn.fetch(mail_id.encode(), "(BODY.PEEK[])")
            if status != "OK" or not msg_data or not msg_data[0]:
                return {"error": f"Mail {mail_id} nicht gefunden"}
            message = email.message_from_bytes(msg_data[0][1])
            body = re.sub(r"\s+\n", "\n", _body_text(message)).strip()
            return {
                "von": _decode(message.get("From")),
                "an": _decode(message.get("To")),
                "betreff": _decode(message.get("Subject")),
                "datum": _decode(message.get("Date")),
                "text": body[:8000],
            }
        finally:
            try:
                conn.logout()
            except Exception:
                pass

    def send_mail(self, to: str, subject: str, body: str) -> dict:
        cfg = self._cfg()
        user = str(cfg.get("mail_imap_user", "")).strip()
        password = str(cfg.get("mail_imap_password", "")).strip()
        host = str(cfg.get("mail_smtp_host", "")).strip()
        if not host:
            imap_host = str(cfg.get("mail_imap_host", "")).strip()
            host = imap_host.replace("imap.", "smtp.", 1) if imap_host else ""
        port = int(cfg.get("mail_smtp_port", 587) or 587)
        if not host or not user or not password:
            raise RuntimeError(
                "SMTP ist nicht eingerichtet. Trage die Mail-Daten im "
                "Zahnrad-Menue unter 'Verbindungen' ein."
            )
        message = MIMEText(body, "plain", "utf-8")
        message["From"] = user
        message["To"] = to
        message["Subject"] = subject
        message["Date"] = email.utils.formatdate(localtime=True)
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.send_message(message)
        return {"gesendet": True, "an": to, "betreff": subject}

    def calendar_events(self, days: int = 7) -> list[dict]:
        url = str(self._cfg().get("calendar_ics_url", "")).strip()
        if not url:
            raise RuntimeError(
                "Kein Kalender eingerichtet. Trage eine ICS-URL im Zahnrad-Menue "
                "unter 'Verbindungen' ein (z.B. die private iCal-Adresse deines "
                "Google-Kalenders)."
            )
        request = urllib.request.Request(url, headers={"User-Agent": "Jon/1.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read(2_000_000).decode("utf-8", errors="replace")
        raw = raw.replace("\r\n", "\n").replace("\n ", "").replace("\n\t", "")
        start = date.today()
        end = start + timedelta(days=max(1, min(int(days), 60)))
        events = []
        for block in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", raw, re.S):
            m_start = re.search(r"DTSTART[^:]*:(\d{8}(?:T\d{6}Z?)?)", block)
            m_summary = re.search(r"SUMMARY[^:]*:(.*)", block)
            if not m_start or not m_summary:
                continue
            value = m_start.group(1)
            try:
                if "T" in value:
                    stamp = datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")
                    day = stamp.date()
                    time_str = stamp.strftime("%H:%M")
                else:
                    day = datetime.strptime(value, "%Y%m%d").date()
                    time_str = ""
            except Exception:
                continue
            if not (start <= day <= end):
                continue
            m_loc = re.search(r"LOCATION[^:]*:(.*)", block)
            events.append(
                {
                    "datum": day.isoformat(),
                    "zeit": time_str,
                    "titel": m_summary.group(1).strip().replace("\\,", ","),
                    "ort": (m_loc.group(1).strip().replace("\\,", ",") if m_loc else ""),
                }
            )
        events.sort(key=lambda e: (e["datum"], e["zeit"]))
        return events[:40]


_service: MailService | None = None


def get_mail_service() -> MailService:
    global _service
    if _service is None:
        _service = MailService()
    return _service
