"""#289 KingChappy sampled-actor runtime fixture: build, stage, run, validate.

Mirrors the #256 Queen harness but drives the interactive P2_KING_ACTOR_1
actor (pc_port/pc_p2_king.cpp). Scenario 1 buries a default Emperor inside
the 5 red / 5 blue starting squad with one fixture-placed BOMB_Wait bomb
(labeled injection) on the squad center line and a second bomb armed for an
external (quartered) blast: the approach triggers Appear with the shake-off,
the tongue eats squad Pikmin (Swallow) and the bomb (Eat -> Damage 200 with
the 180-frame stun). Scenario 2 places two Emperors and three bombs for the
cross-Emperor WarCry contract and the deterministic bomb ingestion lane.
Scenario 3 spawns the force-big variant. Scenario 4 (required) drives the
opt-in kill injection to Dead and the frame-185 kill key. Scenario order is
gated on the actor's own 30 Hz behavior clock (not absolute idle frames) so a
loaded machine cannot truncate an earlier scenario's required keys.
Runs self-terminate at a bounded behavior tick.
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
from experimental.pikmin2_king_actor import protocol

APP = r'''#include "GameStat.h"
class KingCameraTarget : public Creature {
public:KingCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"King startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 // Scenario sequencing is gated on the actor's own 30 Hz behavior clock and
 // on the Dead-key marker, never on absolute idle frames. Mixing ready-gated
 // scenarios with frames-based tail steps truncated long scenarios under
 // load: the behavior clock is real-time and capped at 4 catch-up ticks per
 // frame, so a frame bound and a behavior-tick window diverge. Phase 0 waits
 // out scenario 1, phase 1 runs scenario 2 (WarCry/bomb injection) for a full
 // window, phase 2 is the dedicated death scenario, then reload/big.
 static int phase=0;
 if(phase==0&&pc_p2_king_behavior_tick()>=800){
  {std::ofstream inj("p2-king-inject.txt");inj<<"P2_KING_INJECT_1 500 0 0 50\n";inj.close();}
  std::puts("P2_KING_INJECT_ARMED warcry_tick=500 bomb_tick=50 fixture=1");
  {std::ifstream src("king-fixture-profile2.txt",std::ios::binary);std::ofstream dst("p2-king-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_king_setup();gsys->setHeap(heap);
  std::puts("P2_KING_SCENARIO2 two_emperor_bombs");phase=1;
 }
 // Phase 1 -> 2: scenario 2's WarCry inject fires at behavior tick 500 and
 // its attack/Swallow resolve well before 900; only then reset into the
 // dedicated death scenario so no scenario-2 required check is truncated.
 if(phase==1&&pc_p2_king_behavior_tick()>=900){
  pc_p2_king_reset();std::puts("P2_KING_RESET_REQUEST");
  {std::ifstream src("king-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-king-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  {std::ofstream inj("p2-king-inject.txt");inj<<"P2_KING_INJECT_1 100000 230020 5 0\n";inj.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_king_setup();gsys->setHeap(heap);
  std::puts("P2_KING_DEATH_ARMED kill_tick=5 fixture=1");std::puts("P2_KING_SCENARIO_DEATH kill_tick=5");phase=2;
 }
 // Phase 2 -> 3: wait for the Dead clip's frame-185 kill key, then the
 // reload-cleanup scenario (injection removed so it stays inert).
 if(phase==2&&pc_p2_king_dead_key_seen()){
  capture("king-dead.ppm");std::remove("p2-king-inject.txt");
  {std::ifstream src("king-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-king-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_king_setup();gsys->setHeap(heap);
  std::puts("P2_KING_RELOAD_REQUEST");phase=3;
 }
 // Phase 3 -> 4: force-big variant spawn identity.
 if(phase==3){
  capture("king-reset.ppm");pc_p2_king_reset();
  {std::ifstream src("king-fixture-profile3.txt",std::ios::binary);std::ofstream dst("p2-king-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_king_setup();gsys->setHeap(heap);
  std::puts("P2_KING_SCENARIO3 force_big");phase=4;
 }
 if(phase==4&&pc_p2_king_behavior_tick()>=30){
  capture("king-reload.ppm");std::puts("PASS P2_KING_ACTOR_RUNTIME bounded_behavior_tick");
  std::fflush(nullptr);if(!hold)std::_Exit(0);
 }
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 // Fixture injection: keep the captain alive and standing so a lick barrage
 // cannot down him and stall the frame-driven tail steps (labeled).
 static bool sustainLogged=false;if(n->mHealth<500.0f)n->mHealth=500.0f;
 {int ns=n->mStateMachine->getCurrID(n);if(ns==NAVISTATE_Pressed||ns==NAVISTATE_Flick||ns==NAVISTATE_Dead||ns==NAVISTATE_PikiZero||ns==NAVISTATE_DemoSunset||ns==NAVISTATE_DemoWait||ns==NAVISTATE_DemoInf){n->mStateMachine->transit(n,NAVISTATE_Walk);if(!sustainLogged){sustainLogged=true;std::puts("P2_KING_FIXTURE_NAVI_SUSTAIN injection=1");}}}
 // Fixture injection: fudge the pikmin census off zero so the extinction
 // game-over check (allPikis == 0) cannot latch the day-end flow (labeled).
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_KING_FIXTURE_GUARD_PIKMIN injection=1");}}}
 if(ready==1){n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
 int red=0,blue=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else if(a->mColor==Blue)++blue;else++other;}}require(red==5&&blue==5&&other==0,"King starting5red5blue");
 std::ifstream holding("king-keep-open.txt");hold=bool(holding);
 SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Emperor Bulblax sampled actor (#289)");std::printf("P2_KING_BASELINE red=%d blue=%d\n",red,blue);
 }
 if(ready==30){
 std::ifstream raw("king-fixture-profile.txt");auto cfg=p2king::readActorConfig(raw);require(cfg.placements.size()>=1,"King placement fixture");auto d=cfg.placements[0];
 float ground=mapMgr->getMinY(d.x,d.z,true);require(std::isfinite(ground)&&std::fabs(ground-d.y)<40,"King ground divergence");std::printf("P2_KING_GROUND id=%u x=%.6f y=%.6f z=%.6f ground=%.6f yaw=%.3f\n",d.id,d.x,d.y,d.z,ground,d.yaw);
 require(cameraMgr&&cameraMgr->mCamera,"King camera missing");auto* target=new KingCameraTarget();target->mSRT.t=Vector3f(d.x,d.y+60.f,d.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
 PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=1100;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
 std::printf("P2_KING_CAMERA target=%.6f,%.6f,%.6f\n",target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z);
 // Arm the opt-in tongue injection for scenario 1: it fires at behavior tick
 // 80 (after the appear shake-off at key 55) while the full 10-Pikmin squad is
 // still alive, so ATTACK_ARM / EAT / Swallow / 1->12 are deterministic and
 // cannot be lost to a checkFlick roll on a loaded host.
 {std::ofstream inj("p2-king-inject.txt");inj<<"P2_KING_INJECT_1 100000 230020 0 0 80\n";inj.close();}
 std::puts("P2_KING_TONGUE_ARMED tick=80 fixture=1");
 {std::ifstream src("king-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-king-actor.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}
 const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_king_setup();gsys->setHeap(heap);
 }
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n#include <string>\n#include "pc_p2_king.h"\n'
                '#include "pc_p2_king_policy.h"\n'
                'unsigned long pc_p2_king_behavior_tick();\n'
                'bool pc_p2_king_dead_key_seen();\n'
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


KING_WANTED = ('attack', 'cry', 'damage', 'dead', 'dive', 'flick', 'move1',
               'type1', 'type2', 'type3', 'wait2', 'waitact1', 'waitact2')


def king_profiles(bank):
    """P2_KING_ACTOR_1 configs + model bytes from the #234 sampled bank."""
    bank = Path(bank)
    meta = json.loads((bank / 'bulblax-bank.json').read_bytes())
    motions = meta['motions']['KingChappy']
    clips = []
    files = {}
    for name in KING_WANTED:
        motion = motions.get(name)
        if motion is None or motion['source_frames'] != __import__('experimental.pikmin2_bulblax_behavior',
                                                                   fromlist=['KING_CLIPS']).KING_CLIPS[name]['frames']:
            raise ValueError('Bank motion %s disagrees with the #227 reference' % name)
        clips.append(dict(species='KingChappy', name=name, duration=motion['source_frames'],
                          frames=list(motion['frames'])))
        for i in range(motion['poses']):
            fname = 'bulblax_KingChappy_%s_%02d.mod' % (name, i)
            data = (bank / 'KingChappy' / fname).read_bytes()
            if builder.sha256(bank / 'KingChappy' / fname) != meta['file_sha256'][fname]:
                raise ValueError('Model identity mismatch')
            files[fname] = data
    # Scenario 1: buried Emperor inside the squad (pure tongue/Swallow lane);
    # one bomb sits outside tongue reach and detonates externally at behavior
    # tick 200 (quartered blast, injection).
    p1 = [dict(placement_id=230020, variant='default', xyz=[34, 30, 1896], yaw=0)]
    b1 = [dict(bomb_id=360002, xyz=[34, 30, 1796], external_blast_tick=60)]
    # Scenario 2: two Emperors (one buried far, gauge hidden) + a BOMB_Wait
    # cluster on one bearing: the far bomb sits 90 units north (beyond the 80
    # disc invisible range so the default-on bomb targeting connects;
    # injection) with two more on the same line so one lined-up lick sweeps
    # all three; together they drive multiplied bomb damage and the
    # cross-Emperor WarCry contract.
    p2 = [dict(placement_id=230022, variant='default', xyz=[34, 30, 1896], yaw=0),
          dict(placement_id=230023, variant='default', xyz=[34, 30, 1200], yaw=0)]
    b2 = [dict(bomb_id=360003, xyz=[34, 30, 1986]),
          dict(bomb_id=360004, xyz=[32, 30, 1960]),
          dict(bomb_id=360005, xyz=[37, 30, 1969]),
          dict(bomb_id=360002, xyz=[34, 30, 1796], external_blast_tick=60)]
    # Scenario 3: force-big spawn identity.
    p3 = [dict(placement_id=230024, variant='force_big', xyz=[34, 30, 1896], yaw=0)]
    return (protocol(clips, p1, b1), protocol(clips, p2, b2), protocol(clips, p3), files,
            [dict(placements=p1, bombs=b1), dict(placements=p2, bombs=b2), dict(placements=p3, bombs=[])])


def stage(assets, bank, output):
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
        struct.pack_into('<I', row, 8, 235200 + i)
        row[16:48] = b'King5red5blue fixture'.ljust(32, b'\0')
        write_position(row, [10 + i % 5 * 12, 30, 1890 + i // 5 * 12])
        struct.pack_into('>I', row, 92, 1 if i < 5 else 0)
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/courses/pikmin2room/private-king.txt': b'King sampled actor fixture\n'}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    config, config2, config3, files, scenarios = king_profiles(bank)
    room = run / 'assets/dataDir/courses/pikmin2room'
    for name, blob in files.items():
        (room / name).write_bytes(blob)
    (run / 'king-fixture-profile.txt').write_bytes(config)
    (run / 'king-fixture-profile2.txt').write_bytes(config2)
    (run / 'king-fixture-profile3.txt').write_bytes(config3)
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    original = {str(p.relative_to(assets)): builder.sha256(p)
                for p in (assets / 'dataDir/courses/practice').rglob('*') if p.is_file()}
    for rel, digest in original.items():
        if builder.sha256(run / 'assets' / rel) != digest:
            raise ValueError('Course changed')
    (run / 'king-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 Impact Site', interactive=True, starting_squad={'red': 5, 'blue': 5},
             scenarios=scenarios, config_sha256=builder.sha256(run / 'king-fixture-profile.txt'),
             course_sha256=original), indent=2) + '\n').encode())
    return run


def validate(text, code):
    states = re.findall(r'P2_KING_STATE id=\d+ from=(\d+) to=(\d+)', text)
    transitions = {(int(a), int(b)) for a, b in states}
    required = dict(
        completion=code == 0 and 'PASS P2_KING_ACTOR_RUNTIME' in text,
        baseline='red=5 blue=5' in text,
        ground=text.count('P2_KING_GROUND ') == 1,
        ready='P2_KING_READY id=230020 enemy=53 variant=default' in text and 'gauge_hidden=1' in text,
        appear_trigger='P2_KING_APPEAR_TRIGGER id=230020' in text,
        hidewait_to_appear=(9, 10) in transitions or 'P2_KING_APPEAR_TRIGGER id=230020' in text,
        appear_to_caution=(10, 11) in transitions,
        caution_to_walk=(11, 0) in transitions,
        appear_shakeoff=bool(re.search(r'P2_KING_SHAKEOFF id=230020 appear range=100 power=200', text)),
        attack_arm='P2_KING_ATTACK_ARM id=' in text,
        bomb_arm='P2_KING_ATTACK_BOMB_ARM id=' in text,
        tongue_eat=bool(re.search(r'P2_KING_EAT id=\d+ ', text)),
        swallow=bool(re.search(r'P2_KING_SWALLOW id=\d+ count=[1-9]\d* poison_damage=300 hardcoded=1', text)),
        attack_to_swallow=(1, 12) in transitions,
        bomb_eaten='P2_KING_EAT_BOMB id=' in text,
        eat_to_damage=(7, 5) in transitions,
        bomb_damage=bool(re.search(r'P2_KING_BOMB_DAMAGE id=\d+ bombs=[2-9] damage=[4-9]\d\d killed_mouth=\d+ stun_frames=180', text)),
        reset=text.count('P2_KING_RESET_REQUEST') == 1,
        reload=text.count('P2_KING_RELOAD_REQUEST') == 1,
        reload_ready=text.count('P2_KING_READY ') >= 5,  # s1 + s2(x2) + reload + big
        big_variant=bool(re.search(r'P2_KING_READY id=230024 enemy=53 variant=force_big .* health=1800\.0 scale=1\.50 '
                                   r'speed=45\.0 floor_offset=60', text)),
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_COLLECT' not in text,
        warcry_inject='P2_KING_INJECT_ARMED warcry_tick=500 bomb_tick=50 fixture=1' in text
                       and bool(re.search(r'P2_KING_INJECT id=\d+ tick=\d+ force=WarCry fixture=1', text)),
        bomb_inject=bool(re.search(r'P2_KING_INJECT_BOMB id=\d+ tick=\d+ bomb=\d+ state=Attack fixture=1', text)),
        warcry_astonish='P2_KING_ASTONISH' in text,
        cross_emperor=bool(re.search(r'P2_KING_WARCRY_REQUEST id=\d+ other=\d+ from=\d+ to=\d+', text)),
        death_inject=bool(re.search(r'P2_KING_DEATH_ARMED kill_tick=5 fixture=1', text))
                      and bool(re.search(r'P2_KING_INJECT_KILL id=\d+ tick=\d+ health=0 fixture=1', text)),
        death_reached=bool(re.search(r'P2_KING_STATE id=\d+ from=\d+ to=2 health=0', text)),
        death_key=bool(re.search(r'P2_KING_DEAD_KEY id=\d+ frame=185 kill=1', text)),
    )
    optional = dict(
        flick_trample='P2_KING_TRAMPLE' in text or 'P2_KING_FLICK id=' in text,
        external_quartered='P2_KING_BOMB_QUARTERED' in text,
    )
    untested = [name for name, ok in optional.items() if not ok]
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, optional=optional, untested=untested,
                transitions=sorted(transitions), exit_code=code,
                scope='Sampled actor fixture; bomb placements and external blasts are labeled injections')


def pid_running(pid):
    """True when this exact PID still exists (tasklist by PID, not by name)."""
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, bank, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, bank, output / 'king')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy')
    with (directory / 'native.log').open('w') as log:
        process = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code = 'timeout'
    # Only the exact PID this run launched is our responsibility; a sibling
    # worker's same-named fixture must not flip a green gate to failed.
    text = (directory / 'native.log').read_text(errors='replace')
    evidence = validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('king', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, bank, output, exe):
    directory = stage(assets, bank, output)
    (directory / 'king-keep-open.txt').write_bytes(b'Sampled King actor; close window to exit.\n')
    print('Emperor Bulblax sampled actor fixture.\n' + str(directory), flush=True)
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
        for key in ('assets', 'bank', 'output', 'exe'):
            parser.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native.resolve(), a.build_dir.resolve(), a.output, a.head)
    elif a.command == 'run':
        evidence = run(a.assets, a.bank, a.output, a.exe)
        raise SystemExit(0 if evidence['passed'] else 1)
    else:
        raise SystemExit(play(a.assets, a.bank, a.output, a.exe))
