"""Shared-hook candidate for the Bomb birth provider (#616) for #186 review (#666).

Private scoped candidate: exact engine wiring pins, provider CMake membership
anchors, and the dynamic-bridge source-93 refs a #186 reviewer needs to land
the Bomb birth provider for consumer #573. Read-only verification only: no
maintained/shared/family edits, no runtime, no ADMIT. Anything not verifiable
is recorded ABSENT, never invented.
"""
import hashlib
from pathlib import Path

RESEARCH = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")
NATIVE_CMAKE = Path("C:/Users/alari/pikmin-randomizer/native/CMakeLists.txt")
PROVIDER_NATIVE = Path("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/planning-shards/provider-actor-birth-projectiles/prepared/bomb-mgr-birth-native")

REVIEW_ITEMS = [
    {
        "id": "engine-bomb-birth-path",
        "title": "Engine Bomb birth path (retail manager creation switch)",
        "pins": [
            {"file": "src/plugProjectYamashitaU/generalEnemyMgr.cpp", "line": 322,
             "symbol": "EnemyID_Bomb",
             "role": "retail switch arm creating the Bomb manager"},
            {"file": "src/plugProjectYamashitaU/generalEnemyMgr.cpp", "line": 323,
             "symbol": "Bomb::Mgr",
             "role": "Bomb::Mgr(limit, viewNum) construction call"},
            {"file": "src/plugProjectYamashitaU/generalEnemyMgr.cpp", "line": 421,
             "symbol": "EnemyID_BombOtakara",
             "role": "retail switch arm creating the BombOtakara manager"},
            {"file": "src/plugProjectYamashitaU/generalEnemyMgr.cpp", "line": 422,
             "symbol": "BombOtakara::Mgr",
             "role": "BombOtakara::Mgr(limit, viewNum) construction call"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#186 shared P1 arena contract",
            "reason": "Any engine birth-path hook for the provider sits on the shared enemy-manager path.",
        },
    },
    {
        "id": "provider-cmake-membership",
        "title": "Provider CMake membership (maintained registration anchors)",
        "pins": [
            {"file": "CMakeLists.txt", "line": 552,
             "symbol": "enable_testing",
             "role": "CTest already enabled in the maintained build"},
            {"file": "CMakeLists.txt", "line": 557,
             "symbol": "pc_generator_cache_validation_test",
             "role": "registration pattern to mirror (add_executable + add_test)"},
            {"file": "CMakeLists.txt", "line": 561,
             "symbol": "pc_generator_cache_validation_test",
             "role": "add_test registration line pattern"},
        ],
        "provider_files": {
            "pc_port/pc_p2_bomb_mgr_birth.h":
                "94b09e5510413bc9ee8daee502598f746bc45328c539c27e6ff840e08340a1f0",
            "pc_port/pc_p2_bomb_mgr_birth.cpp":
                "ec36bf049c785e1028b7a0f0248754bd1b8867f76d9f035e14469fc7de68c081",
            "tools/p2_bomb_mgr_birth_test.cpp":
                "de37a9f87debb7f4d1a15813a8e50b218250413ffe84e8b527d85472755a5e66",
        },
        "owner": None,
        "shared_review": {
            "owner": "#186 shared build review",
            "reason": "Registering provider files in maintained CMake/CTest is a shared edit.",
        },
    },
    {
        "id": "dynamic-bridge-source-93",
        "title": "Dynamic-bridge source 93 (Bomb birth output to BombOtakara93 consumer)",
        "pins": [
            {"file": "pc_port/pc_p2_bomb_payload_actor.h", "line": 42,
             "symbol": "P2BombPayloadConfig",
             "role": "#577 payload API config struct consumed by #616 (read-only ref)"},
            {"file": "pc_port/pc_p2_bomb_payload_actor.cpp", "line": 1,
             "symbol": "payload",
             "role": "#577 payload API TU consumed by #616 (read-only ref)"},
        ],
        "bridge_files": {
            "pc_port/pc_p2_bomb_payload_actor.h":
                "9c831a3715b23ea84b7cfefac4a5d6b0662e192d17387b46af2c1bd079368a46",
            "pc_port/pc_p2_bomb_payload_actor.cpp":
                "6b1a0bd29181287f3292b95c914a68548bf68e3d370574294ca904b72c28cca2",
        },
        "owner": None,
        "shared_review": {
            "owner": "#186 shared P1 arena contract",
            "reason": "The source-93 dynamic binding is shared birth/consumer seam, not family FSM.",
        },
    },
]

REQUIRED_PIN_KEYS = {"file", "line", "symbol", "role"}


class HookError(ValueError):
    pass


def _read_lines(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as error:
        raise HookError("Pin file unreadable: " + str(path)) from None


def verify_pin(pin, research=RESEARCH, native_cmake=NATIVE_CMAKE,
               provider_native=PROVIDER_NATIVE):
    """Fail closed unless the recorded anchor text exists at the recorded line."""
    for key in REQUIRED_PIN_KEYS:
        if key not in pin:
            raise HookError("Pin missing key: " + key)
    if not isinstance(pin["line"], int) or pin["line"] < 1:
        raise HookError("Pin line must be a positive int")
    name = pin["file"]
    if name == "CMakeLists.txt":
        path = native_cmake
    elif "/" not in name and "\\" not in name:
        raise HookError("Pin file must be a repository path: " + name)
    elif name.startswith("pc_port/") or name.startswith("tools/"):
        path = provider_native / name
    else:
        path = research / name
    lines = _read_lines(path)
    if pin["line"] > len(lines):
        raise HookError("Pin line beyond file end: " + pin["file"])
    text = lines[pin["line"] - 1]
    symbol = pin["symbol"].split("::")[-1].split("(")[0]
    if symbol not in text:
        raise HookError("Symbol %r not on %s:%d (found %r)" % (
            symbol, pin["file"], pin["line"], text.strip()[:80]))
    return True


def verify_file_hash(path, expected):
    """Fail closed unless the file hashes to the recorded value."""
    try:
        actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError as error:
        raise HookError("Hash target unreadable: " + str(path)) from None
    if actual != expected:
        raise HookError("Hash mismatch for %s: %s" % (path, actual))
    return True


def verify_candidate(data):
    """Validate the candidate record: schema, pins, hashes, owner-or-review."""
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise HookError("Candidate schema must be 1")
    if not data.get("items"):
        raise HookError("Candidate has no items")
    seen = set()
    for item in data["items"]:
        if item.get("id") in seen:
            raise HookError("Duplicate item: " + str(item.get("id")))
        seen.add(item.get("id"))
        if not item.get("pins"):
            raise HookError("Item has no pins: " + str(item.get("id")))
        for pin in item["pins"]:
            verify_pin(pin)
        for path, digest in dict(item.get("provider_files", {})).items():
            verify_file_hash(PROVIDER_NATIVE / path, digest)
        for path, digest in dict(item.get("bridge_files", {})).items():
            verify_file_hash(PROVIDER_NATIVE / path, digest)
        if not item.get("owner") and not item.get("shared_review"):
            raise HookError("Item names neither owner nor review: " + item["id"])
    return True


def candidate():
    """Return the machine-readable shared-hook candidate (deep copy)."""
    import copy
    return {"schema": 1, "issue": 666, "target": "#186 shared-hook review",
            "provider": "#616 provider-bomb-mgr-birth",
            "consumer": "#573 enemy-bombotakara93-payload",
            "items": copy.deepcopy(REVIEW_ITEMS)}
