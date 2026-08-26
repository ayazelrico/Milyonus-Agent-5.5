"""Discord adapter: message parsing + identify payload (no live socket)."""

from milyonus.gateway.adapters.discord import DiscordAdapter


def test_parse_message():
    a = DiscordAdapter(token="t")
    msg = a.parse_message_create(
        {
            "content": "selam",
            "channel_id": "C1",
            "guild_id": "G1",
            "author": {"id": "U1", "username": "ayaz"},
        }
    )
    assert msg is not None
    assert msg.text == "selam" and msg.user_id == "C1"
    assert msg.is_group is True  # guild message


def test_ignore_bot_author():
    a = DiscordAdapter(token="t")
    msg = a.parse_message_create(
        {"content": "x", "channel_id": "C1", "author": {"id": "B1", "bot": True}}
    )
    assert msg is None


def test_ignore_own_messages():
    a = DiscordAdapter(token="t")
    a._bot_user_id = "SELF"
    msg = a.parse_message_create({"content": "x", "channel_id": "C1", "author": {"id": "SELF"}})
    assert msg is None


def test_dm_not_group():
    a = DiscordAdapter(token="t")
    msg = a.parse_message_create({"content": "hi", "channel_id": "D1", "author": {"id": "U1"}})
    assert msg.is_group is False  # no guild_id -> DM


def test_identify_has_intents():
    a = DiscordAdapter(token="t")
    payload = a._identify_payload()
    assert payload["op"] == 2
    assert payload["d"]["intents"] & (1 << 15)  # MESSAGE_CONTENT intent set
