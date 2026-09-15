"""Coverage-contract tests for ``scripts.audit_pikmin2_roster.coverage_gaps`` (lane 02).

Pins the "complete ledger coverage" audit contract: every row cites an existing
source doc and an existing native module; every ``docs/PIKMIN2_*_NATIVE.md``
source slice is cited; and every non-shared native ``pc_p2_*.cpp`` module is
referenced by a row.

Synthetic tests build rosters purely through
``experimental.pikmin2_enemy_roster`` (``synthetic_payload`` + ``entries_from_payload``)
and drive ``coverage_gaps`` with mock ``modules``/``native_docs``/``existing_docs``,
so they never touch the real ledger. The two integration tests at the bottom
exercise the committed ledger and must pass once the ledger is complete.
"""
from pathlib import Path

from experimental.pikmin2_enemy_roster import (
    admitted_ids,
    build_entries,
    entries_from_payload,
    load_and_validate,
    parse_enum_header,
    parse_info_table,
    resolve_ids,
    snapshot_payload,
)
from scripts.audit_pikmin2_roster import (
    ENGINE_PORT,
    MODULE_ALIASES,
    SHARED_MODULES,
    _lane_of_module,
    coverage_gaps,
    native_modules,
    native_source_docs,
)

# ---------------------------------------------------------------------------
# Synthetic roster (Pelplant=0, Frog=17, Egg=37).
# ---------------------------------------------------------------------------

SYNTHETIC_HEADER = """
struct EnemyTypeID {
enum EEnemyTypeID {
\tEnemyID_NULL     = -1, // ID not set
\tEnemyID_Pelplant = 0,\t  // Pellet Posy
\tEnemyID_Frog     = 17,  // Yellow Wollywog
\tEnemyID_Egg      = 37,  // Egg
\tEnemyID_COUNT,
};
};
"""

SYNTHETIC_TABLE = """
EnemyInfo gEnemyInfo[] = {
//  name   ID   parent   members flags   model anim animgr texture param collision stone childID childNum droptype
\t{"Pelplant", EnemyTypeID::EnemyID_Pelplant, -1, 1, (EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "Pelplant", "Pelplant", "Pelplant", "Pelplant", "Pelplant", "Pelplant", "Pelplant", -1, 0, BDT_Empty},
\t{"Frog", EnemyTypeID::EnemyID_Frog, -1, 1, (EFlag_DayEndMax4 | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", EnemyTypeID::EnemyID_Egg, 10, BDT_Strong},
\t{"Egg", EnemyTypeID::EnemyID_Egg, -1, 1, (EFlag_HasNoInfo | EFlag_CanBeSpawned | 2 | EFlag_UseOwnID), "", "", "", "", "", "", "", -1, 0, BDT_Empty},
};
"""


def _synthetic_payload():
    enums = parse_enum_header(SYNTHETIC_HEADER)
    tables = parse_info_table(SYNTHETIC_TABLE)
    return snapshot_payload(resolve_ids(build_entries(enums, tables)), "synthetic")


DOC_FOO = "PIKMIN2_FOO_NATIVE.md"
DOC_BAR = "PIKMIN2_BAR_NATIVE.md"
DOC_BAZ = "PIKMIN2_BAZ_NATIVE.md"
DOC_MISSING = "PIKMIN2_MISSING_NATIVE.md"
DOC_UNUSED = "PIKMIN2_UNUSED_NATIVE.md"

MOD_FOO = "pc_p2_foo"
MOD_BAR = "pc_p2_bar"
MOD_BAZ = "pc_p2_baz"
MOD_MISSING = "pc_p2_not_real"


def _covered_overlays():
    return {
        "0": {"source": [DOC_FOO], "native_module": MOD_FOO},
        "17": {"source": [DOC_BAR], "native_module": MOD_BAR},
        "37": {"source": [DOC_BAZ], "native_module": MOD_BAZ},
    }


def _covered_docs():
    return [DOC_FOO, DOC_BAR, DOC_BAZ]


def _covered_modules():
    return {MOD_FOO, MOD_BAR, MOD_BAZ}


def _gaps(roster, modules=None, native_docs=None, existing_docs=None):
    if modules is None:
        modules = _covered_modules()
    if native_docs is None:
        native_docs = _covered_docs()
    if existing_docs is None:
        existing_docs = {DOC_FOO, DOC_BAR, DOC_BAZ, DOC_MISSING, DOC_UNUSED}
    return coverage_gaps(roster, modules, native_docs, existing_docs=existing_docs)


# ---------------------------------------------------------------------------
# coverage_gaps synthetic tests
# ---------------------------------------------------------------------------

def test_coverage_gaps_no_gaps():
    roster = entries_from_payload(_synthetic_payload(), _covered_overlays())
    gaps = _gaps(roster)
    assert gaps["rows_citing_missing_docs"] == []
    assert gaps["rows_citing_missing_modules"] == []
    assert gaps["uncited_native_docs"] == []
    assert gaps["uncovered_identity_modules"] == []


def test_coverage_gaps_detects_missing_doc():
    overlays = _covered_overlays()
    overlays["17"]["source"] = [DOC_MISSING]
    roster = entries_from_payload(_synthetic_payload(), overlays)
    gaps = _gaps(roster, existing_docs={DOC_FOO, DOC_BAR, DOC_BAZ, DOC_UNUSED})
    assert gaps["rows_citing_missing_docs"] == ["Frog=17 " + DOC_MISSING]


def test_coverage_gaps_detects_missing_module():
    overlays = _covered_overlays()
    overlays["17"]["native_module"] = MOD_MISSING
    roster = entries_from_payload(_synthetic_payload(), overlays)
    gaps = _gaps(roster)
    assert gaps["rows_citing_missing_modules"] == ["Frog=17 " + MOD_MISSING]


def test_coverage_gaps_detects_uncited_doc():
    roster = entries_from_payload(_synthetic_payload(), _covered_overlays())
    gaps = _gaps(roster, native_docs=_covered_docs() + [DOC_UNUSED])
    assert gaps["uncited_native_docs"] == [DOC_UNUSED]


def test_coverage_gaps_detects_uncovered_module():
    shared = next(iter(SHARED_MODULES))
    non_shared = "pc_p2_unreferenced_xyz"
    modules = _covered_modules() | {shared, non_shared}
    roster = entries_from_payload(_synthetic_payload(), _covered_overlays())
    gaps = _gaps(roster, modules=modules)
    assert non_shared in gaps["uncovered_identity_modules"]
    assert shared not in gaps["uncovered_identity_modules"]


def test_module_alias_resolves_to_real_stem():
    # pc_p2_snow (overlay name) resolves to pc_p2_enemy (the real .cpp stem).
    overlays = {"17": {"source": [DOC_FOO], "native_module": "pc_p2_snow"}}
    roster = entries_from_payload(_synthetic_payload(), overlays)
    gaps = coverage_gaps(roster, {"pc_p2_enemy"}, [DOC_FOO], existing_docs={DOC_FOO})
    assert gaps["rows_citing_missing_modules"] == []
    assert "pc_p2_enemy" not in gaps["uncovered_identity_modules"]


# ---------------------------------------------------------------------------
# Helper shape tests
# ---------------------------------------------------------------------------

def test_native_source_docs_shape():
    docs = native_source_docs()
    assert isinstance(docs, list)
    assert docs
    assert all(isinstance(name, str) and name.endswith("_NATIVE.md") for name in docs)
    assert docs == sorted(docs)


def test_shared_modules_and_aliases_shape():
    assert isinstance(SHARED_MODULES, frozenset)
    assert SHARED_MODULES
    assert all(isinstance(stem, str) for stem in SHARED_MODULES)
    assert isinstance(MODULE_ALIASES, dict)
    assert all(isinstance(key, str) and isinstance(value, str)
               for key, value in MODULE_ALIASES.items())


def test_shared_modules_subset_of_native_modules():
    # The allowlist can only name stems that actually exist on disk, otherwise
    # a drifted entry silently masks a real uncovered identity module.
    modules = native_modules(ENGINE_PORT)
    assert SHARED_MODULES <= modules
    assert set(MODULE_ALIASES.values()) <= modules


def test_lane_of_module_routes_to_owning_lane():
    assert _lane_of_module("pc_p2_bigtreasure_receiver") == "32"
    assert _lane_of_module("pc_p2_breadbug_contest_host") == "18"
    assert _lane_of_module("pc_p2_groink_carcass") == "21"
    assert _lane_of_module("pc_p2_sokkuri") == "14"
    assert _lane_of_module("pc_p2_rock_host") == "20"


# ---------------------------------------------------------------------------
# Integration tests against the real ledger.
# ---------------------------------------------------------------------------

def test_real_ledger_is_fully_covered():
    roster = load_and_validate()
    root = Path(__file__).resolve().parents[1]
    modules = {path.stem for path in (root / "engine" / "pc_port").glob("pc_p2_*.cpp")}
    gaps = coverage_gaps(roster, modules, native_source_docs())
    assert gaps["rows_citing_missing_docs"] == []
    assert gaps["rows_citing_missing_modules"] == []
    assert gaps["uncited_native_docs"] == []
    assert gaps["uncovered_identity_modules"] == []


def test_real_ledger_admitted_set():
    assert admitted_ids(load_and_validate()) == [23, 44, 59, 60, 61, 62]  # 23 Sarai; 44 Dwarf Orange; 59-62 Otakara elemental Dweevils (admitted 2026-09-15)


# ---------------------------------------------------------------------------
# CLI exit-code tests for audit_pikmin2_roster.main(['--review'])
# ---------------------------------------------------------------------------

def test_audit_review_exits_zero_on_real_ledger(capsys):
    import scripts.audit_pikmin2_roster as audit
    assert audit.main(["--review"]) == 0


def test_audit_review_exits_one_on_missing_cited_doc(tmp_path, monkeypatch, capsys):
    import json
    import experimental.pikmin2_enemy_roster as roster_mod
    import scripts.audit_pikmin2_roster as audit
    evidence = json.loads(roster_mod.EVIDENCE_PATH.read_text(encoding="utf-8"))
    evidence["entries"]["79"]["source"] = ["PIKMIN2_DOES_NOT_EXIST_NATIVE.md"]
    tmp_evidence = tmp_path / "evidence.json"
    tmp_evidence.write_text(json.dumps(evidence), encoding="utf-8")
    monkeypatch.setattr(roster_mod, "EVIDENCE_PATH", tmp_evidence)
    assert audit.main(["--review"]) == 1
