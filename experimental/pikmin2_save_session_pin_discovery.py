"""Save/session pin-discovery registry for P1-blocking #132 native items (#658).

Read-only pin audit: verifies exact retail function pins (file:line) in the
canonical research tree and records ownership for four native integration
items no lane owns. Emits no placements, claims no runtime, invents no pins:
anything not verifiable is recorded ABSENT with its external location.
"""
import hashlib
from pathlib import Path

RESEARCH_ROOT = Path(
    "C:/Users/alari/pikmin-randomizer/native/pikmin2-research")
KANDOU = "src/plugProjectKandoU"

ITEMS = [
    {
        "id": "sunset-driver",
        "title": "Native sunset driver (day start/end, sunset losses, surface time)",
        "pins": [
            {"file": KANDOU + "/singleGameSection.cpp", "line": 183,
             "symbol": "SingleGame::CaveDayEndState::init",
             "role": "cave day-end entry; day-count advance path"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 209,
             "symbol": "SingleGame::CaveDayEndState::exec",
             "role": "cave day-end tick; time-manager reset leg"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 660,
             "symbol": "SingleGameSection::saveMainMapSituation",
             "role": "surface time capture incl. cave time"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 684,
             "symbol": "SingleGameSection::loadMainMapSituation",
             "role": "time restore on re-entry incl. setTime"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 486,
             "symbol": "SingleGameSection::enableTimer",
             "role": "day timer arming hook"},
            {"file": KANDOU + "/singleGameSection.cpp", "line": 500,
             "symbol": "SingleGameSection::disableTimer",
             "role": "day timer disarm hook"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#186 shared P1 arena contract",
            "reason": "Day start/end and timer hooks sit on the shared section/FSM path.",
        },
        "open_note": "Field-Pikmin sunset-loss enumeration has no sunset-named driver in src (only UI counters); downstream must pin the loss site from the day-end flow.",
    },
    {
        "id": "save-serializer",
        "title": "Save serializer (durable independent saves: areas/squads/captains)",
        "pins": [
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 39,
             "symbol": "PlayData::write",
             "role": "durable save entry incl. BirthMgr/DeathMgr"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 707,
             "symbol": "PlayData::read",
             "role": "restore entry incl. BirthMgr/DeathMgr"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1372,
             "symbol": "CaveSaveData::write",
             "role": "cave payload write incl. time capture"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1411,
             "symbol": "CaveSaveData::read",
             "role": "cave payload restore with size guard"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1346,
             "symbol": "OlimarData::write",
             "role": "captain block write"},
            {"file": KANDOU + "/gamePlayDataMemCard.cpp", "line": 1360,
             "symbol": "OlimarData::read",
             "role": "captain block restore"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#132 saves/progression + #186",
            "reason": "Independent per-area/squad/captain save semantics extend the audited card format.",
        },
        "open_note": None,
    },
    {
        "id": "receipt-ledger-endpoint",
        "title": "Receipt ledger endpoint (surface/area treasure receipt binding)",
        "pins": [
            {"file": KANDOU + "/onyonMgr.cpp", "line": 403,
             "symbol": "InteractSuckDone::actOnyon",
             "role": "delivery endpoint: pellet to poko money via carryInfoMgr"},
            {"file": KANDOU + "/gamePlayData.cpp", "line": 800,
             "symbol": "PlayData::obtainPellet_Main",
             "role": "ledger accumulation incl. money add"},
            {"file": KANDOU + "/onyonMgr.cpp", "line": 195,
             "symbol": "Onyon::isSuckReady",
             "role": "delivery readiness gate"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#606 treasure receipts + #186",
            "reason": "#606 owns the ledger concept; the surface endpoint binding is unscoped.",
        },
        "open_note": "No receipt/ledger-named source exists in research; the endpoint is the Onion delivery path above.",
    },
    {
        "id": "generator-cache-restore",
        "title": "Generator-cache restore (cave/actor regeneration restore)",
        "pins": [
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 557,
             "symbol": "GeneratorCache::read",
             "role": "cache restore entry"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 504,
             "symbol": "GeneratorCache::write",
             "role": "cache persist entry"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 203,
             "symbol": "GeneratorCache::loadGenerators",
             "role": "course generator load"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 281,
             "symbol": "GeneratorCache::slideCache",
             "role": "cache slide/rotation"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 341,
             "symbol": "GeneratorCache::beginSave",
             "role": "save framing entry"},
            {"file": KANDOU + "/gameGeneratorCache.cpp", "line": 665,
             "symbol": "CourseCache::read",
             "role": "per-course restore"},
        ],
        "owner": None,
        "shared_review": {
            "owner": "#607 cave generation + #186",
            "reason": "Restore semantics extend the accepted generator pin.",
        },
        "open_note": None,
    },
]

REQUIRED_PIN_KEYS = {"file", "line", "symbol", "role"}


class PinError(ValueError):
    pass


def registry():
    """Return the machine-readable pin/owner registry (deep copy)."""
    import copy
    return {"schema": 1, "issue": 658,
            "research": "native/pikmin2-research (read-only)",
            "items": copy.deepcopy(ITEMS)}


def verify_pin(pin, root=RESEARCH_ROOT):
    """Fail closed unless the recorded symbol exists at the recorded line."""
    for key in REQUIRED_PIN_KEYS:
        if key not in pin:
            raise PinError("Pin missing key: " + key)
    if not isinstance(pin["line"], int) or pin["line"] < 1:
        raise PinError("Pin line must be a positive int")
    path = Path(root) / pin["file"]
    if not path.is_file():
        raise PinError("Pin file absent: " + pin["file"])
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if pin["line"] > len(lines):
        raise PinError("Pin line beyond file end: " + pin["file"])
    text = lines[pin["line"] - 1]
    symbol = pin["symbol"].split("::")[-1].split("(")[0]
    if symbol not in text:
        raise PinError("Symbol %r not on %s:%d (found %r)" % (
            symbol, pin["file"], pin["line"], text.strip()[:80]))
    return True


def verify_registry(data, root=RESEARCH_ROOT):
    """Validate schema, verify every pin, require owner-or-review per item."""
    if not isinstance(data, dict) or data.get("schema") != 1:
        raise PinError("Registry schema must be 1")
    if not data.get("items"):
        raise PinError("Registry has no items")
    seen = set()
    for item in data["items"]:
        if item.get("id") in seen:
            raise PinError("Duplicate item: " + str(item.get("id")))
        seen.add(item.get("id"))
        if not item.get("pins"):
            raise PinError("Item has no pins: " + str(item.get("id")))
        for pin in item["pins"]:
            verify_pin(pin, root)
        if not item.get("owner") and not item.get("shared_review"):
            raise PinError("Item names neither owner nor review: " + item["id"])
    return True


def file_digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
