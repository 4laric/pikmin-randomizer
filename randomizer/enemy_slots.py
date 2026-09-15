"""Opt-in per-generator adult family layout; names/IDs survive cache serialization."""
from pathlib import Path
import hashlib
from .spawn_data import ADULT_SLOTS, GROUP_SLOTS, GENERATOR_SLOTS, SOURCE_FILES, CATALOG_HASH


def resolve_spawn_layout(seed, slot, miniboss=False):
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
            if miniboss:
                extra = SeedRandom(str(seed) + '/miniboss-slots-v1/' + slot)
                candidates = [i for i,r in enumerate(ADULT_SLOTS) if r['first_day']==2 and 0 < r['respawn_days'] <= 5 and (r['expires_after_day'] is None or r['expires_after_day'] >= 29)]
                for attempt in range(256):
                    changed = list(actual)
                    for i, species in zip(extra.shuffle(candidates)[:3], extra.shuffle([9,17,24])): changed[i] = species
                    if all({4,32} <= {changed[i] for i in candidates if ADULT_SLOTS[i]['stage']==stage} for stage in (1,3)):
                        actual = changed
                        break
                else: raise ValueError('cannot retain renewable adult species with minibosses')
            return dict(version='miniboss-slots-v1' if miniboss else 'adult-slots-v1', catalog_hash=CATALOG_HASH,
                        assignments=[dict(uid=row['uid'], actual=value) for row, value in zip(ADULT_SLOTS, actual)])
    raise ValueError('could not assign persistent sources for both adult species')


def resolve_group_layout(seed, slot):
    from .seed import SeedRandom
    rng = SeedRandom(str(seed) + '/family-groups-v1/' + slot)
    choices = {}
    for stage, pair in ((1, (3,31)), (3, (3,31)), (1, (18,19))):
        rows = [r for r in GROUP_SLOTS if r['stage']==stage and r['original'] in pair]
        for _ in range(256):
            values = rng.shuffle(list(pair) * (len(rows)//2))
            if {v for r,v in zip(rows,values) if r['first_day']==min(x['first_day'] for x in rows)} == set(pair): break
        else: raise ValueError('could not retain early group species coverage')
        choices.update((r['uid'],v) for r,v in zip(rows,values))
    return dict(version='family-groups-v1',catalog_hash=CATALOG_HASH,
                assignments=[dict(uid=r['uid'],actual=choices[r['uid']]) for r in GROUP_SLOTS])


def spawn_sources(layout, groups=None):
    from .enemies import resolve_layout
    sources = [row for row in resolve_layout(0)['sources'] if row['original'] not in (4, 32)]
    for slot, assignment in zip(ADULT_SLOTS, layout['assignments']):
        # Temporary encounters remain in the saved layout, but are not needed by logic.
        if slot['expires_after_day'] is not None and slot['expires_after_day'] < 29: continue
        sources.append(dict(stage=slot['stage'], original=slot['original'], actual=assignment['actual'],
                            protected=False, first_day=slot['first_day']))
    if groups:
        sources = [r for r in sources if r['protected'] or r['original'] not in (3,31,18,19)]
        for slot, assignment in zip(GROUP_SLOTS, groups['assignments']):
            sources.append(dict(stage=slot['stage'],original=slot['original'],actual=assignment['actual'],protected=False,first_day=slot['first_day']))
    return dict(version='family-group-sources-v1' if groups else 'adult-slot-sources-v1', sources=sources)


def bootstrap_slots(manifest):
    if manifest.get('p2_layout'):
        # Opt-in experimental bridge; lazy so ordinary seeds never load lane 02/03.
        from experimental.pikmin2_seed_bridge import bootstrap_for_manifest
        return bootstrap_for_manifest(manifest)
    if 'campaign_layout' in manifest:
        from .campaign_enemies import campaign_bootstrap
        return campaign_bootstrap(manifest)
    if 'spawn_layout' not in manifest: return ''
    text = ('ENEMY_MINIBOSSES 1\n' if manifest.get('miniboss_enemies') else '') + 'ENEMY_SLOTS ' + CATALOG_HASH + ' 15 ' + ' '.join(f"{r['uid']} {r['actual']}" for r in manifest['spawn_layout']['assignments']) + '\n'
    if 'group_layout' in manifest:
        text += 'ENEMY_GROUPS ' + CATALOG_HASH + ' 12 ' + ' '.join(f"{r['uid']} {r['actual']}" for r in manifest['group_layout']['assignments']) + '\n'
    return text


def spoiler(manifest):
    if 'campaign_layout' in manifest:
        from .campaign_data import CAMPAIGN_SLOTS
        names={0:'Yellow Wollywog',3:'Dwarf Bulborb',4:'Spotty Bulborb',9:'Puffstool',11:'Swooping Snitchbug',15:'Fiery Blowhog',16:'Puffy Blowhog',17:'Armored Cannon Beetle',18:'Female Sheargrub',19:'Male Sheargrub',20:'Shearwig',24:'Mamuta',25:'Wogpole',30:'Water Dumple',31:'Dwarf Bulbear',32:'Spotty Bulbear',33:'Wollywog'}
        return [dict(r,actual=a['actual'],original_name=names[r['original']],actual_name=names[a['actual']]) for r,a in zip(CAMPAIGN_SLOTS,manifest['campaign_layout']['assignments'])]
    if 'spawn_layout' not in manifest:
        raise ValueError('this seed does not use per-spawn enemies')
    names = {9:'Puffstool',17:'Armored Cannon Beetle',24:'Mamuta',4: 'Spotty Bulborb', 32: 'Spotty Bulbear',3:'Dwarf Bulborb',31:'Dwarf Bulbear',18:'Female Sheargrub',19:'Male Sheargrub'}
    rows = list(zip(ADULT_SLOTS, manifest['spawn_layout']['assignments']))
    if 'group_layout' in manifest: rows += list(zip(GROUP_SLOTS, manifest['group_layout']['assignments']))
    return [dict(slot, original_name=names[slot['original']], actual=assignment['actual'],
                 actual_name=names[assignment['actual']], protected=False,
                 route_policy='All three colors and conservative corpse carrying requirements; physical route acceptance pending')
            for slot, assignment in rows]


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
