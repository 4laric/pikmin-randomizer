"""#171 Pellet Posy (Pelplant) native release/capture receptor fixture.

Mirrors experimental/pikmin2_king_runtime.py. The fixture boots the real P1
Palm proxy registered by pc_port/pc_p2_flora_actor.cpp from a strict
p2-flora-pelplant.txt sidecar, drives a full posy to its fell path with real
Pikmin attacks, and observes the dead-state pellet release and the Pikmin
capture. It builds, stages, runs and validates; it never edits production input.

The scenario is deliberately bounded: the release and capture receptor are
native, but the Onion-side seed receipt is left to the P1 receiver path and is
recorded as remaining work, so this fixture does not claim it.
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

STAGES = ('small', 'middle', 'full')
PELLETS = (1, 5, 10, 20)
COLOURS = ('blue', 'red', 'yellow', 'random')
POSY_GENERATOR = 240001

APP = r'''#include "GameStat.h"
#include "Pcam/Camera.h"
#include "Pcam/CameraManager.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiAI.h"
#include "Navi.h"
#include "NaviMgr.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>

// Captains must not be downed by combat; keep one static camera target.
class FloraCameraTarget : public Creature {
public:
	FloraCameraTarget() : Creature(nullptr) { mHealth = 1; }
	void refresh(Graphics&) override {}
	void doKill() override {}
};

class RoomApp : public PlugPikiApp {
	int frames = 0, ready = 0, phase = 0, ticks = 0;
	unsigned startTick = 0;
	bool hold = false;
	Teki* posy = nullptr;
	void blocked(const char* gate, const char* reason) {
		// Bounded honest termination: never hang past the harness timeout.
		std::printf("P2_FLORA_RUNTIME_BLOCKED %s reason=%s\n", gate, reason);
		std::fflush(nullptr);
		std::_Exit(0);
	}
public:
	int idle() override {
		int result = PlugPikiApp::idle();
		require(++frames < 20000, "Flora startup timeout");
		if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
			gameflow.mMoviePlayer->requestSkip();
			return result;
		}
		if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !pikiMgr || !tekiMgr || !pelletMgr || !mapMgr) {
			return result;
		}
		Navi* n = naviMgr->getNavi();
		if (!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive) {
			return result;
		}
		// Fixture injection: keep the extinction check (allPikis == 0) from
		// latching the day-end flow while a posy is being harvested (labeled).
		{
			static bool guardLogged = false;
			if ((int)GameStat::allPikis == 0) {
				GameStat::allPikis.set(1, Red);
				if (!guardLogged) {
					guardLogged = true;
					std::puts("P2_FLORA_FIXTURE_GUARD_PIKMIN injection=1");
				}
			}
		}
		if (ready == 1) {
			for (int i = 0; i < DEMOFLAG_COUNT; ++i) {
				playerState->mDemoFlags.setFlagOnly(i);
			}
			SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(), "Pellet Posy release fixture (#171)");
			std::ifstream holding("flora-keep-open.txt");
			hold = bool(holding);
		}
		if (++ready < 10) {
			return result;
		}
		if (!startTick) {
			startTick = SDL_GetTicks();
		}
		// Absolute wall-clock ceiling so the fixture always self-terminates
		// well under the harness 180 s timeout regardless of frame rate.
		if (SDL_GetTicks() - startTick > 110000) {
			blocked(phase < 2 ? "fell" : "captured", "wall_clock_ceiling");
		}
		if (phase == 0) {
			if (posy == nullptr) {
				Iterator it(tekiMgr);
				CI_LOOP(it) {
					Teki* teki = static_cast<Teki*>(*it);
					if (teki && teki->isAlive() && teki->mTekiType == TEKI_Palm) {
						posy = teki;
						break;
					}
				}
			}
			if (posy == nullptr) {
				if (SDL_GetTicks() - startTick > 45000) {
					blocked("ready", "no_proxy");
				}
				return result; // generator proxy not spawned yet
			}
			require(cameraMgr && cameraMgr->mCamera, "camera missing");
			FloraCameraTarget* target = new FloraCameraTarget();
			target->mSRT.t = Vector3f(posy->mSRT.t.x, posy->mSRT.t.y + 40.0f, posy->mSRT.t.z);
			auto* camera = cameraMgr->mCamera;
			camera->setTarget(target);
			camera->mControlsEnabled = false;
			PcamMotionInfo info = camera->mTargetMotionInfo;
			info.mDistance = 500;
			info.mFov = 40;
			info.mAngle = 35;
			info.mNaviWatchWeight = 0;
			info.mWatchAdjustment = 0;
			camera->startMotion(info);
			std::printf("P2_FLORA_FIXTURE_CAMERA target=%.3f,%.3f,%.3f\n", target->mSRT.t.x, target->mSRT.t.y, target->mSRT.t.z);
			int assigned = 0;
			Iterator p(pikiMgr);
			CI_LOOP(p) {
				Piki* v = static_cast<Piki*>(*p);
				if (!v->isAlive() || assigned >= 5) {
					continue;
				}
				v->mActiveAction->abandon(nullptr);
				v->mActiveAction->mCurrActionIdx = PikiAction::Attack;
				v->mActiveAction->mChildActions[PikiAction::Attack].initialise(posy);
				v->mMode = PikiMode::AttackMode;
				++assigned;
			}
			std::printf("P2_FLORA_FIXTURE_ATTACK_ASSIGNED count=%d\n", assigned);
			require(assigned >= 1, "no attackers for the posy");
			phase = 1;
			ticks = 0;
		} else if (phase == 1) {
			if (!posy->isAlive()) {
				std::printf("P2_FLORA_FIXTURE_FELL health=%.2f\n", posy->mHealth);
				phase = 2;
				ticks = 0;
			} else if (SDL_GetTicks() - startTick > 60000) {
				blocked("fell", "posy_survived");
			}
		} else if (phase == 2) {
			Iterator it(pelletMgr);
			CI_LOOP(it) {
				Pellet* pellet = static_cast<Pellet*>(*it);
				if (pellet && pellet->isAlive() && !pellet->isUfoParts() && pellet->mCarrierCount >= 1) {
					require(pellet->mCarrierCount >= 1, "carrier count");
					std::printf("P2_FLORA_FIXTURE_CAPTURED carriers=%u pellet=%08x\n", unsigned(pellet->mCarrierCount), pellet->mConfig->mModelId.mId);
					capture("p2-flora-captured.ppm");
					std::puts("PASS P2_FLORA_PELPLANT_RUNTIME release_and_capture");
					std::fflush(nullptr);
					if (!hold) {
						std::_Exit(0);
					}
					return result;
				}
			}
			if (SDL_GetTicks() - startTick > 90000) {
				blocked("captured", "no_carrier");
			}
			++ticks;
		}
		std::fflush(stdout);
		return result;
	}
};
'''

INCLUDES = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n'
            '#include "pc_p2_flora_actor.h"\n'
            '#include "pc_p2_flora_policy.h"\n')


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return INCLUDES + source[:start] + APP + source[end:]


def generator_uid(record):
    """Generator::_70 for a .gen record.

    Stream::readInt byte-swaps on little-endian hosts (returning the big-endian
    view of the file bytes), then Generator::readID byte-swaps again, so the
    engine sees the little-endian view of record[8:12]. Writers must therefore
    stamp generator ids little-endian for the module's id match to hold.
    """
    return struct.unpack_from('<I', record, 8)[0]


def pelplant_sidecar(specs):
    """Strict P2_FLORA_PELPLANT_1 text, mirroring pc_p2_flora_policy.h."""
    if not isinstance(specs, (list, tuple)) or not 1 <= len(specs) <= 64:
        raise ValueError('Invalid Pelplant record count')
    lines = ['P2_FLORA_PELPLANT_1 %d' % len(specs)]
    seen = set()
    for spec in specs:
        generator_id = spec['generator']
        if not isinstance(generator_id, int) or not 0 <= generator_id <= 0xffffffff:
            raise ValueError('Invalid Pelplant generator')
        if generator_id in seen:
            raise ValueError('Duplicate Pelplant generator')
        seen.add(generator_id)
        if spec['stage'] not in STAGES:
            raise ValueError('Invalid Pelplant stage')
        if spec['pellet'] not in PELLETS:
            raise ValueError('Invalid Pelplant pellet size')
        if spec['colour'] not in COLOURS:
            raise ValueError('Invalid Pelplant colour')
        lines.append('%d %s %d %s' % (generator_id, spec['stage'], spec['pellet'], spec['colour']))
    return ('\n'.join(lines) + '\n').encode('ascii')


def build(native, build_dir, output, head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(encoding='utf-8')), encoding='utf-8')
    return builder.build_fixture(build_dir, native, room, output / 'build', head)


def stage(assets, output):
    """Stage the practice course plus a squad and one injected Pellet Posy.

    Mirrors experimental/pikmin2_king_runtime.py: the private chal0 slot reuses
    the byte-preserved practice stage (no pikmin2room course asset is needed) and
    p2-cargo-free.txt keeps pc_p2_preview from loading courses/pikmin2room/*.mod.
    """
    assets = Path(assets).resolve()
    source = assets / 'dataDir/stages/practice/default.gen'
    data = source.read_bytes()
    entries = records(source)

    raw = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', raw)]
    rows = [raw[a:(starts[i + 1] if i + 1 < len(starts) else len(raw))] for i, a in enumerate(starts)]
    piki = next((r for r in rows if r[72:76] == b'ikip'), None)
    enemy = next((r for r in rows if len(r) > 80 and r[80] == 3), None)
    if piki is None or enemy is None:
        raise ValueError('Missing P1 Pikmin/enemy generator template')

    # Starting squad (injection; the practice stage carries no Pikmin here).
    for i in range(10):
        row = bytearray(piki)
        struct.pack_into('<I', row, 8, 235200 + i)
        row[16:48] = b'flora squad'.ljust(32, b'\0')
        write_position(row, [10 + i % 5 * 12, 30, 1890 + i // 5 * 12])
        struct.pack_into('>I', row, 92, 1)  # native Red
        entries.append(bytes(row))

    # One full Pellet Posy (TEKI_Palm) among the squad (labeled injection; the
    # source position is authored, not copied from source placement data). The
    # generator id is written little-endian so Generator::_70 reads it back as
    # POSY_GENERATOR (readID byte-swaps the streamed int), matching how
    # preview_pikmin2_room.ensure_pikmin_squad stamps its own generators.
    posy = bytearray(enemy)
    posy[80] = 7  # TEKI_Palm, Pellet Posy
    struct.pack_into('<I', posy, 8, POSY_GENERATOR)
    posy[16:48] = b'flora pellet posy fixture'.ljust(32, b'\0')
    write_position(posy, [34, 30, 1896])
    if generator_uid(bytes(posy)) != POSY_GENERATOR:
        raise ValueError('Injected Pellet Posy generator id does not bind to %d' % POSY_GENERATOR)
    entries.append(bytes(posy))

    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)

    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    # The preview only tries courses/pikmin2room/treasure.mod when cargo is
    # enabled; cargo-free keeps the fixture on the practice course. Other
    # pikmin2room pose banks are gated by their own sidecars, all absent here.
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    sidecar = pelplant_sidecar([dict(generator=POSY_GENERATOR, stage='full', pellet=1, colour='red')])
    (run / 'p2-flora-pelplant.txt').write_bytes(sidecar)
    (run / 'flora-stage.json').write_bytes((json.dumps(
        dict(scene='P1 Palm proxy / P2 Pelplant policy', source_id=0, sidecar='p2-flora-pelplant.txt',
             generator=POSY_GENERATOR, stage='full', pellet=1, colour='red',
             sidecar_sha256=builder.sha256(run / 'p2-flora-pelplant.txt')), indent=2) + '\n').encode())

    required = {run / 'p2-flora-pelplant.txt', run / 'p2-cargo-free.txt',
                run / 'assets/dataDir/stages/chal0.ini', run / 'assets/dataDir/stages/chal0/default.gen',
                run / 'assets/dataDir/courses/practice/practice.mod'}
    missing = sorted(str(p) for p in required if not p.is_file())
    if missing:
        raise ValueError('Flora staging incomplete; missing: ' + ', '.join(missing))
    return run


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_FLORA_PELPLANT_RUNTIME' in text,
        ready=bool(re.search(r'P2_FLORA_PELPLANT_READY generator=%d stage=full' % POSY_GENERATOR, text)),
        fell=bool(re.search(r'P2_FLORA_PELPLANT_FELL generator=%d stage=full .*released_on_death=1 regrowth=0' % POSY_GENERATOR, text)),
        released=bool(re.search(r'P2_FLORA_PELLET_RELEASED generator=%d pellet=\d+ colour=\d+' % POSY_GENERATOR, text)),
        captured=bool(re.search(r'P2_FLORA_PELLET_CAPTURED generator=%d carriers=[1-9]\d*' % POSY_GENERATOR, text)),
        fixture_attack='P2_FLORA_FIXTURE_ATTACK_ASSIGNED count=' in text,
        fixture_captured='P2_FLORA_FIXTURE_CAPTURED carriers=' in text,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    # A bounded honest run prints an explicit BLOCKED marker instead of hanging.
    blocked = sorted(name for name in ('ready', 'fell', 'released', 'captured')
                     if ('P2_FLORA_RUNTIME_BLOCKED %s' % name) in text)
    return dict(passed=not failed, failed=failed, checks=required, blocked=blocked, exit_code=code,
                scope='P1 Palm proxy driven by real Pikmin attacks; Pellet Posy generator is a labeled fixture injection')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'flora')
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
    text = (directory / 'native.log').read_text(errors='replace')
    evidence = validate(text, code)
    evidence['directory'] = str(directory)
    evidence['exe'] = builder.snapshot([Path(exe)])
    evidence['leftover_pid'] = process.pid if pid_running(process.pid) else None
    evidence['no_leftover_process'] = evidence['leftover_pid'] is None
    evidence['passed'] = evidence['passed'] and evidence['no_leftover_process']
    (output / 'result.json').write_text(json.dumps(evidence, indent=2))
    print('flora', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'flora-keep-open.txt').write_bytes(b'Pellet Posy release fixture; close window to exit.\n')
    print('Pellet Posy release fixture.\n' + str(directory), flush=True)
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
