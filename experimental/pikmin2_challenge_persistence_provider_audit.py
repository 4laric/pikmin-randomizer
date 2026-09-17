"""P2 challenge persistence/natural-acceptance provider pin-discovery (#136).

Bounded ownership audit for the remaining NAMED input that blocks the
challenge-0 consumer `p2-challenge-ch_mat_route_rover-p1` (#561): the
persistence/natural-acceptance runtime slice for the challenge stages.

Finding (fail-closed, citation-backed): the landed challenge framework
contract (#136) DECLARES that save/unlock persistence for challenge clear
flags and highscores is provided through the #132 surface-saves provider
(`experimental/pikmin2_challenge_framework_contract.py` line 134), and assigns
that owner as `saves_unlocks='#132'` (line 158). But the three landed #132
save-progression contracts contain no challenge/highscore/unlock anchors at
all, so the challenge-specific persistence adapter has NO producer: #132 is a
completed backlog epic, not an input producer.

This module pins the exact evidence blobs, proves the declared-vs-landed gap
with file:line citations, and publishes the exact missing provider, its
concrete owner, and a first bounded executable slice for the challenge stages
with downstream consumer #561.

Tooling only: no runtime, no gameplay, no native/shared edits, no ADMIT. All
six runtime gates stay UNTESTED. Every input is consumed read-only by exact
commit; any drift (missing doc, blob/sha mismatch, changed anchor, or an
unexpected challenge anchor in a #132 doc) fails closed with AuditError.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess

SCHEMA = "p2-challenge-persistence-provider-audit-v1"

PINS = {
    "contract_doc": {
        "commit": "b9bb55f0c52d1722a6c8cada958f2b1452a5ae99",
        "path": "docs/PIKMIN2_CHALLENGE_FRAMEWORK_CONTRACT.md",
        "blob": "14de48306394d959c4051ddb541aadf428105fa7",
        "sha256": "55ef70425c665c8a6e1e523707f40d1f61d5d58bc3d7329b64ccf6b41179f545",
    },
    "contract_mod": {
        "commit": "b9bb55f0c52d1722a6c8cada958f2b1452a5ae99",
        "path": "experimental/pikmin2_challenge_framework_contract.py",
        "blob": "4ad264df3d917375a1fce8a1445f16661114a7e0",
        "sha256": "7236c25309287e822c67cd619c8fe652281c21aa2ab03f98f7a9b2e6efc93517",
    },
    "surface_doc": {
        "commit": "7b6d25df49749fa22f583ddc74773d5fdbd65ea0",
        "path": "docs/PIKMIN2_SURFACE_SESSION_CONTRACT.md",
        "blob": "094badb39ba0370c44bba0e395358a4c3e159691",
        "sha256": "12c4a76a4c0573b8ec4de810674c8d35f27905758b83567e4ac2016f2b378d0a",
    },
    "cavesave_doc": {
        "commit": "8aaf6cf67abaf20de1568a9559ee53b516ee084b",
        "path": "docs/PIKMIN2_CAVE_SAVE_PROVIDER_REVIEW.md",
        "blob": "8464aafad97f41ad458f9b4df2e39df0cd997352",
        "sha256": "b43be48703b740285b9ef26c9ebd3db8c038eeace66c60a42a7faf33d2a61de8",
    },
    "dayclock_doc": {
        "commit": "4fff74c7ed656c42e24c46b8d9294fc97367b417",
        "path": "docs/PIKMIN2_SAVE_DAYCLOCK_ANCHOR_AUDIT.md",
        "blob": "17afe849198f998757a645957ceafeaa4ba42205",
        "sha256": "7a3f7b85ec34ceb8bdc415e27e59ac6d398da060fe6ed35b2a283a4224826ef1",
    },
    "consumer_doc": {
        "commit": "2ae0fe613ba577751e28e1d0c97014f66f7aa5b0",
        "path": "docs/content_lanes/p2-challenge-ch_mat_route_rover.md",
        "blob": "5103075899ac0e857858be842f5053cbaff751e6",
        "sha256": "db82b2694eda244dae1b5cbd09fc28cf845503da7a1a61af5999be1c639fe92c",
    },
}

REQUIRED_ANCHORS = {
    "contract_doc": {
        46: "Unsupported (no port evidence - do not claim)",
        50: "unlock persistence wiring",
    },
    "contract_mod": {
        134: "surface_saves_132': 'Day/save persistence incl. challenge clear flags and highscores",
        158: "saves_unlocks='#132'",
    },
    "consumer_doc": {
        1: "p2-challenge-ch_mat_route_rover import contract (P0, issue #561)",
    },
}

ABSENT_DOCS = ("surface_doc", "cavesave_doc", "dayclock_doc")
FORBIDDEN_SUBSTRINGS = ("challenge clear flag", "highscore", "unlock", "stage unlock")

DOWNSTREAM_CONSUMER = 561

PROVIDER = {
    "key": "challenge_persistence",
    "missing_input": (
        "Challenge-stage save/unlock persistence adapter: challenge clear flags, "
        "highscores and saved stage unlocks (PlayCommonData) wired between the "
        "challenge stage flow and the port save layer."
    ),
    "declared_owner": "#132 (saves_unlocks) per framework contract line 158",
    "producer_status": "absent",
    "finding": (
        "no live lane produces the challenge persistence/natural-acceptance runtime "
        "slice; #132 is a completed backlog epic and is not an input producer"
    ),
    "concrete_owner": {
        "lane": "p2-challenge-persistence-wiring",
        "issue": 136,
        "kind": "root-only tooling first slice (native save-layer hookup needs the #132 save owner contract + #186 review)",
        "route": "coordinator #570 review/publication; #186 hook review before any native save-layer edit",
    },
}

FIRST_SLICE = {
    "id": "p2-challenge-persistence-wiring-v1",
    "issue": 136,
    "role": "implementation",
    "priority": "existing_content",
    "heavy": False,
    "owned_files": [
        "experimental/pikmin2_challenge_persistence.py",
        "tests/test_pikmin2_challenge_persistence.py",
        "docs/PIKMIN2_CHALLENGE_PERSISTENCE.md",
    ],
    "consumes_readonly": [
        "docs/PIKMIN2_CHALLENGE_FRAMEWORK_CONTRACT.md (#136 @ b9bb55f0)",
        "experimental/pikmin2_challenge_framework_contract.py (#136 @ b9bb55f0)",
        "docs/PIKMIN2_SURFACE_SESSION_CONTRACT.md (#132 @ 7b6d25df)",
        "docs/PIKMIN2_CAVE_SAVE_PROVIDER_REVIEW.md (#132 @ 8aaf6cf6)",
        "docs/PIKMIN2_SAVE_DAYCLOCK_ANCHOR_AUDIT.md (#132 @ 4fff74c7)",
    ],
    "deliverable": (
        "Root-only challenge persistence contract adapter mapping the 30 challenge "
        "stages to their clear-flag/highscore/saved-unlock persistence keys, defined "
        "against the landed #132 save contracts and the #136 framework contract; "
        "fail-closed on drift; names the exact native save-layer owner and #186 hook "
        "review needed for engine hookup."
    ),
    "downstream_consumer": DOWNSTREAM_CONSUMER,
    "gates": "all six runtime gates UNTESTED; no runtime, no ADMIT",
}

GATES = (
    "identity_spawn",
    "movement_animation",
    "attacks_receivers",
    "death_corpse",
    "transport_reward",
    "cleanup_reentry",
)


class AuditError(ValueError):
    """Fail-closed audit rejection."""


def git_show(root, commit, path):
    result = subprocess.run(
        ["git", "-C", str(root), "show", "%s:%s" % (commit, path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        raise AuditError("cannot read %s@%s: %s" % (path, commit, result.stderr.strip()[:160]))
    return result.stdout


def git_blob(root, commit, path):
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "%s:%s" % (commit, path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode != 0:
        raise AuditError("cannot resolve blob %s@%s" % (path, commit))
    return result.stdout.strip()


def verify_pins(root, show=None, blob=None, pins=None):
    show = show or git_show
    blob = blob or git_blob
    pins = pins if pins is not None else PINS
    loaded = {}
    for key, spec in pins.items():
        text = show(root, spec["commit"], spec["path"])
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest != spec["sha256"]:
            raise AuditError("content sha256 mismatch for %s: %s" % (key, spec["path"]))
        if spec.get("blob"):
            oid = blob(root, spec["commit"], spec["path"])
            if oid != spec["blob"]:
                raise AuditError("blob id mismatch for %s: %s" % (key, spec["path"]))
        loaded[key] = text
    return loaded


def anchor_citations(loaded, anchors=None):
    anchors = anchors if anchors is not None else REQUIRED_ANCHORS
    citations = []
    for key, wanted in anchors.items():
        if key not in loaded:
            raise AuditError("anchor document not loaded: " + key)
        lines = loaded[key].splitlines()
        for number, substring in wanted.items():
            if number < 1 or number > len(lines):
                raise AuditError("%s: missing line %d" % (key, number))
            actual = lines[number - 1]
            if substring not in actual:
                raise AuditError("%s:%d missing anchor %r" % (key, number, substring))
            citations.append({
                "pin": key,
                "path": PINS.get(key, {}).get("path", key),
                "line": number,
                "text": actual.strip()[:160],
            })
    return citations


def absent_in_landed_contracts(loaded, docs=None, forbidden=None):
    docs = docs if docs is not None else ABSENT_DOCS
    forbidden = forbidden if forbidden is not None else FORBIDDEN_SUBSTRINGS
    checked = []
    for key in docs:
        if key not in loaded:
            raise AuditError("absence document not loaded: " + key)
        lowered = loaded[key].lower()
        for token in forbidden:
            if token in lowered:
                raise AuditError("%s unexpectedly contains challenge anchor %r" % (key, token))
        checked.append({"pin": key, "path": PINS.get(key, {}).get("path", key), "anchors_absent": list(forbidden)})
    return checked


def audit(root, show=None, blob=None, pins=None, anchors=None, docs=None, forbidden=None):
    loaded = verify_pins(root, show=show, blob=blob, pins=pins)
    citations = anchor_citations(loaded, anchors=anchors)
    absent = absent_in_landed_contracts(loaded, docs=docs, forbidden=forbidden)
    provider = PROVIDER
    owner = provider.get("concrete_owner") or {}
    if not owner.get("lane") or not owner.get("issue"):
        raise AuditError("missing provider/owner decision")
    return {
        "schema": SCHEMA,
        "valid": True,
        "provider": provider,
        "citations": citations,
        "landed_contracts_checked": absent,
        "first_slice": first_slice_spec(),
        "downstream_consumer": DOWNSTREAM_CONSUMER,
        "gates": {name: "UNTESTED" for name in GATES},
    }


def first_slice_spec():
    spec = json.loads(json.dumps(FIRST_SLICE))
    consumer_files = {
        "experimental/content_lanes/p2-challenge-ch_mat_route_rover.py",
        "tests/content_lanes/test_p2_challenge_ch_mat_route_rover.py",
        "docs/content_lanes/p2-challenge-ch_mat_route_rover.md",
    }
    overlap = consumer_files.intersection(spec["owned_files"])
    if overlap:
        raise AuditError("first slice overlaps consumer #561 owned files: %s" % sorted(overlap))
    return spec


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        verdict = audit(args.root)
    except AuditError as error:
        print(json.dumps({"schema": SCHEMA, "valid": False, "error": str(error)}))
        return 2
    if args.json:
        print(json.dumps(verdict, indent=2, sort_keys=True))
    else:
        print("%s valid" % verdict["schema"])
        for citation in verdict["citations"]:
            print("  %s:%d  %s" % (citation["path"], citation["line"], citation["text"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())