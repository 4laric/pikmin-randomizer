"""Lane-22 BombOtakara payload runtime fixture (#170, child #447).

Mirrors experimental/pikmin2_dweevil_runtime.py: stages the original P1 practice
course into the existing chal0 experimental slot with the standard squad overlay
and a 960x540 centred window, builds a private replacement-main fixture via
scripts/build_pikmin2_fixture.py, and drives the pc_port/pc_p2_bombotakara.cpp
sidecar.

Two carriers are born holding a sidecar-staged Bomb stub (labeled injection).
Carrier 30 is detonated by contact, carrier 31 by death; each is triggered twice
so the second trigger emits P2_BOMBOTAKARA_DETONATE_SUPPRESSED (exactly-once).
There is no shared blast/projectile contract at this base, so every detonation
emits P2_BOMBOTAKARA_BLAST_BLOCKED reason=no_shared_blast instead of a duplicate
blast. The fixture self-terminates on the gates or on a bounded behavior-tick
timeout with an explicit BLOCKED marker; it never hangs. This module does not
launch the fixture (the coordinator owns the serialized GL slot).
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

MAGIC = 'P2_BOMBOTAKARA_NATIVE_1'
INJECT_MAGIC = 'P2_BOMBOTAKARA_INJECT_1'

CARRIER_A = 30
CARRIER_B = 31
PAYLOAD_A = 40
PAYLOAD_B = 41


def _finite(value):
    return type(value) in (int, float) and abs(value) <= 100000


def protocol(units):
    """Serialize a P2_BOMBOTAKARA_NATIVE_1 profile; strict mirror of the native reader."""
    if not 1 <= len(units) <= 4:
        raise ValueError('carrier budget')
    lines = [MAGIC, str(len(units))]
    ids = set()
    for unit in units:
        generator = unit['generator_id']
        payload = unit['payload_id']
        xyz = unit['xyz']
        bomb = unit['bomb_xyz']
        yaw = unit.get('yaw', 0)
        health = unit.get('health', 150.0)
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('invalid carrier identity')
        if type(payload) is not int or not 0 <= payload <= 0xffffffff or payload in ids:
            raise ValueError('invalid payload identity')
        if (not isinstance(xyz, (list, tuple)) or len(xyz) != 3
                or any(not _finite(v) for v in xyz)):
            raise ValueError('invalid carrier transform')
        if (not isinstance(bomb, (list, tuple)) or len(bomb) != 3
                or any(not _finite(v) for v in bomb)):
            raise ValueError('invalid payload transform')
        if type(yaw) not in (int, float) or abs(yaw) > 360:
            raise ValueError('invalid carrier yaw')
        if type(health) not in (int, float) or not 0 < health <= 100000:
            raise ValueError('invalid carrier health')
        ids.add(generator)
        ids.add(payload)
        lines.append('%d %.6f %.6f %.6f %.6f %.6f %d %.6f %.6f %.6f'
                     % (generator, xyz[0], xyz[1], xyz[2], yaw, health,
                        payload, bomb[0], bomb[1], bomb[2]))
    return ('\n'.join(lines) + '\n').encode('ascii')


def scenario_units(cx=0.0, cy=0.0, cz=0.0):
    return [dict(generator_id=CARRIER_A, xyz=[cx, cy, cz], bomb_xyz=[cx + 10, cy, cz + 10],
                 payload_id=PAYLOAD_A),
            dict(generator_id=CARRIER_B, xyz=[cx + 6, cy, cz + 6], bomb_xyz=[cx + 16, cy, cz + 16],
                 payload_id=PAYLOAD_B)]


def injection_text():
    return ('%s 75 %d contact\n'
            '%s 90 %d death\n'
            '%s 105 %d contact\n'
            '%s 120 %d death\n'
            % (INJECT_MAGIC, CARRIER_A, INJECT_MAGIC, CARRIER_B,
               INJECT_MAGIC, CARRIER_A, INJECT_MAGIC, CARRIER_B)).encode('ascii')


APP = r'''#include "GameStat.h"
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;bool armed=false,finished=false;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"BombOtakara startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_BOMBOTAKARA_FIXTURE_GUARD_PIKMIN injection=1");}}}
 if(ready==1){
  n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
  int red=0,blue=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else if(a->mColor==Blue)++blue;else++other;}}
  require(red==5&&blue==5&&other==0,"BombOtakara starting5red5blue");
  std::ifstream holding("bombotakara-keep-open.txt");hold=bool(holding);
  SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"BombOtakara payload sidecar (#447)");
  std::printf("P2_BOMBOTAKARA_BASELINE red=%d blue=%d\n",red,blue);
 }
 if(ready==30&&!armed){
  float sx=0,sy=0,sz=0;int count=0;
  Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(!a->isAlive())continue;const Vector3f& pos=a->getPosition();sx+=pos.x;sy+=pos.y;sz+=pos.z;++count;}
  require(count>0,"BombOtakara no live Pikmin for placement");
  const float cx=sx/count,cy=sy/count,cz=sz/count;
  {std::ofstream cfg("p2-bombotakara-native.txt");
   cfg<<"P2_BOMBOTAKARA_NATIVE_1\n2\n";
   cfg<<"30 "<<cx<<" "<<cy<<" "<<cz<<" 0 150 40 "<<cx+10<<" "<<cy<<" "<<cz+10<<"\n";
   cfg<<"31 "<<cx+6<<" "<<cy<<" "<<cz+6<<" 0 150 41 "<<cx+16<<" "<<cy<<" "<<cz+16<<"\n";cfg.close();}
  {std::ofstream inj("p2-bombotakara-inject.txt");
   inj<<"P2_BOMBOTAKARA_INJECT_1 75 30 contact\n";
   inj<<"P2_BOMBOTAKARA_INJECT_1 90 31 death\n";
   inj<<"P2_BOMBOTAKARA_INJECT_1 105 30 contact\n";
   inj<<"P2_BOMBOTAKARA_INJECT_1 120 31 death\n";inj.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_bombotakara_setup();gsys->setHeap(heap);
  std::printf("P2_BOMBOTAKARA_SCENARIO carry_arm_detonate centroid=%.3f,%.3f,%.3f\n",cx,cy,cz);
  armed=true;
 }
 if(armed&&!finished){
  if(pc_p2_bombotakara_gates_ready()){
   pc_p2_bombotakara_kill_all();
   std::puts("P2_BOMBOTAKARA_CLEANUP kill_all=1");
   std::puts("PASS P2_BOMBOTAKARA_RUNTIME gates_ready");
   finished=true;std::fflush(nullptr);if(!hold)std::_Exit(0);
  } else if(pc_p2_bombotakara_behavior_tick()>900){
   std::printf("P2_BOMBOTAKARA_BLOCKED gates reason=timeout carry=%d armed=%d detonated=%d suppressed=%d blast=%d\n",
               pc_p2_bombotakara_carry_count(),pc_p2_bombotakara_armed_count(),
               pc_p2_bombotakara_detonated_count(),pc_p2_bombotakara_suppressed_count(),
               pc_p2_bombotakara_blast_blocked_count());
   finished=true;std::fflush(nullptr);if(!hold)std::_Exit(0);
  }
 }
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n#include <string>\n'
                '#include "pc_p2_bombotakara.h"\n')
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
        struct.pack_into('<I', row, 8, 237300 + i)
        row[16:48] = b'BombOtakara5red5blue'.ljust(32, b'\0')
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
    # No p2-bombotakara-native.txt at startup: the sidecar stays inert until the
    # fixture writes the profile and trigger injections at ready==30.
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    (run / 'bombotakara-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 practice course', interactive=True, window='960x540',
             starting_squad={'red': 5, 'blue': 5}, scenario='carry_arm_detonate',
             carriers=[dict(generator=CARRIER_A, payload=PAYLOAD_A, trigger='contact'),
                       dict(generator=CARRIER_B, payload=PAYLOAD_B, trigger='death')],
             payload_injection=True, shared_blast='blocked:no_shared_blast'),
        indent=2) + '\n').encode())
    return run


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_BOMBOTAKARA_RUNTIME' in text,
        baseline='red=5 blue=5' in text,
        window='Experimental preview window set to 960x540 windowed and centered' in text,
        scenario='P2_BOMBOTAKARA_SCENARIO carry_arm_detonate' in text,
        ready=text.count('P2_BOMBOTAKARA_READY') == 2,
        carry=text.count('P2_BOMBOTAKARA_CARRY') == 2,
        arm=text.count('P2_BOMBOTAKARA_ARM') == 2,
        detonate_contact=bool(re.search(r'P2_BOMBOTAKARA_DETONATE generator=30 payload=40 '
                                        r'trigger=contact detonated=1 exactly_once=1', text)),
        detonate_death=bool(re.search(r'P2_BOMBOTAKARA_DETONATE generator=31 payload=41 '
                                      r'trigger=death detonated=1 exactly_once=1', text)),
        exactly_two_detonations=text.count('detonated=1 exactly_once=1') == 2,
        suppressed_contact=bool(re.search(r'P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=30 payload=40 '
                                          r'trigger=contact detonated=0 already_detonated=1', text)),
        suppressed_death=bool(re.search(r'P2_BOMBOTAKARA_DETONATE_SUPPRESSED generator=31 payload=41 '
                                        r'trigger=death detonated=0 already_detonated=1', text)),
        exactly_two_suppressed=text.count('P2_BOMBOTAKARA_DETONATE_SUPPRESSED') == 2,
        blast_blocked=text.count('P2_BOMBOTAKARA_BLAST_BLOCKED') == 2
                      and 'reason=no_shared_blast' in text,
        cleanup='P2_BOMBOTAKARA_CLEANUP kill_all=1' in text,
        no_timeout='P2_BOMBOTAKARA_BLOCKED' not in text,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, exit_code=code,
                scope='Actor-local payload policy fixture; bomb stub and triggers are labeled injections; '
                      'shared blast BLOCKED (no shared interface at this base)')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'bombotakara')
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
    print('bombotakara', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'bombotakara-keep-open.txt').write_bytes(b'BombOtakara payload fixture; close window to exit.\n')
    print('BombOtakara payload fixture.\n' + str(directory), flush=True)
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
