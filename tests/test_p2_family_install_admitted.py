"""Family installers for the 11 admitted P2 ids (#442).

Proves ``install_layout`` stages a layout binding all 11 admitted ids without
raising, and each species' sidecar exists and parses in the native reader's
format:

- Kogane (9) -> ``p2-kogane-native.txt`` (``pc_p2_kogane_policy.h::read``) +
  ``kogane_*.mod`` via ``experimental.pikmin2_kogane_install``.
- Sokkuri (79) -> ``p2-ground-actors.txt`` + ``p2-ground-bank.txt`` via
  ``experimental.pikmin2_ground_inverts_install`` (native
  ``pc_p2_sokkuri_setup`` parses ``P2_GROUND_ACTORS_1`` /
  ``P2_GROUND_BANK_1``).
- Kurage (57) -> ``p2-kurage-teki.txt`` (``p2kurage::read``:
  ``P2_KURAGE_TEKI_1 1 <gen> 0``).
- MiniHoudai (78) -> ``p2-groink-teki.txt`` (``p2groink::read`` via
  ``experimental.pikmin2_groink_carcass_teki.sidecar_config``).

Bridge-mode note: the native setups take bound actor ids from the seed
(``pc_p2_campaign_ids``), so the Kurage/Groink filed generators are
placeholders there (single-entry sidecars); Kogane/Sokkuri file the real seed
generators. All synthetic sources; no retail assets or ISO reads.
"""
import hashlib
import json
from pathlib import Path

from experimental import pikmin2_family_install as family_install
from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_kogane_install import sha as kogane_sha
from tests.test_pikmin2_install_binding import make_dwarf_orange_source
from tests.test_pikmin2_batch2 import fake_imported as batch_fake_imported
from tests.test_pikmin2_mamuta_install import fake_imported as mamuta_fake_imported

ADMITTED = [
    ("gen-009", 9, "Kogane", 219009),
    ("gen-023", 23, "Sarai", 219023),
    ("gen-044", 44, "BlueKochappy", 219044),
    ("gen-054", 54, "Miulin", 219054),
    ("gen-057", 57, "Kurage", 219057),
    ("gen-059", 59, "FireOtakara", 219059),
    ("gen-060", 60, "WaterOtakara", 219060),
    ("gen-061", 61, "GasOtakara", 219061),
    ("gen-062", 62, "ElecOtakara", 219062),
    ("gen-078", 78, "MiniHoudai", 219078),
    ("gen-079", 79, "Sokkuri", 219079),
]


def make_kogane_source(content_root):
    source = content_root / "Kogane"
    bank = source
    (bank / "shared").mkdir(parents=True)
    clips = []
    expected_events = {"move.bca": [[2, 0], [11, 1]], "wait.bca": [[0, 0], [14, 1]],
                       "damage.bca": [[5, 2], [7, 3], [29, 4]]}
    for clip_name, events in expected_events.items():
        poses = []
        for i in range(2):
            name = f"{Path(clip_name).stem}_{i:02}.mod"
            data = b"pose-bytes" + name.encode()
            (bank / "shared" / name).write_bytes(data)
            poses.append(dict(file=name, frame=i, sha256=kogane_sha(data), conversion={}))
        clips.append(dict(file=clip_name, events=events, sha256=kogane_sha(clip_name.encode()),
                          status="converted", source_frames=15, poses=poses))
    manifest = {"schema": 1, "family": "Kogane", "native_ready": False,
                "species": {s: {"enemy_id": i} for s, i in
                            (("kogane", 9), ("wealthy", 10), ("fart", 11))},
                "shared": {"joints": ["null1", "body"], "clips": clips}}
    (bank / "beetles.json").write_text(json.dumps(manifest))
    return source


def make_sarai_source(content_root):
    source = content_root / "Sarai"
    source.mkdir(parents=True)
    (source / "sarai-attack-mouths.txt").write_text(
        "P2_DEMON_MOUTHS_1 deadbeef 1\n", encoding="ascii")
    return source


def make_kurage_source(content_root):
    source = content_root / "Kurage"
    source.mkdir(parents=True)
    (source / "identity.json").write_text(
        json.dumps({"schema": 1, "source_id": 57, "enum_name": "Kurage"}),
        encoding="utf-8")
    return source


def make_minihoudai_source(content_root):
    source = content_root / "MiniHoudai"
    source.mkdir(parents=True)
    (source / "identity.json").write_text(
        json.dumps({"schema": 1, "source_id": 78, "enum_name": "MiniHoudai"}),
        encoding="utf-8")
    return source


def make_content_root(content_root):
    make_dwarf_orange_source(content_root)
    mamuta_fake_imported(content_root / "Miulin")
    make_sarai_source(content_root)
    make_kogane_source(content_root)
    batch_fake_imported(content_root / "Sokkuri", FAMILIES["ground"])
    make_kurage_source(content_root)
    make_minihoudai_source(content_root)
    for enum_name in ("FireOtakara", "WaterOtakara", "GasOtakara", "ElecOtakara"):
        batch_fake_imported(content_root / enum_name, FAMILIES["dweevil"])
    return content_root


def make_retail(root):
    retail = root / "retail"
    (retail / "dataDir" / "stages").mkdir(parents=True)
    return retail


def parse_kogane_native(text):
    """Mirror of ``p2kogane::read`` (pc_p2_kogane_policy.h)."""
    tokens = text.split()
    assert tokens[0] == "P2_KOGANE_NATIVE_1"
    assert tokens[1] == "karada" and 0 <= int(tokens[2]) <= 64
    assert tokens[3] == "actors"
    count = int(tokens[4])
    assert 1 <= count <= 100
    pos = 5
    seen = set()
    for _ in range(count):
        gen, species = int(tokens[pos]), int(tokens[pos + 1])
        assert 0 < gen <= 0xFFFFFFFF and 9 <= species <= 11
        assert gen not in seen
        seen.add(gen)
        pos += 2
    clips = {}
    while pos < len(tokens):
        name = tokens[pos]
        assert name in ("move", "wait", "damage") and name not in clips
        n, duration = int(tokens[pos + 1]), int(tokens[pos + 2])
        assert 2 <= n <= 24 and 1 <= duration <= 10000
        frames = [int(t) for t in tokens[pos + 3:pos + 3 + n]]
        assert frames == sorted(set(frames)) and frames[0] == 0
        assert frames[-1] == duration - 1
        clips[name] = frames
        pos += 3 + n
    assert set(clips) == {"move", "wait", "damage"}
    return seen


def parse_ground_actors(text):
    tokens = text.split()
    assert tokens[0] == "P2_GROUND_ACTORS_1"
    assert int(tokens[1]) == (len(tokens) - 2) // 2
    pairs = [(int(tokens[i]), tokens[i + 1]) for i in range(2, len(tokens), 2)]
    assert all(g > 0 for g, _ in pairs)
    return pairs


def parse_ground_bank(text):
    lines = text.splitlines()
    assert lines[0] == "P2_GROUND_BANK_1"
    assert any(l.startswith("species Sokkuri 79") for l in lines[1:])
    assert any(l.startswith("clip Sokkuri ") for l in lines[1:])


def parse_kurage_teki(text):
    tokens = text.split()
    assert tokens == ["P2_KURAGE_TEKI_1", "1", tokens[2], "0"]
    assert int(tokens[2]) > 0


def parse_groink_teki(text):
    tokens = text.split()
    assert tokens[0] == "P2_GROINK_TEKI_1" and tokens[1] == "1"
    assert int(tokens[2]) > 0 and int(tokens[3]) == 0
    gauge, recovery, health = float(tokens[4]), float(tokens[5]), float(tokens[6])
    assert gauge >= 0.0 and recovery > 0.0 and health >= 0.0
    assert len(tokens) in (7, 8) and (len(tokens) == 7 or tokens[7] == "transport")


def test_install_layout_stages_all_11_admitted_ids(tmp_path):
    content_root = make_content_root(tmp_path / "content")
    retail = make_retail(tmp_path)
    run = tmp_path / "run"
    layout = {"bindings": [
        {"target": t, "source_id": sid, "enum_name": enum}
        for t, sid, enum, _gen in ADMITTED]}
    actor_bindings = {t: gen for t, _sid, _enum, gen in ADMITTED}
    receipt = family_install.install_layout(
        run, layout, content_root, actor_bindings, retail_assets=retail)
    assert set(receipt["receipts"]) == {t for t, _, _, _ in ADMITTED}

    kogane_txt = (run / "p2-kogane-native.txt").read_text(encoding="ascii")
    assert parse_kogane_native(kogane_txt) == {219009}
    room = run / "assets" / "dataDir" / "courses" / "pikmin2room"
    assert len(list(room.glob("kogane_*.mod"))) == 6

    ground_actors = (run / "p2-ground-actors.txt").read_text(encoding="ascii")
    assert (219079, "Sokkuri") in parse_ground_actors(ground_actors)
    parse_ground_bank((run / "p2-ground-bank.txt").read_text(encoding="ascii"))

    kurage_txt = (run / "p2-kurage-teki.txt").read_text(encoding="ascii")
    parse_kurage_teki(kurage_txt)
    assert "219057" in kurage_txt

    groink_txt = (run / "p2-groink-teki.txt").read_text(encoding="ascii")
    parse_groink_teki(groink_txt)
    assert "219078" in groink_txt

    assert "219044" in (run / "p2-dwarf-orange-actors.txt").read_text(encoding="ascii")
    assert "219054" in (run / "p2-mamuta-actors.txt").read_text(encoding="ascii")
    assert "219023" in (run / "p2-sarai-actors.txt").read_text(encoding="ascii")
    dweevil_txt = (run / "p2-dweevil-actors.txt").read_text(encoding="ascii")
    for gen, species in ((219059, "FireOtakara"), (219060, "WaterOtakara"),
                         (219061, "GasOtakara"), (219062, "ElecOtakara")):
        assert str(gen) in dweevil_txt and species in dweevil_txt


def test_resolve_family_covers_new_admitted_ids():
    assert family_install.resolve_family(9) == "kogane"
    assert family_install.resolve_family("Kogane") == "kogane"
    assert family_install.resolve_family(79) == "sokkuri"
    assert family_install.resolve_family("Sokkuri") == "sokkuri"
    assert family_install.resolve_family(57) == "kurage"
    assert family_install.resolve_family("Kurage") == "kurage"
    assert family_install.resolve_family(78) == "minihoudai"
    assert family_install.resolve_family("MiniHoudai") == "minihoudai"


def test_new_validators_fail_closed(tmp_path):
    from experimental.pikmin2_staging import StagingError
    import pytest
    for validator, dirname in (
            (family_install._validator("kogane"), "Kogane"),
            (family_install._validator("sokkuri"), "Sokkuri"),
            (family_install._validator("kurage"), "Kurage"),
            (family_install._validator("minihoudai"), "MiniHoudai")):
        empty = tmp_path / f"empty-{dirname}"
        empty.mkdir(exist_ok=True)
        with pytest.raises(StagingError):
            validator(empty)


def test_sidecar_hashes_recorded(tmp_path):
    content_root = make_content_root(tmp_path / "content")
    retail = make_retail(tmp_path)
    run = tmp_path / "run"
    layout = {"bindings": [
        {"target": t, "source_id": sid, "enum_name": enum}
        for t, sid, enum, _gen in ADMITTED]}
    actor_bindings = {t: gen for t, _sid, _enum, gen in ADMITTED}
    receipt = family_install.install_layout(
        run, layout, content_root, actor_bindings, retail_assets=retail)
    for name in ("p2-kogane-native.txt", "p2-kurage-teki.txt",
                 "p2-groink-teki.txt", "p2-ground-actors.txt",
                 "p2-ground-bank.txt"):
        data = (run / name).read_bytes()
        assert receipt["files"][name] == hashlib.sha256(data).hexdigest()
