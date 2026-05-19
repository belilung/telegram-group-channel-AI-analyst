"""Unit tests for the WATCHED_GROUPS_INIT parser."""

from tools.resolve_groups import ResolveSpec, parse_init_string


def test_parse_empty() -> None:
    assert parse_init_string("") == []
    assert parse_init_string(";;") == []


def test_parse_single_username() -> None:
    out = parse_init_string("@mygroup|3d")
    assert out == [ResolveSpec(raw="@mygroup", topic_hint="3d")]


def test_parse_multiple_mixed() -> None:
    raw = "@a|ai;https://t.me/b|gamedev;https://t.me/c/123/4|3d"
    out = parse_init_string(raw)
    assert out == [
        ResolveSpec(raw="@a", topic_hint="ai"),
        ResolveSpec(raw="https://t.me/b", topic_hint="gamedev"),
        ResolveSpec(raw="https://t.me/c/123/4", topic_hint="3d"),
    ]


def test_parse_missing_hint() -> None:
    out = parse_init_string("@only_link")
    assert out == [ResolveSpec(raw="@only_link", topic_hint="")]


def test_parse_strips_whitespace() -> None:
    raw = "  @foo | ai  ; @bar | gamedev "
    out = parse_init_string(raw)
    assert out == [
        ResolveSpec(raw="@foo", topic_hint="ai"),
        ResolveSpec(raw="@bar", topic_hint="gamedev"),
    ]
