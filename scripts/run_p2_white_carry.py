"""Broker-authorized bounded tutorial traversal; build receipts cannot launch it."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from scripts.stage_p2_white_carry import prepare
from scripts.fixture_platform import is_windows, linux_admission
from scripts.run_pikmin2_fixture import launch

MODES = ('ready', 'forced-down', 'paused-down', 'positive')
SUITE = 'white-carry-sdl-runtime'
TARGET = 'pikmin_ci_fixture_white_carry'
SOURCE = 'tools/p2_white_carry_runtime.cpp'


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
    if mode == 'ready': result['P2_WHITE_CARRY_READY_ONLY'] = '1'
    if mode == 'forced-down': result['P2_WHITE_CARRY_FORCE_CAPTAIN_DOWN'] = '1'
    if mode == 'paused-down': result['P2_WHITE_CARRY_PAUSED_DOWN'] = '1'
    return result


def validate_proof(proof, root_head, native_head, source_sha):
    pins = proof.get('pins', {})
    if (proof.get('admitted') is not True or pins.get('FIXTURE_SUITE') != SUITE
            or proof.get('target') != TARGET or proof.get('source') != SOURCE
            or pins.get('PIKMIN_SHA') != root_head or pins.get('NATIVE_SHA') != native_head
            or pins.get('FIXTURE_SOURCE_SHA256') != source_sha):
        raise ValueError('Exact fixed traversal runtime/source admission required')


def rows(text,marker):
 result=[]
 for line in text.splitlines():
  if not line.startswith(marker+' '):continue
  pairs=re.findall(r'(\w+)=([^\s]+)',line)
  if len(pairs)!=len(dict(pairs)):raise ValueError('Duplicate observation key')
  result.append(dict(pairs))
 return result

def assess(text,receipt,*,economy,exit_code,elapsed_seconds,timed_out,source_proof):
 """Accept only compiled fixture observations plus production receipt bytes.

 Body strength, carry-speed power and physical carriers remain distinct. This
 does not certify source fidelity of the declared one-body engineering cargo.
 """
 if exit_code!=0 or timed_out or not math.isfinite(elapsed_seconds) or not 0<elapsed_seconds<=60:raise ValueError('Bounded raw0 required')
 if source_proof is not True:raise ValueError('Exact compiled source/guard/executable/catalog proof required')
 if any(s in text for s in ('P2_FIXTURE_CAPTAIN_DOWN','P2_WHITE_CARRY_FAIL')):raise ValueError('Native failure present')
 window=rows(text,'P2_WHITE_CARRY_WINDOW')
 if len(window)!=1 or window[0]!={'width':'960','height':'540','centered':'1'}:raise ValueError('Measured centered960x540 required')
 baseline=rows(text,'P2_WHITE_CARRY_BASELINE')
 if len(baseline)!=1 or baseline[0]!={'red':'20','white':'0','heads':'0','bodies':'20','cargo_min':'1','cargo_max':'1','initial_pokos':'0'}:raise ValueError('Exact engineering baseline required')
 acquired=rows(text,'P2_WHITE_CARRY_PLUCKED')
 if len(acquired)!=1 or acquired[0]!={'red':'19','white':'1','heads':'0','bodies':'20','spent':'1','ordinary_birth_pluck':'1'}:raise ValueError('Ordinary singleWhite acquisition required')
 order=[text.index('P2_WHITE_CARRY_WINDOW '),text.index('P2_WHITE_CARRY_BASELINE '),text.index('P2_WHITE_CARRY_PLUCKED '),text.index('P2_WHITE_CARRY_SAMPLE '),text.index('[Pikipelago] P2_POD_RECEIPT '),text.index('P2_WHITE_CARRY_PASS ')]
 if order!=sorted(order):raise ValueError('Original ordered physical phases required')
 samples=rows(text,'P2_WHITE_CARRY_SAMPLE')
 if len(samples)<10:raise ValueError('Sustained actual soleWhite transport missing')
 if any(text.index(line)>order[-2] for line in text.splitlines() if line.startswith('P2_WHITE_CARRY_SAMPLE ')):raise ValueError('Transport observations must precede receipt')
 previous=None;cargo_uid=None;white_uid=None
 for r in samples:
  frame=int(r['frame']);uid=int(r['cargo_uid']);white=int(r['white_uid'])
  if uid!=26:raise ValueError('Actual generated cargo identity26 required')
  if previous is not None and frame!=previous+1:raise ValueError('Consecutive original transport frames required')
  if cargo_uid is not None and (uid!=cargo_uid or white!=white_uid):raise ValueError('Carrier/cargo identity changed')
  previous=frame;cargo_uid=uid;white_uid=white
  exact={'carrier_white':'1','carrier_red':'0','carrier_other':'0','carrier_bodies':'1','strength':'1','native_strength':'1','mode':'9','body_total':'20','heads':'0'}
  if any(r.get(k)!=v for k,v in exact.items()):raise ValueError('Real soleWhite attachment/body/strength/transport required')
  if not math.isfinite(float(r['speed_power'])) or abs(float(r['speed_power'])-3)>1e-3:raise ValueError('Source leaf speedpower3 distinct from strength1')
  for key in ('x','y','z','goal_distance'): 
   if not math.isfinite(float(r[key])):raise ValueError('Finite physical geometry required')
 distance=math.hypot(float(samples[-1]['x'])-float(samples[0]['x']),float(samples[-1]['z'])-float(samples[0]['z']))
 if distance<30 or float(samples[0]['goal_distance'])-float(samples[-1]['goal_distance'])<20:raise ValueError('Actual towarddestination haul missing')
 deliveries=rows(text,'[Pikipelago] P2_POD_RECEIPT')
 if len(deliveries)!=1 or deliveries[0]!={'id':'treasure:white_carry_smoke','value':'1','new':'1','pokos':'1','seeds':'0'}:raise ValueError('Exactlyone original production receipt required')
 if economy!='P2_ECONOMY_1\ntreasure:white_carry_smoke 1\n':raise ValueError('Exact persistent production economy required')
 if receipt!='treasure=white_carry_smoke count=1 pokos=1\n':raise ValueError('Exact durable production receipt required')
 complete=rows(text,'P2_WHITE_CARRY_PASS')
 if len(complete)!=1 or complete[0]!={'cargo_removed':'1','stable_frames':'60','red':'19','white':'1','heads':'0','bodies':'20','pokos':'1'}:raise ValueError('Actual removedcargo/stableconservation completion required')
 return {'slice_passed':True,'gameplay_accepted':False,'scope':'ordinary singleWhite engineering onebody hauling+physicalPod receipt','full_campaign':False,'physical_displacement':distance,'carrier_uid':white_uid,'cargo_uid':cargo_uid}
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
    destination = ROOT/'output/white-carry'/uuid.uuid4().hex
    run = prepare(a.assets.resolve(strict=True), a.bundle.resolve(strict=True), destination)
    root_head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(ROOT), 'status', '--porcelain'], text=True)
    env = environment(os.environ, a.mode, destination/'private-save', a.exe.resolve())
    (run/'source-inputs.json').write_text(json.dumps(dict(root=root_head, root_dirty=dirty,
        native=a.native_sha, fixture_source_sha256=a.source_sha256, mode=a.mode,
        timeout=a.timeout, human_launched=False), indent=2)+'\n')
    (destination/'private-save').mkdir(exist_ok=False)
    if a.prepare_only:
        print(run); return 0
    if is_windows():
        raise ValueError('Windows artifact admission and human companion are separate pending work; this driver requires the reviewed fixed Linux broker')
    if dirty:
        raise ValueError('Runtime requires the exact published clean root')
    with child_environment(env):
        proof = linux_admission(a.exe, ROOT, destination, run)
        validate_proof(proof, root_head, a.native_sha, a.source_sha256)
        marker = 'P2_WHITE_CARRY_READY_PASS' if a.mode == 'ready' else 'P2_WHITE_CARRY_PASS'
        raw = launch(a.exe, run, ['--experimental-pikmin2-room'],
                     [marker], a.timeout, canonical_root=ROOT, session_root=destination)
    text = (run/'native.log').read_text(errors='replace') if (run/'native.log').exists() else ''
    passed=False
    if a.mode in ('forced-down','paused-down'):
        passed=raw.get('exit_code')==86 and raw.get('captain_down') is True and 'P2_WHITE_CARRY_PASS' not in text and 'P2_WHITE_CARRY_READY_PASS' not in text
    elif a.mode=='ready':
        passed=raw.get('passed') is True and raw.get('exit_code')==0 and 'P2_WHITE_CARRY_READY_PASS' in text
    else:
        try:
            assess(text,(run/'treasure-receipt.txt').read_text(),economy=(run/'p2-economy.txt').read_text(),exit_code=raw.get('exit_code'),elapsed_seconds=raw.get('elapsed_seconds'),timed_out=raw.get('timed_out'),source_proof=proof.get('admitted') is True)
            passed=True
        except (ValueError,KeyError,OSError,TypeError) as error:
            raw['white_carry_failure']=str(error)
    record = dict(passed=passed, gameplay_pass=passed and a.mode=='positive', mode=a.mode,
                  raw=raw, admission=proof, original_inputs_sha256=digest(run/'white-carry-inputs.json'),
                  human_launched=False)
    (run/'acceptance-assessment.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record)); return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
