"""#448 real-engine Candypop fixture: bind the actual engine Pom Boss.

Mirrors experimental/pikmin2_pom_runtime.py but drives the genuine
`src/plugPikiNishimura/PomAi.cpp` colour Candypop instead of the module-local
injected actor. The fixture stages real `boss` generators for a RedPom and a
BluePom (cloned from the challenge Pom template), writes the strict
`p2-pom-engine.txt` sidecar consumed by `pc_port/pc_p2_candypop.cpp`, and throws
real Pikmin with the ordinary throw path. It then observes the engine accept,
close and discharge, the module's own-colour refund (`P2_CANDYPOP_WITNESS`
refund=1 consumes no slot) and the born sprouts.

The run is wall-clock bounded and self-terminates with PASS or an explicit
`P2_POM_ENGINE_BLOCKED <gate> reason=...`; it never hangs. Aim/throw timing is a
labeled injection; the actor, swallow, close, discharge, refund and sprout
creation are real engine behaviour.
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
from scripts.preview_pikmin2_room import generator, overlay, records
from experimental.pikmin2_generator_pose import write_position

SPECIES = ('BluePom', 'RedPom', 'YellowPom', 'BlackPom', 'WhitePom', 'RandPom', 'Pom')
REDPOM = 240011
BLUEPOM = 240012
BASEPOM = 240013

APP = r'''#include "GameStat.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "ItemMgr.h"
#include "Boss.h"
#include "Pom.h"
#include "Generator.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <vector>

class RoomApp : public PlugPikiApp {
	int frames = 0, ready = 0, phase = 0, timer = 0;
	unsigned startTick = 0;
	bool hold = false;
	struct Assign { Piki* piki; Pom* flower; };
	std::vector<Assign> plan;
	Pom* redFlower = nullptr;
	Pom* blueFlower = nullptr;
	unsigned initialPikis = 0;
	void blocked(const char* gate, const char* reason) {
		std::printf("P2_POM_ENGINE_BLOCKED %s reason=%s\n", gate, reason);
		std::fflush(nullptr);
		std::_Exit(0);
	}
	void aim(Piki* piki, Pom* flower) {
		if (!piki || !piki->isAlive() || piki->getStickObject() || piki->getState() != PIKISTATE_Normal) {
			return;
		}
		piki->changeMode(PikiMode::FreeMode, naviMgr->getNavi());
		piki->mFSM->transit(piki, PIKISTATE_Flying);
		naviMgr->getNavi()->throwPiki(piki, flower->mSRT.t);
	}
public:
	int idle() override {
		int result = PlugPikiApp::idle();
		++timer;
		require(++frames < 40000, "Pom engine startup timeout");
		if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
			gameflow.mMoviePlayer->requestSkip();
			return result;
		}
		if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !pikiMgr || !itemMgr || !bossMgr) {
			return result;
		}
		Navi* n = naviMgr->getNavi();
		if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) {
			return result;
		}
		if (phase == 0 && (int)GameStat::allPikis == 0) {
			GameStat::allPikis.set(1, Red);
		}
		if (ready == 1) {
			for (int i = 0; i < DEMOFLAG_COUNT; ++i) {
				playerState->mDemoFlags.setFlagOnly(i);
			}
			std::ifstream holding("pom-keep-open.txt");
			hold = bool(holding);
		}
		if (++ready < 10) {
			return result;
		}
		if (!startTick) {
			startTick = SDL_GetTicks();
		}
		if (SDL_GetTicks() - startTick > 130000) {
			blocked("timeout", "wall_clock_ceiling");
		}
		if (phase == 0) {
			int found = 0;
			Iterator bosses(bossMgr);
			CI_LOOP(bosses) {
				Boss* b = static_cast<Boss*>(*bosses);
				if (!b || !b->isAlive() || b->mObjType != OBJTYPE_Pom) {
					continue;
				}
				const unsigned g = b->mGenerator ? static_cast<unsigned>(b->mGenerator->_70) : 0u;
				if (g == 240011u) {
					require(!redFlower, "duplicate red engine flower");
					redFlower = static_cast<Pom*>(b);
					++found;
				} else if (g == 240012u) {
					require(!blueFlower, "duplicate blue engine flower");
					blueFlower = static_cast<Pom*>(b);
					++found;
				}
			}
			std::vector<Piki*> alive;
			Iterator pikis(pikiMgr);
			CI_LOOP(pikis) {
				Piki* p = static_cast<Piki*>(*pikis);
				if (p && p->isAlive()) {
					alive.push_back(p);
				}
			}
			if (found == 2 && alive.size() >= 10) {
				// Red flower: two own-colour Reds (refund) then three Blues.
				// Blue flower: two own-colour Blues (refund) then three Reds.
				const int colours[10] = {Red, Red, Blue, Blue, Blue, Blue, Blue, Red, Red, Red};
				for (int i = 0; i < 10; ++i) {
					alive[i]->setColor(colours[i]);
				}
				for (int i = 0; i < 5; ++i) {
					plan.push_back({alive[i], redFlower});
				}
				for (int i = 5; i < 10; ++i) {
					plan.push_back({alive[i], blueFlower});
				}
				initialPikis = unsigned(alive.size());
				std::printf("P2_POM_ENGINE_PLAN initial=%u red_flower=%u blue_flower=%u\n", initialPikis, 240011u, 240012u);
				phase = 1;
			}
		} else if (phase == 1) {
			if (timer % 12 == 0) {
				for (Assign& assign : plan) {
					aim(assign.piki, assign.flower);
				}
			}
			int sprouts = 0;
			Iterator heads(itemMgr->getPikiHeadMgr());
			CI_LOOP(heads) {
				PikiHeadItem* head = static_cast<PikiHeadItem*>(*heads);
				if (head && head->isAlive()) {
					++sprouts;
				}
			}
			int alive = 0;
			Iterator pikis(pikiMgr);
			CI_LOOP(pikis) {
				if (static_cast<Piki*>(*pikis)->isAlive()) {
					++alive;
				}
			}
			if (timer % 150 == 0) {
				std::printf("P2_POM_ENGINE_PROGRESS sprouts=%d alive=%d states=%d,%d\n", sprouts, alive,
				            redFlower ? redFlower->getCurrentState() : -1, blueFlower ? blueFlower->getCurrentState() : -1);
			}
			if (sprouts >= 10) {
				std::printf("P2_POM_ENGINE_STATE initial=%u sprouts=%d alive=%d\n", initialPikis, sprouts, alive);
				if (alive + sprouts != int(initialPikis)) {
					blocked("conservation", "population_not_conserved");
				}
				capture("p2-pom-engine.ppm");
				std::puts("PASS P2_POM_ENGINE real_conversion_refund_conservation");
				std::fflush(nullptr);
				if (!hold) {
					std::_Exit(0);
				}
			}
			require(timer < 25000, "engine conversion timeout");
		}
		std::fflush(stdout);
		return result;
	}
};
'''

INCLUDES = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n'
            '#include <vector>\n')


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return INCLUDES + source[:start] + APP + source[end:]


def engine_sidecar(specs):
    """Strict P2_POM_1 text shared with pc_p2_pom_policy.h::readPoms."""
    if not isinstance(specs, (list, tuple)) or not 1 <= len(specs) <= 64:
        raise ValueError('Invalid engine Candypop record count')
    lines = ['P2_POM_1 %d' % len(specs)]
    seen = set()
    for spec in specs:
        generator_id = spec['generator']
        if not isinstance(generator_id, int) or not 0 <= generator_id <= 0xffffffff:
            raise ValueError('Invalid engine Candypop generator')
        if generator_id in seen:
            raise ValueError('Duplicate engine Candypop generator')
        seen.add(generator_id)
        if spec['species'] not in SPECIES:
            raise ValueError('Invalid engine Candypop species')
        for axis in ('x', 'y', 'z'):
            value = spec[axis]
            if not isinstance(value, (int, float)) or value != value or abs(value) > 100000:
                raise ValueError('Invalid engine Candypop position')
        lines.append('%d %s %s %s %s' % (generator_id, spec['species'], spec['x'], spec['y'], spec['z']))
    return ('\n'.join(lines) + '\n').encode('ascii')


def build(native, build_dir, output, head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(encoding='utf-8')), encoding='utf-8')
    return builder.build_fixture(build_dir, native, room, output / 'build', head)


def stage(assets, output):
    """Stage the practice course, a mixed squad, real boss generators and the sidecar."""
    assets = Path(assets).resolve()
    source = assets / 'dataDir/stages/practice/default.gen'
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    piki = next((r for r in rows if r[72:76] == b'ikip'), None)
    if piki is None:
        raise ValueError('Missing P1 Pikmin generator template')
    entries = []
    squad = [1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0]  # 6 red, 6 blue; ten assigned
    for i, colour in enumerate(squad):
        row = bytearray(piki)
        struct.pack_into('<I', row, 8, 236000 + i)
        row[16:48] = b'pom engine squad'.ljust(32, b'\0')
        write_position(row, [-30 + i % 4 * 20, 30, 1900 + i // 4 * 12])
        struct.pack_into('>I', row, 92, colour)
        entries.append(bytes(row))

    boss = next((r for r in records(assets / 'dataDir/stages/chal0/default.gen') if r[72:80] == b'ssob\x02\x00\x00\x00'), None)
    if boss is None:
        raise ValueError('Missing Pom boss generator template')
    for generator_id, name, x, z in ((REDPOM, b'preview candypop RedPom', -25.0, 1850.0),
                                     (BLUEPOM, b'preview candypop BluePom', 25.0, 1850.0)):
        row = bytearray(boss)
        struct.pack_into('<I', row, 8, generator_id)
        row[16:48] = name.ljust(32, b'\0')
        write_position(row, [x, 30.0, z])
        # GENBOSS_Pom (5) | Red container colour (1<<6): the engine birth gate
        # checks hasContainer(mItemColour); the module re-stamps the source colour.
        struct.pack_into('>I', row, 80, 5 | (1 << 6))
        entries.append(bytes(row))

    data = bytearray(source.read_bytes()[:20])
    struct.pack_into('>4f', data, 4, 0.0, 0.0, 1900.0, 180.0)
    data = bytes(data) + struct.pack('>I', len(entries)) + b''.join(entries)

    stage_ini = re.sub(rb'(?m)^navi_start[^\r\n]*', b'navi_start 0.0 1900.0',
                       (assets / 'dataDir/stages/practice.ini').read_bytes(), count=1)
    if b'navi_start 0.0 1900.0' not in stage_ini:
        stage_ini += b'\nnavi_start 0.0 1900.0\n'

    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 0)
    overrides = {'dataDir/stages/chal0.ini': stage_ini, 'dataDir/stages/chal0/default.gen': data}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    sidecar = engine_sidecar([
        dict(generator=REDPOM, species='RedPom', x=-25.0, y=30.0, z=1850.0),
        dict(generator=BLUEPOM, species='BluePom', x=25.0, y=30.0, z=1850.0),
        dict(generator=BASEPOM, species='Pom', x=0.0, y=30.0, z=1850.0),
    ])
    (run / 'p2-pom-engine.txt').write_bytes(sidecar)
    (run / 'pom-engine-stage.json').write_bytes((json.dumps(
        dict(scene='real engine P2 Candypop via pc_p2_candypop', redpom=REDPOM, bluepom=BLUEPOM, basepom=BASEPOM,
             sidecar='p2-pom-engine.txt', sidecar_sha256=builder.sha256(run / 'p2-pom-engine.txt'),
             squad=dict(red=6, blue=6, assigned=10), aim='real throwPiki, scripted timing'), indent=2) + '\n').encode())

    required = {run / 'p2-pom-engine.txt', run / 'p2-cargo-free.txt',
                run / 'assets/dataDir/stages/chal0.ini', run / 'assets/dataDir/stages/chal0/default.gen',
                run / 'assets/dataDir/courses/practice/practice.mod'}
    missing = sorted(str(p) for p in required if not p.is_file())
    if missing:
        raise ValueError('Engine Candypop staging incomplete; missing: ' + ', '.join(missing))
    return run


def _convert_totals(text):
    totals = {}
    for generator, converted, used, refunds in re.findall(
            r'^P2_CANDYPOP_CONVERT generator=(\d+) species=\S+ converted=(\d+) used=(\d+) refunds=(\d+)$', text, re.M):
        bucket = totals.setdefault(int(generator), [0, 0, 0])
        bucket[0] += int(converted)
        bucket[1] += int(used)
        bucket[2] += int(refunds)
    return totals


def validate(text, code):
    totals = _convert_totals(text)
    state = re.search(r'^P2_POM_ENGINE_STATE initial=(\d+) sprouts=(\d+) alive=(\d+)$', text, re.M)
    conserved = bool(state) and int(state.group(2)) + int(state.group(3)) == int(state.group(1))
    witnesses = re.findall(r'^P2_CANDYPOP_WITNESS generator=(\d+) species=\S+ input=(\w+) refund=([01])$', text, re.M)
    required = dict(
        completion=code == 0 and 'PASS P2_POM_ENGINE' in text,
        ready_red=bool(re.search(r'P2_POM_READY generator=%d species=RedPom .*engine=1' % REDPOM, text)),
        ready_blue=bool(re.search(r'P2_POM_READY generator=%d species=BluePom .*engine=1' % BLUEPOM, text)),
        base_rejection=bool(re.search(r'P2_POM_BASE_REJECTED generator=%d species=Pom source_id=82' % BASEPOM, text)),
        convert_red=totals.get(REDPOM) == [5, 3, 2],
        convert_blue=totals.get(BLUEPOM) == [5, 3, 2],
        witnesses_refund=sum(1 for _, _, refund in witnesses if refund == '1') == 4,
        witnesses_used=sum(1 for _, _, refund in witnesses if refund == '0') == 6,
        conservation=conserved,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, exit_code=code,
                scope='real engine Pom Boss; scripted aim/throw timing is labeled, conversion/refund are engine behaviour')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'engine')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
    with (directory / 'native.log').open('w') as log:
        process = subprocess.Popen([str(Path(exe).resolve()), '--experimental-pikmin2-room'], cwd=directory,
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=220)
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
    print('pom-engine', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'pom-keep-open.txt').write_bytes(b'Engine Candypop fixture; close window to exit.\n')
    print('Engine Candypop fixture.\n' + str(directory), flush=True)
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
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
