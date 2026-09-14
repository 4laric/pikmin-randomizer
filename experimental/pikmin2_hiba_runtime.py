"""Lane-22 fixed-hazard runtime fixture (#170, child #447).

Mirrors experimental/pikmin2_dweevil_runtime.py: stages the original P1 practice
course into the existing chal0 experimental slot with the standard squad overlay
and a 960x540 centred window, builds a private replacement-main fixture via
scripts/build_pikmin2_fixture.py, and drives the pc_port/pc_p2_hiba.cpp sidecar.

The single scenario stages Hiba (fire), GasHiba (gas) and ElecHiba (denki) on
the live-Pikmin centroid so one run proves: activation, emission, a vulnerable
colour hit (Hiba/Blue via the engine InteractFire receiver) and an immune colour
pass (Hiba/Red), plus the lane-10 gas/electric receivers driven by a natural
emitter (GasHiba -> InteractGas -> PIKISTATE_Panic, ElecHiba -> InteractDenki ->
PIKISTATE_DenkiDying) with White/Yellow immunity rejection and a lethal outcome.
The fixture recolours one Blue to White and one Blue to Yellow to expose the
elemental immunity boundary. It self-terminates on the gates or on a bounded
behavior-tick timeout with an explicit BLOCKED marker; it never hangs. This
module does not launch the fixture (the coordinator owns the serialized GL
slot).
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

MAGIC = 'P2_HIBA_NATIVE_1'
HAZARD_IDS = (20, 21, 22)

HIBA_GEN = 20
GAS_GEN = 21
ELEC_GEN = 22


def _finite(value):
    return type(value) in (int, float) and abs(value) <= 100000


def protocol(hazards):
    """Serialize a P2_HIBA_NATIVE_1 profile; strict mirror of the native reader."""
    if not 1 <= len(hazards) <= 8:
        raise ValueError('hazard budget')
    lines = [MAGIC, str(len(hazards))]
    ids = set()
    for hazard in hazards:
        generator = hazard['generator_id']
        hazard_id = hazard['hazard_id']
        xyz = hazard['xyz']
        yaw = hazard.get('yaw', 0)
        health = hazard.get('health', 100.0)
        wait = hazard.get('wait_override', -1.0)
        separation = hazard.get('separation', 0.0)
        link = hazard.get('link', 0)
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('invalid hazard identity')
        if hazard_id not in HAZARD_IDS:
            raise ValueError('invalid hazard id')
        if (not isinstance(xyz, (list, tuple)) or len(xyz) != 3
                or any(not _finite(v) for v in xyz)):
            raise ValueError('invalid hazard transform')
        if type(yaw) not in (int, float) or abs(yaw) > 360:
            raise ValueError('invalid hazard yaw')
        if type(health) not in (int, float) or not 0 < health <= 100000:
            raise ValueError('invalid hazard health')
        if type(wait) not in (int, float) or abs(wait) > 1000:
            raise ValueError('invalid wait override')
        if type(separation) not in (int, float) or not 0 <= separation <= 1000:
            raise ValueError('invalid separation')
        if hazard_id != 22 and separation != 0:
            raise ValueError('separation only applies to ElecHiba')
        if type(link) is not int or not 0 <= link <= 3:
            raise ValueError('invalid link')
        if hazard_id != 21 and link != 0:
            raise ValueError('link only applies to GasHiba')
        ids.add(generator)
        lines.append('%d %d %.6f %.6f %.6f %.6f %.6f %.6f %.6f %d'
                     % (generator, hazard_id, xyz[0], xyz[1], xyz[2], yaw, health, wait, separation, link))
    return ('\n'.join(lines) + '\n').encode('ascii')


def scenario_hazards():
    """Reference profile shape written by the fixture at runtime (centroid TBD)."""
    return [dict(generator_id=HIBA_GEN, hazard_id=20, xyz=[0, 0, 0], wait_override=0.4),
            dict(generator_id=GAS_GEN, hazard_id=21, xyz=[0, 0, 8], wait_override=-1.0),
            dict(generator_id=ELEC_GEN, hazard_id=22, xyz=[0, 0, -8], wait_override=0.4, separation=40.0)]


APP = r'''#include "GameStat.h"
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0;bool hold=false;bool armed=false,finished=false;
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"Hiba startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 {static bool guardLogged=false;if((int)GameStat::allPikis==0){GameStat::allPikis.set(1,Red);if(!guardLogged){guardLogged=true;std::puts("P2_HIBA_FIXTURE_GUARD_PIKMIN injection=1");}}}
  if(ready==1){
   n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   int red=0,blue=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else if(a->mColor==Blue)++blue;else++other;}}
   require(red==5&&blue==5&&other==0,"Hiba starting5red5blue");
   std::ifstream holding("hiba-keep-open.txt");hold=bool(holding);
   SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Fixed hazard sidecar (#447)");
   std::printf("P2_HIBA_BASELINE red=%d blue=%d\n",red,blue);
   // Labeled squad recolour: one Blue -> White (gas-immune, denki-vulnerable)
   // and one Blue -> Yellow (gas-vulnerable, denki-immune) so the elemental
   // immunity and receiver gates can be observed on the natural emitters.
   Piki* whiteTarget=nullptr;Piki* yellowTarget=nullptr;
   {Iterator q(pikiMgr);CI_LOOP(q){Piki* a=static_cast<Piki*>(*q);if(!a||!a->isAlive())continue;if(a->mColor!=Blue)continue;
     if(!whiteTarget)whiteTarget=a;else if(!yellowTarget)yellowTarget=a;else break;}}
   require(whiteTarget&&yellowTarget,"Hiba recolour blue targets");
   pc_p2_set_species(whiteTarget,P2SpeciesWhite);
   pc_p2_set_species(yellowTarget,P2SpeciesYellow);
   std::printf("P2_HIBA_RECOLOUR white=1 yellow=1\n");
  }
 if(ready==30&&!armed){
  // Labeled placement: put the hazards on the live-Pikmin centroid so the
  // vulnerable/immune receivers are deterministic and never chase a wanderer.
  float sx=0,sy=0,sz=0;int count=0;
  Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(!a->isAlive())continue;const Vector3f& pos=a->getPosition();sx+=pos.x;sy+=pos.y;sz+=pos.z;++count;}
  require(count>0,"Hiba no live Pikmin for placement");
  const float cx=sx/count,cy=sy/count,cz=sz/count;
  {std::ofstream cfg("p2-hiba-native.txt");
   cfg<<"P2_HIBA_NATIVE_1\n3\n";
   cfg<<"20 20 "<<cx<<" "<<cy<<" "<<cz<<" 0 100 0.4 0 0\n";
   cfg<<"21 21 "<<cx<<" "<<cy<<" "<<cz+8<<" 0 100 -1 0 0\n";
   cfg<<"22 22 "<<cx<<" "<<cy<<" "<<cz-8<<" 0 100 0.4 40 0\n";cfg.close();}
  const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_hiba_setup();gsys->setHeap(heap);
  std::printf("P2_HIBA_SCENARIO hiba_gas_elec centroid=%.3f,%.3f,%.3f\n",cx,cy,cz);
  armed=true;
 }
 if(armed&&!finished){
  if(pc_p2_hiba_gates_ready()){
   pc_p2_hiba_kill_all();
   std::puts("P2_HIBA_CLEANUP kill_all=1");
   std::puts("PASS P2_HIBA_RUNTIME gates_ready");
   finished=true;std::fflush(nullptr);if(!hold)std::_Exit(0);
  } else if(pc_p2_hiba_behavior_tick()>900){
   std::printf("P2_HIBA_BLOCKED gates reason=timeout hit=%d immune=%d activated=%d emitted=%d\n",
               int(pc_p2_hiba_hit_seen()),int(pc_p2_hiba_immune_seen()),
               pc_p2_hiba_activated(),pc_p2_hiba_emitted());
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
                '#include "pc_p2_hiba.h"\n#include "pc_p2_species.h"\n')
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
    # Reference squad grid: 5 red (colour 1) and 5 blue (colour 0).
    for i in range(10):
        row = bytearray(template)
        struct.pack_into('<I', row, 8, 236300 + i)
        row[16:48] = b'Hiba5red5blue fixture'.ljust(32, b'\0')
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
    # No p2-hiba-native.txt at startup: the sidecar stays inert until the
    # fixture writes it on the live-Pikmin centroid at ready==30.
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    (run / 'hiba-stage.json').write_bytes((json.dumps(
        dict(scene='original P1 practice course', interactive=True, window='960x540',
             starting_squad={'red': 5, 'blue': 5},
             scenario='hiba_gas_elec', hazards=scenario_hazards(), placements_labeled=True),
        indent=2) + '\n').encode())
    return run


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_HIBA_RUNTIME' in text,
        baseline='red=5 blue=5' in text,
        window='Experimental preview window set to 960x540 windowed and centered' in text,
        scenario='P2_HIBA_SCENARIO hiba_gas_elec' in text,
        ready=text.count('P2_HIBA_READY') == 3,
        activate_hiba=bool(re.search(r'P2_HIBA_ACTIVATE generator=\d+ hazard=Hiba from=wait to=attack', text)),
        activate_gas=bool(re.search(r'P2_HIBA_ACTIVATE generator=\d+ hazard=GasHiba from=\w+ to=attack', text)),
        activate_elec=bool(re.search(r'P2_HIBA_ACTIVATE generator=\d+ hazard=ElecHiba from=\w+ to=attack', text)),
        emit_hiba=bool(re.search(r'P2_HIBA_EMIT generator=\d+ hazard=Hiba stimulus=InteractFire', text)),
        emit_gas=bool(re.search(r'P2_HIBA_EMIT generator=\d+ hazard=GasHiba stimulus=InteractGas', text)),
        emit_elec=bool(re.search(r'P2_HIBA_EMIT generator=\d+ hazard=ElecHiba stimulus=InteractDenki', text)),
        vulnerable_hit=bool(re.search(r'P2_HIBA_HIT generator=\d+ hazard=Hiba stimulus=InteractFire '
                                      r'colour=Blue immune=0 applied=1', text)),
        immune_pass=bool(re.search(r'P2_HIBA_PASS generator=\d+ hazard=Hiba stimulus=InteractFire '
                                   r'colour=Red immune=1 applied=0', text)),
        gas_hit=bool(re.search(r'P2_HIBA_GAS_HIT generator=\d+ hazard=GasHiba species=\d+ state=36 applied=1', text)),
        gas_pass=bool(re.search(r'P2_HIBA_GAS_PASS generator=\d+ hazard=GasHiba species=4 immune=1', text)),
        denki_hit=bool(re.search(r'P2_HIBA_DENKI_HIT generator=\d+ hazard=ElecHiba species=\d+ state=35 applied=1',
                                 text)),
        denki_pass=bool(re.search(r'P2_HIBA_DENKI_PASS generator=\d+ hazard=ElecHiba species=2 immune=1', text)),
        gas_lethal='P2_HIBA_GAS_LETHAL dead=1' in text,
        denki_lethal='P2_HIBA_DENKI_LETHAL dead=1' in text,
        recolour='P2_HIBA_RECOLOUR white=1 yellow=1' in text,
        no_gas_blocked=not bool(re.search(r'P2_HIBA_APPLY_BLOCKED generator=\d+ hazard=GasHiba stimulus=InteractGas ',
                                          text)),
        cleanup='P2_HIBA_CLEANUP kill_all=1' in text,
        cleanup_dead=text.count('P2_HIBA_DEAD') >= 3,
        no_timeout='P2_HIBA_BLOCKED' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, exit_code=code,
                scope='Actor-local policy fixture; hazard placement is on the live-Pikmin centroid (labeled)')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'hiba')
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
    print('hiba', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'hiba-keep-open.txt').write_bytes(b'Fixed hazard sidecar fixture; close window to exit.\n')
    print('Fixed hazard fixture.\n' + str(directory), flush=True)
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
