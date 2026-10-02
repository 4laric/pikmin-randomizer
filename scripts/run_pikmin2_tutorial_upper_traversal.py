"""Broker-authorized bounded tutorial traversal; build receipts cannot launch it."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from scripts.stage_pikmin2_tutorial_upper_traversal import prepare
from scripts.fixture_platform import is_windows, linux_admission
from scripts.run_pikmin2_fixture import launch

MODES = ('ready', 'forced-down', 'paused-down', 'positive')
SUITE = 'tutorial-upper-traversal-runtime'
TARGET = 'pikmin_ci_fixture_tutorial_upper_traversal'
SOURCE = 'tools/p2_tutorial_upper_traversal_runtime.cpp'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_timeout(value):
    if not math.isfinite(value) or not 0 < value <= 60:
        raise ValueError('Owned native child must have a finite deadline <=60 seconds')


def environment(current, mode, private_save, executable):
    if mode not in MODES:
        raise ValueError('Unknown fixed traversal phase')
    result = {k: v for k, v in current.items()
              if (k == 'PIKMIN_SHA' or not k.upper().startswith(('PIKMIN_', 'P2_', 'COOP_', 'COOP_ONION_')))
              and k.upper() not in ('NECTAR_SAVE_DIR', 'NECTAR_EXECUTABLE_PATH', 'SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS')}
    result.update(NECTAR_SAVE_DIR=str(private_save), NECTAR_EXECUTABLE_PATH=str(executable),
                  SDL_AUDIODRIVER='dummy', SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS='1',
                  PIKMIN_RANDOMIZER_AUTOPLAY='0', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',
                  PIKMIN_P2_ROOM_WINDOW='960x540')
    if mode == 'ready': result['P2_UPPER_READY_ONLY'] = '1'
    if mode == 'forced-down': result['P2_UPPER_FORCE_DOWN'] = '1'
    if mode == 'paused-down': result['P2_UPPER_PAUSED_DOWN'] = '1'
    return result


def validate_proof(proof, root_head, native_head, source_sha):
    pins = proof.get('pins', {})
    if (proof.get('admitted') is not True or pins.get('FIXTURE_SUITE') != SUITE
            or proof.get('target') != TARGET or proof.get('source') != SOURCE
            or pins.get('PIKMIN_SHA') != root_head or pins.get('NATIVE_SHA') != native_head
            or pins.get('FIXTURE_SOURCE_SHA256') != source_sha):
        raise ValueError('Exact fixed traversal runtime/source admission required')


def assess(mode, raw, text):
    if not raw.get('launched', True) or raw.get('timed_out') or raw.get('error'):
        return False
    if mode in ('forced-down', 'paused-down'):
        return raw.get('exit_code') == 86 and raw.get('captain_down') is True and 'P2_UPPER_READY' not in text and 'PASS P2_UPPER_TRAVERSAL' not in text
    if not raw.get('passed') or raw.get('exit_code') != 0 or raw.get('captain_down'):
        return False
    marker = 'P2_UPPER_READY live=20 faces=5332 waters=3 start=west_bank gameplay_pass=0'
    if marker not in text or 'P2_UPPER_WINDOW size=960x540 centered=1' not in text:
        return False
    return mode == 'ready' or 'PASS P2_UPPER_TRAVERSAL original_reds=20 original_captain=1 all_outbound=21 all_returned=21 source_faces=5332 source_water=3 route=retail_bank_20_19 high_ridge=UNPROVEN ordinary_SDL=1 actor_writes=0 gamefeel=UNPLAYED' in text


@contextmanager
def child_environment(env):
    old = dict(os.environ)
    os.environ.clear(); os.environ.update(env)
    try:
        yield
    finally:
        os.environ.clear(); os.environ.update(old)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('assets', 'bundle', 'exe'):
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--native-sha', required=True)
    p.add_argument('--source-sha256', required=True)
    p.add_argument('--mode', choices=MODES, required=True)
    p.add_argument('--timeout', type=float, default=60)
    p.add_argument('--prepare-only', action='store_true')
    a = p.parse_args(); validate_timeout(a.timeout)
    destination = ROOT/'output/tutorial-upper-traversal'/uuid.uuid4().hex
    run = prepare(a.assets.resolve(strict=True), a.bundle.resolve(strict=True), destination)
    root_head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True)
    env = environment(os.environ, a.mode, destination/'private-save', a.exe.resolve())
    (run/'source-inputs.json').write_text(json.dumps(dict(root=root_head, root_dirty=dirty,
        native=a.native_sha, fixture_source_sha256=a.source_sha256, mode=a.mode,
        timeout=a.timeout, human_launched=False), indent=2)+'\n')
    if a.prepare_only:
        print(run); return 0
    if is_windows():
        raise ValueError('Windows artifact admission and human companion are separate pending work; this driver requires the reviewed fixed Linux broker')
    if dirty:
        raise ValueError('Runtime requires the exact published clean root')
    with child_environment(env):
        proof = linux_admission(a.exe, ROOT, destination, run)
        validate_proof(proof, root_head, a.native_sha, a.source_sha256)
        marker = 'P2_UPPER_READY' if a.mode == 'ready' else 'PASS P2_UPPER_TRAVERSAL'
        raw = launch(a.exe, run, ['--experimental-pikmin2-surface', 'tutorial'],
                     [marker], a.timeout, canonical_root=ROOT, session_root=destination)
    text = (run/'native.log').read_text(errors='replace') if (run/'native.log').exists() else ''
    passed = assess(a.mode, raw, text)
    record = dict(passed=passed, gameplay_pass=passed and a.mode=='positive', mode=a.mode,
                  raw=raw, admission=proof, original_inputs_sha256=digest(run/'upper-traversal-inputs.json'),
                  human_launched=False)
    (run/'acceptance-assessment.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record)); return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
