"""Two-captain / squad-ownership / controller pin audit (#819).

Downstream consumer: p2-challenge-ch-mat-crawler-p1 (#562 gen 10; gap #130).
Read-only audit of four native files at pin a95040b6 (plus cited footholds
verified present at the same pin). No engine edits, no builds, no launches.

This module encodes the verified finding records (file:line citations with
blob provenance) and fail-closed validates finding records supplied to it:
FOUND findings must carry exact file/line/symbol/owner; ABSENT findings must
carry a reason; malformed records and missing inputs are refused, never
defaulted. It does not re-read the native tree; the citations below are the
audited evidence, transcribed once from `git show a95040b6:<path>`.
"""

NATIVE_PIN = "a95040b6c4f7d9b6b8ce5a901a8af3ef36a50af8"

FILES = {
    "native/include/NaviMgr.h": "89e0d0772e167954215562feee4a718c2d089d4e",
    "native/src/plugPikiKando/naviMgr.cpp": "4295c874cc6253ca3617e646ecac2d6359af9abe",
    "native/include/Controller.h": "a6159320ddb9d1a3ca5c5632d9bb3a65f0804fbf",
    "native/src/sysDolphin/controllerMgr.cpp": "c2c01c3af3a5dee162fab59639ae99a2fc3f8172",
}

FINDINGS = [
    {
        "id": "second-captain-instantiation",
        "status": "FOUND",
        "file": "native/src/plugPikiKando/naviMgr.cpp",
        "lines": [65, 70],
        "symbol": "NaviMgr::createObject",
        "detail": ("new Navi(mNaviParms, mNaviID); mNaviID++: indexed "
                   "instantiation supports N navis; owner NaviMgr/system."),
    },
    {
        "id": "second-shape-object-missing",
        "status": "FOUND",
        "file": "native/src/plugPikiKando/naviMgr.cpp",
        "lines": [43, 47],
        "symbol": "NaviMgr::NaviMgr",
        "detail": ("Only mNaviShapeObject[0] is built; index 1 stays "
                   "uninitialized, so a second Navi reads garbage at "
                   "navi.cpp:490 and derefs it at :492. Owner: engine "
                   "(NaviMgr construction)."),
    },
    {
        "id": "second-captain-selection",
        "status": "FOUND",
        "file": "native/src/plugPikiKando/naviMgr.cpp",
        "lines": [93, 102],
        "symbol": "NaviMgr::getNavi(int)",
        "detail": ("Bounds-checked indexed selection; the comment names "
                   "leftover multiplayer out-of-bounds requests. Sole "
                   "indexed consumer at this pin: "
                   "src/plugPikiNakata/pcamcamera.cpp:148 getNavi(1). "
                   "All other callers use getNavi()."),
    },
    {
        "id": "per-navi-controller-binding",
        "status": "FOUND",
        "file": "native/src/plugPikiKando/navi.cpp",
        "lines": [513, 513],
        "symbol": "Navi::Navi",
        "detail": ("mKontroller = new Kontroller(naviID + 1): each Navi "
                   "owns a per-player controller (Navi.h:159, Navi.h:47 "
                   "ctor decl, Navi.h:248 mNaviID)."),
    },
    {
        "id": "per-pad-routing",
        "status": "FOUND",
        "file": "native/src/sysDolphin/controllerMgr.cpp",
        "lines": [59, 67],
        "symbol": "ControllerMgr::updateController",
        "detail": ("Routes sControllerPad[controller->mPlayerNum - 1] "
                   "sticks/buttons/triggers per player; driven per "
                   "Controller via sysCommon/controller.cpp:70 and per "
                   "Navi via navi.cpp:1058. Controller.h:45 ctor, :77 "
                   "mPlayerNum."),
    },
    {
        "id": "global-keydown-port0-only",
        "status": "FOUND",
        "file": "native/src/sysDolphin/controllerMgr.cpp",
        "lines": [42, 45],
        "symbol": "ControllerMgr::keyDown",
        "detail": ("Hardcodes sControllerPad[0]: global key queries ignore "
                   "player 2. A second captain driven through this path "
                   "would never register."),
    },
    {
        "id": "squad-ownership-split",
        "status": "FOUND",
        "file": "native/include/Piki.h",
        "lines": [282, 282],
        "symbol": "Piki::mPlayerId",
        "detail": ("Ownership split exists: Piki::mPlayerId (Piki.h:282) "
                   "vs Navi::mNaviID (Navi.h:248); enforced at "
                   "aiFree.cpp:200, aiTransport.cpp:1041, piki.cpp:837, "
                   "pluck gating navi.cpp:1219; whistle effects branch on "
                   "mNaviID 0/1 (naviState.cpp:1688,1845,1890)."),
    },
    {
        "id": "versus-never-spawns-second-navi",
        "status": "FOUND",
        "file": "native/include/FlowController.h",
        "lines": [63, 63],
        "symbol": "FlowController::mIsVersusMode",
        "detail": ("Indicator of an (unimplemented) VS mode - never TRUE "
                   "because we never spawn a second navi. Explicit "
                   "no-second-captain statement in source."),
    },
    {
        "id": "second-navi-spawn-owner",
        "status": "ABSENT",
        "file": "native/src/plugPikiKando/naviMgr.cpp",
        "lines": [],
        "symbol": "NaviMgr::createObject",
        "detail": ("No callsite in the audited tree invokes createObject a "
                   "second time; nothing owns second-Navi spawning. "
                   "Reason: versus unimplemented (FlowController.h:63) and "
                   "the shape-object gap above. Follow-on: an engine lane "
                   "under #186 must own spawn + shape init + pad-0 "
                   "keyDown fix."),
    },
]


class Refused(ValueError):
    """Fail-closed refusal with a reason."""


def validate_finding(record):
    """Fail-closed validation of one finding record. Returns the record."""
    if not isinstance(record, dict):
        raise Refused("finding is not a mapping")
    for key in ("id", "status", "file", "symbol", "detail"):
        if key not in record or not isinstance(record[key], str) or not record[key].strip():
            raise Refused("finding missing/invalid %r" % key)
    if record["status"] not in ("FOUND", "ABSENT"):
        raise Refused("finding status must be FOUND or ABSENT")
    if record["status"] == "FOUND":
        lines = record.get("lines")
        if (not isinstance(lines, list) or len(lines) != 2
                or not all(isinstance(n, int) and n > 0 for n in lines)
                or lines[1] < lines[0]):
            raise Refused("FOUND finding %r needs a valid [first, last] line range"
                          % record["id"])
    return record


def validate_all(findings):
    """Validate a finding list; refuse empty, duplicate or unknown-file input."""
    if not isinstance(findings, list) or not findings:
        raise Refused("no findings supplied")
    seen = set()
    for record in findings:
        validate_finding(record)
        if record["id"] in seen:
            raise Refused("duplicate finding id %r" % record["id"])
        seen.add(record["id"])
    return findings


def summarize(findings):
    """Count FOUND vs ABSENT findings."""
    validate_all(findings)
    return {
        "found": sum(1 for r in findings if r["status"] == "FOUND"),
        "absent": sum(1 for r in findings if r["status"] == "ABSENT"),
        "total": len(findings),
    }
