"""Private batch-4 arena runtime probe (#352, #353, #312).

Builds a private instrumented ``preview_p2_room`` against the batch-4 native
build and validates the arena's spawn identity and effective XYZ for the three
batch-4 families, then exits. This is a spawn/identity/placement probe only: it
does not claim source FSM, combat, lifecycle or rewards.

Usage::

    py -3.12 -m experimental.pikmin2_batch2_runtime build \
        --native <native worktree> --build-dir <build> --output <dir> --head <sha>
    py -3.12 -m experimental.pikmin2_batch2_runtime run \
        --family waterwraith --assets <P1 assets> --imported <manifest dir> \
        --output <dir> --exe <fixture.exe>
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<15000,"batch4 startup timeout");
 if(frames%120==0){std::printf("P2_BATCH4_GATE frame=%d ready=%d pause=%d ui=%d movie=%d\n",frames,int(pc_p2_preview_cargo_free_ready()),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive));std::fflush(stdout);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
 std::ifstream input("batch4-positions.txt");
 unsigned id;int type,registered;float x,y,z;int count=0;
 while(input>>id>>type>>registered>>x>>y>>z){
  Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a&&a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
  require(matches==1,"batch4 identity");require(actor->mTekiType==type,"batch4 native type");
  Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
  require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"batch4 birth XYZ");
  require(std::fabs(gen.x-x)<.02&&std::fabs(gen.y-y)<.02&&std::fabs(gen.z-z)<.02,"batch4 generator XYZ");
  std::printf("P2_BATCH4_BIRTH id=%u type=%d registered=%d x=%.3f y=%.3f z=%.3f\n",id,type,registered,birth.x,birth.y,birth.z);++count;
 }
 require(count>0,"batch4 roster");
 std::printf("PASS P2_BATCH4_RUNTIME actors=%d\n",count);std::fflush(stdout);std::_Exit(0);
 return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    head = ('#include <fstream>\n#include "Generator.h"\n#include "TekiPersonality.h"\n'
            '#include "pc_p2_batch2.h"\n#include "pc_p2_long_legs.h"\n')
    return head + source[:start] + APP + source[end:]


def build(native, build_dir, output, head):
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text())
    room.write_text(source)
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe


def _arena(name, assets, imported, output):
    output = Path(output).resolve()
    if name == 'waterwraith':
        from experimental.pikmin2_waterwraith_arena import prepare
        return prepare(assets, imported, output)
    if name == 'flora':
        from experimental.pikmin2_flora_arena import prepare
        return prepare(assets, imported, output)
    if name == 'long-legs':
        from experimental.pikmin2_long_legs_arena import prepare
        return prepare(assets, imported, output)
    raise ValueError('Unknown batch-4 family: ' + name)


def run(name, assets, imported, output, exe, timeout=180):
    run_dir = _arena(name, assets, imported, output)
    if name == 'long-legs':
        from experimental.pikmin2_long_legs_visual import convert, verify
        room = run_dir / 'assets/dataDir/courses/pikmin2room'
        convert(room)
        verify(room)
    manifest = json.loads((run_dir / 'arena.json').read_text())
    control = manifest['control']
    rows = [f"{a['generator']} {a['native_teki_type']} {int(a['species'] != control)} "
            + ' '.join(str(v) for v in a['expected_xyz'])
            for a in manifest['actors']]
    (run_dir / 'batch4-positions.txt').write_text('\n'.join(rows) + '\n')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy')
    log = run_dir / 'native.log'
    with log.open('w') as stream:
        try:
            code = subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                  cwd=run_dir, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    text = log.read_text(errors='replace')
    births = re.findall(r'P2_BATCH4_BIRTH id=(\d+) type=(\d+) registered=(\d+)', text)
    evidence = dict(family=name, exit_code=code, run=str(run_dir),
                    pass_marker='PASS P2_BATCH4_RUNTIME' in text,
                    births=births, actors=len(manifest['actors']),
                    executable=builder.snapshot([Path(exe).resolve()]),
                    failures=re.findall(r'FAIL p2 room: (.*)', text))
    evidence['passed'] = bool(code == 0 and evidence['pass_marker']
                              and len(births) == len(manifest['actors']))
    (run_dir / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence))
    return evidence


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run')
    for n in ('assets', 'imported', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    r.add_argument('--family', required=True)
    r.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head)
    else:
        run(args.family, args.assets, args.imported, args.output, args.exe, args.timeout)
