"""Overworld session save-serializer reference model (#736).

Python reference for the native engine slice
(native/pc_port/pc_p2_overworld_save.{h,cpp}): the same deterministic text
grammar, strict field validation and size-guarded parsing, so the native
behaviour has an independent oracle. Mirrors the #712 round-trip and
size-guard rules. Tooling only: no engine wire, no save-format change beyond
the documented grammar, no ADMIT. All six runtime gates UNTESTED.
"""
from __future__ import annotations

MAGIC = "P2_OVERWORLD_SAVE_1"
DEFAULT_MAX_BYTES = 4096
FIELDS = ("area", "day", "squad", "other", "total", "highscore", "unlocked")


class SaveError(ValueError):
    """Fail-closed serializer rejection."""


def _valid_area(area):
    return (isinstance(area, str) and 1 <= len(area) <= 63
            and all(c.isalnum() or c == "_" for c in area))


def _valid_int(value, lo, hi):
    return type(value) is int and lo <= value <= hi


def validate_session(session):
    if not isinstance(session, dict):
        return False
    if not _valid_area(session.get("area")):
        return False
    if not _valid_int(session.get("day"), 0, 1000000):
        return False
    squad = session.get("squad")
    if not isinstance(squad, list) or len(squad) != 8:
        return False
    if not all(_valid_int(v, 0, 1000000) for v in squad):
        return False
    if not _valid_int(session.get("other"), 0, 1000000):
        return False
    if not _valid_int(session.get("total"), 0, 1000000):
        return False
    if sum(squad) + session["other"] != session["total"]:
        return False
    if not _valid_int(session.get("highscore"), 0, 1000000000):
        return False
    if session.get("unlocked") not in (0, 1):
        return False
    return True


def serialize(session):
    """Deterministic text encoding; refuses invalid sessions."""
    if not validate_session(session):
        raise SaveError("invalid session")
    lines = [MAGIC,
             "area %s" % session["area"],
             "day %d" % session["day"],
             "squad %s other %d total %d" % (" ".join(str(v) for v in session["squad"]),
                                            session["other"], session["total"]),
             "highscore %d" % session["highscore"],
             "unlocked %d" % session["unlocked"]]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _parse_int(token, lo, hi):
    if not token or len(token) > 11:
        raise SaveError("bad integer")
    neg = token.startswith("-")
    digits = token[1:] if neg else token
    if not digits or not digits.isdigit():
        raise SaveError("bad integer")
    value = int(digits)
    if neg:
        value = -value
    if not lo <= value <= hi:
        raise SaveError("integer out of range")
    return value


def parse(data, max_bytes=DEFAULT_MAX_BYTES):
    """Strict size-guarded parse; refuses anything malformed."""
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise SaveError("empty/non-bytes input")
    if len(data) > max_bytes:
        raise SaveError("size guard")
    try:
        text = bytes(data).decode("utf-8")
    except UnicodeDecodeError as error:
        raise SaveError("undecodable input") from None
    lines = [line for line in text.split("\n") if line != ""]
    if len(lines) != 6 or lines[0] != MAGIC:
        raise SaveError("bad framing")
    words = [line.split() for line in lines[1:]]
    if len(words[0]) != 2 or words[0][0] != "area" or not _valid_area(words[0][1]):
        raise SaveError("bad area")
    if len(words[1]) != 2 or words[1][0] != "day":
        raise SaveError("bad day")
    day = _parse_int(words[1][1], 0, 1000000)
    if len(words[2]) != 13 or words[2][0] != "squad" or words[2][9] != "other" or words[2][11] != "total":
        raise SaveError("bad squad")
    squad = [_parse_int(v, 0, 1000000) for v in words[2][1:9]]
    other = _parse_int(words[2][10], 0, 1000000)
    total = _parse_int(words[2][12], 0, 1000000)
    if len(words[3]) != 2 or words[3][0] != "highscore":
        raise SaveError("bad highscore")
    highscore = _parse_int(words[3][1], 0, 1000000000)
    if len(words[4]) != 2 or words[4][0] != "unlocked":
        raise SaveError("bad unlocked")
    unlocked = _parse_int(words[4][1], 0, 1)
    session = {"area": words[0][1], "day": day, "squad": squad, "other": other,
               "total": total, "highscore": highscore, "unlocked": unlocked}
    if not validate_session(session):
        raise SaveError("census mismatch")
    return session


def round_trip(session, max_bytes=DEFAULT_MAX_BYTES):
    """True only when the parsed fields equal the input exactly."""
    return parse(serialize(session), max_bytes) == session


NATIVE_FILES = (
    "native/pc_port/pc_p2_overworld_save.h",
    "native/pc_port/pc_p2_overworld_save.cpp",
    "native/tools/p2_overworld_save_serializer_fixture.cpp",
)
GUARD_HEADER = "scripts/p2_fixture_captain_guard.h"