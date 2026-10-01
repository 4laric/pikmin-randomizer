"""Focused tests for experimental.pikmin2_cave_geometry (lane 45).

Covers the real-geometry plan over a synthetic six-node forest_1-like lane-44
rooms dict, its strict ``P2_CAVE_GEOMETRY_1`` text round-trip, fail-closed
validation of proxies and missing gate actors/models, parser rejection of
malformed text, determinism, the CLI and (when present) the real lane-44
artifact. No disc, ISO or network access.
"""

import json
from pathlib import Path

import pytest

from experimental import pikmin2_cave_geometry as geo

L44_ROOMS = Path(__file__).resolve().parents[2] / "l44-out" / "rooms-salt0" / "p2-cave-rooms.json"


def forest_rooms():
    return {
        "schema": "p2-cave-rooms/1",
        "source": "engine",
        "geometry": "proxy",
        "cave": "forest_1",
        "floor": 1,
        "seed": 468001,
        "salt": 0,
        "cell": 48,
        "origin": [0, 0],
        "entrance": "forest_1:f1:segment:0",
        "hole": "forest_1:f1:segment:1",
        "units": [
            {"id": "forest_1:f1:segment:0", "kind": "segment", "hazard": None,
             "segment_index": 0, "items": ["juji_key_fc"], "gx": 0, "gz": 0,
             "doors": ["choke_water_0", "leaf_elec_0"]},
            {"id": "choke_water_0", "kind": "choke", "hazard": "water",
             "segment_index": 1, "items": [], "gx": 24, "gz": 48,
             "doors": ["forest_1:f1:segment:0", "forest_1:f1:segment:1"]},
            {"id": "leaf_elec_0", "kind": "leaf", "hazard": "elec",
             "segment_index": 0, "items": ["treasure_elec"], "gx": 72, "gz": 48,
             "doors": ["forest_1:f1:segment:0", "gate:leaf_elec_0"]},
            {"id": "forest_1:f1:segment:1", "kind": "segment", "hazard": None,
             "segment_index": 1, "items": [], "gx": 0, "gz": 96,
             "doors": ["choke_water_0", "leaf_water_0"]},
            {"id": "gate:leaf_elec_0", "kind": "gate", "hazard": "elec",
             "segment_index": 0, "items": [], "gx": 48, "gz": 96,
             "doors": ["leaf_elec_0"]},
            {"id": "leaf_water_0", "kind": "leaf", "hazard": "water",
             "segment_index": 1, "items": ["treasure_water"], "gx": 24, "gz": 144,
             "doors": ["forest_1:f1:segment:1"]},
        ],
        "edges": [
            ["forest_1:f1:segment:0", "choke_water_0"],
            ["choke_water_0", "forest_1:f1:segment:1"],
            ["forest_1:f1:segment:0", "leaf_elec_0"],
            ["forest_1:f1:segment:1", "leaf_water_0"],
            ["leaf_elec_0", "gate:leaf_elec_0"],
        ],
    }


def full_models():
    return {
        "choke_water_0": "models/choke_water_0.mdl",
        "leaf_elec_0": "models/leaf_elec_0.mdl",
        "leaf_water_0": "models/leaf_water_0.mdl",
        "gate:leaf_elec_0": "models/p2_elec_gate.mdl",
    }


def make_model_root(root, models):
    for relative in models.values():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"MDL")


def test_build_preserves_order_ids_and_round_trips():
    rooms = forest_rooms()
    plan = geo.build_geometry(rooms, models=full_models())

    assert [node["id"] for node in plan["nodes"]] == [unit["id"] for unit in rooms["units"]]
    assert plan["geometry"] == "real"
    assert plan["cave"] == rooms["cave"]
    assert plan["entrance"] == rooms["entrance"]
    assert plan["hole"] == rooms["hole"]

    text = geo.geometry_text(plan)
    assert text.splitlines()[0] == geo.TEXT_HEADER
    parsed = geo.parse_geometry_text(text)
    assert parsed == plan
    assert geo.geometry_text(parsed) == text


def test_validate_passes_with_model_root(tmp_path):
    plan = geo.build_geometry(forest_rooms(), models=full_models())
    make_model_root(tmp_path, full_models())

    result = geo.validate_geometry(plan, model_root=tmp_path)
    assert result["valid"] is True
    assert result["geometry"] == "real"
    assert result["errors"] == []
    assert result["real_nodes"] == 4
    assert result["proxy_nodes"] == 2
    assert result["gate_actors"] == 2


def test_choke_without_model_is_invalid():
    models = full_models()
    del models["choke_water_0"]
    plan = geo.build_geometry(forest_rooms(), models=models)

    result = geo.validate_geometry(plan)
    assert result["valid"] is False
    assert any("choke_water_0" in error for error in result["errors"])


def test_elec_leaf_without_gate_actor_is_invalid():
    models = full_models()
    del models["gate:leaf_elec_0"]
    plan = geo.build_geometry(forest_rooms(), models=models)

    result = geo.validate_geometry(plan)
    assert result["valid"] is False
    assert any("gate" in error for error in result["errors"])
    assert any(node["id"] == "leaf_elec_0" and node["gate"]["placed"] is False
               for node in plan["nodes"])


def test_missing_model_file_is_invalid(tmp_path):
    plan = geo.build_geometry(forest_rooms(), models=full_models())
    make_model_root(tmp_path, {"choke_water_0": full_models()["choke_water_0"]})

    result = geo.validate_geometry(plan, model_root=tmp_path)
    assert result["valid"] is False
    assert any("missing on disk" in error for error in result["errors"])


def test_proxy_input_never_validates_real():
    proxy = geo.build_geometry(forest_rooms(), models={})
    assert proxy["geometry"] == "proxy"
    result = geo.validate_geometry(proxy)
    assert result["valid"] is False
    assert result["geometry"] == "proxy"

    mixed = geo.build_geometry(forest_rooms(), models={"choke_water_0": "models/choke.mdl"})
    assert mixed["geometry"] == "mixed"
    assert geo.validate_geometry(mixed)["valid"] is False

    lying = geo.build_geometry(forest_rooms(), models={})
    lying["geometry"] = "real"
    checked = geo.validate_geometry(lying)
    assert checked["valid"] is False
    assert checked["geometry"] == "proxy"


def test_parser_rejects_malformed_text():
    plan = geo.build_geometry(forest_rooms(), models=full_models())
    text = geo.geometry_text(plan)
    lines = text.splitlines()

    bad_header = "\n".join(["P2_CAVE_GEOMETRY_X"] + lines[1:]) + "\n"
    with pytest.raises(ValueError):
        geo.parse_geometry_text(bad_header)

    truncated = list(lines)
    truncated[7] = " ".join(truncated[7].split()[:-1])
    with pytest.raises(ValueError):
        geo.parse_geometry_text("\n".join(truncated) + "\n")

    bad_class = list(lines)
    bad_class[7] = bad_class[7].replace(" proxy ", " weird ", 1)
    with pytest.raises(ValueError):
        geo.parse_geometry_text("\n".join(bad_class) + "\n")

    wrong_count = list(lines)
    wrong_count[6] = "units %d" % (len(plan["nodes"]) + 1)
    with pytest.raises(ValueError):
        geo.parse_geometry_text("\n".join(wrong_count) + "\n")

    duplicate = list(lines)
    first_id = duplicate[7].split()[0]
    parts = duplicate[8].split()
    parts[0] = first_id
    duplicate[8] = " ".join(parts)
    with pytest.raises(ValueError):
        geo.parse_geometry_text("\n".join(duplicate) + "\n")


def test_parser_rejects_truncation_and_trailing():
    text = geo.geometry_text(geo.build_geometry(forest_rooms(), models=full_models()))
    with pytest.raises(ValueError):
        geo.parse_geometry_text(text[:len(text) // 2])
    with pytest.raises(ValueError):
        geo.parse_geometry_text(text + "extra\n")
    with pytest.raises(ValueError):
        geo.parse_geometry_text("P2_CAVE_GEOMETRY_1\n")


def test_determinism_same_input_identical_text():
    first = geo.geometry_text(geo.build_geometry(forest_rooms(), models=full_models()))
    second = geo.geometry_text(geo.build_geometry(forest_rooms(), models=full_models()))
    assert first == second


def test_marker_reports_counts():
    plan = geo.build_geometry(forest_rooms(), models=full_models())
    marker = geo.geometry_marker(plan)
    assert marker.startswith("P2_CAVE_GEOMETRY_READY ")
    fields = dict(part.split("=", 1) for part in marker.split()[1:])
    assert fields["nodes"] == "6"
    assert fields["real"] == "4"
    assert fields["proxy"] == "2"
    assert fields["gate_actors"] == "2"
    assert fields["geometry"] == "real"
    assert fields["cave"] == "forest_1"
    assert fields["seed"] == "468001"
    assert fields["salt"] == "0"


def test_cli_writes_artifacts(tmp_path, capsys):
    rooms_path = tmp_path / "p2-cave-rooms.json"
    rooms_path.write_text(json.dumps(forest_rooms()), encoding="utf-8")
    out_dir = tmp_path / "out"

    argv = ["--rooms", str(rooms_path), "--out-dir", str(out_dir)]
    for node_id, model in full_models().items():
        argv += ["--model", "%s=%s" % (node_id, model)]

    status = geo.main(argv)
    assert status == 0

    json_path = out_dir / "p2-cave-geometry.json"
    text_path = out_dir / "p2-cave-geometry.txt"
    assert json_path.exists()
    assert text_path.exists()
    plan = json.loads(json_path.read_text(encoding="utf-8"))
    assert geo.parse_geometry_text(text_path.read_text(encoding="utf-8")) == plan
    assert capsys.readouterr().out.startswith("P2_CAVE_GEOMETRY_READY ")


@pytest.mark.skipif(not L44_ROOMS.exists(), reason="lane-44 rooms artifact not present")
def test_lane44_rooms_round_trips(tmp_path):
    rooms = json.loads(L44_ROOMS.read_text(encoding="utf-8"))
    plan = geo.build_geometry(rooms, models={}, model_root=tmp_path)

    assert [node["id"] for node in plan["nodes"]] == [unit["id"] for unit in rooms["units"]]
    assert plan["geometry"] == "proxy"
    assert geo.parse_geometry_text(geo.geometry_text(plan)) == plan
