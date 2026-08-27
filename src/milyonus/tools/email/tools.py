"""Email tools — read (IMAP) and send (SMTP), on the standard library.

Reading email is an untrusted-content source: anything the agent reads is data,
and if it later proposes a memory from it, that goes through the verified-memory
pipeline as third-party (T3). Sending email is outward and irreversible, so
`email_send` is danger-classed and always routes through approval.

Credentials come from the environment, never config:
  EMAIL_ADDRESS, EMAIL_PASSWORD (an app password), IMAP_HOST, SMTP_HOST
  IMAP_PORT (993), SMTP_PORT (587)
The parsing helpers are pure so they can be unit-tested without a live server.
"""

from __future__ import annotations

import email
import imaplib
import os
import smtplib
import ssl
from email.header import decode_header
from email.message import EmailMessage, Message
from typing import Any

from milyonus.security.redact import redact
from milyonus.tools.registry import Tool

_MAX_BODY = 20_000


# --- pure helpers (unit-testable) --------------------------------------


def decode_mime_header(raw: str | None) -> str:
    """Decode an RFC 2047 header (e.g. '=?UTF-8?B?...?=') to text."""
    if not raw:
        return ""
    parts = decode_header(raw)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", "replace"))
        else:
            out.append(text)
    return "".join(out)


def extract_body(msg: Message) -> str:
    """Return the plain-text body of an email.message.Message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(
                part.get("Content-Disposition", "")
            ):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", "replace")
        # fall back to the first text/html stripped-ish
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", "replace")
        return ""
    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode(msg.get_content_charset() or "utf-8", "replace")
    return str(msg.get_payload())


def _config() -> dict[str, str]:
    return {
        "address": os.environ.get("EMAIL_ADDRESS", ""),
        "password": os.environ.get("EMAIL_PASSWORD", ""),
        "imap_host": os.environ.get("IMAP_HOST", ""),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "imap_port": os.environ.get("IMAP_PORT", "993"),
        "smtp_port": os.environ.get("SMTP_PORT", "587"),
    }


def make_email_tools() -> list[Tool]:
    async def email_list(args: dict[str, Any]) -> str:
        cfg = _config()
        if not (cfg["address"] and cfg["password"] and cfg["imap_host"]):
            return "email not configured (set EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_HOST)"
        limit = int(args.get("limit", 10))
        folder = args.get("folder", "INBOX")
        try:
            with imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg["imap_port"])) as m:
                m.login(cfg["address"], cfg["password"])
                m.select(folder, readonly=True)
                _, data = m.search(None, "ALL")
                ids = data[0].split()[-limit:]
                lines = []
                for i in reversed(ids):
                    _, msg_data = m.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
                    hdr = email.message_from_bytes(msg_data[0][1])
                    lines.append(
                        f"[{i.decode()}] {decode_mime_header(hdr['From'])} — "
                        f"{decode_mime_header(hdr['Subject'])}"
                    )
                return redact("\n".join(lines) or "(no messages)")
        except Exception as exc:  # noqa: BLE001 - surface as a tool result
            return f"email error: {redact(str(exc))}"

    async def email_read(args: dict[str, Any]) -> str:
        cfg = _config()
        if not (cfg["address"] and cfg["password"] and cfg["imap_host"]):
            return "email not configured"
        msg_id = str(args["id"])
        folder = args.get("folder", "INBOX")
        try:
            with imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg["imap_port"])) as m:
                m.login(cfg["address"], cfg["password"])
                m.select(folder, readonly=True)
                _, msg_data = m.fetch(msg_id.encode(), "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                body = extract_body(msg)[:_MAX_BODY]
                return redact(
                    f"From: {decode_mime_header(msg['From'])}\n"
                    f"Subject: {decode_mime_header(msg['Subject'])}\n\n{body}"
                )
        except Exception as exc:  # noqa: BLE001
            return f"email error: {redact(str(exc))}"

    async def email_send(args: dict[str, Any]) -> str:
        cfg = _config()
        if not (cfg["address"] and cfg["password"] and cfg["smtp_host"]):
            return "email not configured (set EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_HOST)"
        msg = EmailMessage()
        msg["From"] = cfg["address"]
        msg["To"] = args["to"]
        msg["Subject"] = args.get("subject", "(no subject)")
        msg.set_content(args["body"])
        try:
            ctx = ssl.create_default_context()
            with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"])) as s:
                s.starttls(context=ctx)
                s.login(cfg["address"], cfg["password"])
                s.send_message(msg)
            return f"sent to {args['to']}"
        except Exception as exc:  # noqa: BLE001
            return f"email error: {redact(str(exc))}"

    return [
        Tool(
            name="email_list",
            description="List recent emails (sender + subject) from a folder.",
            parameters={
                "type": "object",
                "properties": {
                    "folder": {"type": "string"},
                    "limit": {"type": "integer"},
                },
            },
            handler=email_list,
            risk="caution",  # reads untrusted content
        ),
        Tool(
            name="email_read",
            description="Read the full body of an email by its id.",
            parameters={
                "type": "object",
                "properties": {"id": {"type": "string"}, "folder": {"type": "string"}},
                "required": ["id"],
            },
            handler=email_read,
            risk="caution",
        ),
        Tool(
            name="email_send",
            description="Send an email. Outward and irreversible — requires approval.",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "body"],
            },
            handler=email_send,
            risk="danger",  # outward + irreversible
        ),
    ]
