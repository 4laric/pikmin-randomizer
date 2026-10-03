"""Authenticate retail cave descriptors; never infer scene authority from an alias."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import BASE, unit_definition
from experimental.pikmin2_cave_catalog import RETAIL, parse
from experimental.pikmin2_pod import pellet_catalog


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def authenticate(catalog_path, iso, source):
    raw = catalog_path.read_bytes()
    catalog = json.loads(raw)
    if catalog.get('schema') != 1 or catalog.get('generated') is not False:
        raise ValueError('Expected ungenerated retail cave catalog')
    if tuple(c['cave_id'] for c in catalog['caves']) != RETAIL:
        raise ValueError('Retail cave source order differs')
    files = disc_files(iso)
    authenticated = {}
    with iso.open('rb') as stream:
        for member, expected in catalog['source_sha256'].items():
            at, size = files[member]
            stream.seek(at)
            data = stream.read(size)
            if len(data) != size or digest(data) != expected:
                raise ValueError('Retail source differs: ' + member)
            authenticated[member] = data
    info = (source/'src/plugProjectYamashitaU/enemyInfo.cpp').read_bytes()
    if digest(info) != catalog['enemy_catalog_sha256']:
        raise ValueError('Enemy registry changed')
    header = (source/'include/Game/enemyInfo.h').read_bytes()
    text = header.decode('utf-8')
    ids = dict((name, int(value)) for name, value in re.findall(
        r'EnemyID_(\w+)\s*=\s*(-?\d+)', text))
    macro = text.split('#define IS_ENEMY_BOSS(id)', 1)[1].split('\n\n', 1)[0]
    bosses = set(re.findall(r'EnemyID_(\w+)', macro))
    symbols = dict(re.findall(r'\{"(\w+)",\s*EnemyTypeID::EnemyID_(\w+)', info.decode('utf-8')))
    # Hashes alone do not authenticate decoded rows supplied by a host catalog.
    # Reparse actual bytes and compare the complete floor and unit definitions.
    archive = archive_files(authenticated['user/Abe/Pellet/us/pelletlist_us.szs'])
    treasures = set()
    for member in ('otakara_config.txt', 'item_config.txt'):
        treasures.update(pellet_catalog(archive[member].decode('shift_jis')))
    for cave in catalog['caves']:
        expected_member = BASE+'/caveinfo/'+cave['cave_id']+'.txt'
        if cave['source'] != expected_member:
            raise ValueError('Cave source member alias')
        actual = parse(authenticated[expected_member].decode('shift_jis'), set(symbols), treasures)
        if any(cave[k] != actual[k] for k in ('definition_count','floor_count','floors')):
            raise ValueError('Decoded cave differs from authenticated bytes')
        for floor in actual['floors']:
            pool = floor['parameters']['f008']
            member = BASE+'/units/'+pool
            if (catalog['unit_pools'][pool]['source'] != member or
                    catalog['unit_pools'][pool]['units'] != unit_definition(authenticated[member].decode('shift_jis'))):
                raise ValueError('Decoded unit pool differs from authenticated bytes')
    result = dict(schema=1, catalog_sha256=digest(raw), enemy_header_sha256=digest(header),
                  enemy_catalog_sha256=digest(info), caves=[])
    for cave in catalog['caves']:
        occupied = []
        floors = []
        for definition in cave['floors']:
            occupied.extend(range(definition['first_floor'], definition['last_floor']+1))
            rows = []
            def enemy(row, kind, index):
                name = row['enemy_id']
                symbol = symbols[name]
                if symbol not in ids:
                    raise ValueError('Unknown numeric source enemy: '+symbol)
                return dict(kind=kind, index=index, source_id=ids[symbol], catalog_id=name,
                            source_token=row['source_token'], boss=symbol in bosses,
                            held_treasure=row['carried_treasure'] or '', drop_mode=row['drop_mode'],
                            placement_type=row['placement_type'], source_weight=row['source_weight'])
            for i, row in enumerate(definition['enemies']):
                rows.append(enemy(row, 'enemy', i))
            for i, cap in enumerate(definition['caps']):
                if not cap['empty']:
                    rows.append(enemy(cap['enemy'], 'cap_enemy', i))
            for i, row in enumerate(definition['treasures']):
                rows.append(dict(kind='loose_treasure', index=i, source_id=-1,
                                 catalog_id=row['treasure_id'], source_token=row['treasure_id'],
                                 boss=False, held_treasure='', drop_mode=0,
                                 placement_type=2, source_weight=row['source_weight']))
            # Gate and empty cap records stay in the authenticated full catalog.
            # Providers must not claim a complete floor by checking enemies only.
            floors.append(dict(definition_index=definition['definition_index'],
                               first_floor=definition['first_floor'], last_floor=definition['last_floor'],
                               unit_pool=definition['parameters']['f008'], rows=rows,
                               gates=definition['gates'], caps=definition['caps']))
        if sorted(occupied) != list(range(1, cave['floor_count']+1)):
            raise ValueError('Noncontiguous retail floor range')
        result['caves'].append(dict(cave_id=cave['cave_id'], source=cave['source'],
                                  source_sha256=catalog['source_sha256'][cave['source']],
                                  max_floor=max(occupied), floors=floors))
    return result


def cpp(context):
    """Metadata only: no models, textures, source text or invented placements."""
    quote = json.dumps
    out = ['// Generated by experimental.pikmin2_retail_context; metadata only.\n',
           'const std::vector<CaveDescriptor>& retailCatalog() {\n',
           ' static const std::vector<CaveDescriptor> value = {\n']
    for cave in context['caves']:
        out.append('  {'+','.join(quote(cave[k]) for k in ('cave_id','source','source_sha256'))+
                   ','+quote(context['catalog_sha256'])+','+str(cave['max_floor'])+',{\n')
        for floor in cave['floors']:
            out.append('   {'+','.join(str(floor[k]) for k in ('definition_index','first_floor','last_floor'))+
                       ','+quote(floor['unit_pool'])+','+str(len(floor['gates']))+','+
                       str(len(floor['caps']))+',{\n')
            for row in floor['rows']:
                out.append('    {'+','.join(quote(row[k]) for k in ('kind','catalog_id','source_token','held_treasure'))+
                           ','+','.join(str(row[k]) for k in ('index','source_id','drop_mode','placement_type','source_weight'))+
                           ','+str(row['boss']).lower()+'},\n')
            out.append('   }},\n')
        out.append('  }},\n')
    out.append(' };\n return value;\n}\n')
    return ''.join(out)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','iso','source','output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--cpp', type=Path)
    a = p.parse_args()
    result = authenticate(a.catalog, a.iso, a.source)
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output/'context.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    if a.cpp:
        a.cpp.write_text(cpp(result), encoding='utf-8')
    print(json.dumps(dict(caves=len(result['caves']), floors=sum(c['max_floor'] for c in result['caves']),
                         catalog_sha256=result['catalog_sha256'])))
