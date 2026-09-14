"""Build and run the Giant Breadbug actor arena fixture (#220 batch 4).

Builds the private fixture against a completed private-worktree Ninja build
(never the shared checkout), stages the private arena and validates the native
log gates: spawn identity/params, Purple-only press, PelletCarry contest,
hide-digest heal, defeat throw-up and owner-linked nest birth/death.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_giant_breadbug_arena import prepare, GIANT_ID, NEST_ID

ROOT = Path(__file__).resolve().parent.parent
# Prefix comes from the pinned native source, not another lane's ignored output.

GATES = {
    'actor_ready': r'P2_GIANT_BREADBUG_ACTOR_READY generator=%d nest=%d native_type=8 .*boss=1 bdt=empty_no_music threshold=at_or_above1 health=2000 carryspeed=45 pressdamage=100' % (GIANT_ID, NEST_ID),
    'nest_birth': r'P2_GIANT_NEST_BIRTH generator=%d ' % NEST_ID,
    'squad': r'P2_GIANT_ARENA_SQUAD count=20 color=red health=2000\.0',
    'press_resist_module': r'P2_GIANT_PRESS generator=%d purple=0 resisted=1 health=2000\.0' % GIANT_ID,
    'press_purple_module': r'P2_GIANT_PRESS generator=%d purple=1 damage=100 health=1900\.0' % GIANT_ID,
    'press_gate': r'P2_GIANT_ARENA_PRESS non_purple=resisted purple_damage=100 health=1900\.0',
    'contest_module': r'P2_GIANT_CONTEST_LOST generator=%d carriers=2 strength=1\.5 freeze=0\.5s' % GIANT_ID,
    'contest_gate': r'P2_GIANT_ARENA_CONTEST released=1 ',
    'digest_module': r'P2_GIANT_DIGEST generator=%d ' % GIANT_ID,
    'digest_heal_module': r'P2_GIANT_DIGEST_HEAL generator=%d health=2000\.0' % GIANT_ID,
    'digest_gate': r'P2_GIANT_ARENA_DIGEST healed=1 health=2000\.0',
    'defeated_module': r'P2_GIANT_DEFEATED generator=%d thrown_back=\d+' % GIANT_ID,
    'throwup_module': r'P2_GIANT_THROWUP generator=%d pellets=\d+ ' % GIANT_ID,
    'throwup_gate': r'P2_GIANT_ARENA_THROWUP pellets=\d+ ',
    'nest_death': r'P2_GIANT_NEST_DEATH generator=%d' % NEST_ID,
    'draw': r'P2_GIANT_BREADBUG_ACTOR_DRAW generator=%d scale=2 texture_matrix_animation=gap_static_frames' % GIANT_ID,
    'pass': r'PASS P2_GIANT_BREADBUG_ARENA spawn_identity press contest digest_heal defeat_throwup nest_linked',
}


def build(native, build_dir, output, head):
    native, build_dir, output = native.resolve(), build_dir.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    fixture = output / 'fixture.cpp'
    fixture.write_text((ROOT / 'scripts/pikmin2_giant_breadbug_actor_fixture.cpp').read_text())
    source = (native / 'tools/preview_p2_room.cpp').read_text()
    anchor = 'class RoomApp : public PlugPikiApp {'
    if source.count(anchor) != 1:
        raise ValueError('Room fixture prefix boundary changed')
    (output / 'room-prefix.inc').write_text(source[:source.index(anchor)])
    record = builder.build_fixture(build_dir, native, fixture, output / 'baseline', head)
    compile_cmd = list(record['commands'][-2])
    link = list(record['commands'][-1])
    link[builder.option_index(link, '-o')] = str(output / 'fixture.exe')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    code, text = builder.run_command(link, build_dir, env, output, 'fixture-link')
    (output / 'fixture-link.log').write_text(text)
    if code:
        raise RuntimeError('fixture link failed')
    return output / 'fixture.exe'


def evidence(text, code):
    checks = {name: bool(re.search(pattern, text)) for name, pattern in GATES.items()}
    return dict(passed=code == 0 and all(checks.values()), checks=checks, exit_code=code)


def run(args):
    exe = args.exe
    if exe is None:
        exe = build(args.native, args.build_dir, args.output / 'build', args.head)
    stage = prepare(args.assets, args.profile, args.purple, args.pod, args.output / 'stages')
    env = dict(os.environ, SDL_AUDIODRIVER='dummy')
    env['PATH'] = 'C:/msys64/mingw64/bin;' + env['PATH']
    with (stage / 'host.log').open('w') as out:
        native = subprocess.run([str(exe), '--experimental-pikmin2-room'], cwd=stage, env=env,
                                stdout=out, stderr=subprocess.STDOUT, timeout=args.timeout)
    text = (stage / 'host.log').read_text(errors='replace')
    result = dict(executable=builder.snapshot([exe]), directory=str(stage),
                  evidence=evidence(text, native.returncode),
                  scope='P1-bound Giant actor; P1 FSM locomotion/cargo retained; P1 collision scale retained',
                  gaps=['texture-matrix animation (static sampled frames)',
                        'nest treasure day-save persistence (engine owner)',
                        'manager lifetimes (engine owner)'])
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for k in ('assets', 'profile', 'purple', 'pod', 'output'):
        p.add_argument('--' + k, type=Path, required=True)
    p.add_argument('--exe', type=Path)
    p.add_argument('--native', type=Path)
    p.add_argument('--build-dir', type=Path)
    p.add_argument('--head')
    p.add_argument('--timeout', type=int, default=170)
    a = p.parse_args()
    for k, v in vars(a).items():
        if isinstance(v, Path):
            setattr(a, k, v.resolve())
    if a.exe is None and not (a.native and a.build_dir and a.head):
        p.error('either --exe or --native/--build-dir/--head required')
    if not re.fullmatch(r'[0-9a-f]{40}', a.head or '0' * 40) and a.exe is None:
        p.error('invalid --head')
    if not 1 <= a.timeout <= 180:
        p.error('timeout must be 1..180')
    a.output.mkdir(parents=True, exist_ok=False)
    run(a)
