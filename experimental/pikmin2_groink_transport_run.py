"""Stage and run the lane-21 Groink carcass transport GL scenario (#198).

The generated host is the lane-16 staged Frog arena (generator 201001 `Frog`;
the `MaroFrog` 201002 is a second actor in the same stage). This runner copies
that base session, writes a `transport` Groink carcass sidecar and stages the
Research Pod cargo, then launches the lane's private fixture under
``--carcass-transport``.

The carcass carry is natural: the native sidecar
(``pc_port/pc_p2_groink_teki.cpp``) parks the captain and re-rings the survivors
in FreeMode onto the host's own corpse pellet until one latches; the Pod is the
``aiTransport`` goal (``pc_p2_preview_goal()``) and ``pc_p2_preview_deliver``
credits ``corpse:groink:<gen>``. No delivery endpoint is called directly.

Fixture concessions (labelled): the base session's 20-red squad is expanded to
40 (the host's own area attack otherwise thins the squad before the carry
completes; lane-27 recipe), the base is a lane-16 run output rather than a
regenerated arena, and the carcass ``carry_min`` is forced to 1 by the sidecar.
"""
import argparse
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from scripts.preview_pikmin2_room import records  # noqa: E402
from experimental.pikmin2_mamuta_rules import stage_cargo  # noqa: E402

DEFAULT_BASE = Path('C:/Users/alari/pikmin-randomizer/output/dsw/l16-out/run-runtime/stages/'
                    '1a2f21ebde494a0eb4986841b5446131')
DEFAULT_ASSETS = Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
DEFAULT_POD = Path('C:/Users/alari/pikmin-randomizer/output/dsw/l13-out/pod')
DEFAULT_FIXTURE = Path('C:/Users/alari/pikmin-randomizer/output/dsw/l21-out/groink-transport-fixture')
DEFAULT_OUTPUT = Path('C:/Users/alari/pikmin-randomizer/output/dsw/l21-out/run-carcass-transport3')

# A huge gauge delay means the carcass policy never reaches KillPellet, so the
# dropped corpse survives for the free squad to carry to the Pod. The trailing
# `transport` token turns on the native carcass tail.
SIDECAR = 'P2_GROINK_TEKI_1\n1\n201001 0 100000.0 10.0 1200.0 transport\n'


def expand_squad(gen_path, count):
    """Append `count - existing` red-Pikmin squad records to a staged generator."""
    data = gen_path.read_bytes()
    entries = records(gen_path)
    squad = [r for r in entries if r[16:48].startswith(b'fixture starting squad')]
    if not squad:
        raise ValueError('no squad template in staged generator')
    used = {struct.unpack_from('<I', r, 8)[0] for r in entries}
    next_id = max(used)
    extra = []
    while len(squad) + len(extra) < count:
        next_id += 1
        row = bytearray(squad[len(extra) % len(squad)])
        struct.pack_into('<I', row, 8, next_id)
        x = -140.0 + (len(extra) % 10) * 8.0
        z = 1800.0 - (len(extra) // 10) * 8.0
        struct.pack_into('>6f', row, 48, x, 30.0, z, 0.0, 0.0, 0.0)
        extra.append(bytes(row))
    if not extra:
        return 0
    gen_path.write_bytes(data[:20] + struct.pack('>I', len(entries) + len(extra))
                         + b''.join(entries) + b''.join(extra))
    return len(extra)


def stage(base, assets, pod, output, squad=40):
    if output.exists():
        raise SystemExit('run directory already exists: ' + str(output))
    if not (base / 'assets').is_dir():
        raise SystemExit('missing base-session assets: ' + str(base / 'assets'))
    output.mkdir(parents=True)
    shutil.copytree(base / 'assets', output / 'assets')
    shutil.copy2(base / 'p2-frog.txt', output / 'p2-frog.txt')
    (output / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n', encoding='ascii')
    (output / 'p2-groink-teki.txt').write_text(SIDECAR, encoding='ascii')
    added = expand_squad(output / 'assets/dataDir/stages/chal0/default.gen', squad)
    info = stage_cargo(output, assets, pod)
    return {'added_pikmin': added, 'squad': squad, 'pod': info.get('treasure')}


def run(fixture, output, timeout=330, extra=()):
    exe = fixture / 'fixture.exe'
    if not exe.is_file():
        raise SystemExit('missing fixture: ' + str(exe))
    env = os.environ.copy()
    env['PATH'] = 'C:/msys64/mingw64/bin;' + env['PATH']
    env['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    env['PYTHONUTF8'] = '1'
    with (output / 'native.log').open('w', encoding='utf-8') as log:
        completed = subprocess.run([str(exe), '--experimental-pikmin2-room', '--carcass-transport', *extra],
                                   cwd=output, env=env, stdout=log, stderr=subprocess.STDOUT,
                                   timeout=timeout)
    return completed.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=DEFAULT_BASE)
    parser.add_argument('--assets', type=Path, default=DEFAULT_ASSETS)
    parser.add_argument('--pod', type=Path, default=DEFAULT_POD)
    parser.add_argument('--fixture', type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--squad', type=int, default=40)
    parser.add_argument('--timeout', type=int, default=330)
    parser.add_argument('--stage-only', action='store_true')
    args = parser.parse_args()
    info = stage(args.base, args.assets, args.pod, args.output, args.squad)
    print('staged', info, flush=True)
    if not args.stage_only:
        print('returncode', run(args.fixture, args.output, args.timeout), flush=True)
