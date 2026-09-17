"""Machine-readable input package for the P1 Challenge guarded boot fixture (#649).

Builds per-stage (chal0..chal4) run inputs by consuming the campaign contract
read-only from its recorded commit (no merge: the contract file is owned by
the p1-challenge-campaign-contract lane) plus the canonical captain guard
header hash. No gameplay claims; the package is validated fail-closed before
any run.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

CONTRACT_PIN = '9aa6faad2c76b3182b5ad3de3f564d5e5431ba90'
CONTRACT_PATH = 'experimental/pikmin1_challenge_campaign_contract.py'
GUARD_PATH = 'scripts/p2_fixture_captain_guard.h'
GUARD_SHA256 = 'd2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474'
SLOT_RE = re.compile(r'^chal[0-4]$')


class InputError(ValueError):
    pass


def load_contract(root):
    """Import the campaign contract source from its recorded commit (read-only).

    The file is owned by the contract lane, so it is never merged or copied
    into this tree; it is executed from a git-show snapshot instead.
    """
    root = Path(root)
    proc = subprocess.run(['git', '-C', str(root), 'show',
                           CONTRACT_PIN + ':' + CONTRACT_PATH],
                          capture_output=True, timeout=60)
    if proc.returncode != 0:
        raise InputError('Contract commit unreadable: ' + CONTRACT_PIN)
    name = 'p1_challenge_campaign_contract_at_' + CONTRACT_PIN[:12]
    spec = importlib.util.spec_from_loader(name, loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(compile(proc.stdout.decode('utf-8-sig'), CONTRACT_PATH, 'exec'), module.__dict__)
    return module


def guard_record(root):
    """Hash-verify the canonical captain guard header (read-only)."""
    path = Path(root) / Path(*GUARD_PATH.split('/'))
    if not path.is_file():
        raise InputError('Missing captain guard header: ' + GUARD_PATH)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != GUARD_SHA256:
        raise InputError('Captain guard header drifted: ' + digest)
    return dict(path=GUARD_PATH, sha256=digest)


def audit_stage(contract, assets, slot):
    """Audit one vanilla stage from the legal asset tree (read-only)."""
    entry = contract.stage_entry(slot)
    ini = Path(assets) / entry['ini']
    if not ini.is_file():
        raise InputError('Missing stage ini for %s' % slot)
    return dict(slot=slot, area_id=entry['area_id'], name=entry['name'],
                ini=entry['ini'], ini_sha256=hashlib.sha256(ini.read_bytes()).hexdigest(),
                ini_size=ini.stat().st_size)


def build_input_package(root, contract_pin, assets, output):
    """Write the per-stage input package; return path and sha256."""
    if contract_pin != CONTRACT_PIN:
        raise InputError('Contract pin mismatch')
    contract = load_contract(root)
    guard = guard_record(root)
    slots = contract.stage_slots()
    if slots != ['chal%d' % n for n in range(5)]:
        raise InputError('Contract stage slots changed')
    stages = []
    for index, slot in enumerate(slots):
        audit = audit_stage(contract, assets, slot)
        audit.update(
            challenge_level=index,
            argv=['nectar.exe', '--experimental-challenge-level', str(index)],
            env={'PIKMIN_P2_ROOM_WINDOW': '960x540', 'SDL_AUDIODRIVER': 'dummy', 'PYTHONUTF8': '1'},
            acceptance=['Window 960x540 centred; live starting squad; no immediate extinction.',
                        'Stage identity row for level %d observed; no gameplay claims.' % index])
        stages.append(audit)
    packet = dict(schema=1, contract_pin=contract_pin, contract_path=CONTRACT_PATH,
                  guard=guard, stages=stages,
                  limitations=['Starting-squad composition, timers, scoring and retry semantics are unverified per the contract.',
                               'No claim of playability; P1 follow-on scopes remain OPEN.'])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'challenge-runtime-inputs.json'
    text = json.dumps(packet, indent=2, sort_keys=True) + '\n'
    path.write_text(text, encoding='utf-8', newline='')
    return dict(path=str(path), sha256=hashlib.sha256(text.encode('utf-8')).hexdigest())


def validate_package(obj):
    """Fail-closed validation of an input package dict."""
    if not isinstance(obj, dict) or obj.get('schema') != 1:
        raise InputError('Unknown input package schema')
    if obj.get('contract_pin') != CONTRACT_PIN or obj.get('contract_path') != CONTRACT_PATH:
        raise InputError('Input package contract pin mismatch')
    guard = obj.get('guard', {})
    if guard.get('path') != GUARD_PATH or guard.get('sha256') != GUARD_SHA256:
        raise InputError('Input package guard record mismatch')
    stages = obj.get('stages')
    if not isinstance(stages, list) or len(stages) != 5:
        raise InputError('Input package must carry exactly five stages')
    for index, stage in enumerate(stages):
        for key in ('slot', 'area_id', 'name', 'ini', 'ini_sha256', 'challenge_level', 'argv', 'env'):
            if key not in stage:
                raise InputError('Stage %d missing %s' % (index, key))
        if stage['slot'] != 'chal%d' % index or stage['challenge_level'] != index:
            raise InputError('Stage order/identity mismatch at index %d' % index)
        if not SLOT_RE.match(stage['slot']) or not isinstance(stage['ini_sha256'], str):
            raise InputError('Stage identity malformed at index %d' % index)
    return True


BOOT_RE = re.compile(r'P2_CHALLENGE_BOOT level=([0-4]) slot=(chal[0-4])')
SQUAD_RE = re.compile(r'P2_CHALLENGE_SQUAD pikis=(\d+)')


def validate_run_log(text):
    """Map a fixture log to observed/blocked (never a gameplay PASS).

    CAPTAIN_DOWN anywhere means blocked, even beside boot rows.
    """
    if 'P2_FIXTURE_CAPTAIN_DOWN' in text:
        return dict(observed=False, blocked=True, levels=[])
    levels = sorted({int(m.group(1)) for m in BOOT_RE.finditer(text)
                     if m.group(2) == 'chal%s' % m.group(1)})
    squads = [int(m.group(1)) for m in SQUAD_RE.finditer(text)]
    observed = bool(levels) and any(squad >= 1 for squad in squads)
    return dict(observed=observed, blocked=False, levels=levels)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    record = build_input_package(args.root, CONTRACT_PIN, args.assets, args.output)
    validate_package(json.loads(Path(record['path']).read_text(encoding='utf-8')))
    print(json.dumps(record, indent=2))