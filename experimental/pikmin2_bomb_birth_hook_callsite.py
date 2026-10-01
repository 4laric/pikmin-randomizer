"""Call-site registry + hook-log verifier for #732 (root tooling half).

Owns the evidence record for the native wire: exact commits/hashes, the
required marker sequence, and a fail-closed checker over a hook log.
No engine execution here; the runtime proof lives in the hashed hook log.
"""
import hashlib

NATIVE_BASE = "93603dc232f9c6ddc4fb2c1241bd590fe95d9b54"
NATIVE_COMMITS = (
    "42e223396106013d56234ef51831721f251f1172",
    "46f8c684472f4d4e6db131defde9238bd4f7a3fa",
    "eeb3a49f5f472a975afdfdf132f215a8aa3d88e2",
)
ENGINE_EXE_SHA256 = ("82804be772d8a644280a469d91bfc45586b2b77511f81e64132729beb60d3507")
FIXTURE_EXE_SHA256 = ("259f8e4db513ee2add20eb8e04ccf179e8b8725831c163236a21db6a8ab34773")
HOOK_LOG_SHA256 = ("4e32d064a83f4feabeddc2d1916d5e4cf7cd06526b9af0a457bf6d6a90fd33c8")
GUARD_SHA256 = ("d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474")

# Ordered proof chain; each must appear at least once, in this order.
MARKERS = (
    "P2_BOMB_MGR_BIND generator=349005",
    "P2_BOMB_CALLSITE_SETUP ready=1",
    "P2_BOMB_CALLSITE_NEGATIVE_PASS refused_id=1",
    "P2_BOMB_MGR_BIRTH generator=349005",
    "P2_BOMB_ENGINE_BIRTH generator=349005",
    "engine_driven=1",
    "P2_GENERAL_ENEMY_MGR_BIRTH_CALLSITE enemyID=93",
    "P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=93",
    "PASS BOMB_BIRTH_HOOK_CALLSITE",
)

FORBIDDEN = (
    "P2_FIXTURE_CAPTAIN_DOWN",
    "FAIL BOMB_CALLSITE",
)


def read_log_text(path):
    """Decode a hook log regardless of UTF-8/UTF-16 console encoding."""
    raw = open(path, "rb").read()
    for encoding in ("utf-8", "utf-16"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("hook log is not UTF-8 or UTF-16: " + str(path))


def verify_hook_log(path):
    """Fail-closed check of the #732 proof chain. Returns marker counts."""
    text = read_log_text(path)
    for bad in FORBIDDEN:
        if bad in text:
            raise ValueError("forbidden marker present: " + bad)
    positions = []
    for marker in MARKERS:
        at = text.find(marker, positions[-1] if positions else 0)
        if at < 0:
            raise ValueError("required marker absent or out of order: "
                             + marker)
        positions.append(at)
    counts = {marker: text.count(marker) for marker in MARKERS}
    if counts["P2_BOMB_BIRTH_HOOK_NOTIFY enemyID=93"] < 1:
        raise ValueError("hook never fired")
    return counts


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
