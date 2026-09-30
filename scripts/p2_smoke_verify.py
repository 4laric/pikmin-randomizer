"""Headless verification for owner smoke packages (CONTRIBUTING "Playtest seeds").

Reads a native.log and reports the captain's real start and where every
requested instance bound, then fails loudly when the nearest instance of a
species is farther than a threshold or anything did not bind. Pure parsing is
unit-tested; ``launch_and_read`` runs a capacity-gated headless session.
"""
from __future__ import annotations

import glob
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAX_DISTANCE = 400.0

_CAPTAIN_MARKER = re.compile(r'CAPTAIN_START\b.*?\bx=(-?[\d.]+)\s+(?:y=-?[\d.]+\s+)?z=(-?[\d.]+)')
_AUTOPLAY_NAVI = re.compile(r'AUTOPLAY_(?:NAVI|WITHDRAW)\b.*?\bnavi=\((-?[\d.]+),(-?[\d.]+)\)')
_RESOLVE = re.compile(r'P2_SEED_RESOLVE source_id=(\d+) target=(\d+)\b.*?\bx=(-?[\d.]+) z=(-?[\d.]+)')
_FAILURE = re.compile(r'slot-rejected|P2_\w*UNBOUND|P2_\w*_REJECT|P2_\w*BIND_FAIL')
_READY = re.compile(r'P2_\w*READY\b[^\n]*?\bgenerator=(\d+)[^\n]*?\bx=(-?[\d.]+)[^\n]*?\bz=(-?[\d.]+)')
_BIND = re.compile(r'P2_\w*_BIND\b[^\n]*?\bgenerator=(\d+)(?![^\n]*visual_only=1)')
_GENERATOR = re.compile(r'\bgenerator=(\d+)')


def parse_log(text):
    """{'captain_start': (x, z, source) | None, 'instances': [...], 'failures': [...], 'ready': n}.
    Captain start prefers an explicit CAPTAIN_START marker, else the first
    AUTOPLAY_NAVI/WITHDRAW position (the bot is at rest on the first line)."""
    captain = None
    for line in text.splitlines():
        m = _CAPTAIN_MARKER.search(line)
        if m:
            captain = (float(m.group(1)), float(m.group(2)), 'CAPTAIN_START')
            break
    if captain is None:
        for line in text.splitlines():
            m = _AUTOPLAY_NAVI.search(line)
            if m:
                captain = (float(m.group(1)), float(m.group(2)), 'AUTOPLAY_NAVI')
                break
    seen, instances = set(), []
    for m in _RESOLVE.finditer(text):
        key = (int(m.group(1)), int(m.group(2)))
        if key in seen:
            continue
        seen.add(key)
        instances.append({'source_id': key[0], 'target': key[1], 'x': float(m.group(3)), 'z': float(m.group(4))})
    ready = {}
    for m in _READY.finditer(text):
        ready.setdefault(int(m.group(1)), (float(m.group(2)), float(m.group(3))))
    bound = {int(m.group(1)) for m in _BIND.finditer(text)} | set(ready)
    failures = []
    for line in text.splitlines():
        if _FAILURE.search(line):
            gen = _GENERATOR.search(line)
            failures.append((line.strip(), int(gen.group(1)) if gen else None))
    return {'captain_start': captain, 'instances': instances, 'failures': failures,
            'ready': ready, 'bound': bound}


def evaluate(parsed, assignments, bosses_uids=(), max_distance=DEFAULT_MAX_DISTANCE):
    """Verdict for ``assignments`` {uid: source_id}. Returns dict with per-species
    nearest distances, a problems list, and ok."""
    problems = []
    captain = parsed['captain_start']
    if captain is None:
        problems.append('no captain start in native.log (no CAPTAIN_START / AUTOPLAY_NAVI line; was autoplay on?)')
    by_target = {i['target']: i for i in parsed['instances']}
    bound = parsed['bound']
    ready = parsed['ready']
    wanted = dict(assignments)
    per_species = {}
    for uid, sid in sorted(wanted.items()):
        inst = by_target.get(uid)
        if inst is None:
            problems.append(f'slot {uid} (species {sid}) never resolved/bound in native.log')
            continue
        if inst['source_id'] != sid:
            problems.append(f'slot {uid}: wanted species {sid}, log resolved {inst["source_id"]}')
            continue
        if uid not in bound:
            problems.append(f'slot {uid} (species {sid}) resolved but has no READY/BIND line: it did not spawn')
            continue
        x, z = ready.get(uid, (inst['x'], inst['z']))
        dist = math.hypot(x - captain[0], z - captain[1]) if captain else None
        per_species.setdefault(sid, []).append({'uid': uid, 'x': x, 'z': z,
                                                'distance': None if dist is None else round(dist, 1)})
    for sid in sorted(set(wanted.values())):
        rows = per_species.get(sid, [])
        dists = [r['distance'] for r in rows if r['distance'] is not None]
        if not dists:
            problems.append(f'species {sid}: no instance with a measurable distance')
        elif min(dists) > max_distance:
            problems.append(f'species {sid}: nearest instance is {min(dists):.0f} units from the captain start '
                            f'(> {max_distance:.0f}); not "at the landing site"')
    for line, gen in parsed['failures']:
        # early UNBOUND lines are transient while a bank stages; only a generator
        # that never reaches READY/BIND (or a line naming no generator) is a failure
        if gen is not None and gen in bound:
            continue
        problems.append('native failure line: ' + line[:200])
    summary = {sid: {'nearest': min((r['distance'] for r in rows if r['distance'] is not None), default=None),
                     'instances': sorted(rows, key=lambda r: (r['distance'] is None, r['distance']))}
               for sid, rows in per_species.items()}
    return {'ok': not problems, 'problems': problems, 'captain_start': captain,
            'species': summary, 'ready_lines': len(parsed['ready']), 'max_distance': max_distance}


def capacity_gate(timeout=3600.0):
    return subprocess.run([sys.executable, str(ROOT / 'scripts' / 'capacity_gate.py'), '--kind', 'game',
                           '--wait', '--timeout', str(timeout)], cwd=ROOT).returncode == 0


def launch_and_read(seed_path, exe, assets, session_dir, content_dir=None, actors_path=None,
                    extra_env=None, cwd=ROOT, want_targets=(), timeout=300.0, settle=4.0, gate=capacity_gate,
                    purple_bank=None, purple_motion=None):
    """Capacity-gated headless launch (background window + autoplay so the log
    carries the captain start). Waits until the captain start and every wanted
    target are logged, then kills only the process tree it started. Returns the
    native.log text."""
    if gate is not None and not gate():
        raise RuntimeError('capacity gate did not admit a game session')
    session_dir = Path(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8='1', PIKMIN_RANDOMIZER_TEST_BACKGROUND='1',
               PIKMIN_RANDOMIZER_AUTOPLAY='1', **(extra_env or {}))
    cmd = [sys.executable, '-m', 'randomizer', 'run', str(seed_path), '--session-dir', str(session_dir),
           '--exe', str(exe), '--assets', str(assets)]
    if content_dir:
        cmd += ['--p2-content', str(content_dir)]
    if actors_path:
        cmd += ['--p2-actors', str(actors_path)]
    if purple_bank:  # #958: a --p2-purple-campaign seed does not launch without the Purple banks
        cmd += ['--purple-bank', str(purple_bank)]
    if purple_motion:
        cmd += ['--purple-motion', str(purple_motion)]
    proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    text = ''
    deadline = time.time() + timeout
    try:
        while time.time() < deadline and proc.poll() is None:
            logs = glob.glob(str(session_dir / 'runs' / '*' / 'native.log'))
            if logs:
                text = Path(logs[0]).read_text(encoding='utf-8', errors='replace')
                parsed = parse_log(text)
                have = {i['target'] for i in parsed['instances']}
                if parsed['captain_start'] and set(want_targets) <= have:
                    time.sleep(settle)
                    text = Path(logs[0]).read_text(encoding='utf-8', errors='replace')
                    break
            time.sleep(2.0)
    finally:
        if proc.poll() is None:  # only the tree this call started
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return text
