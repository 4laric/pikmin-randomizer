"""Deterministic P1 Challenge Mode campaign contract (#52).

Lane p1-challenge-campaign-contract. Implementation owner: Codex through
shared GitHub account 4laric; contributor Muse Spark 1.3 via OpenCode.

This module defines the AP challenge campaign as pure data + validation over
the five vanilla P1 Challenge stages (chal0..chal4: Impact, Forest, Navel,
Spring, Trial). It separates:

- VERIFIED facts: stage identity, file hashes, generator-record inventories,
  day-rate multipliers, map files (all read from the local legal P1 asset
  tree, never redistributed).
- CONTRACT rules: deterministic stage/attempt/check IDs, attempt-local vs
  persistent state boundary, one-time check deduplication, reward-threshold
  data model.
- EXPLICITLY UNVERIFIED assumptions: scoring formula, exact timer seconds,
  starting-squad composition, native retry/reset semantics, upgrade
  carry-over. These are follow-on scopes, never claims.

No Archipelago installation is touched; no campaign/native integration is
claimed. Stdlib only.
"""

import hashlib
import json
import math
import re

# Vanilla stage slots in native area-id order.
STAGES = (
    {"slot": "chal0", "area_id": 0, "name": "Impact",
     "ini": "dataDir/stages/chal0.ini"},
    {"slot": "chal1", "area_id": 1, "name": "Forest",
     "ini": "dataDir/stages/chal1.ini"},
    {"slot": "chal2", "area_id": 2, "name": "Navel",
     "ini": "dataDir/stages/chal2.ini"},
    {"slot": "chal3", "area_id": 3, "name": "Spring",
     "ini": "dataDir/stages/chal3.ini"},
    {"slot": "chal4", "area_id": 4, "name": "Trial",
     "ini": "dataDir/stages/chal4.ini"},
)

GENERATOR_FILES = ("default.gen", "plants.gen")

# Template-kind tags observed at record bytes [72:76] in v0.1 .gen files.
# Labels below are working names from established in-tree usage, NOT a full
# semantic decode: 'ikip' behaves as the Piki template, 'iket' as the Teki
# template, 'tnlp' as plant rows. Unknown bytes are never classified.
TEMPLATE_KINDS = ("meti", "ikip", "tlep", "iket", "krow", "ssob", "tnlp")

# Attempt-local state: reset on every attempt start. Persistent state:
# survives retries and reconnects. Anything not listed here is out of scope.
ATTEMPT_LOCAL_KEYS = ("population", "score", "timer", "enemy_state",
                      "resource_state", "squad")
PERSISTENT_KEYS = ("unlocked_stages", "awarded_checks", "met_thresholds",
                   "upgrades")

CHECK_ID_RE = re.compile(r"^[a-z0-9]+:[a-z0-9-]+:[a-z0-9-]+$")


class ContractError(ValueError):
    """Raised for malformed campaign inputs; never for gameplay outcomes."""


def stage_slots():
    """Return the five vanilla stage slot names in area-id order."""
    return [stage["slot"] for stage in STAGES]


def stage_entry(slot):
    """Return the stage table entry for a slot, else raise ContractError."""
    for stage in STAGES:
        if stage["slot"] == slot:
            return dict(stage)
    raise ContractError("Unknown challenge stage slot: %r" % (slot,))


def attempt_id(seed, slot, attempt_index):
    """Deterministic attempt identity: ``<seed>/<slot>#<n>``.

    ``seed`` is a non-empty string, ``attempt_index`` a non-negative int.
    """
    if not isinstance(seed, str) or not seed:
        raise ContractError("Seed must be a non-empty string")
    stage_entry(slot)
    if type(attempt_index) is not int or attempt_index < 0:
        raise ContractError("Attempt index must be a non-negative int")
    return "%s/%s#%d" % (seed, slot, attempt_index)


def check_id(slot, kind, name):
    """Deterministic one-time check identity: ``<slot>:<kind>:<name>``."""
    stage_entry(slot)
    for value, label in ((kind, "kind"), (name, "name")):
        if (not isinstance(value, str) or not value
                or not re.fullmatch(r"[a-z0-9-]+", value)):
            raise ContractError("Check %s must be a lowercase slug" % label)
    return "%s:%s:%s" % (slot, kind, name)


def parse_check_id(value):
    """Split a check id into ``(slot, kind, name)``; raise on malformed."""
    if not isinstance(value, str) or not CHECK_ID_RE.match(value):
        raise ContractError("Malformed check id: %r" % (value,))
    slot, kind, name = value.split(":")
    stage_entry(slot)  # rejects unknown slots
    return slot, kind, name


def audit_stage(asset_root, slot):
    """Audit one vanilla stage from the legal asset tree (read-only).

    Returns observed facts: ini hash/size, day-rate multiplier, map file,
    and per-generator-file record inventories with sha256. Generator files
    that fail the shared v0.1 framing check are reported as
    ``undecoded_variant`` with their hash pinned, never silently skipped
    and never fabricated.
    """
    from pathlib import Path
    entry = stage_entry(slot)
    root = Path(asset_root)
    ini_path = root / entry["ini"]
    try:
        ini_bytes = ini_path.read_bytes()
    except OSError as error:
        raise ContractError("Missing stage ini: %s (%s)" % (entry["ini"], error))
    ini_text = ini_bytes.decode("utf-8", errors="replace")
    facts = {
        "slot": slot,
        "area_id": entry["area_id"],
        "name": entry["name"],
        "ini": entry["ini"],
        "ini_sha256": hashlib.sha256(ini_bytes).hexdigest(),
        "ini_bytes": len(ini_bytes),
        "day_multiply": _ini_field(ini_text, "day_multiply", float),
        "map_file": _ini_field(ini_text, "map_file", str),
        "generators": {},
    }
    stage_dir = root / ("dataDir/stages/" + slot)
    for name in GENERATOR_FILES:
        path = stage_dir / name
        if not path.is_file():
            facts["generators"][name] = {"present": False}
            continue
        blob = path.read_bytes()
        record = {"present": True, "bytes": len(blob),
                  "sha256": hashlib.sha256(blob).hexdigest()}
        try:
            kinds = _record_kinds(blob)
        except ValueError as error:
            record["decoded"] = False
            record["undecoded_variant"] = str(error)
        else:
            record["decoded"] = True
            record["record_count"] = sum(kinds.values())
            record["template_kinds"] = kinds
        facts["generators"][name] = record
    return facts


def _ini_field(text, key, kind):
    match = re.search(r"(?m)^" + key + r"[ \t]+([^\r\n]+)", text)
    if not match:
        raise ContractError("Stage ini lacks field: " + key)
    raw = match.group(1).strip()
    try:
        value = kind(raw)
    except (TypeError, ValueError):
        raise ContractError("Stage ini field not parseable: " + key)
    if kind is float and (not math.isfinite(value) or value <= 0):
        raise ContractError("Stage day rate must be positive finite")
    return value


def _record_kinds(blob):
    """Count v0.1 generator template kinds; raise ValueError on framing."""
    import struct
    if blob[:4] != b"1.0v":
        raise ValueError("Expected v0.1 generator fixture source")
    starts = [m.start() for m in re.finditer(b"    0.0v", blob)]
    if (not starts or starts[0] != 24
            or len(starts) != struct.unpack_from(">I", blob, 20)[0]):
        raise ValueError("Unsupported template record framing")
    kinds = {}
    for start in starts:
        tag = blob[start + 72:start + 76]
        try:
            name = tag.decode("ascii")
        except UnicodeDecodeError:
            raise ValueError("Non-ascii template tag")
        if name not in TEMPLATE_KINDS:
            raise ValueError("Unknown template kind: %r" % (name,))
        kinds[name] = kinds.get(name, 0) + 1
    return kinds


def classify_state(keys):
    """Partition state keys into attempt-local vs persistent; reject unknown."""
    local, persistent, unknown = [], [], []
    for key in keys or []:
        if key in ATTEMPT_LOCAL_KEYS:
            local.append(key)
        elif key in PERSISTENT_KEYS:
            persistent.append(key)
        else:
            unknown.append(key)
    if unknown:
        raise ContractError("Unclassified state keys: %s" % sorted(unknown))
    return {"attempt_local": sorted(local), "persistent": sorted(persistent)}


class CheckLedger:
    """One-time AP check ledger: replaying a threshold never duplicates."""

    def __init__(self, awarded=()):
        self._awarded = set()
        for value in awarded or ():
            parse_check_id(value)  # validate on load
            self._awarded.add(value)

    def award(self, value):
        """Award a check; return True if newly awarded, False if duplicate."""
        parse_check_id(value)
        if value in self._awarded:
            return False
        self._awarded.add(value)
        return True

    def has(self, value):
        parse_check_id(value)
        return value in self._awarded

    def awarded(self):
        return sorted(self._awarded)


def reward_threshold(slot, kind, target):
    """Define a reward threshold record (data only, never achievability).

    ``target`` is a non-negative int (population/score units TBD by the
    resource audit). Whether the target is achievable in the stage timer is
    explicitly NOT decided here.
    """
    check = check_id(slot, kind, "threshold")
    if type(target) is not int or target < 0:
        raise ContractError("Threshold target must be a non-negative int")
    return {"check": check, "slot": slot, "kind": kind, "target": target,
            "achievability": "unevaluated: requires resource/timing audit"}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True,
                        help="Legal P1 asset tree root containing dataDir (read-only)")
    parser.add_argument("--slot", help="Audit one slot (default: all five)")
    args = parser.parse_args(argv)
    slots = [args.slot] if args.slot else stage_slots()
    print(json.dumps([audit_stage(args.assets, slot) for slot in slots], indent=2))


if __name__ == "__main__":
    raise SystemExit(main())