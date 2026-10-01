"""Original tutorial day-five Red encounter on complete imported terrain (#1150)."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

from experimental.pikmin2_kochappy_bank import install
from scripts.preview_pikmin2_room import records
from scripts.stage_pikmin2_surface_water import prepare as prepare_water

ENEMY_UID = 0x50323101
ONION_UID = 0x50324F01
ENEMY_POSITION = (-1153.361206, 47.871529, 2231.686035)
ONION_POSITION = (-225.018997, 0.0, 2784.604980)
# Only starting captain/squad are engineering placements; retail actors stay exact.
START = (-1023.361206, 87.871529, 2231.686035)


def source_selection(bundle, day):
    if type(day) is not int or not 5 <= day <= 29:
        raise ValueError("The original nonloop schedule is days5..29 only")
    inventory = json.loads((bundle / "surface-generators.json").read_text(encoding="utf8"))
    enemy = inventory["nonloop/5-29.txt"]["actors"][0]
    onion = inventory["defaultgen.txt"]["actors"][1]
    if (enemy["kind"] != "teki" or enemy["index"] != 0 or enemy["reserved"] != 5
            or enemy["respawn_days"] != 3 or tuple(enemy["effective_position"]) != ENEMY_POSITION):
        raise ValueError("Original day-five encounter identity/placement changed")
    if (onion["kind"] != "item" or onion["item"] != "onyn" or onion["onion_index"] != 1
            or onion["after_boot"] != 1 or tuple(onion["effective_position"]) != ONION_POSITION):
        raise ValueError("Original booted Red Onion identity/placement changed")
    raw = (bundle / "generators/nonloop/5-29.txt").read_bytes()
    # The imported inventory retains positions but not teki payload. Verify the
    # actual first raw record's sourceID/version/count/facing/radius before use.
    text = raw.decode("shift_jis")
    first = text.split("{teki}", 1)[1].split("{????}", 1)[0]
    clean = "\n".join(line.split("#", 1)[0] for line in first.splitlines())
    tokens = clean.split()
    expected = ["{0005}", "1", "0", "1", "0.000000", "1", "100.000000",
                "0.000000", "0", "3", "1", "1", "2", "0.400000"]
    if tokens != expected:
        raise ValueError("Unsupported source1 generator payload; do not substitute a proxy")
    return enemy, onion, hashlib.sha256(raw).hexdigest()


def positioned(row, uid, position, label):
    result = bytearray(row)
    if result[:8] != b"    0.0v" or len(result) < 81:
        raise ValueError("Unsupported native generator template")
    struct.pack_into(">I", result, 8, uid)
    result[16:48] = label.encode("ascii").ljust(32, b"\0")
    struct.pack_into(">6f", result, 48, *position, 0, 0, 0)
    return result


def encounter_generator(assets, original_squad):
    practice = records(assets / "dataDir/stages/practice/default.gen")
    challenge = records(assets / "dataDir/stages/chal0/default.gen")
    if practice[1][16:24] != b"red goal" or challenge[9][72:76] != b"iket":
        raise ValueError("Unexpected native Onion/teki framing")
    onion = positioned(practice[1], ONION_UID, ONION_POSITION, "P2 tutorial original Red Onion")
    enemy = positioned(challenge[9], ENEMY_UID, ENEMY_POSITION, "P2 original day5 Kochappy1")
    enemy[80] = 3  # Native TEKI_Chappy scaffold; explicit imported Red1 bank/FSM owns it.
    type_start = enemy.index(b"nota0.0v", 80)
    count_start = enemy.index(b"p00\x04", type_start) + 4
    if struct.unpack_from(">I", enemy, count_start)[0] != 2:
        raise ValueError("Unexpected pair template")
    struct.pack_into(">I", enemy, count_start, 1)
    starts = [m.start() for m in re.finditer(b"    0.0v", original_squad)] + [len(original_squad)]
    rows = []
    for i, (a, b) in enumerate(zip(starts, starts[1:])):
        row = original_squad[a:b]
        if row[72:76] != b"ikip":
            raise ValueError("Expected only the current twenty-Pikmin overlay")
        rows.append(positioned(row, i + 1, (START[0] - 12 + (i % 5)*6, START[1], START[2] - 9 + (i // 5)*6), "P2 twenty Red baseline"))
    if len(rows) != 20:
        raise ValueError("Expected current20 starting Red Pikmin")
    rows += [onion, enemy]
    return b"1.0v" + struct.pack(">4fI", *START, 0, len(rows)) + b"".join(rows)


def prepare(assets, bundle, identity, bank, output, day=5):
    enemy, onion, raw_sha = source_selection(bundle, day)
    run = prepare_water(assets, bundle, identity, output)
    path = run / "assets/dataDir/stages/p2_tutorial/default.gen"
    path.write_bytes(encounter_generator(assets, path.read_bytes()))
    for name in ("init.gen", "plants.gen", "day.gen"):
        (path.parent / name).write_bytes(b"1.0v" + struct.pack(">4fI", *START, 0, 0))
    stage = run / "assets/dataDir/stages/p2_tutorial.ini"
    stage.write_bytes(re.sub(rb"(?m)^navi_start[^\r\n]*", ("navi_start %.6f %.6f" % (START[0], START[2])).encode(), stage.read_bytes()))
    destination = run / "assets/dataDir/courses/pikmin2room"
    if not destination.parent.resolve().is_relative_to(run.resolve()):
        raise ValueError("Refusing bank through shared asset parent")
    if destination.exists() and (destination.is_symlink() or destination.is_junction()):
        raise ValueError("Refusing bank through shared asset junction")
    destination.mkdir(exist_ok=True)
    install(bank, run, [ENEMY_UID])
    (run / "p2-dwarf-red-fsm.txt").write_text("P2_DWARF_RED_FSM_1\n", encoding="ascii")
    result = dict(schema=1, source_id=1, source_species="Kochappy", day=day,
                  schedule="nonloop/5-29.txt", source_reserved=5, respawn_days=3,
                  source_enemy=enemy, source_onion=onion, generator_id=ENEMY_UID,
                  source_raw_sha256=raw_sha, full_source_route_graph=True,
                  source_spawn_adaptation="fixed original generator center inside retail100-radius circle; no retail RNG claim",
                  source_yaw=0, onion_source_yaw=onion["rotation"][1],
                  onion_rotation_admitted=False, starting_squad="20 native Red1 near captain, engineering placement",
                  captain_start=START, source_fsm_optin=True, other_retail_generators_imported=False,
                  native_goal_visual="P1 Red Onion scaffold at original retail coordinates",
                  source_generator_loot_parity=False, playable_acceptance=False)
    result["inputs_sha256"] = {name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in
         ("assets/dataDir/stages/p2_tutorial/default.gen", "assets/dataDir/courses/p2tutorial/full.mod",
          "assets/dataDir/courses/p2tutorial/full.ini", "assets/dataDir/courses/p2tutorial/full.water", "p2-dwarf-red-fsm.txt")}
    (run / "tutorial-encounter-inputs.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    return run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("assets", "bundle", "bank", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--identity", required=True)
    parser.add_argument("--day", type=int, default=5)
    args = parser.parse_args()
    print(prepare(args.assets.resolve(), args.bundle.resolve(), args.identity, args.bank.resolve(), args.output.resolve(), args.day))
