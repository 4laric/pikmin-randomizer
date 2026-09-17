"""Content-wiring bridge: staged crawler floor-1 layout to boot (#706).

Connects the staged ch_MAT_crawler run layout (the #562 consumer staging under
`challenge-0/prepared/p1-crawler-output/run-layout`) to boot parameters: arena
geometry bindings, actor placement rows, starting-squad wiring and observation
markers. Consumes the #701 validated content-loading path and the integrated
#688 kusachi analog READ-ONLY (by contract, never by import). Reuses only the
shared brace-stream decoder `experimental.pikmin2_cave_catalog.parse`.

Emits definitions and boot parameters, never placements or gameplay. No
family/shared/native edits, no runtime, no ADMIT.
"""
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_cave_catalog import parse as parse_caveinfo

CAVE_ID = "ch_MAT_crawler"
SOURCE_PATH = "user/Mukki/mapunits/caveinfo/ch_MAT_crawler.txt"
SOURCE_SHA256 = "ab3b2dbb238e4a0c2d1bd4c3c958fd52d25b8ee0a0245f756d6d6a138a325bbd"
SOURCE_OFFSET = 770486496
SOURCE_SIZE = 2411
EXPECTED_FLOORS = 2
UI_INDEX = 29
SQUAD_TOTAL = 60
FLOOR_SECONDS = [170.0, 120.0]
STAGED_COMMIT = None  # staged by consumer lane #562; layout lives under output/

# Pinned decoded floor facts (verified this turn against the disc bytes and the
# staged stage-manifest.json, which agree exactly).
PINNED_FLOORS = [
    {"floor": 1, "unit_pool": "4_units_c_e_j_l_conc.txt",
     "light": "normal_light_cha.ini", "enemies": 14, "treasures": 3, "gates": 1},
    {"floor": 2, "unit_pool": "1_units_manh_conc.txt",
     "light": "normal_light_cha.ini", "enemies": 7, "treasures": 0, "gates": 0},
]
EXPECTED_SQUAD = [{"color": 0, "maturity": 2, "count": 30},
                  {"color": 1, "maturity": 2, "count": 30}]

# Token-classification sets for the shared decoder (no parser fork). The
# decoder distinguishes enemies from treasures by membership, so the real
# ch_MAT_crawler rosters must be named explicitly.
ENEMY_IDS = frozenset({
    "Hana_silver_medal", "Armor_wadou_kaichin", "Wealthy_gold_medal",
    "Magaret", "UjiA_be_dama_red", "UjiB_be_dama_blue", "Tobi_donguri",
    "Wakame_l", "Wakame_s", "Ooinu_s", "Ooinu_l", "Clover",
    "SnakeWhole_key", "KareOoinu_l", "KareOoinu_s",
})
TREASURE_IDS = frozenset({"key", "haniwa", "kouseki_suisyou"})

# Staged run-layout files produced by the #562 consumer (read-only inputs).
STAGED_LAYOUT_FILES = ("stage-manifest.json", "squad.json", "run-config.json",
                       "markers.txt")
STAGED_MARKERS = ("P2_CRAWLER_WINDOW", "P2_CRAWLER_SQUAD",
                  "P2_CRAWLER_FLOOR_READY", "P2_CRAWLER_ACTOR",
                  "P2_CRAWLER_PASS")
# Boot markers this bridge defines for a booted crawler run. Staged markers
# describe the layout; these boot markers name the observation points a runtime
# must emit. No marker is fabricated evidence.
BOOT_MARKERS = ("P2_CRAWLER_BOOT", "P2_CRAWLER_ARENA_BOUND",
                "P2_CRAWLER_SQUAD", "P2_CRAWLER_ACTOR_ROWS",
                "P2_CRAWLER_SELECT")

# Read-only consumer evidence (issue #706, #562 consumer verification).
STAGED_EVIDENCE = {
    "path": "output/workflow/autofill/planning-shards/challenge-0/prepared/"
            "p1-crawler-output/consumer-verify-content-loading.log",
    "sha256": "99e71a06b5af32c9d4d0d7067c31fc0543fdd3238b836af8102812ab76eb48ec",
}
KUSACHI_ANALOG_COMMIT = "a2bd212269996541d54a749ed51934d26291fd80"

# Boot-selection contract (verified read-only, not implemented here): P2
# challenge stages boot through the #651 host-mode StageEntry table keyed by
# ui_index; crawler resolves at ui_index 29. The #701 content-loading binder is
# read-only selection/coverage, not a roster loader. The P1
# `--experimental-challenge-level <id 0-4>` namespace is for P1 layouts and is
# NOT the crawler boot path.
BOOT_SELECTION = {
    "mechanism": "host-mode StageEntry table keyed by ui_index",
    "ui_index": UI_INDEX,
    "cave_id": CAVE_ID,
    "native_entry": "challenge host-mode stage-boot hook",
    "read_only_consumers": ["#701 content-loading binder (selection/coverage)",
                            "#688 kusachi content-wiring bridge"],
    "not_this_path": "--experimental-challenge-level (P1 layouts only)",
}
HARNESS_CONTRACT = {
    "harness": "challenge host-mode build/run harness",
    "needs": ["staged run layout (this bridge)", "#632 guard header"],
    "emits": ["boot/run evidence logs"],
}

# Native fixture change: none required by this bridge. Every input is a
# root-level staged file or a documented external interface. If the downstream
# consumer later proves one necessary, it must be a private scoped candidate
# for owner review with exact file:line anchors and hashes, never a shared edit.
NATIVE_FIXTURE_CANDIDATE = {
    "required": False,
    "reason": "All inputs are root-level staged layout files plus documented "
              "external interfaces; no native fixture change is needed.",
    "if_needed": "Specify a private scoped candidate for owner review with "
                 "exact file:line anchors and hashes; never a shared edit.",
    "candidate_anchors": [
        "pc_port/pc_p2_challenge_mode.h (host-mode StageEntry table, read-only)",
        "pc_port/pc_p2_challenge_content_loading.h (#701 binder, read-only)",
    ],
}


class MissingInput(ValueError):
    pass


class HashMismatch(ValueError):
    pass


class LayoutDecodeError(ValueError):
    pass


def staged_identity():
    """Pinned staged-layout facts (from the #562 consumer staging + disc)."""
    return dict(cave_id=CAVE_ID, source_path=SOURCE_PATH,
                source_sha256=SOURCE_SHA256, source_offset=SOURCE_OFFSET,
                source_size=SOURCE_SIZE, floors=EXPECTED_FLOORS,
                ui_index=UI_INDEX, squad_total=SQUAD_TOTAL,
                floor_seconds=list(FLOOR_SECONDS),
                squad=[dict(row) for row in EXPECTED_SQUAD],
                floors_pinned=[dict(row) for row in PINNED_FLOORS],
                boot_markers=list(BOOT_MARKERS),
                staged_markers=list(STAGED_MARKERS))


def verify_source_bytes(data):
    """Fail closed unless bytes match the pinned canonical hash and size."""
    blob = bytes(data)
    actual = hashlib.sha256(blob).hexdigest()
    if len(blob) != SOURCE_SIZE:
        raise HashMismatch("Source size %d does not match pinned %d"
                           % (len(blob), SOURCE_SIZE))
    if actual != SOURCE_SHA256:
        raise HashMismatch("Source hash %s does not match pinned %s"
                           % (actual, SOURCE_SHA256))
    return dict(source_path=SOURCE_PATH, offset=SOURCE_OFFSET,
                size=len(blob), sha256=actual)


def decode_layout(text, enemy_ids=None, treasure_ids=None):
    """Decode the stage through the shared parser (never forked)."""
    try:
        return parse_caveinfo(text, set(enemy_ids or ENEMY_IDS),
                              set(treasure_ids or TREASURE_IDS))
    except ValueError as error:
        raise LayoutDecodeError("Shared decode rejected input: %s" % error) from None


def decode_source_bytes(data):
    """Verify then decode raw caveinfo bytes (shift_jis retail text)."""
    verify_source_bytes(data)
    return decode_layout(bytes(data).decode("shift_jis", errors="replace"))


def load_staged_layout(layout_dir):
    """Read and validate the staged crawler run layout. Fail closed."""
    root = Path(layout_dir)
    if not root.is_dir():
        raise MissingInput("Staged crawler layout directory missing: %s" % root)
    texts = {}
    for name in STAGED_LAYOUT_FILES:
        path = root / name
        if not path.is_file():
            raise MissingInput("Staged crawler layout file missing: %s" % path)
        texts[name] = path.read_text(encoding="utf-8", errors="replace")
    try:
        manifest = json.loads(texts["stage-manifest.json"])
        squad = json.loads(texts["squad.json"])
        config = json.loads(texts["run-config.json"])
    except ValueError as error:
        raise LayoutDecodeError("Staged layout is not valid JSON: %s" % error) from None
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise LayoutDecodeError("Unsupported staged manifest schema")
    if manifest.get("source_id") != CAVE_ID:
        raise LayoutDecodeError("Staged source_id mismatch: %r"
                                % manifest.get("source_id"))
    if manifest.get("source_sha256") != SOURCE_SHA256:
        raise HashMismatch("Staged source_sha256 is not the pinned crawler hash")
    if manifest.get("floor_count") != EXPECTED_FLOORS:
        raise LayoutDecodeError("Staged floor_count mismatch: %r"
                                % manifest.get("floor_count"))
    if manifest.get("ui_index") != UI_INDEX:
        raise LayoutDecodeError("Staged ui_index mismatch: %r"
                                % manifest.get("ui_index"))
    floors = manifest.get("floors")
    if not isinstance(floors, list) or len(floors) != EXPECTED_FLOORS:
        raise LayoutDecodeError("Staged floor coverage mismatch")
    markers = tuple(line.strip() for line in texts["markers.txt"].splitlines()
                    if line.strip())
    names = {line.split()[0] for line in markers if line.split()}
    if not set(STAGED_MARKERS) <= names:
        raise LayoutDecodeError("Staged markers incomplete: %s"
                                % sorted(set(STAGED_MARKERS) - names))
    if not isinstance(squad, dict) or not isinstance(squad.get("squad"), list):
        raise LayoutDecodeError("Staged squad section malformed")
    return dict(source_id=CAVE_ID, source_sha256=SOURCE_SHA256,
                floor_count=manifest["floor_count"], ui_index=manifest["ui_index"],
                floors=floors, squad=squad.get("squad"),
                squad_total=squad.get("total"),
                floor_seconds=list(manifest.get("floor_seconds", [])),
                run_config=config, markers=markers, layout_dir=str(root))


def cross_check(decoded, staged):
    """Fail closed unless the decoded stage agrees with the staged layout."""
    if decoded.get("floor_count") != staged.get("floor_count"):
        raise LayoutDecodeError("Decoded/staged floor count mismatch")
    decoded_floors = decoded.get("floors", [])
    staged_floors = staged.get("floors", [])
    if len(decoded_floors) != len(staged_floors):
        raise LayoutDecodeError("Decoded/staged floor definition mismatch")
    for index, (df, sf) in enumerate(zip(decoded_floors, staged_floors)):
        want_pool = sf.get("unit_pool")
        got_pool = df.get("parameters", {}).get("f008")
        if want_pool != got_pool:
            raise LayoutDecodeError("Floor %d unit pool mismatch: %r != %r"
                                    % (index + 1, got_pool, want_pool))
        for kind, key in (("enemies", "enemies"), ("treasures", "treasures"),
                          ("gates", "gates")):
            if len(df.get(key, [])) != len(sf.get(key, [])):
                raise LayoutDecodeError("Floor %d %s count mismatch" % (index + 1, kind))
    return True


def pinned_staged_facts():
    """Manifest-shaped view of the pinned staged facts (for offline checks)."""
    return {"schema": 1, "source_id": CAVE_ID, "source_sha256": SOURCE_SHA256,
            "floor_count": EXPECTED_FLOORS, "ui_index": UI_INDEX,
            "floor_seconds": list(FLOOR_SECONDS),
            "squad": [dict(row) for row in EXPECTED_SQUAD], "total": SQUAD_TOTAL,
            "floors": [{"floor": row["floor"], "unit_pool": row["unit_pool"],
                        "light": row["light"],
                        "enemies": [None] * row["enemies"],
                        "treasures": [None] * row["treasures"],
                        "gates": [None] * row["gates"]} for row in PINNED_FLOORS]}


def arena_binding(decoded):
    """Arena geometry bindings per floor: unit pools and lights only."""
    floors = decoded.get("floors", [])
    if len(floors) != EXPECTED_FLOORS:
        raise LayoutDecodeError("Floor coverage mismatch")
    bindings = []
    for floor in floors:
        params = floor.get("parameters")
        if not isinstance(params, dict) or not params.get("f008"):
            raise LayoutDecodeError("Unit pool unresolved")
        bindings.append({"floor": floor.get("first_floor"), "unit_pool": params["f008"],
                         "light": params.get("f009", "none")})
    return bindings


def actor_rows(decoded):
    """Actor placement ROWS as definitions (weights/types), never placements."""
    rows = []
    for floor in decoded.get("floors", []):
        for kind, entries in (("enemy", floor.get("enemies", [])),
                              ("treasure", floor.get("treasures", [])),
                              ("gate", floor.get("gates", [])),
                              ("cap", floor.get("caps", []))):
            for entry in entries:
                rows.append({"floor": floor.get("first_floor"), "kind": kind,
                             "record": dict(entry)})
    return rows


def starting_squad(staged):
    """Starting-squad wiring from the staged layout (60 across two colors)."""
    return dict(cave_id=CAVE_ID, ui_index=staged["ui_index"],
                squad=[dict(row) for row in (staged.get("squad") or [])],
                squad_total=staged.get("squad_total"),
                floor_seconds=list(staged.get("floor_seconds", [])))


def boot_params(staged, decoded):
    """Assemble boot parameters: arena + actors + squad + markers + selection."""
    cross_check(decoded, staged)
    return dict(cave_id=CAVE_ID, ui_index=staged["ui_index"],
                arena=arena_binding(decoded), actor_rows=actor_rows(decoded),
                squad=starting_squad(staged), selection=dict(BOOT_SELECTION),
                harness=dict(HARNESS_CONTRACT), markers=list(BOOT_MARKERS))


def wiring_packet(params, decoded=None):
    """Reviewed packet: identity, boot params, contracts, open items."""
    packet = {
        "schema": 1,
        "cave_id": CAVE_ID,
        "source_path": SOURCE_PATH,
        "source_sha256": SOURCE_SHA256,
        "source_offset": SOURCE_OFFSET,
        "source_size": SOURCE_SIZE,
        "staged_evidence": dict(STAGED_EVIDENCE),
        "kusachi_analog_commit": KUSACHI_ANALOG_COMMIT,
        "boot": params,
        "native_fixture_candidate": dict(NATIVE_FIXTURE_CANDIDATE),
        "semantic_resolution": "open",
        "downstream_consumer": "p2-challenge-ch-mat-crawler-p1 (#562)",
        "blockers": [
            "P1 runtime observation needs the challenge host-mode harness plus "
            "ui_index-29 selection wiring against these boot params (owner lanes).",
            "Enemy/treasure token resolution and unit-asset presence stay with the "
            "#562 adapter record and the shared asset readers.",
            "Any native fixture change is a private scoped candidate for owner "
            "review, never a shared edit.",
        ],
        "limitations": [
            "Actor rows are definition inputs, not spawn instances or placements; "
            "no coordinates are emitted.",
            "Timers, squad and markers are staged baseline carried into boot "
            "params, not observed gameplay.",
            "Markers name observation points; emitting them without a runtime "
            "would fabricate evidence.",
        ],
        "generated": False,
    }
    if decoded is not None:
        packet["floor_count"] = decoded.get("floor_count")
    return packet