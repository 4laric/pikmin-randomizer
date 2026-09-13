"""Hash-bound Snagret/Segmented-Crawbster install into a private P1 run.

Pipeline section 4 (#376, parent #174, batch 1 #351). Consumes the batch-1
`snagret.json` schema-1 manifest and installs exact-byte per-species poses
(bound by SHA-256) plus a generator/species actor config and a receipt into an
already-private run directory. Every conflict or changed source is refused
BEFORE any mutation. The sampled pose bank is optional: when the `.mod` files
are absent the install proceeds with the actor config only and the room's
baseline visuals are preserved untouched.

The lane keeps two explicit identity classes from the batch-1 audit: the
shared-base snagret pair (SnakeCrow + SnakeWhole, both driven by
`Game::SnakeJointMgr` over the bodyjnt3-bodyjnt8 spine) and the standalone
segmented Crawbster (DangoMushi, direct `EnemyBase` + `EnemyBlendAnimatorBase`,
no SnakeJointMgr). Native registration belongs to the integration lead (#186)
and is flagged on #376; no shared/native code is changed here.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from experimental.pikmin2_snagret_assets import BASE_CLASSIFICATION, SHARED_BASE, SPECIES

MANIFEST = 'snagret.json'
POLICY = 'P2_SNAGRET_1'
POSE_PREFIX = 'snake'
ACTORS_TXT = 'p2-snagret-actors.txt'
ACTORS_HEADER = 'P2_SNAGRET_ACTORS_1'
BANK_TXT = 'p2-snagret-bank.txt'
BANK_HEADER = 'P2_SNAGRET_BANK_1'
INSTALL_JSON = 'snagret-install.json'
ROOM = 'assets/dataDir/courses/pikmin2room'
DIGEST = re.compile('[0-9a-f]{64}')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def classification():
    """Explicit shared-base vs standalone split, straight from the batch-1 audit."""
    return {
        'shared_base': {s: SHARED_BASE[s] for s in sorted(SHARED_BASE)
                        if SHARED_BASE[s] is not None},
        'standalone': {s: BASE_CLASSIFICATION[s]['animator']
                       for s in sorted(SHARED_BASE) if SHARED_BASE[s] is None},
    }


def bank_text(metadata):
    """Canonical LF clip/frame/event/pose listing for every sourced species."""
    rows = [BANK_HEADER]
    for species in sorted(SPECIES):
        info = metadata['species'][species]
        rows.append(f'species {species} {info["enemy_id"]}')
        for clip in info.get('clips', []):
            events = ','.join(f'{frame}:{event}'
                              for frame, event in clip.get('events', [])) or '-'
            poses = sum(1 for pose in clip.get('poses', []) if 'file' in pose)
            rows.append(f'clip {species} {clip["name"]} {clip.get("source_frames", 0)} '
                        f'{events} poses {poses} {clip.get("status", "unknown")}')
    return ('\n'.join(rows) + '\n').encode('ascii')


def plan(imported, actors):
    """Validate the actor roster and manifest and return exact payloads.

    Actor identity/count is checked before any import IO. The manifest schema,
    policy, non-claims and per-species enemy identity are validated next. Every
    converted pose is bound by SHA-256; the optional visual bank is
    all-or-nothing (partial or stray banks are refused). Never writes.
    """
    actors = [(generator, species) for generator, species in actors]
    if not 1 <= len(actors) <= 100:
        raise ValueError('Expected 1..100 actors')
    ids = set()
    rows = [ACTORS_HEADER, str(len(actors))]
    for generator, species in actors:
        if type(generator) is not int or not 0 <= generator <= 0xffffffff or generator in ids:
            raise ValueError('Invalid/duplicate actor identity')
        if species not in SPECIES:
            raise ValueError('Unsupported snagret actor species')
        ids.add(generator)
        rows.append(f'{generator} {species}')
    metadata = json.loads((imported / MANIFEST).read_text())
    if metadata.get('schema') != 1 or metadata.get('policy') != POLICY:
        raise ValueError('Unsupported snagret import schema/policy')
    for flag in ('native_ready', 'gameplay_events_executed', 'btk_playback'):
        if metadata.get(flag):
            raise ValueError(f'Import claims unsupported {flag}')
    info = metadata.get('species')
    if not isinstance(info, dict) or set(info) != set(SPECIES) or any(
            not isinstance(info[s], dict) or info[s].get('enemy_id') != i
            for s, i in SPECIES.items()):
        raise ValueError('Import species/ID mismatch')
    expected = {}
    for species in sorted(SPECIES):
        clips = info[species].get('clips')
        if not clips:
            raise ValueError('Missing species clips: ' + species)
        for clip in clips:
            for pose in clip.get('poses', []):
                name = pose.get('file')
                if name is None:
                    continue
                if (Path(name).name != name or not name.endswith('.mod')
                        or not name.startswith(f'{POSE_PREFIX}_{species}_')):
                    raise ValueError('Unsafe pose filename')
                digest = pose.get('sha256')
                if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
                    raise ValueError('Missing pose digest: ' + name)
                expected[name] = (species, digest)
    files = {}
    found = [n for n, (s, _) in expected.items() if (imported / s / n).is_file()]
    stray = [p.name for s in SPECIES for p in (imported / s).glob('*.mod')
             if p.name not in expected]
    if found or stray:
        if sorted(found) != sorted(expected) or stray:
            raise ValueError('Incomplete/unexpected snagret visual bank')
        for name, (species, digest) in expected.items():
            data = (imported / species / name).read_bytes()
            if sha(data) != digest:
                raise ValueError('Pose hash mismatch: ' + name)
            files[name] = data
    return dict(actors_config=('\n'.join(rows) + '\n').encode('ascii'),
                bank_config=bank_text(metadata),
                files=files, generators=[g for g, _ in actors],
                classification=classification(), metadata=metadata,
                import_sha256=sha((imported / MANIFEST).read_bytes()))


def install(imported, run, actors):
    """Install validated actor config (and optional visuals) into a private run."""
    actors = list(actors)
    payload = plan(imported, actors)
    room = run / ROOM
    if (not room.is_dir() or room.is_symlink() or room.is_junction()
            or room.resolve() != room.absolute()):
        raise ValueError('Expected private non-junction room directory')
    targets = [run / ACTORS_TXT, run / BANK_TXT, run / INSTALL_JSON]
    targets += [room / name for name in payload['files']]
    if any(t.exists() for t in targets):
        raise ValueError('Refusing existing/conflicting snagret installation')
    for other in sorted(run.glob('p2-*-actors.txt')) + (
            [run / 'p2-sheargrub.txt'] if (run / 'p2-sheargrub.txt').exists() else []):
        tokens = other.read_text().split()
        if len(tokens) < 2 or not tokens[0].startswith('P2_') or not tokens[0].endswith('_1'):
            raise ValueError('Invalid existing actor bindings: ' + other.name)
        used = set()
        for token in tokens[2:]:
            try:
                used.add(int(token))
            except ValueError:
                pass
        if used & set(payload['generators']):
            raise ValueError('Generator ID overlap with ' + other.name)
    for name, data in payload['files'].items():
        (room / name).write_bytes(data)
    (run / ACTORS_TXT).write_bytes(payload['actors_config'])
    (run / BANK_TXT).write_bytes(payload['bank_config'])
    receipt = dict(
        schema=1, policy=payload['metadata'].get('policy'),
        family='Snagret shared-base pair + standalone Segmented Crawbster',
        enemy_ids={s: SPECIES[s] for s in sorted(SPECIES)},
        generators=payload['generators'],
        actors=[{'generator': g, 'species': s} for g, s in actors],
        classification=payload['classification'],
        import_sha256=payload['import_sha256'],
        actors_config_sha256=sha(payload['actors_config']),
        bank_config_sha256=sha(payload['bank_config']),
        visuals='installed' if payload['files'] else 'absent_baseline_preserved',
        file_sha256={name: sha(data) for name, data in payload['files'].items()},
        gameplay_events_executed=False,
        native_registration='integration lead (#186); flagged on #376; not installed here')
    (run / INSTALL_JSON).write_bytes(
        (json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    return receipt


def verify_install(imported, run, actors):
    """Reload an installed layout and prove every artifact matches the import."""
    payload = plan(imported, actors)
    room = run / ROOM
    if (run / ACTORS_TXT).read_bytes() != payload['actors_config']:
        raise ValueError('Installed actor config mismatch')
    if (run / BANK_TXT).read_bytes() != payload['bank_config']:
        raise ValueError('Installed bank config mismatch')
    for name, data in payload['files'].items():
        target = room / name
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError('Installed visual mismatch: ' + name)
    receipt = json.loads((run / INSTALL_JSON).read_text())
    if receipt.get('actors_config_sha256') != sha(payload['actors_config']):
        raise ValueError('Installed receipt/config mismatch')
    return dict(verified=sorted(payload['files']), config=ACTORS_TXT,
                visuals=receipt.get('visuals'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('imported', 'run'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--actors', nargs=2, action='append', type=str, required=True,
                        metavar=('GENERATOR', 'SPECIES'))
    args = parser.parse_args()
    roster = [(int(g), s) for g, s in args.actors]
    print(json.dumps(install(args.imported, args.run, roster), indent=2))
