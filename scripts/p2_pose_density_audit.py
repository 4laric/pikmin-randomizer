"""Pose-density / frames-trailer / resident-budget audit of a staged P2 run (#895).

Reads the bank files a native run directory carries (the same files the
native loaders open) plus the pose MODs under
``assets/dataDir/courses/pikmin2room/`` and reports, per clip:

* ``poses`` and ``source_frames``, the pose source ``frames`` (explicit when
  the bank carries them, else the uniform native synthesis) and the largest
  gap between adjacent samples;
* whether a ``P2_*_BANK_1`` row carries the ``frames`` trailer
  (``P2_BANK_FRAMES_1``); rows without it fall back to uniform frames, which
  misplaces poses when a clip has conversion gaps;
* on-disk and native resident bytes (``pikmin2_animation.resident_clip_bytes``,
  the accounting of ``pc_p2_pose_loader.h``).

Acceptance checks (``violations``):

* density: every non-trivial clip (source_frames >= 3) has at least
  ``--min-poses`` poses (default 12) or samples no more than ``--max-gap``
  source frames apart (default 5);
* trailer: every ``P2_*_BANK_1`` clip row with poses carries a valid trailer;
* budget: every clip is within 1 MiB resident and every setup (bank file)
  within 48 MiB resident.

``--stage CONTENT --assets ASSETS`` first stages every identity in the content
root into a fresh run directory through the production installer
(``pikmin2_family_install.install_layout``), so the audit sees exactly what a
campaign run would load. Families drawn without a pose bank (Long Legs bind
meshes) are listed under ``not_pose_banks``.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_animation import (  # noqa: E402
    RESIDENT_CLIP_BYTES, RESIDENT_TOTAL_BYTES, resident_clip_bytes)

ROOM = Path('assets/dataDir/courses/pikmin2room')

# P2_*_BANK_1 files (batch2/batch3/Chappy grammar) -> MOD prefix.
BANK_PREFIX = {
    'p2-dweevil-bank.txt': 'ota', 'p2-flora-bank.txt': 'flora', 'p2-ground-bank.txt': 'ginv',
    'p2-uji-bank.txt': 'uji', 'p2-cannon-bank.txt': 'cannon', 'p2-waterwraith-bank.txt': 'ww',
    'p2-proxy-bank.txt': 'px', 'p2-aquatic-bank.txt': 'aquatic', 'p2-flying-bank.txt': 'fly',
    'p2-snagret-bank.txt': 'snake', 'p2-chappy-bank.txt': 'ch',
}
# Native setups whose resident TotalBytes (48 MiB) the families share.
SETUP = {'p2-dweevil-bank.txt': 'batch2', 'p2-flora-bank.txt': 'batch2', 'p2-ground-bank.txt': 'batch2',
         'p2-uji-bank.txt': 'batch2', 'p2-cannon-bank.txt': 'batch2', 'p2-waterwraith-bank.txt': 'batch2',
         'p2-proxy-bank.txt': 'batch2', 'p2-aquatic-bank.txt': 'batch3', 'p2-flying-bank.txt': 'batch3',
         'p2-snagret-bank.txt': 'batch3'}
NOT_POSE_BANKS = {'p2-long-legs-bank.txt': 'Long Legs bind meshes (no sampled pose bank; legs stay bind pose)'}


def uniform(count, duration):
    """Native p2batch2clock::uniformFrames."""
    if count <= 0 or duration <= 0:
        return []
    if count == 1:
        return [0]
    return [min(duration - 1, max(0, int(math.floor(i * (duration - 1) / (count - 1) + 0.5))))
            for i in range(count)]


def trailer_ok(frames, count, duration):
    return (len(frames) == count and count >= 1 and frames[0] == 0 and frames[-1] == duration - 1
            and all(a < b for a, b in zip(frames, frames[1:])))


def parse_bank1(text):
    """P2_*_BANK_1 rows: (species, clip, source_frames, poses, trailer frames or None)."""
    tokens = text.split()
    if not tokens or not re.fullmatch(r'P2_[A-Z0-9_]+_BANK_1', tokens[0]):
        raise ValueError('not a P2_*_BANK_1 file')
    rows, i = [], 1
    while i < len(tokens):
        word = tokens[i]
        if word == 'species':
            i += 3
        elif word == 'clip':
            species, name, frames = tokens[i + 1], tokens[i + 2], int(tokens[i + 3])
            if tokens[i + 5] != 'poses':
                raise ValueError(f'bad clip row at token {i}')
            poses = int(tokens[i + 6])
            i += 7
            while i < len(tokens) and tokens[i] not in ('species', 'clip', 'frames'):
                i += 1  # status words ("converted", "status converted", ...)
            trailer = None
            if i < len(tokens) and tokens[i] == 'frames':
                trailer = [int(v) for v in tokens[i + 1].split(',')] if i + 1 < len(tokens) else []
                i += 2
            rows.append((species, name, frames, poses, trailer))
        else:
            raise ValueError(f'unexpected token {word!r}')
    return rows


def parse_snow_rows(lines):
    """`name count duration f0 .. fN` rows (Frog/Tank/Kabuto/Dwarf Orange)."""
    out = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[1].isdigit() and parts[2].isdigit():
            count, duration = int(parts[1]), int(parts[2])
            frames = [int(v) for v in parts[3:3 + count]]
            if len(frames) == count:
                out.append((parts[0], count, duration, frames))
    return out


def clip_record(family, species, clip, count, duration, frames, explicit, stem, room, trailer=None):
    datas = []
    for index in range(count):
        path = room / f'{stem}_{index:02}.mod'
        datas.append(path.read_bytes() if path.is_file() else b'')
    missing = sum(1 for d in datas if not d)
    gap = max((b - a for a, b in zip(frames, frames[1:])), default=0)
    return dict(family=family, species=species, clip=clip, stem=stem, poses=count, source_frames=duration,
                frames=frames, explicit_frames=explicit, max_gap=gap, trailer=trailer,
                missing_files=missing, disk_bytes=sum(len(d) for d in datas),
                resident_bytes=resident_clip_bytes([d for d in datas if d]) if not missing else None)


def audit_run(run):
    run = Path(run)
    room = run / ROOM
    clips, setups, not_pose = [], {}, {}
    for bank, prefix in BANK_PREFIX.items():
        path = run / bank
        if not path.is_file():
            continue
        for species, name, duration, poses, trailer in parse_bank1(path.read_text()):
            if poses == 0:
                clips.append(dict(family=bank, species=species, clip=name, poses=0, source_frames=duration,
                                  frames=[], explicit_frames=False, max_gap=duration, trailer=None,
                                  missing_files=0, disk_bytes=0, resident_bytes=0, unconverted=True))
                continue
            dur = duration if duration >= 2 else max(poses, 2)
            explicit = trailer is not None and trailer_ok(trailer, poses, dur)
            frames = trailer if explicit else uniform(poses, dur)
            clips.append(clip_record(bank, species, name, poses, dur, frames, explicit,
                                     f'{prefix}_{species}_{name}', room,
                                     trailer='valid' if explicit else ('malformed' if trailer else 'missing')))
    snow = [('p2-dwarf-orange-bank.txt', None, lambda sp, c: f'dwarf_orange_{c}'),
            ('p2-kabuto.txt', 'Kabuto', lambda sp, c: f'kabuto_Kabuto_{c}'),
            ('p2-frog.txt', None, lambda sp, c: f'frog_{sp}_{c}'),
            ('p2-tank.txt', None, lambda sp, c: f'tank_{sp}_{c}')]
    for bank, fixed, stem in snow:
        path = run / bank
        if not path.is_file():
            continue
        species = fixed or ('BlueKochappy' if 'dwarf' in bank else None)
        for line in path.read_text().splitlines():
            parts = line.split()
            if len(parts) == 1 and parts[0][:1].isupper() and not parts[0].startswith('P2_'):
                species = parts[0]
                continue
            for name, count, duration, frames in parse_snow_rows([line]):
                clips.append(clip_record(bank, species, name, count, duration, frames, True,
                                         stem(species, name), room, trailer='explicit'))
    mamuta = run / 'p2-mamuta-bank.txt'
    if mamuta.is_file():
        tokens = mamuta.read_text().split()
        i = 2
        while i < len(tokens):
            name, source, count, events = tokens[i + 1], int(tokens[i + 2]), int(tokens[i + 3]), int(tokens[i + 4])
            frames = [int(v) for v in tokens[i + 6:i + 6 + count]]
            i += 6 + count + 1 + events
            clips.append(clip_record('p2-mamuta-bank.txt', 'Miulin', name, count, source, frames, True,
                                     f'miulin_{name}', room, trailer='explicit'))
    elif (run / 'p2-mamuta-actors.txt').is_file():
        clips.append(dict(family='p2-mamuta-actors.txt', species='Miulin', clip='*', poses=0, source_frames=0,
                          frames=[], explicit_frames=False, max_gap=0, trailer='no manifest', missing_files=0,
                          disk_bytes=0, resident_bytes=0, note='no p2-mamuta-bank.txt manifest staged'))
    for path in sorted(run.glob('sarai-*-poses.txt')):
        tokens = path.read_text().split()
        count = int(tokens[2])
        frames, models, i = [], [], 3
        for _ in range(count):
            frames.append(int(tokens[i]))
            models.append(tokens[i + 1])
            i += 26
        datas = [(room / m).read_bytes() if (room / m).is_file() else b'' for m in models]
        clips.append(dict(family=path.name, species='Sarai', clip=path.stem, models=models, poses=count,
                          source_frames=frames[-1] + 1 if frames else 0, frames=frames, explicit_frames=True,
                          max_gap=max((b - a for a, b in zip(frames, frames[1:])), default=0), trailer='explicit',
                          missing_files=sum(1 for d in datas if not d), disk_bytes=sum(len(d) for d in datas),
                          resident_bytes=sum(len(d) for d in datas), note='host loads every sample as a Shape'))
    groink = run / 'p2-groink-bank.txt'
    if groink.is_file():
        tokens = groink.read_text().split()
        count, i = int(tokens[1]), 2
        for _ in range(count):
            name, frames_n, events = tokens[i + 2], int(tokens[i + 3]), int(tokens[i + 4])
            i += 5 + 2 * events
            poses = int(tokens[i])
            frames = [int(v) for v in tokens[i + 1:i + 1 + poses]]
            i += 1 + poses
            clips.append(clip_record('p2-groink-bank.txt', 'MiniHoudai', name, poses, frames_n, frames, True,
                                     f'minihoudai_{name}', room, trailer='explicit'))
    for bank, why in NOT_POSE_BANKS.items():
        if (run / bank).is_file():
            not_pose[bank] = why
    staged = []
    for clip in clips:
        # A bank row for a species this run does not bind has no pose files
        # at all; native never loads it (only bound species are set up).
        if clip['poses'] and clip['missing_files'] == clip['poses']:
            continue
        staged.append(clip)
        if clip.get('resident_bytes') is not None:
            setup = SETUP.get(clip['family'], clip['family'])
            setups[setup] = setups.get(setup, 0) + clip['resident_bytes']
    return staged, setups, not_pose


def violations(clips, setups, min_poses=12, max_gap=5):
    out = []
    for c in clips:
        where = f"{c['family']} {c['species']} {c['clip']}"
        if c.get('unconverted'):
            out.append(f'unconverted: {where} (0 poses)')
            continue
        if c.get('note', '').startswith('no p2-mamuta'):
            out.append(f'manifest: {where}: {c["note"]}')
            continue
        if c['source_frames'] >= 3 and c['poses'] < min_poses and c['max_gap'] > max_gap:
            out.append(f"density: {where} poses={c['poses']} frames={c['source_frames']} max_gap={c['max_gap']}")
        if c['trailer'] in ('missing', 'malformed'):
            out.append(f"trailer: {where} {c['trailer']}")
        if c['missing_files']:
            out.append(f"files: {where} missing={c['missing_files']}")
        if c.get('resident_bytes') is not None and c['resident_bytes'] > RESIDENT_CLIP_BYTES:
            out.append(f"budget: {where} resident={c['resident_bytes']} > {RESIDENT_CLIP_BYTES}")
    for family, total in setups.items():
        if total > RESIDENT_TOTAL_BYTES:
            out.append(f'budget: {family} setup resident={total} > {RESIDENT_TOTAL_BYTES}')
    return out


def stage_all(content, run, assets):
    """Stage every identity in ``content`` into ``run`` via install_layout."""
    from experimental.pikmin2_family_install import install_layout
    sys.path.insert(0, str(ROOT / 'scripts'))
    from p2_prepare_content import ENUM_FOR_SOURCE
    manifest = json.loads((Path(content) / 'prepared.json').read_text())
    ids = {ENUM_FOR_SOURCE[i]: i for i in manifest['extracted']}
    enums = sorted(ids)
    bindings, actors = [], {}
    for n, enum in enumerate(enums):
        if enum not in ids:
            continue
        target = f'audit{n:02}'
        bindings.append(dict(target=target, source_id=ids[enum], enum_name=enum))
        actors[target] = 900000 + n
    Path(run).mkdir(parents=True, exist_ok=False)
    return install_layout(run, {'bindings': bindings}, Path(content), actor_bindings=actors,
                          retail_assets=Path(assets) if assets else None)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('run', type=Path, help='staged native run directory (bank files + assets/dataDir)')
    parser.add_argument('--stage', type=Path, default=None, help='content root to stage into RUN first')
    parser.add_argument('--assets', type=Path, default=None, help='retail P1 assets dir (with --stage)')
    parser.add_argument('--json', type=Path, default=None, help='write the full report here')
    parser.add_argument('--min-poses', type=int, default=12)
    parser.add_argument('--max-gap', type=int, default=5)
    parser.add_argument('--strict', action='store_true', help='exit 1 on any violation')
    args = parser.parse_args(argv)
    if args.stage is not None:
        stage_all(args.stage, args.run, args.assets)
    clips, setups, not_pose = audit_run(args.run)
    bad = violations(clips, setups, args.min_poses, args.max_gap)
    report = dict(run=str(args.run), clips=clips, setups_resident_bytes=setups, not_pose_banks=not_pose,
                  violations=bad,
                  summary=dict(clips=len(clips), violations=len(bad),
                               min_poses=min((c['poses'] for c in clips if c['poses']), default=0),
                               max_clip_resident=max((c['resident_bytes'] or 0 for c in clips), default=0),
                               max_clip_disk=max((c['disk_bytes'] for c in clips), default=0),
                               max_setup_resident=max(setups.values(), default=0)))
    if args.json:
        args.json.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
    print(json.dumps(report['summary']))
    for line in bad:
        print('VIOLATION', line)
    for bank, why in not_pose.items():
        print('NOT_POSE_BANK', bank, why)
    return 1 if (args.strict and bad) else 0


if __name__ == '__main__':
    sys.exit(main())
