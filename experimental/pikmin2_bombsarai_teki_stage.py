"""Stage a generated BombSarai carrier (Napkid vehicle) arena (#244).

Produces a private room-preview run directory whose generated `.gen` includes a
P1 TEKI_Napkid (type 11, the flying placement vehicle pattern used by Fuefuki)
plus the standard 20-red squad, and a `p2-bombsarai-teki.txt` sidecar so
GameCoreSection::finalSetup binds that generated actor to the lane-27 BomSarai
carrier adapter. Everything the run needs comes from this emitter and the
read-only P1 asset tree + converted P2 room; no hand-edited run-dir profiles.

The Napkid is a placement vehicle only: BombSarai identity (EnemyID 58) is NOT
claimed by the P1 actor; the sidecar is what routes its position into the lane's
13-state carrier FSM.
"""
from pathlib import Path
import struct
import uuid

from scripts.preview_pikmin2_room import prepare as room_prepare, records

NAPKID_TYPE = 11  # TEKI_Napkid (Swooping Snitchbug), flying placement vehicle
SIDECAR_MAGIC = 'P2_BOMBSARAI_TEKI_1'
DEFAULT_GENERATOR = 270001
# Cargo-enabled Research Pod so a killed carrier's corpse can be credited
# (`P2_POD_RECEIPT id=corpse:...bombsarai:<gen>`). The room preview already
# stages a `pr05` treasure actor (`preview treasure bolt`), so a `p2-pod.txt`
# alone enables the Pod; without it `pc_p2_preview_goal()` is null and
# `pc_p2_preview_deliver` is never entered (the lane-27 receipt branch is dead).
# Format matches the native reader: P2_POD_1 <id> <value> <weight> <capacity>
# Kochappy <corpse_value>.
POD_CARGO_PROFILE = 'P2_POD_1\nbolt 180 15 25\nKochappy 2\n'
# Spawn near the red-Pikmin squad so ordinary Pikmin can attack and kill the
# vehicle after it has thrown; engineered placement, not production evidence.
DEFAULT_POSITION = (-90.0, 30.0, 10.0)


def append_napkid(gen_path, generator, position):
    """Append a Napkid (type 11) enemy record to the staged default.gen."""
    data = gen_path.read_bytes()
    entries = records(gen_path)
    # Reuse the dwarf-bulborb 'iket' enemy record as the row template; its
    # native teki-type byte is at offset 80 (generator v10 byte enum).
    enemy = next((r for r in entries if r[72:76] == b'iket'), None)
    if enemy is None:
        raise ValueError('No iket enemy record template in staged generator')
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    if generator in used:
        raise ValueError('Generator ID collision: ' + str(generator))
    row = bytearray(enemy)
    struct.pack_into('<I', row, 8, generator)
    row[16:48] = b'BombSarai Napkid vehicle'.ljust(32, b'\0')
    row[80] = NAPKID_TYPE
    struct.pack_into('>6f', row, 48, float(position[0]), float(position[1]),
                     float(position[2]), 0.0, 0.0, 0.0)
    # data[:20] is the '1.0v' + stage spawn (4 floats); data[20:24] is the
    # record count which must be re-emitted to include the appended row.
    rebuilt = data[:20] + struct.pack('>I', len(entries) + 1) + b''.join(entries) + bytes(row)
    gen_path.write_bytes(rebuilt)
    return rebuilt



def stage(assets, converted, output, generator=DEFAULT_GENERATOR, position=DEFAULT_POSITION, reds=40):
    # The carrier's area bombs otherwise wipe the shared 20-red default squad
    # before it can be killed; lane 27 opts in to 40 so survivors are left to
    # haul the carcass (see preview_pikmin2_room.generator).
    run = room_prepare(Path(assets).resolve(), Path(converted).resolve(), Path(output), reds=reds)
    gen = run / 'assets' / 'dataDir' / 'stages' / 'chal0' / 'default.gen'
    append_napkid(gen, generator, position)
    (run / 'p2-bombsarai-teki.txt').write_text(
        '{magic} 1 {generator} {type}\n'.format(magic=SIDECAR_MAGIC,
                                                 generator=generator,
                                                 type=NAPKID_TYPE),
        encoding='ascii')
    # Cargo-enabled Pod so the corpse receipt path is reachable at all.
    (run / 'p2-pod.txt').write_text(POD_CARGO_PROFILE, encoding='ascii')
    return run


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--converted', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--generator', type=int, default=DEFAULT_GENERATOR)
    args = parser.parse_args()
    print(stage(args.assets, args.converted, args.output, args.generator))
