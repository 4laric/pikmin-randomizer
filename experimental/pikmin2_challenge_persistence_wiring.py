"""Root-only challenge persistence-wiring adapter (#708).

Implements the exact first slice the integrated #136 audit verdict selected
(`p2-challenge-persistence-wiring-v1`): maps the 30 retail challenge stages to
their persistence keys (save/load/clear/highscore/unlock), fail-closed on
drift, consuming the integrated #136 scope read-only. Names the exact native
save-layer hookup + #186 follow-on without editing anything native.

The 30 pinned rows were decoded this turn from the retail stage table
(`user/Matoba/challenge/stages.txt`, GPVE01 rev 0) with the #136 framework
decoder and cross-checked against the canonical content inventory (30/30
agree, zero mismatches; ui_index covers 0..29 exactly). This adapter carries
the verified rows as constants and re-verifies any caller-supplied table
against them; it does not fork or duplicate any decoder.

Emits definitions and key contracts, never placements or gameplay. No
family/shared/native edits, no runtime, no ADMIT.
"""
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "p2-challenge-persistence-wiring-v1"

# Retail stage-table pin (verified this turn against the legal disc).
SOURCE_TABLE_PATH = "user/Matoba/challenge/stages.txt"
SOURCE_TABLE_OFFSET = 770387248
SOURCE_TABLE_SIZE = 18875
SOURCE_TABLE_SHA256 = "59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1"

# The 30 challenge stages in retail table order: (cave_id, ui_index, floors).
# Verified this turn: decoded with the #136 framework decoder, inventory
# cross-check reports zero mismatches, ui_index covers 0..29 exactly.
STAGES = (
    ("ch_ABEM_tutorial", 0, 2),
    ("ch_NARI_07whitepurple", 20, 2),
    ("ch_NARI_03toy", 5, 2),
    ("ch_NARI_01kusachi", 3, 1),
    ("ch_ABEM_LeafChappy", 17, 2),
    ("ch_NARI_05start3easy", 15, 2),
    ("ch_MUKI_metal", 1, 2),
    ("ch_MAT_limited_time", 11, 1),
    ("ch_MAT_t_hunter_hana", 14, 1),
    ("ch_MUKI_damagumo", 6, 1),
    ("ch_MAT_t_hunter_enemy", 10, 5),
    ("ch_MAT_conc_cave", 2, 3),
    ("ch_NARI_04series", 12, 7),
    ("ch_MAT_t_hunter_otakara", 23, 1),
    ("ch_MUKI_bigfoot", 7, 1),
    ("ch_MIYA_oopan", 21, 1),
    ("ch_MAT_yellow_purple_white", 19, 1),
    ("ch_MUKI_redblue", 18, 2),
    ("ch_NARI_08tobasare", 24, 2),
    ("ch_NARI_02tile", 4, 2),
    ("ch_MAT_crawler", 29, 2),
    ("ch_MAT_route_rover", 27, 1),
    ("ch_MUKI_enemyzero", 13, 1),
    ("ch_NARI_09suikomi", 25, 1),
    ("ch_MUKI_houdai", 8, 2),
    ("ch_NARI_06start3hard", 16, 3),
    ("ch_MAT_flier", 28, 1),
    ("ch_MIYA_trap", 26, 1),
    ("ch_MUKI_bombing", 22, 1),
    ("ch_MUKI_king", 9, 5),
)

KEY_PREFIX = "p2_challenge"
KEY_FIELDS = ("save", "load", "clear", "highscore", "unlock")
# The 7 probe artifacts the downstream persistence probe counts per stage run
# (#561 probe: challenge_save_key, challenge_load_key, clear_flag, highscore,
# unlock, receipt_dedup, reentry; 0/7 at gen 11).
PROBE_ARTIFACTS = ("challenge_save_key", "challenge_load_key", "clear_flag",
                   "highscore", "unlock", "receipt_dedup", "reentry")
CAVE_ID_PATTERN = re.compile(r"[A-Za-z0-9_]+")

# Integrated #136 scope consumed read-only (never duplicated here).
AUDIT_EVIDENCE = {
    "audit_validation_log": {
        "path": "output/workflow/integration-recovery/species-owner/"
                "challenge136-persistence-audit-validation.log",
        "sha256": "9a9b0ddf28475a3d3572081cc685d0960336d87fec93e3a065ba8811231ffec1",
    },
    "framework_contract_commit": "b9bb55f0c52d1722a6c8cada958f2b1452a5ae99",
    "landed_audit_commits": ["52c7475c", "3eb88069"],
}
PROBE_EVIDENCE = {
    "path": "output/workflow/autofill/planning-shards/challenge-0/prepared/"
            "p1-route-rover-launch/out/persistence-probe-gen11.json",
    "sha256": "38d87f0015db1846458e098687d5638a4b6a34e5d280d23717bcde315dc9c56f",
}

# Native save-layer hookup + #186 follow-on (specified, never edited here).
NATIVE_HOOKUP = {
    "owner": "#132 save owner contract (saves_unlocks) + #186 hook review",
    "route": "coordinator #570 review/publication; #186 hook review before "
             "any native save-layer edit",
    "needs": ["PlayCommonData challenge clear-flag/highscore/unlock anchors",
              "result-screen score computation per compute_score semantics"],
    "emits": "the 7 probe artifacts per stage run, using the key/marker "
             "contract below",
}
DOWNSTREAM_CONSUMER = "p2-challenge-ch_mat_route_rover-p1 (#561)"


class DriftError(ValueError):
    """Pinned persistence inputs drifted; refuse rather than map."""


def pinned_stages():
    """The 30 pinned stages as dicts in retail table order."""
    return [{"cave_id": cave_id, "ui_index": ui_index, "floors": floors}
            for cave_id, ui_index, floors in STAGES]


def _check_cave_id(cave_id):
    if not isinstance(cave_id, str) or not CAVE_ID_PATTERN.fullmatch(cave_id):
        raise DriftError("Unsafe cave_id for key derivation: %r" % (cave_id,))


def stage_keys(cave_id):
    """Persistence keys for one stage (save/load/clear/highscore/unlock)."""
    pinned = {row[0] for row in STAGES}
    _check_cave_id(cave_id)
    if cave_id not in pinned:
        raise DriftError("Stage %r is not one of the 30 pinned stages" % cave_id)
    return {field: "%s_%s_%s" % (KEY_PREFIX, field, cave_id)
            for field in KEY_FIELDS}


def marker_for(artifact, cave_id):
    """Exact run-log marker the downstream probe counts for one artifact."""
    _check_cave_id(cave_id)
    if artifact not in PROBE_ARTIFACTS:
        raise DriftError("Unknown probe artifact: %r" % (artifact,))
    stems = {"challenge_save_key": "SAVE_KEY", "challenge_load_key": "LOAD_KEY",
             "clear_flag": "CLEAR", "highscore": "HIGHSCORE", "unlock": "UNLOCK",
             "receipt_dedup": "RECEIPT_DEDUP", "reentry": "REENTRY"}
    return "P2_CHALLENGE_%s stage=%s" % (stems[artifact], cave_id)


def probe_artifacts(cave_id):
    """The 7 probe artifact names for one stage run, in probe order."""
    _check_cave_id(cave_id)
    if cave_id not in {row[0] for row in STAGES}:
        raise DriftError("Stage %r is not one of the 30 pinned stages" % cave_id)
    return list(PROBE_ARTIFACTS)


def all_keys():
    """Every derived key across all 30 stages (global collision check)."""
    keys = []
    for cave_id, _, _ in STAGES:
        keys.extend(stage_keys(cave_id).values())
    return keys


def verify_stage_table(rows):
    """Fail closed unless a caller-supplied table matches the pinned rows."""
    if not isinstance(rows, list) or len(rows) != len(STAGES):
        raise DriftError("Stage table drift: expected %d stages, got %s"
                         % (len(STAGES), len(rows) if isinstance(rows, list) else type(rows)))
    for index, (row, pinned) in enumerate(zip(rows, STAGES)):
        if not isinstance(row, dict):
            raise DriftError("Stage table drift at row %d: not a mapping" % index)
        want = {"cave_id": pinned[0], "ui_index": pinned[1], "floors": pinned[2]}
        for key, value in want.items():
            if row.get(key) != value:
                raise DriftError("Stage table drift at row %d: %s=%r, pinned %r"
                                 % (index, key, row.get(key), value))
    return True


def verify_table_bytes(data):
    """Fail closed unless raw stage-table bytes match the pinned hash/size."""
    blob = bytes(data)
    if len(blob) != SOURCE_TABLE_SIZE:
        raise DriftError("Stage table size %d does not match pinned %d"
                         % (len(blob), SOURCE_TABLE_SIZE))
    actual = hashlib.sha256(blob).hexdigest()
    if actual != SOURCE_TABLE_SHA256:
        raise DriftError("Stage table hash %s does not match pinned %s"
                         % (actual, SOURCE_TABLE_SHA256))
    return dict(source_path=SOURCE_TABLE_PATH, offset=SOURCE_TABLE_OFFSET,
                size=len(blob), sha256=actual)


def adapter_packet():
    """Reviewed packet: identity, key contract, hookup, open items."""
    return {
        "schema": 1,
        "slice": "p2-challenge-persistence-wiring-v1",
        "stage_count": len(STAGES),
        "source_table": {"path": SOURCE_TABLE_PATH, "offset": SOURCE_TABLE_OFFSET,
                         "size": SOURCE_TABLE_SIZE, "sha256": SOURCE_TABLE_SHA256},
        "key_scheme": {"prefix": KEY_PREFIX, "fields": list(KEY_FIELDS),
                       "probe_artifacts": list(PROBE_ARTIFACTS)},
        "stage_map": {cave_id: stage_keys(cave_id) for cave_id, _, _ in STAGES},
        "audit_evidence": json.loads(json.dumps(AUDIT_EVIDENCE)),
        "probe_evidence": dict(PROBE_EVIDENCE),
        "native_hookup": dict(NATIVE_HOOKUP),
        "downstream_consumer": DOWNSTREAM_CONSUMER,
        "semantic_resolution": "open",
        "blockers": [
            "Native save-layer hookup needs the #132 save owner contract plus the "
            "#186 hook review before any native edit (owner lanes).",
            "The downstream #561 persistence probe must observe 7/7 artifacts "
            "against this key/marker contract at runtime.",
        ],
        "limitations": [
            "Keys and markers are contract definitions, not save-tree writes; "
            "emitting them without the native hookup would fabricate evidence.",
            "Stage rows are the verified retail snapshot; any retail drift fails "
            "closed and must be re-pinned, never silently remapped.",
        ],
        "generated": False,
    }