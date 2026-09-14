"""Lane-22 dweevil treasure capture/drop runtime fixture (#170, child #447).

Mirrors experimental/pikmin2_king_runtime.py: stages the original P1 practice
course into the existing chal0 experimental slot with the standard 20-Pikmin
overlay and a 960x540 centred window, builds a private replacement-main fixture
via scripts/build_pikmin2_fixture.py, and drives two deterministic scenarios of
the pc_port/pc_p2_dweevil.cpp sidecar:

  scenario 1 (death)         capture -> carry -> fixture kill -> exactly-once
                             drop reason=death, then a replay that must be
                             suppressed (dropped=0 already_dropped=1)
  scenario 2 (interruption)  capture -> carry -> fixture interrupting receiver
                             -> exactly-once drop reason=interruption

The capture/carry/drop simulation is actor-local and policy-driven; the fixture
placements and kill/interrupt ticks are labeled injections. This module does
not launch the fixture (the coordinator owns the serialized GL slot).
"""
import argparse
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import uuid

from scripts import build_pikmin2_fixture as builder
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_generator_pose import write_position
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial

MAGIC = 'P2_DWEEVIL_NATIVE_1'
SPECIES = (59, 60, 61, 62, 93)
INJECT_MAGIC = 'P2_DWEEVIL_INJECT_1'

UNIT_ID = 235300
TREASURE_A = 900001
TREASURE_B = 900002


def _finite(value):
    return type(value) in (int, float) and abs(value) <= 100000


def protocol(units, treasures=()):
    """Serialize a P2_DWEEVIL_NATIVE_1 profile; strict mirror of the native reader."""
    if not 1 <= len(units) <= 8:
        raise ValueError('unit budget')
    lines = [MAGIC, str(len(units))]
    ids = set()
    for unit in units:
        generator = unit['generator_id']
        species = unit['species']
        xyz = unit['xyz']
        yaw = unit.get('yaw', 0)
        life = unit['otakara_life']
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('invalid unit identity')
        if species not in SPECIES:
            raise ValueError('invalid species')
        if (not isinstance(xyz, (list, tuple)) or len(xyz) != 3
                or any(not _finite(v) for v in xyz)):
            raise ValueError('invalid unit transform')
        if type(yaw) not in (int, float) or abs(yaw) > 360:
            raise ValueError('invalid unit yaw')
        if type(life) not in (int, float) or not 0 < life <= 100000:
            raise ValueError('invalid otakara life')
        ids.add(generator)
        lines.append('%d %d %.6f %.6f %.6f %.6f %.6f' % (generator, species, xyz[0], xyz[1], xyz[2], yaw, life))
    if not 0 <= len(treasures) <= 8:
        raise ValueError('treasure budget')
    lines.append(str(len(treasures)))
    for treasure in treasures:
        identity = treasure['id']
        xyz = treasure['xyz']
        if type(identity) is not int or not 0 <= identity <= 0xffffffff or identity in ids:
            raise ValueError('invalid treasure identity')
        if (not isinstance(xyz, (list, tuple)) or len(xyz) != 3
                or any(not _finite(v) for v in xyz)):
            raise ValueError('invalid treasure transform')
        flags = [treasure.get('alive', False), treasure.get('pickable', False),
                 treasure.get('captured', False)]
        if any(type(flag) is not bool for flag in flags):
            raise ValueError('invalid treasure flags')
        ids.add(identity)
        lines.append('%d %.6f %.6f %.6f %d %d %d'
                     % (identity, xyz[0], xyz[1], xyz[2],
                        int(flags[0]), int(flags[1]), int(flags[2])))
    return ('\n'.join(lines) + '\n').encode('ascii')


def _unit(generator, species, xyz, life):
    return dict(generator_id=generator, species=species, xyz=list(xyz), yaw=0, otakara_life=life)


def _treasure(identity, xyz):
    return dict(id=identity, xyz=list(xyz), alive=True, pickable=True, captured=False)


def scenario_a():
    """Death drop followed by a suppressed replay."""
    return protocol([_unit(UNIT_ID, 59, (34, 30, 1896), 80.0)],
                    [_treasure(TREASURE_A, (30, 30, 1880))])


def scenario_b():
    """Fatal/interrupting receiver drop."""
    return protocol([_unit(UNIT_ID, 59, (34, 30, 1896), 80.0)],
                    [_treasure(TREASURE_B, (30, 30, 1880))])


APP = r'''#include "GameStat.h"
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;
 static void copyFile(const char* from,const char* to){std::ifstream s(from,std::ios::binary);std::ofstream d(to,std::ios::binary);d<<s.rdbuf();}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"Dweevil startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 // Scenario sequencing is gated on the sidecar's own 30 Hz behavior clock so a
 // loaded host cannot truncate the capture/drop or the suppressed replay.
 static int phase=0;
 if(phase==0&&pc_p2_dweevil_behavior_tick()>=160){
  pc_p2_dweevil_reset();std::puts("P2_DWEEVIL_RESET_REQUEST");
  copyFile("dweevil-fixture-b.txt","p2-dweevil-native.txt");
  {std::ofstream inj("p2-dweevil-inject.txt");
   inj<<"P2_DWEEVIL_INJECT_1 40 235300 interrupt\nP2_DWEEVIL_INJECT_1 100 235300 kill\n";inj.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_dweevil_setup();gsys->setHeap(heap);
  std::puts("P2_DWEEVIL_SCENARIO2 interrupt_drop");phase=1;
 }
 if(phase==1&&pc_p2_dweevil_behavior_tick()>=160){
  std::puts("PASS P2_DWEEVIL_RUNTIME bounded_behavior_tick");
  std::fflush(nullptr);if(!hold)std::_Exit(0);
 }
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 // Fixture injection (labeled): keep the passive squad from latching extinction.
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_DWEEVIL_FIXTURE_GUARD_PIKMIN injection=1");}}}
 if(ready==1){
  n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  int red=0,blue=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else if(a->mColor==Blue)++blue;else++other;}}
  require(red==5&&blue==5&&other==0,"Dweevil starting5red5blue");
  std::ifstream holding("dweevil-keep-open.txt");hold=bool(holding);
  SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Dweevil capture/drop sidecar (#447)");
  std::printf("P2_DWEEVIL_BASELINE red=%d blue=%d\n",red,blue);
 }
 if(ready==30){
  copyFile("dweevil-fixture-a.txt","p2-dweevil-native.txt");
  {std::ofstream inj("p2-dweevil-inject.txt");
   inj<<"P2_DWEEVIL_INJECT_1 40 235300 kill\nP2_DWEEVIL_INJECT_1 100 235300 replay\n";inj.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_dweevil_setup();gsys->setHeap(heap);
  std::puts("P2_DWEEVIL_SCENARIO1 death_drop_replay");std::puts("P2_DWEEVIL_DEATH_ARMED kill_tick=40 fixture=1");
 }
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n#include <string>\n'
                '#include "pc_p2_dweevil.h"\n')
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


def stage(assets, output):
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
        struct.pack_into('<I', row, 8, UNIT_ID + i)
        row[16:48] = b'Dweevil5red5blue fixture'.ljust(32, b'\0')
        write_position(row, [10 + i % 5 * 12, 30, 1890 + i // 5 * 12])
        struct.pack_into('>I', row, 92, 1 if i < 5 else 0)
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)
    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = data[:20] + struct.pack('>I', 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    config_a = scenario_a()
    config_b = scenario_b()
    (run / 'dweevil-fixture-a.txt').write_bytes(config_a)
    (run / 'dweevil-fixture-b.txt').write_bytes(config_b)
    (run / 'p2-dweevil-native.txt').write_bytes(config_a)
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    (run / 'dweevil-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 practice course', interactive=True, window='960x540',
             starting_squad={'red': 5, 'blue': 5},
             scenarios=[dict(name='death', unit=UNIT_ID, treasure=TREASURE_A,
                             injections=['40 kill', '100 replay']),
                        dict(name='interruption', unit=UNIT_ID, treasure=TREASURE_B,
                             injections=['40 interrupt', '100 kill'])],
             config_a_sha256=builder.sha256(run / 'dweevil-fixture-a.txt'),
             config_b_sha256=builder.sha256(run / 'dweevil-fixture-b.txt'),
             injections_labeled=True),
        indent=2) + '\n').encode())
    return run


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_DWEEVIL_RUNTIME' in text,
        baseline='red=5 blue=5' in text,
        window='Experimental preview window set to 960x540 windowed and centered' in text,
        scenario1='P2_DWEEVIL_SCENARIO1 death_drop_replay' in text,
        scenario2='P2_DWEEVIL_SCENARIO2 interrupt_drop' in text,
        reset=text.count('P2_DWEEVIL_RESET_REQUEST') == 1,
        ready=text.count('P2_DWEEVIL_READY generator=235300 species=FireOtakara') >= 2,
        captures=text.count('P2_DWEEVIL_CAPTURE generator=235300 species=FireOtakara') == 2,
        carries=text.count('P2_DWEEVIL_CARRY generator=235300') == 2,
        death_drop=bool(re.search(r'P2_DWEEVIL_DROP generator=235300 treasure=900001 reason=death '
                                  r'dropped=1 exactly_once=1', text)),
        interrupt_drop=bool(re.search(r'P2_DWEEVIL_DROP generator=235300 treasure=900002 reason=interruption '
                                      r'dropped=1 exactly_once=1', text)),
        suppressed=bool(re.search(r'P2_DWEEVIL_DROP_SUPPRESSED generator=235300 treasure=900001 '
                                  r'reason=death dropped=0 already_dropped=1', text)),
        exactly_two_drops=text.count('dropped=1 exactly_once=1') == 2,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, exit_code=code,
                scope='Actor-local policy fixture; placements and kill/interrupt ticks are labeled injections')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'dweevil')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
    with (directory / 'native.log').open('w') as log:
        process = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=180)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            code = 'timeout'
    text = (directory / 'native.log').read_text(errors='replace')
    evidence = validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('dweevil', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'dweevil-keep-open.txt').write_bytes(b'Dweevil sidecar fixture; close window to exit.\n')
    print('Dweevil treasure capture/drop fixture.\n' + str(directory), flush=True)
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
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
        for key in ('assets', 'output', 'exe'):
            parser.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native.resolve(), a.build_dir.resolve(), a.output, a.head)
    elif a.command == 'run':
        evidence = run(a.assets, a.output, a.exe)
        raise SystemExit(0 if evidence['passed'] else 1)
    else:
        raise SystemExit(play(a.assets, a.output, a.exe))
