"""Email: header decoding, body extraction, tool classes, config guard."""

from email.message import EmailMessage

from milyonus.tools.email.tools import (
    decode_mime_header,
    extract_body,
    make_email_tools,
)


def test_decode_plain_header():
    assert decode_mime_header("Hello World") == "Hello World"


def test_decode_encoded_header():
    # "=?UTF-8?B?w4d3IEFsdMSxbg==?=" etc. — use a simple encoded word
    assert "ç" in decode_mime_header("=?UTF-8?B?w6c=?=")  # 'ç'


def test_extract_plain_body():
    m = EmailMessage()
    m.set_content("hello body")
    assert "hello body" in extract_body(m)


def test_extract_multipart_prefers_plain():
    m = EmailMessage()
    m.set_content("plain version")
    m.add_alternative("<p>html version</p>", subtype="html")
    body = extract_body(m)
    assert "plain version" in body


def test_email_tool_risk_classes():
    tools = {t.name: t for t in make_email_tools()}
    assert tools["email_list"].risk == "caution"
    assert tools["email_read"].risk == "caution"
    assert tools["email_send"].risk == "danger"  # outward + irreversible


async def test_send_without_config_is_graceful(monkeypatch):
    for k in ("EMAIL_ADDRESS", "EMAIL_PASSWORD", "SMTP_HOST"):
        monkeypatch.delenv(k, raising=False)
    tools = {t.name: t for t in make_email_tools()}
    out = await tools["email_send"].handler({"to": "a@b.c", "body": "hi"})
    assert "not configured" in out


async def test_list_without_config_is_graceful(monkeypatch):
    for k in ("EMAIL_ADDRESS", "EMAIL_PASSWORD", "IMAP_HOST"):
        monkeypatch.delenv(k, raising=False)
    tools = {t.name: t for t in make_email_tools()}
    out = await tools["email_list"].handler({})
    assert "not configured" in out
