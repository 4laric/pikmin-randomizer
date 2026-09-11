"""Opt-in per-generator adult family layout; names/IDs survive cache serialization."""
from pathlib import Path
import hashlib
from .spawn_data import ADULT_SLOTS, GENERATOR_SLOTS, SOURCE_FILES, CATALOG_HASH


def resolve_spawn_layout(seed, slot):
    from .seed import SeedRandom
    rng = SeedRandom(str(seed) + '/adult-slots-v1/' + slot)
    # Preserve the original total of nine Bulborbs and six Bulbears.
    for _ in range(256):
        actual = rng.shuffle([row['original'] for row in ADULT_SLOTS])
        # Early renewable sources in both areas; no timed-only species guarantee.
        if all({actual[i] for i, row in enumerate(ADULT_SLOTS) if row['stage'] == stage
                and row['first_day'] == 2 and 0 < row['respawn_days'] <= 5
                and (row['expires_after_day'] is None or row['expires_after_day'] >= 29)} == {4, 32}
               for stage in (1, 3)):
            return dict(version='adult-slots-v1', catalog_hash=CATALOG_HASH,
                        assignments=[dict(uid=row['uid'], actual=value) for row, value in zip(ADULT_SLOTS, actual)])
    raise ValueError('could not assign persistent sources for both adult species')


def spawn_sources(layout):
    from .enemies import resolve_layout
    sources = [row for row in resolve_layout(0)['sources'] if row['original'] not in (4, 32)]
    for slot, assignment in zip(ADULT_SLOTS, layout['assignments']):
        # Temporary encounters remain in the saved layout, but are not needed by logic.
        if slot['expires_after_day'] is not None and slot['expires_after_day'] < 29: continue
        sources.append(dict(stage=slot['stage'], original=slot['original'], actual=assignment['actual'],
                            protected=False, first_day=slot['first_day']))
    return dict(version='adult-slot-sources-v1', sources=sources)


def bootstrap_slots(manifest):
    if 'spawn_layout' not in manifest: return ''
    return 'ENEMY_SLOTS ' + CATALOG_HASH + ' 15 ' + ' '.join(f"{r['uid']} {r['actual']}" for r in manifest['spawn_layout']['assignments']) + '\n'


def spoiler(manifest):
    if 'spawn_layout' not in manifest:
        raise ValueError('this seed does not use per-spawn enemies')
    names = {4: 'Spotty Bulborb', 32: 'Spotty Bulbear'}
    return [dict(slot, original_name=names[slot['original']], actual=assignment['actual'],
                 actual_name=names[assignment['actual']], protected=False,
                 route_policy='All three colors and conservative corpse carrying requirements; physical route acceptance pending')
            for slot, assignment in zip(ADULT_SLOTS, manifest['spawn_layout']['assignments'])]


def verify_source_assets(assets):
    base = Path(assets) / 'dataDir/stages'
    for name, expected in SOURCE_FILES.items():
        path = base / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'per-spawn enemy catalog does not match asset file {name}')
    # Newly added campaign files could add an unmodeled source or duplicate encounter.
    import re
    for folder in ('practice', 'stage1', 'stage2', 'stage3', 'last'):
        for path in (base / folder).glob('*.gen'):
            if re.fullmatch(r'(default|init|plants|\d+(?:-\d+)?)\.gen', path.name) and f'{folder}/{path.name}' not in SOURCE_FILES:
                raise ValueError(f'unrecognized campaign generator {folder}/{path.name}')
