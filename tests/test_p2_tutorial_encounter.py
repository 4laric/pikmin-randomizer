import json
import struct
import pytest
from scripts.stage_pikmin2_tutorial_encounter import source_selection, positioned, ENEMY_POSITION, ONION_POSITION


def source_fixture(tmp_path):
    inventory = {"nonloop/5-29.txt": {"actors": [{"kind":"teki","index":0,"reserved":5,"respawn_days":3,"effective_position":ENEMY_POSITION}]},
                 "defaultgen.txt": {"actors": [{}, {"kind":"item","item":"onyn","onion_index":1,"after_boot":1,"effective_position":ONION_POSITION}]}}
    (tmp_path / "surface-generators.json").write_text(json.dumps(inventory),encoding="utf8")
    raw = tmp_path / "generators/nonloop/5-29.txt"
    raw.parent.mkdir(parents=True)
    raw.write_text("{teki} {0005} 1 0 1 0.000000 1 100.000000 0.000000 0 3 1 1 2 0.400000 {????}",encoding="shift_jis")
    return tmp_path, raw, inventory


@pytest.mark.parametrize("day", [5, 29])
def test_original_schedule_bounds(tmp_path, day):
    bundle, _, _ = source_fixture(tmp_path)
    enemy, onion, sha = source_selection(bundle, day)
    assert tuple(enemy["effective_position"]) == ENEMY_POSITION
    assert tuple(onion["effective_position"]) == ONION_POSITION
    assert len(sha) == 64


@pytest.mark.parametrize("day", [4, 30, True, 5.0])
def test_refuse_non_original_schedule(tmp_path, day):
    bundle, _, _ = source_fixture(tmp_path)
    with pytest.raises(ValueError,match="days5"):
        source_selection(bundle, day)


@pytest.mark.parametrize("payload", ["{teki} {0005} 2 0 1 0.000000 1 100.000000 0.000000 0 3 1 1 2 0.400000 {????}",
 "{teki} {0005} 1 0 2 0.000000 1 100.000000 0.000000 0 3 1 1 2 0.400000 {????}",
 "{teki} {0005} 1 0 1 0.000000 1 100.000000"])
def test_refuse_changed_identity_count_or_truncation(tmp_path, payload):
    bundle, raw, _ = source_fixture(tmp_path)
    raw.write_text(payload,encoding="shift_jis")
    with pytest.raises((ValueError,IndexError)):
        source_selection(bundle, 5)


def test_refuse_source_relocation(tmp_path):
    bundle, _, inventory = source_fixture(tmp_path)
    inventory["defaultgen.txt"]["actors"][1]["effective_position"] = [0,0,0]
    (bundle/"surface-generators.json").write_text(json.dumps(inventory),encoding="utf8")
    with pytest.raises(ValueError,match="placement changed"):
        source_selection(bundle,5)


@pytest.mark.parametrize("uid, disk", [(0x50323101, b"\x01\x31\x32\x50"),
                                      (0x50324F01, b"\x01\x4f\x32\x50")])
def test_native_fourcc_identity_boundary(uid, disk):
    row = positioned(b"    0.0v" + bytes(100), uid, ENEMY_POSITION, "original encounter")
    assert row[8:12] == disk
    # native src/sysCommon/stream.cpp Stream::readInt reads BE; generator.cpp
    # readID then bswap32s that integer. Model both distinct boundaries.
    stream_int = struct.unpack_from(">I", row, 8)[0]
    native_generator_id = int.from_bytes(stream_int.to_bytes(4, "little"), "big")
    assert native_generator_id == uid
    assert struct.unpack_from(">3f", row, 48) == pytest.approx(ENEMY_POSITION)
