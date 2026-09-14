"""#448 real-engine Queen Candypop fixture: colour cycle + ip13 sprout multiplier.

Companion to experimental/pikmin2_pom_engine_runtime.py. Stages a single real
`GENBOSS_Pom` bound to the source `RandPom` (Queen) and drives the genuine
engine actor:

* the bound Queen cycles Blue/Red/Yellow every fp02 = 2.6 s (the fixture waits
  long enough to observe the changes before touching it),
* one real throw converts the Pikmin and shoots the source `ip13` = 9 leaf
  sprouts (the Queen never refunds and its budget `ip11` = 1).

The run is wall-clock bounded and self-terminates with PASS or an explicit
`P2_POM_QUEEN_BLOCKED <gate> reason=...`; it never hangs.
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

QUEEN = 240013
QUEEN_POS = (-25.0, 30.0, 1790.0)  # kept clear of the idle squad at z=1900

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
	unsigned startTick = 0, phaseStart = 0;
	bool hold = false;
	bool thrown = false;
	Pom* queen = nullptr;
	Piki* target = nullptr;
	unsigned initialPikis = 0;
	void blocked(const char* gate, const char* reason) {
		std::printf("P2_POM_QUEEN_BLOCKED %s reason=%s\n", gate, reason);
		std::fflush(nullptr);
		std::_Exit(0);
	}
	void aim() {
		if (!target || !queen) {
			return;
		}
		if (!target->isAlive() || target->getStickObject() || target->getState() != PIKISTATE_Normal) {
			return;
		}
		target->changeMode(PikiMode::FreeMode, naviMgr->getNavi());
		target->mFSM->transit(target, PIKISTATE_Flying);
		naviMgr->getNavi()->throwPiki(target, queen->mSRT.t);
	}
public:
	int idle() override {
		int result = PlugPikiApp::idle();
		++timer;
		require(++frames < 40000, "Queen startup timeout");
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
			Iterator bosses(bossMgr);
			CI_LOOP(bosses) {
				Boss* b = static_cast<Boss*>(*bosses);
				if (!b || !b->isAlive() || b->mObjType != OBJTYPE_Pom) {
					continue;
				}
				const unsigned g = b->mGenerator ? static_cast<unsigned>(b->mGenerator->_70) : 0u;
				if (g == 240013u) {
					require(!queen, "duplicate Queen boss");
					queen = static_cast<Pom*>(b);
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
			if (queen && alive.size() >= 2) {
				target = alive[0];
				target->setColor(Red);
				initialPikis = unsigned(alive.size());
				phaseStart = SDL_GetTicks();
				std::printf("P2_POM_QUEEN_PLAN initial=%u queen=%u\n", initialPikis, 240013u);
				phase = 1;
			}
		} else if (phase == 1) {
			// Observe the fp02 colour cycle before the Queen is consumed.
			if (SDL_GetTicks() - phaseStart > 8500) {
				aim();
				thrown = true;
				phase = 2;
			}
		} else if (phase == 2) {
			if (!thrown || (timer % 8 == 0)) {
				aim();
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
				std::printf("P2_POM_QUEEN_PROGRESS sprouts=%d alive=%d state=%d\n", sprouts, alive,
				            queen ? queen->getCurrentState() : -1);
			}
			if (sprouts >= 9) {
				std::printf("P2_POM_QUEEN_STATE initial=%u sprouts=%d alive=%d\n", initialPikis, sprouts, alive);
				capture("p2-pom-queen.ppm");
				std::puts("PASS P2_POM_QUEEN cycle_and_multiplier");
				std::fflush(nullptr);
				if (!hold) {
					std::_Exit(0);
				}
			}
			require(timer < 25000, "Queen conversion timeout");
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


def queen_sidecar(generator_id=QUEEN):
    return ('P2_POM_1 1\n%d RandPom %.1f %.1f %.1f\n' % ((generator_id,) + QUEEN_POS)).encode('ascii')


def build(native, build_dir, output, head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(encoding='utf-8')), encoding='utf-8')
    return builder.build_fixture(build_dir, native, room, output / 'build', head)


def stage(assets, output):
    assets = Path(assets).resolve()
    source = assets / 'dataDir/stages/practice/default.gen'
    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    piki = next((r for r in rows if r[72:76] == b'ikip'), None)
    if piki is None:
        raise ValueError('Missing P1 Pikmin generator template')
    entries = []
    for i in range(2):
        row = bytearray(piki)
        struct.pack_into('<I', row, 8, 237000 + i)
        row[16:48] = b'pom queen squad'.ljust(32, b'\0')
        write_position(row, [-10 + i * 20, 30, 1900])
        struct.pack_into('>I', row, 92, 1 if i == 0 else 0)
        entries.append(bytes(row))
    boss = next((r for r in records(assets / 'dataDir/stages/chal0/default.gen') if r[72:80] == b'ssob\x02\x00\x00\x00'), None)
    if boss is None:
        raise ValueError('Missing Pom boss generator template')
    row = bytearray(boss)
    struct.pack_into('<I', row, 8, QUEEN)
    row[16:48] = b'preview candypop Queen'.ljust(32, b'\0')
    write_position(row, list(QUEEN_POS))
    struct.pack_into('>I', row, 80, 5 | (1 << 6))  # GENBOSS_Pom | Red container colour
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
    (run / 'p2-pom-engine.txt').write_bytes(queen_sidecar())
    (run / 'pom-queen-stage.json').write_bytes((json.dumps(
        dict(scene='real engine P2 Queen Candypop', queen=QUEEN, sidecar='p2-pom-engine.txt',
             sidecar_sha256=builder.sha256(run / 'p2-pom-engine.txt'), squad=2, cycle_wait_ms=8500), indent=2) + '\n').encode())
    required = {run / 'p2-pom-engine.txt', run / 'p2-cargo-free.txt',
                run / 'assets/dataDir/stages/chal0.ini', run / 'assets/dataDir/stages/chal0/default.gen',
                run / 'assets/dataDir/courses/practice/practice.mod'}
    missing = sorted(str(p) for p in required if not p.is_file())
    if missing:
        raise ValueError('Queen Candypop staging incomplete; missing: ' + ', '.join(missing))
    return run


def validate(text, code):
    colours = re.findall(r'^P2_POM_QUEEN_COLOUR generator=%d colour=([012]) met=7$' % QUEEN, text, re.M)
    state = re.search(r'^P2_POM_QUEEN_STATE initial=(\d+) sprouts=(\d+) alive=(\d+)$', text, re.M)
    required = dict(
        completion=code == 0 and 'PASS P2_POM_QUEEN' in text,
        ready=bool(re.search(r'P2_POM_READY generator=%d species=RandPom .*queen=1 engine=1' % QUEEN, text)),
        cycle=len(colours) >= 2 and len(set(colours)) >= 2,
        convert=bool(re.search(r'^P2_CANDYPOP_CONVERT generator=%d species=RandPom converted=1 used=1 refunds=0$' % QUEEN, text, re.M)),
        sprouts=bool(re.search(r'^P2_CANDYPOP_SPROUTS generator=%d species=RandPom sprouts=9 multiplier=9$' % QUEEN, text, re.M)),
        state=bool(state) and int(state.group(2)) == 9 and int(state.group(3)) == int(state.group(1)) - 1,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, cycle_colours=colours, exit_code=code,
                scope='real engine Queen; ip13 multiplier grows the population by design, not conservation')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'queen')
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
    print('pom-queen', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'pom-keep-open.txt').write_bytes(b'Queen Candypop fixture; close window to exit.\n')
    print('Queen Candypop fixture.\n' + str(directory), flush=True)
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
