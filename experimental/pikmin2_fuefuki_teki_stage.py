"""Stage a generated Fuefuki (Antenna Beetle) vehicle arena (#245).

Produces a private room-preview run directory whose generated `.gen` includes a
P1 TEKI_Napkid (type 11, the flying placement vehicle pattern used by Fuefuki)
plus the standard red-Pikmin squad and a cargo-enabled Research Pod, so
GameCoreSection::finalSetup binds that generated actor to the lane-28 Fuefuki
host (`pc_p2_hardlanes`) and a killed vehicle's carcass can be credited by the
Pod as `corpse:...fuefuki:<gen>`.

Mirrors `pikmin2_bombsarai_teki_stage.py`. The Napkid is a placement vehicle
only: Fuefuki identity (EnemyID 41) is NOT claimed by the P1 actor; the sidecar
is what routes its position into the lane's nine-state FSM.

The room preview's staged `pr05` treasure actor (`preview treasure bolt`) is the
Pod anchor, so a `p2-pod.txt` alone enables the receipt path. No
`p2-cargo-free.txt` is written (cargo-free aborts on real cargo).
"""
import argparse
import shutil
from pathlib import Path
import struct

from scripts.preview_pikmin2_room import prepare as room_prepare, records

NAPKID_TYPE = 11  # TEKI_Napkid (Swooping Snitchbug), flying placement vehicle
SIDECAR_MAGIC = 'P2_FUEFUKI_TEKI_1'
DEFAULT_GENERATOR = 245001
# Cargo-enabled Research Pod (`P2_POD_1 <id> <value> <weight> <capacity>` then
# `<corpse_id> <corpse_value>`). Format matches the native reader.
POD_CARGO_PROFILE = 'P2_POD_1\nbolt 180 15 25\nKochappy 2\n'
# Spawn near the red-Pikmin squad so the grounded vehicle is inside the squad's
# attack volume; engineered placement, not production evidence.
DEFAULT_POSITION = (-110.0, 20.0, 0.0)


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
    row[16:48] = b'Fuefuki Napkid vehicle'.ljust(32, b'\0')
    row[80] = NAPKID_TYPE
    struct.pack_into('>6f', row, 48, float(position[0]), float(position[1]),
                     float(position[2]), 0.0, 0.0, 0.0)
    # Drop the staged control dwarf bulborb: it is an unrelated hostile that eats
    # squad Pikmin, and the dead-Pikmin `pr01` number pellets it creates are
    # unregistered cargo the preview Pod aborts on. Fixture concession.
    kept = [r for r in entries if r is not enemy]
    # data[:20] is the '1.0v' + stage spawn (4 floats); data[20:24] is the
    # record count which must be re-emitted to include the appended row.
    rebuilt = data[:20] + struct.pack('>I', len(kept) + 1) + b''.join(kept) + bytes(row)
    gen_path.write_bytes(rebuilt)
    return rebuilt


def copy_pose_bank(pose_stage, run):
    """Overlay the converted Fuefuki pose bank + motion/visual profile.

    Optional: without it the host FSM parks in Land and does not whistle-steal
    the attackers, which keeps the squad on the kill for the receipt fixture.
    """
    pose_stage = Path(pose_stage)
    visual = pose_stage / 'p2-fuefuki-visual.txt'
    motion = pose_stage / 'p2-fuefuki-motion.txt'
    if not visual.exists() or not motion.exists():
        raise ValueError('Pose stage is missing the Fuefuki visual/motion profile')
    shutil.copyfile(visual, run / 'p2-fuefuki-visual.txt')
    shutil.copyfile(motion, run / 'p2-fuefuki-motion.txt')
    source = pose_stage / 'assets' / 'dataDir' / 'courses' / 'pikmin2room'
    if not source.is_dir():
        raise ValueError('Pose stage is missing the converted pose mods')
    dest = run / 'assets' / 'dataDir' / 'courses' / 'pikmin2room'
    dest.mkdir(parents=True, exist_ok=True)
    for pose in sorted(source.glob('*.mod')):
        shutil.copyfile(pose, dest / pose.name)


def stage(assets, converted, output, generator=DEFAULT_GENERATOR,
          position=DEFAULT_POSITION, pose_stage=None):
    run = room_prepare(Path(assets).resolve(), Path(converted).resolve(), Path(output))
    gen = run / 'assets' / 'dataDir' / 'stages' / 'chal0' / 'default.gen'
    append_napkid(gen, generator, position)
    (run / 'p2-fuefuki-teki.txt').write_text(
        '{magic} {generator} {type}\n'.format(magic=SIDECAR_MAGIC,
                                               generator=generator,
                                               type=NAPKID_TYPE),
        encoding='ascii')
    # Cargo-enabled Pod so the corpse receipt path is reachable at all. No
    # p2-cargo-free.txt: cargo-free aborts on real cargo.
    (run / 'p2-pod.txt').write_text(POD_CARGO_PROFILE, encoding='ascii')
    if pose_stage:
        copy_pose_bank(pose_stage, run)
    return run


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--converted', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--generator', type=int, default=DEFAULT_GENERATOR)
    parser.add_argument('--pose-stage', type=Path, default=None)
    args = parser.parse_args()
    print(stage(args.assets, args.converted, args.output, args.generator,
                pose_stage=args.pose_stage))
