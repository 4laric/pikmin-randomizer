"""Stage a generated Kurage (Lesser Spotted Jellyfloat) arena for the Pod gate (#243).

Produces a private room-preview run directory whose generated `.gen` includes a
P1 TEKI_Frog (type 0, the grounded body vehicle used as the Kurage proxy) plus the
standard red squad, and a `p2-kurage-teki.txt` sidecar so
GameCoreSection::finalSetup binds that generated actor to the lane-29 Kurage
adapter. Everything the run needs comes from this emitter and the read-only P1
asset tree + converted P2 room; no hand-edited run-dir profiles.

The Frog is a body vehicle only: Kurage identity (source ID 57) is NOT claimed by
the P1 actor; the sidecar is what routes its lifecycle into the lane's corpse
receipt. This mirrors `experimental/pikmin2_bombsarai_teki_stage.py`.

A cargo Research Pod (`p2-pod.txt`) is staged so a killed proxy's corpse can be
credited (`P2_POD_RECEIPT id=corpse:kurage:<gen>`). The room preview already
stages a `pr05` treasure actor (`preview treasure bolt`), so `p2-pod.txt` alone
enables the Pod; without it `pc_p2_preview_goal()` is null and
`pc_p2_preview_deliver` is never entered, so the lane receipt branch is dead.
`p2-cargo-free.txt` must NOT be present (cargo-free aborts on real cargo).
"""
from pathlib import Path
import struct

from scripts.preview_pikmin2_room import prepare as room_prepare, records

FROG_TYPE = 0  # TEKI_Frog (Yellow Wollywog), grounded body vehicle proxy
SIDECAR_MAGIC = 'P2_KURAGE_TEKI_1'
DEFAULT_GENERATOR = 201001
# Cargo-enabled Research Pod (native reader format):
#   P2_POD_1 <id> <value> <weight> <capacity> Kochappy <corpse_value>
POD_CARGO_PROFILE = 'P2_POD_1\nbolt 180 15 25\nKochappy 2\n'
# Spawn near the red-Pikmin squad so ordinary Pikmin can attack and kill the
# proxy after the sidecar grounds it; engineered placement, not production data.
DEFAULT_POSITION = (-90.0, 30.0, 10.0)


def append_frog(gen_path, generator, position):
    """Append a TEKI_Frog (type 0) enemy record to the staged default.gen."""
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
    row[16:48] = b'Kurage frog vehicle'.ljust(32, b'\0')
    row[80] = FROG_TYPE
    struct.pack_into('>6f', row, 48, float(position[0]), float(position[1]),
                     float(position[2]), 0.0, 0.0, 0.0)
    # data[:20] is the '1.0v' + stage spawn (4 floats); data[20:24] is the
    # record count which must be re-emitted to include the appended row.
    rebuilt = data[:20] + struct.pack('>I', len(entries) + 1) + b''.join(entries) + bytes(row)
    gen_path.write_bytes(rebuilt)
    return rebuilt


def stage(assets, converted, output, generator=DEFAULT_GENERATOR, position=DEFAULT_POSITION):
    run = room_prepare(Path(assets).resolve(), Path(converted).resolve(), Path(output))
    gen = run / 'assets' / 'dataDir' / 'stages' / 'chal0' / 'default.gen'
    append_frog(gen, generator, position)
    (run / 'p2-kurage-teki.txt').write_text(
        '{magic} 1 {generator} {type}\n'.format(magic=SIDECAR_MAGIC,
                                                 generator=generator,
                                                 type=FROG_TYPE),
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
