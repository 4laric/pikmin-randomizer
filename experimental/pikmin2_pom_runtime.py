"""#448 Candypop Bud native fixture: build, stage, run, validate.

Mirrors experimental/pikmin2_flora_runtime.py. The fixture boots the opt-in
pc_port/pc_p2_pom.cpp actor from a strict p2-pom.txt sidecar: one RedPom, one
RandPom Queen and one nonspawnable base Pom. It injects Pikmin conversions
(own-colour refund on the RedPom, accept on both, Queen shot sprouts) and
observes the module markers accept/refund/close/sprout/base-rejection. The run
is wall-clock bounded and self-terminates with PASS or an explicit
`P2_POM_RUNTIME_BLOCKED <gate> reason=...`; it never hangs.

The base Pom row is only an explicit rejection check; it is never bound. The
fixture does not claim engine-Pom-FSM or Onion-side behaviour.
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
RANDPOM = 240012
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
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <vector>

class RoomApp : public PlugPikiApp {
	int frames = 0, ready = 0, phase = 0;
	unsigned startTick = 0;
	bool hold = false;
	struct Inject { Piki* piki; float x, y, z; };
	std::vector<Inject> plan;
	int injected = 0;
	void blocked(const char* gate, const char* reason) {
		std::printf("P2_POM_RUNTIME_BLOCKED %s reason=%s\n", gate, reason);
		std::fflush(nullptr);
		std::_Exit(0);
	}
	static bool fly(Piki* piki, float x, float y, float z) {
		if (!piki || !piki->isAlive()) {
			return false;
		}
		piki->mSRT.t.set(x, y, z);
		piki->mFSM->transit(piki, PIKISTATE_Flying);
		return true;
	}
public:
	int idle() override {
		int result = PlugPikiApp::idle();
		require(++frames < 12000, "Pom startup timeout");
		if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
			gameflow.mMoviePlayer->requestSkip();
			return result;
		}
		if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !pikiMgr || !itemMgr) {
			return result;
		}
		Navi* n = naviMgr->getNavi();
		if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) {
			return result;
		}
		{
			static bool guardLogged = false;
			if ((int)GameStat::allPikis == 0) {
				GameStat::allPikis.set(1, Red);
				if (!guardLogged) {
					guardLogged = true;
					std::puts("P2_POM_FIXTURE_GUARD_PIKMIN injection=1");
				}
			}
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
		if (SDL_GetTicks() - startTick > 100000) {
			blocked("sprout", "wall_clock_ceiling");
		}
		if (phase == 0) {
			// Fixed squad order: RedPom refund(Red) then accept(Blue); Queen accept(Yellow).
			std::vector<Piki*> alive;
			Iterator it(pikiMgr);
			CI_LOOP(it) {
				Piki* p = static_cast<Piki*>(*it);
				if (p && p->isAlive()) {
					alive.push_back(p);
				}
			}
			require(alive.size() >= 3, "Pom fixture needs at least three Pikmin");
			alive[0]->setColor(Red);
			alive[1]->setColor(Blue);
			alive[2]->setColor(Yellow);
			plan.push_back({alive[0], 0.0f, 30.0f, 1850.0f});   // RedPom, own colour -> refund
			plan.push_back({alive[1], 0.0f, 30.0f, 1850.0f});   // RedPom, other colour -> accept
			plan.push_back({alive[2], 30.0f, 30.0f, 1850.0f});  // RandPom Queen -> accept
			std::printf("P2_POM_FIXTURE_PLAN injected=%u\n", unsigned(plan.size()));
			phase = 1;
		} else if (phase == 1) {
			// Re-drive the flying state until the module consumes each Pikmin.
			for (Inject& inject : plan) {
				fly(inject.piki, inject.x, inject.y, inject.z);
			}
			if (!plan.empty() && !plan[0].piki->isAlive() && !plan[1].piki->isAlive() && !plan[2].piki->isAlive()) {
				phase = 2;
				startTick = SDL_GetTicks();
			}
		} else if (phase == 2) {
			// Wait out the fp01 close and the Queen shot before ending.
			if (SDL_GetTicks() - startTick > 4000) {
				int sprouts = 0;
				Iterator heads(itemMgr->getPikiHeadMgr());
				CI_LOOP(heads) {
					PikiHeadItem* head = static_cast<PikiHeadItem*>(*heads);
					if (head && head->isAlive()) {
						++sprouts;
					}
				}
				std::printf("P2_POM_FIXTURE_SPROUTS n=%d\n", sprouts);
				if (sprouts <= 0) {
					blocked("sprout", "no_leaf_sprout");
				}
				capture("p2-pom-sprouts.ppm");
				std::puts("PASS P2_POM_NATIVE accept_refund_close_sprout");
				std::fflush(nullptr);
				if (!hold) {
					std::_Exit(0);
				}
			}
		}
		std::fflush(stdout);
		return result;
	}
};
'''

INCLUDES = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n'
            '#include "pc_p2_pom.h"\n'
            '#include "pc_p2_pom_policy.h"\n')


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return INCLUDES + source[:start] + APP + source[end:]


def pom_sidecar(specs):
    """Strict P2_POM_1 text, mirroring pc_p2_pom_policy.h."""
    if not isinstance(specs, (list, tuple)) or not 1 <= len(specs) <= 64:
        raise ValueError('Invalid Candypop record count')
    lines = ['P2_POM_1 %d' % len(specs)]
    seen = set()
    for spec in specs:
        generator_id = spec['generator']
        if not isinstance(generator_id, int) or not 0 <= generator_id <= 0xffffffff:
            raise ValueError('Invalid Candypop generator')
        if generator_id in seen:
            raise ValueError('Duplicate Candypop generator')
        seen.add(generator_id)
        if spec['species'] not in SPECIES:
            raise ValueError('Invalid Candypop species')
        for axis in ('x', 'y', 'z'):
            value = spec[axis]
            if not isinstance(value, (int, float)) or value != value or abs(value) > 100000:
                raise ValueError('Invalid Candypop position')
        lines.append('%d %s %s %s %s' % (generator_id, spec['species'], spec['x'], spec['y'], spec['z']))
    return ('\n'.join(lines) + '\n').encode('ascii')


def build(native, build_dir, output, head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(encoding='utf-8')), encoding='utf-8')
    return builder.build_fixture(build_dir, native, room, output / 'build', head)


def stage(assets, output):
    """Stage the practice course, a squad, and a strict p2-pom.txt sidecar."""
    assets = Path(assets).resolve()
    source = assets / 'dataDir/stages/practice/default.gen'
    data = source.read_bytes()
    entries = records(source)

    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    piki = next((r for r in rows if r[72:76] == b'ikip'), None)
    if piki is None:
        raise ValueError('Missing P1 Pikmin generator template')
    for i in range(10):
        row = bytearray(piki)
        struct.pack_into('<I', row, 8, 235400 + i)
        row[16:48] = b'pom squad'.ljust(32, b'\0')
        write_position(row, [10 + i % 5 * 12, 30, 1890 + i // 5 * 12])
        struct.pack_into('>I', row, 92, 1)  # native Red
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)

    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    sidecar = pom_sidecar([
        dict(generator=REDPOM, species='RedPom', x=0.0, y=30.0, z=1850.0),
        dict(generator=RANDPOM, species='RandPom', x=30.0, y=30.0, z=1850.0),
        dict(generator=BASEPOM, species='Pom', x=60.0, y=30.0, z=1850.0),
    ])
    (run / 'p2-pom.txt').write_bytes(sidecar)
    (run / 'pom-stage.json').write_bytes((json.dumps(
        dict(scene='module-local P2 Candypop policy', redpom=REDPOM, randpom=RANDPOM, basepom=BASEPOM,
             sidecar='p2-pom.txt', sidecar_sha256=builder.sha256(run / 'p2-pom.txt')), indent=2) + '\n').encode())

    required = {run / 'p2-pom.txt', run / 'p2-cargo-free.txt', run / 'assets/dataDir/stages/chal0.ini',
                run / 'assets/dataDir/stages/chal0/default.gen', run / 'assets/dataDir/courses/practice/practice.mod'}
    missing = sorted(str(p) for p in required if not p.is_file())
    if missing:
        raise ValueError('Pom staging incomplete; missing: ' + ', '.join(missing))
    return run


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_POM_NATIVE' in text,
        ready=bool(re.search(r'P2_POM_READY generator=%d species=RedPom' % REDPOM, text))
              and bool(re.search(r'P2_POM_READY generator=%d species=RandPom' % RANDPOM, text)),
        base_rejection=bool(re.search(r'P2_POM_BASE_REJECTED generator=%d species=Pom source_id=82' % BASEPOM, text)),
        accept=bool(re.search(r'P2_POM_ACCEPT generator=%d ' % REDPOM, text))
               and bool(re.search(r'P2_POM_ACCEPT generator=%d ' % RANDPOM, text)),
        refund=bool(re.search(r'P2_POM_REFUND generator=%d ' % REDPOM, text)),
        close=bool(re.search(r'P2_POM_CLOSE generator=%d .*outcome=shot' % REDPOM, text))
              and bool(re.search(r'P2_POM_CLOSE generator=%d .*outcome=shot' % RANDPOM, text)),
        sprout=bool(re.search(r'P2_POM_SPROUT generator=%d species=RandPom count=9 .*leaf=1' % RANDPOM, text)),
        invulnerable=text.count('P2_POM_INVULNERABLE ') >= 2,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    blocked = sorted(name for name in ('ready', 'accept', 'refund', 'close', 'sprout')
                     if ('P2_POM_RUNTIME_BLOCKED %s' % name) in text)
    return dict(passed=not failed, failed=failed, checks=required, blocked=blocked, exit_code=code,
                scope='module-local Candypop policy actor; base Pom rejection is a labeled sidecar probe')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'pom')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''), SDL_AUDIODRIVER='dummy', PIKMIN_P2_ROOM_WINDOW='960x540')
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
    print('pom', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'pom-keep-open.txt').write_bytes(b'Candypop fixture; close window to exit.\n')
    print('Candypop fixture.\n' + str(directory), flush=True)
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
