"""Extinction-probe registry + marker-log verifier for #793 (root tooling half).

Records the exact pins/hashes of the kusachi extinction-window probe and
fail-closed checks over the headed probe log. No engine execution here; the
runtime proof lives in the hashed probe log. The verdict on
navi-drop-cascade vs direct manager clear belongs to the #780 consumer
reading the log, never to this module.
"""
import hashlib

NATIVE_BASE = "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54"
NATIVE_COMMITS = (
    "b9f07431bd000251a5200b608c33e9b8bb61f68f",
)
ENGINE_EXE_SHA256 = ("fbc6b16380a5a61669eb1b5af2d7e7556bc2bba1b43109058ae640c7d7892d55")
FIXTURE_EXE_SHA256 = ("17dd759c94d411b581652b9d70ab01c41418788b06af74e36da17c260015927c")
GUARD_SHA256 = ("d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")
PROBE_LOG_SHA256 = ("4ea12ef375dbbb6360a07c4f98d03ee6681067e6a56d26d29a94e6812ffc4af2")

FORBIDDEN = (
    "P2_FIXTURE_CAPTAIN_DOWN",
    "FAIL KUSACHI_PROBE",
)


def read_log_text(path):
    """Decode a probe log regardless of UTF-8/UTF-16 console encoding."""
    raw = open(path, "rb").read()
    for encoding in ("utf-8", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("probe log is not UTF-8 or UTF-16: " + str(path))


def parse_probe_line(line):
    """Parse one P2_KUSACHI_PROBE line into a dict; refuse malformed."""
    fields = {}
    for token in line.strip().split():
        if "=" not in token:
            continue
        key, _, value = token.partition("=")
        fields[key] = value
    for key in ("tick", "navimgr", "navi", "navi_alive", "orima_dead",
                "alive", "reds", "slots"):
        if key not in fields:
            raise ValueError("probe line missing field: " + key)
    tick = int(fields["tick"])
    alive = int(fields["alive"])
    slots = fields["slots"]
    if alive != slots.count("1"):
        raise ValueError("slots disagree with alive count at tick %d" % tick)
    if any(c not in "01" for c in slots):
        raise ValueError("non-binary slots at tick %d" % tick)
    return fields


def verify_probe_log(path, minimum_ticks=600):
    """Fail-closed check of the probe stream. Returns parsed rows."""
    text = read_log_text(path)
    for bad in FORBIDDEN:
        if bad in text:
            raise ValueError("forbidden marker present: " + bad)
    rows = []
    for line in text.splitlines():
        if "P2_KUSACHI_PROBE " in line:
            rows.append(parse_probe_line(line))
    if len(rows) < minimum_ticks:
        raise ValueError("only %d probe ticks, need %d"
                         % (len(rows), minimum_ticks))
    if "P2_CHALLENGE_MODE_BOOT" not in text:
        raise ValueError("BOOT marker absent: stage never bound")
    if "PASS KUSACHI_PROBE" not in text:
        raise ValueError("PASS marker absent")
    return rows


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
