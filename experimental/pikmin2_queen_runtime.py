"""#256 Queen sampled-actor runtime fixture: build, stage, run, validate.

Mirrors the #235 noninteractive display harness but drives the interactive
P2_QUEEN_ACTOR_1 actor (pc_port/pc_p2_queen.cpp). The Queen is placed inside
the 5 red / 5 blue starting squad so the actor-local receivers engage without
any scripted input: stuck Pikmin trigger Flick, Flick starts Rolling, Rolling
presses squad Pikmin, the territory bound crashes the pass, and the birth
interval spawns a larva. Runs self-terminate at a bounded frame.
"""
import argparse
import json
import os
import re
import struct
import subprocess
import uuid
from pathlib import Path

from scripts import build_pikmin2_fixture as builder
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
from experimental.pikmin2_queen_actor import protocol

APP = r'''class QueenCameraTarget : public Creature {
public:QueenCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"Queen startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 if(ready==1){n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
 int red=0,blue=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else if(a->mColor==Blue)++blue;else++other;}}require(red==5&&blue==5&&other==0,"Queen starting5red5blue");
 std::ifstream holding("queen-keep-open.txt");hold=bool(holding);
 SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Empress Bulblax sampled actor (#256)");std::printf("P2_QUEEN_BASELINE red=%d blue=%d\n",red,blue);
 }
 if(ready==30){
 std::ifstream raw("queen-fixture-profile.txt");auto cfg=p2queen::readActorConfig(raw);require(cfg.placements.size()==1,"Queen single placement fixture");auto d=cfg.placements[0];
 float ground=mapMgr->getMinY(d.x,d.z,true);require(std::isfinite(ground)&&std::fabs(ground-d.y)<40,"Queen ground divergence");std::printf("P2_QUEEN_GROUND id=%u x=%.6f y=%.6f z=%.6f ground=%.6f yaw=%.3f\n",d.id,d.x,d.y,d.z,ground,d.yaw);
 require(cameraMgr&&cameraMgr->mCamera,"Queen camera missing");auto* target=new QueenCameraTarget();target->mSRT.t=Vector3f(d.x,d.y+85.f,d.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
 PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
 std::printf("P2_QUEEN_CAMERA target=%.6f,%.6f,%.6f\n",target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z);
 {std::ifstream src("queen-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-queen-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
 const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_queen_setup();gsys->setHeap(heap);
 }
 // Scenario 2: Queen isolated from the squad so the birth cycle runs without
 // stuck Pikmin (Flick correctly outranks Born while Pikmin stay stuck).
 if(ready==300){pc_p2_queen_reset();{std::ifstream src("queen-fixture-profile2.txt",std::ios::binary);std::ofstream dst("p2-queen-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_queen_setup();gsys->setHeap(heap);std::puts("P2_QUEEN_SCENARIO2 isolated_birth_cycle");}
 if(ready==630)capture("queen-actor.ppm");
 if(ready==640){pc_p2_queen_reset();std::puts("P2_QUEEN_RESET_REQUEST");}
 if(ready==645){capture("queen-reset.ppm");const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_queen_setup();gsys->setHeap(heap);std::puts("P2_QUEEN_RELOAD_REQUEST");}
 if(ready==700){capture("queen-reload.ppm");std::puts("PASS P2_QUEEN_ACTOR_RUNTIME bounded_frames");std::fflush(nullptr);if(!hold)std::_Exit(0);}
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <fstream>\n#include <string>\n#include "pc_p2_queen.h"\n#include "pc_p2_queen_policy.h"\n'
                '#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n')
    return includes + source[:start] + APP + source[end:]


def build(native, build_dir, output, head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'tutorial-private.inc').write_text(
        instrument_tutorial((native / 'src/plugPikiColin/newPikiGame.cpp').read_text(encoding='utf-8')),
        encoding='utf-8')
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(encoding='utf-8'))
                    + '\n#include "tutorial-private.inc"\n', encoding='utf-8')
    return builder.build_fixture(build_dir, native, room, output / 'build', head)


def queen_profile(profile):
    """P2_QUEEN_ACTOR_1 config + model bytes from the #235 sampled bank profile."""
    profile = Path(profile)
    meta = json.loads((profile / 'bulblax-visual.json').read_bytes())
    if meta.get('kind') != 'bulblax_sampled_display':
        raise ValueError('Unsupported bank profile')
    wanted = [('Queen', n) for n in ('dead', 'sleep', 'wait1', 'damage', 'flick', 'rolling_l', 'rolling_r', 'born')]
    wanted += [('Baby', n) for n in ('born', 'move', 'dead')]
    clips = []
    files = {}
    for species, name in wanted:
        clip = next((c for c in meta['clips'] if c['species'] == species and c['name'] == name), None)
        if clip is None:
            raise ValueError('Bank profile lacks %s/%s' % (species, name))
        clips.append(dict(species=species, name=name, duration=clip['duration'], frames=clip['frames']))
        for i in range(len(clip['frames'])):
            fname = 'bulblax_%s_%s_%02d.mod' % (species, name, i)
            data = (profile / 'models' / fname).read_bytes()
            if builder.sha256(profile / 'models' / fname) != meta['files'][fname]:
                raise ValueError('Model identity mismatch')
            files[fname] = data
    placement = dict(placement_id=230010, variant='default', larvae=True, xyz=[34, 30, 1896], yaw=0)
    config = protocol(clips, [placement])
    isolated = dict(placement_id=230011, variant='default', larvae=True, xyz=[34, 30, 1200], yaw=0)
    config2 = protocol(clips, [isolated])
    return config, config2, files, [placement, isolated]


def stage(assets, profile, output):
    assets = Path(assets).resolve()
    source = assets / 'dataDir/stages/practice/default.gen'
    data = source.read_bytes()
    entries = records(source)
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    template = next(r for r in rows if r[72:76] == b'ikip')
    for i in range(10):
        row = bytearray(template)
        struct.pack_into('<I', row, 8, 235100 + i)
        row[16:48] = b'Queen5red5blue fixture'.ljust(32, b'\0')
        write_position(row, [10 + i % 5 * 12, 30, 1890 + i // 5 * 12])
        struct.pack_into('>I', row, 92, 1 if i < 5 else 0)
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/private-queen.txt': b'Queen sampled actor fixture\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    config, config2, files, placements = queen_profile(profile)
    room = run / 'assets/dataDir/courses/pikmin2room'
    for name, blob in files.items():
        (room / name).write_bytes(blob)
    (run / 'queen-fixture-profile.txt').write_bytes(config)
    (run / 'queen-fixture-profile2.txt').write_bytes(config2)
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    original = {str(p.relative_to(assets)): builder.sha256(p)
                for p in (assets / 'dataDir/courses/practice').rglob('*') if p.is_file()}
    for rel, digest in original.items():
        if builder.sha256(run / 'assets' / rel) != digest:
            raise ValueError('Course changed')
    (run / 'queen-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 Impact Site', interactive=True, starting_squad={'red': 5, 'blue': 5},
             placements=placements, config_sha256=builder.sha256(run / 'queen-fixture-profile.txt'),
             course_sha256=original), indent=2) + '\n').encode())
    return run


def validate(text, code):
    states = re.findall(r'P2_QUEEN_STATE id=\d+ from=(\d+) to=(\d+)', text)
    transitions = {(int(a), int(b)) for a, b in states}
    checks = dict(
        completion=code == 0 and 'PASS P2_QUEEN_ACTOR_RUNTIME' in text,
        baseline='red=5 blue=5' in text,
        ground=text.count('P2_QUEEN_GROUND ') == 1,
        ready=text.count('P2_QUEEN_READY id=230010 enemy=30') >= 1,
        reload_ready=text.count('P2_QUEEN_READY ') >= 3,  # scenario 1 + scenario 2 + reload
        wait_to_damage=(2, 3) in transitions or (2, 4) in transitions,
        flick_entry=(3, 4) in transitions or (2, 4) in transitions,  # Flick outranks Damage/Born when stuck
        flick_to_rolling=(4, 5) in transitions,
        rolling_to_wait=(5, 2) in transitions or (5, 3) in transitions,
        flick_event='P2_QUEEN_FLICK id=230010' in text,
        crash='P2_QUEEN_CRASH id=230010' in text,
        press='P2_QUEEN_PRESS id=230010' in text,
        ignore_atari='P2_QUEEN_IGNORE_ATARI id=230010' in text,
        larva_spawn=bool(re.search(r'P2_QUEEN_LARVA id=\d+ xyz=', text)),
        reset=text.count('P2_QUEEN_RESET_REQUEST') == 1,
        reload=text.count('P2_QUEEN_RELOAD_REQUEST') == 1,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_COLLECT' not in text,
    )
    return dict(passed=all(checks.values()), checks=checks, transitions=sorted(transitions), exit_code=code,
                scope='Sampled actor fixture; Baby captain attack damage deferred (UNTESTED)')


def run(assets, profile, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, profile, output / 'queen')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    with (directory / 'native.log').open('w') as log:
        try:
            code = subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory,
                                  env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    # No game process may remain.
    leftovers = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq %s' % Path(exe).name], capture_output=True,
                               text=True).stdout
    text = (directory / 'native.log').read_text(errors='replace')
    evidence = validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['no_leftover_process'] = Path(exe).name not in leftovers
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('queen', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, profile, output, exe):
    directory = stage(assets, profile, output)
    (directory / 'queen-keep-open.txt').write_bytes(b'Sampled Queen actor; close window to exit.\n')
    print('Empress Bulblax sampled actor fixture.\n' + str(directory), flush=True)
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    with (directory / 'native.log').open('w') as log:
        return subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory, env=env,
                              stdout=log, stderr=subprocess.STDOUT).returncode


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for key in ('native', 'build-dir', 'output'):
        b.add_argument('--' + key, type=Path, required=True)
    b.add_argument('--head', required=True)
    for parser in (sub.add_parser('run'), sub.add_parser('play')):
        for key in ('assets', 'profile', 'output', 'exe'):
            parser.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native.resolve(), a.build_dir.resolve(), a.output, a.head)
    elif a.command == 'run':
        evidence = run(a.assets, a.profile, a.output, a.exe)
        raise SystemExit(0 if evidence['passed'] else 1)
    else:
        raise SystemExit(play(a.assets, a.profile, a.output, a.exe))
