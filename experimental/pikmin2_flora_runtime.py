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
from scripts.preview_pikmin2_room import generator, overlay
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
	bool hold = false;
	Teki* posy = nullptr;
public:
	int idle() override {
		int result = PlugPikiApp::idle();
		require(++frames < 20000, "Flora startup timeout");
		if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
			gameflow.mMoviePlayer->requestSkip();
			return result;
		}
		if (!pc_p2_preview_ready() || !naviMgr || !pikiMgr || !tekiMgr || !pelletMgr || !mapMgr) {
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
		if (phase == 0) {
			Iterator it(tekiMgr);
			CI_LOOP(it) {
				Teki* teki = static_cast<Teki*>(*it);
				if (teki && teki->isAlive() && teki->mTekiType == TEKI_Palm) {
					posy = teki;
					break;
				}
			}
			require(posy != nullptr, "Pellet Posy proxy not present");
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
			require(++ticks < 14000, "posy did not fall");
			if (!posy->isAlive()) {
				std::printf("P2_FLORA_FIXTURE_FELL health=%.2f\n", posy->mHealth);
				phase = 2;
				ticks = 0;
			}
		} else if (phase == 2) {
			require(++ticks < 6000, "released pellet never captured");
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
    assets = Path(assets).resolve()
    blob = generator(assets)
    starts = [m.start() for m in re.finditer(b'    0.0v', blob)]
    if not starts or starts[0] != 24:
        raise ValueError('Unsupported generated room framing')
    entries = [blob[s:(starts[i + 1] if i + 1 < len(starts) else len(blob))] for i, s in enumerate(starts)]
    enemy = next((r for r in entries if len(r) > 80 and r[80] == 3), None)
    if enemy is None:
        raise ValueError('Missing P1 enemy generator template')
    posy = bytearray(enemy)
    posy[80] = 7  # TEKI_Palm, Pellet Posy
    struct.pack_into('>I', posy, 8, POSY_GENERATOR)
    posy[16:48] = b'flora pellet posy fixture'.ljust(32, b'\0')
    write_position(posy, [60.0, 0.0, -40.0])
    struct.pack_into('>I', posy, 92, 0)
    entries.append(bytes(posy))
    data = blob[:20] + struct.pack('>I', len(entries)) + b''.join(entries)

    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    sidecar = pelplant_sidecar([dict(generator=POSY_GENERATOR, stage='full', pellet=5, colour='blue')])
    (run / 'p2-flora-pelplant.txt').write_bytes(sidecar)
    (run / 'flora-stage.json').write_bytes((json.dumps(
        dict(scene='P1 Palm proxy / P2 Pelplant policy', source_id=0, sidecar='p2-flora-pelplant.txt',
             generator=POSY_GENERATOR, stage='full', pellet=5, colour='blue',
             sidecar_sha256=builder.sha256(run / 'p2-flora-pelplant.txt')), indent=2) + '\n').encode())
    return run


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_FLORA_PELPLANT_RUNTIME' in text,
        ready=bool(re.search(r'P2_FLORA_PELPLANT_READY generator=%d stage=full pellet=5 colour=blue' % POSY_GENERATOR, text)),
        fell=bool(re.search(r'P2_FLORA_PELPLANT_FELL generator=%d stage=full .*released_on_death=1 regrowth=0' % POSY_GENERATOR, text)),
        released=bool(re.search(r'P2_FLORA_PELLET_RELEASED generator=%d pellet=5' % POSY_GENERATOR, text)),
        captured=bool(re.search(r'P2_FLORA_PELLET_CAPTURED generator=%d carriers=[1-9]\d*' % POSY_GENERATOR, text)),
        fixture_attack='P2_FLORA_FIXTURE_ATTACK_ASSIGNED count=' in text,
        fixture_captured='P2_FLORA_FIXTURE_CAPTURED carriers=' in text,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    return dict(passed=not failed, failed=failed, checks=required, exit_code=code,
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
