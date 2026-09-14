"""#448 plant / Spectralid-sentinel native fixture: build, stage, run, validate.

Mirrors experimental/pikmin2_flora_runtime.py. The fixture stages two (three)
P1 Plant actors with generator ids and a strict p2-plant.txt sidecar. It boots
the opt-in pc_port/pc_p2_plant.cpp policy layer and observes the LOD sizing, the
reserved sentinel plant's spawn decision, the slot-rule suppression and the
non-sentinel no-spawn.

The lane-15 pc_p2_qurione module is a visual-only binder with no spawn seam, so
a reserved sentinel plant reports `P2_PLANT_SENTINEL_BLOCKED reason=no_qurione_seam`
instead of forking the flier. The run is wall-clock bounded and self-terminates
with PASS or `P2_PLANT_RUNTIME_BLOCKED <gate> reason=...`; it never hangs.
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

# P1 PlantTypes (include/PlantMgr.h:14-30).
PLANT_CLOVER = 0
PLANT_TANPOPO = 4
PLANT_OOINU_L = 5

SENTINEL = 240021   # Ooinu_l, reserved -> ARMED + BLOCKED(no_qurione_seam)
NONSENTINEL = 240022  # Tanpopo, sentinel 0 -> NONE
SLOTRULE = 240023   # Clover carrying sentinel but not reserved -> SUPPRESSED

APP = r'''#include "GameStat.h"
#include "PlantMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>

class RoomApp : public PlugPikiApp {
	int frames = 0, ready = 0;
	unsigned startTick = 0;
	bool hold = false;
	void blocked(const char* gate, const char* reason) {
		std::printf("P2_PLANT_RUNTIME_BLOCKED %s reason=%s\n", gate, reason);
		std::fflush(nullptr);
		std::_Exit(0);
	}
public:
	int idle() override {
		int result = PlugPikiApp::idle();
		require(++frames < 12000, "Plant startup timeout");
		if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) {
			gameflow.mMoviePlayer->requestSkip();
			return result;
		}
		if (!pc_p2_preview_cargo_free_ready() || !naviMgr || !plantMgr) {
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
					std::puts("P2_PLANT_FIXTURE_GUARD_PIKMIN injection=1");
				}
			}
		}
		if (ready == 1) {
			for (int i = 0; i < DEMOFLAG_COUNT; ++i) {
				playerState->mDemoFlags.setFlagOnly(i);
			}
			std::ifstream holding("plant-keep-open.txt");
			hold = bool(holding);
		}
		if (++ready < 10) {
			return result;
		}
		if (!startTick) {
			startTick = SDL_GetTicks();
		}
		if (SDL_GetTicks() - startTick > 90000) {
			blocked("lod", "wall_clock_ceiling");
		}
		if (SDL_GetTicks() - startTick > 3000) {
			int count = 0;
			Iterator it(plantMgr);
			CI_LOOP(it) {
				Plant* plant = static_cast<Plant*>(*it);
				if (plant && plant->isAlive()) {
					++count;
				}
			}
			std::printf("P2_PLANT_FIXTURE_BOUND n=%d\n", count);
			if (count <= 0) {
				blocked("lod", "no_plant_actor");
			}
			capture("p2-plant.ppm");
			std::puts("PASS P2_PLANT_NATIVE lod_sentinel_slot_rule");
			std::fflush(nullptr);
			if (!hold) {
				std::_Exit(0);
			}
		}
		std::fflush(stdout);
		return result;
	}
};
'''

INCLUDES = ('#include <cstdio>\n#include <cstdlib>\n#include <fstream>\n'
            '#include "pc_p2_plant.h"\n'
            '#include "pc_p2_plant_policy.h"\n')


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return INCLUDES + source[:start] + APP + source[end:]


def plant_sidecar(specs):
    """Strict P2_PLANT_1 text, mirroring pc_p2_plant_policy.h."""
    if not isinstance(specs, (list, tuple)) or not 1 <= len(specs) <= 64:
        raise ValueError('Invalid plant record count')
    lines = ['P2_PLANT_1 %d' % len(specs)]
    seen = set()
    for spec in specs:
        generator_id = spec['generator']
        if not isinstance(generator_id, int) or not 0 <= generator_id <= 0xffffffff:
            raise ValueError('Invalid plant generator')
        if generator_id in seen:
            raise ValueError('Duplicate plant generator')
        seen.add(generator_id)
        if not isinstance(spec['sentinel'], int) or spec['sentinel'] not in (0, 1):
            raise ValueError('Invalid plant sentinel')
        lines.append('%d %s %s %s %d' % (generator_id, spec['species'], spec['lod_scale'], spec['floor_offset'],
                                         spec['sentinel']))
    return ('\n'.join(lines) + '\n').encode('ascii')


def build(native, build_dir, output, head):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(encoding='utf-8')), encoding='utf-8')
    return builder.build_fixture(build_dir, native, room, output / 'build', head)


def _plant_record(template, generator_id, plant_type, x, z, name):
    row = bytearray(template)
    struct.pack_into('<I', row, 8, generator_id)  # Generator::_70 (LE) read back as the id
    row[16:48] = name.ljust(32, b'\0')
    write_position(row, [x, 0.0, z])
    struct.pack_into('>I', row, 80, plant_type)  # GenObjectPlant::mPlantType
    return bytes(row)


def stage(assets, output):
    """Stage the practice course, a squad, three plants and a p2-plant.txt sidecar."""
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
        struct.pack_into('<I', row, 8, 235500 + i)
        row[16:48] = b'plant squad'.ljust(32, b'\0')
        write_position(row, [10 + i % 5 * 12, 30, 1890 + i // 5 * 12])
        struct.pack_into('>I', row, 92, 1)  # native Red
        entries.append(bytes(row))
    data = data[:20] + struct.pack('>I', len(entries)) + b''.join(entries)

    plant_source = assets / 'dataDir/stages/practice/plants.gen'
    plant_template = records(plant_source)[0]
    plants = (b''.join([
        _plant_record(plant_template, SENTINEL, PLANT_OOINU_L, -40.0, 1850.0, b'plant sentinel Ooinu_l'),
        _plant_record(plant_template, NONSENTINEL, PLANT_TANPOPO, -10.0, 1850.0, b'plant non-sentinel Tanpopo'),
        _plant_record(plant_template, SLOTRULE, PLANT_CLOVER, 20.0, 1850.0, b'plant slot-rule Clover'),
    ]))
    plants_data = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 3) + plants

    run = Path(output).resolve() / uuid.uuid4().hex
    run.mkdir(parents=True)
    empty = b'1.0v' + struct.pack('>4fI', -85, 0, 0, 45, 0)
    overrides = {'dataDir/stages/chal0.ini': (assets / 'dataDir/stages/practice.ini').read_bytes(),
                 'dataDir/stages/chal0/default.gen': data,
                 'dataDir/stages/chal0/plants.gen': plants_data}
    for p in (assets / 'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/' + p.name, empty)
    overlay(assets, run / 'assets', overrides)
    (run / 'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    sidecar = plant_sidecar([
        dict(generator=SENTINEL, species='Ooinu_l', lod_scale=1.5, floor_offset=0, sentinel=1),
        dict(generator=NONSENTINEL, species='Tanpopo', lod_scale=0.1, floor_offset=25, sentinel=0),
        dict(generator=SLOTRULE, species='Clover', lod_scale=9.0, floor_offset=25, sentinel=1),
    ])
    (run / 'p2-plant.txt').write_bytes(sidecar)
    (run / 'plant-stage.json').write_bytes((json.dumps(
        dict(scene='P1 Plant actors / P2 plant policy', sentinel=SENTINEL, nonsentinel=NONSENTINEL, slotrule=SLOTRULE,
             sidecar='p2-plant.txt', sidecar_sha256=builder.sha256(run / 'p2-plant.txt')), indent=2) + '\n').encode())

    required = {run / 'p2-plant.txt', run / 'p2-cargo-free.txt', run / 'assets/dataDir/stages/chal0.ini',
                run / 'assets/dataDir/stages/chal0/default.gen', run / 'assets/dataDir/stages/chal0/plants.gen',
                run / 'assets/dataDir/courses/practice/practice.mod'}
    missing = sorted(str(p) for p in required if not p.is_file())
    if missing:
        raise ValueError('Plant staging incomplete; missing: ' + ', '.join(missing))
    return run


def validate(text, code):
    required = dict(
        completion=code == 0 and 'PASS P2_PLANT_NATIVE' in text,
        lod=bool(re.search(r'P2_PLANT_LOD generator=%d species=Ooinu_l .*scale=1\.500.*bound=1' % SENTINEL, text))
            and bool(re.search(r'P2_PLANT_LOD generator=%d species=Tanpopo .*clamped=1' % NONSENTINEL, text))
            and bool(re.search(r'P2_PLANT_LOD generator=%d species=Clover .*floor_role=floor_offset floor_offset=40\.000.*reconstructed=1' % SLOTRULE, text)),
        sentinel_spawn=bool(re.search(r'P2_PLANT_SENTINEL_ARMED generator=%d species=Ooinu_l .*slot_reserved=1' % SENTINEL, text))
            and bool(re.search(r'P2_PLANT_SENTINEL_BLOCKED generator=%d species=Ooinu_l reason=no_qurione_seam' % SENTINEL, text)),
        non_sentinel_no_spawn=bool(re.search(r'P2_PLANT_SENTINEL_NONE generator=%d species=Tanpopo' % NONSENTINEL, text))
            and not re.search(r'P2_PLANT_SENTINEL_(ARMED|BLOCKED|SUPPRESSED) generator=%d ' % NONSENTINEL, text),
        slot_rule=bool(re.search(r'P2_PLANT_SENTINEL_SUPPRESSED generator=%d species=Clover reason=no_reserved_slot' % SLOTRULE, text)),
        no_qurione_fork='P2_QURIONE_BANK' not in text and 'P2_ENEMY_READY species=Qurione' not in text,
        no_rewards='P2_CARGO_READY' not in text and 'P2_POD_RECEIPT' not in text,
    )
    failed = sorted(name for name, ok in required.items() if not ok)
    blocked = sorted(name for name in ('lod', 'sentinel_spawn', 'non_sentinel_no_spawn')
                     if ('P2_PLANT_RUNTIME_BLOCKED %s' % name) in text)
    return dict(passed=not failed, failed=failed, checks=required, blocked=blocked, exit_code=code,
                scope='P1 Plant actors + module-local policy; sentinel spawn is BLOCKED reason=no_qurione_seam')


def pid_running(pid):
    out = subprocess.run(['tasklist', '/FI', 'PID eq %d' % pid, '/FO', 'CSV', '/NH'],
                         capture_output=True, text=True).stdout
    return str(pid) in out


def run(assets, output, exe):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directory = stage(assets, output / 'plant')
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
    print('plant', evidence['passed'], directory, flush=True)
    return evidence


def play(assets, output, exe):
    directory = stage(assets, output)
    (directory / 'plant-keep-open.txt').write_bytes(b'Plant fixture; close window to exit.\n')
    print('Plant fixture.\n' + str(directory), flush=True)
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
