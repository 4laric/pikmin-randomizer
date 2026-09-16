"""Per-floor source dependency closure; no selected placement or asset conversion."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_cave import BASE,safe_name
from experimental.pikmin2_pod import pellet_catalog

ROLES=('model','animation','animation_manager','texture','parameters','collision','stone')


def enemy_registry(text):
    registry={};symbols={};pending={}
    pattern=r'^\s*\{"([A-Za-z0-9_]+)",\s*EnemyTypeID::(EnemyID_\w+),\s*(-1|EnemyTypeID::EnemyID_\w+),\s*\d+,\s*\(([^)]*)\)'
    for line in text.splitlines():
        match=re.match(pattern,line)
        if not match:continue
        name,symbol,parent,flags=match.groups()
        strings=re.findall(r'"([^"]*)"',line)
        if len(strings)!=8:raise ValueError('Unexpected enemy resource table width')
        aliases=dict(zip(ROLES,(value or name for value in strings[1:]),strict=True))
        for alias in aliases.values():safe_name(alias)
        tail=line[line.rfind('"')+1:]
        child=re.search(r'EnemyTypeID::(EnemyID_\w+)',tail)
        row=dict(enemy_id=name,can_spawn='EFlag_CanBeSpawned' in flags,has_no_info='EFlag_HasNoInfo' in flags,
                 resource_families=aliases,source_flags=flags,parents=[],helpers=[])
        if name in registry and registry[name]!=row:raise ValueError('Conditional enemy metadata differs')
        registry[name]=row;symbols[symbol]=name
        pending[name]=(parent.split('::')[-1] if parent!='-1' else None,child.group(1) if child else None)
    if not registry:raise ValueError('Missing enemy registry')
    for name,(parent,child) in pending.items():
        for field,reference in (('parents',parent),('helpers',child)):
            if reference:
                if reference not in symbols:raise ValueError('Unknown enemy helper symbol')
                registry[name][field].append(symbols[reference])
    return registry


def closure(direct,registry):
    result={};todo=[(name,'direct') for name in direct]
    while todo:
        name,reason=todo.pop()
        if name not in registry:raise ValueError('Unknown enemy dependency: '+name)
        if reason=='direct' and not registry[name]['can_spawn']:raise ValueError('Nonspawnable enemy used directly: '+name)
        if name in result:
            result[name].add(reason);continue
        result[name]={reason}
        todo.extend((p,'parent_manager') for p in registry[name]['parents'])
        todo.extend((p,'spawned_helper') for p in registry[name]['helpers'])
    return [dict(registry[name],dependency_roles=sorted(result[name])) for name in sorted(result)]


def floor_dependencies(cave,floor,registry,cargo,unit_pools):
    prefix=f'{cave}:definition{floor["definition_index"]}'
    definitions=[];direct=[];required_cargo={}
    def add_enemy(enemy,origin,index):
        ident=f'{prefix}:{origin}:{index}'
        direct.append(enemy['enemy_id'])
        definitions.append(dict(definition_id=ident,kind=origin,source=enemy))
        if enemy.get('carried_treasure'):
            required_cargo.setdefault(enemy['carried_treasure'],[]).append(ident+':held')
    for index,enemy in enumerate(floor['enemies']):add_enemy(enemy,'enemy',index)
    for index,cap in enumerate(floor['caps']):
        if not cap['empty']:add_enemy(cap['enemy'],'cap_enemy',index)
    for index,item in enumerate(floor['treasures']):
        ident=f'{prefix}:treasure:{index}'
        definitions.append(dict(definition_id=ident,kind='loose_treasure',source=item))
        required_cargo.setdefault(item['treasure_id'],[]).append(ident)
    for index,gate in enumerate(floor['gates']):
        definitions.append(dict(definition_id=f'{prefix}:gate:{index}',kind='gate',source=gate))
    needed=[]
    for name in sorted(required_cargo):
        if name not in cargo:raise ValueError('Unknown cargo dependency: '+name)
        needed.append(dict(cargo[name],catalog_id=name,required_by=sorted(required_cargo[name])))
    pool=floor['parameters']['f008']
    if pool not in unit_pools:raise ValueError('Unknown unit pool')
    units=[u['name'] for u in unit_pools[pool]['units']]
    if len(units)!=len(set(units)):raise ValueError('Duplicate unit candidate')
    p=floor['parameters']
    return dict(dependency_id=prefix,first_floor=floor['first_floor'],last_floor=floor['last_floor'],
                definitions=definitions,enemies=closure(direct,registry),cargo=needed,unit_pool=pool,
                unit_candidates=sorted(units),fixtures=dict(gates=bool(floor['gates']),
                    has_geyser=p.get('f007','0')=='1',clogged_hole=p.get('f010','0')=='1',
                    hole_rule='Requires selected floor/end-of-cave generation rule; not inferred from geyser flag.'),
                selected_placements=False)


def audit(catalog_path,iso,source,output):
    output.mkdir(parents=True,exist_ok=False)
    raw=catalog_path.read_bytes();catalog=json.loads(raw)
    if catalog.get('schema')!=1 or catalog.get('generated') is not False:raise ValueError('Expected source definition catalog')
    enemy_raw=(source/'src/plugProjectYamashitaU/enemyInfo.cpp').read_bytes()
    if hashlib.sha256(enemy_raw).hexdigest()!=catalog['enemy_catalog_sha256']:raise ValueError('Enemy source changed since catalog audit')
    registry=enemy_registry(enemy_raw.decode('utf-8'));files=disc_files(iso);hashes={}
    with iso.open('rb') as disc:
        def read(path):
            if path not in files:raise ValueError('Missing source dependency: '+path)
            at,size=files[path];disc.seek(at);data=disc.read(size)
            if len(data)!=size:raise ValueError('Truncated source dependency')
            hashes[path]=hashlib.sha256(data).hexdigest();return data
        # Reject stale catalogs even when their paths still happen to exist.
        for path,expected in catalog['source_sha256'].items():
            if hashlib.sha256(read(path)).hexdigest()!=expected:raise ValueError('Catalog source hash differs: '+path)
        archive=archive_files(read('user/Abe/Pellet/us/pelletlist_us.szs'));cargo={}
        for config in ('otakara_config.txt','item_config.txt'):
            for name,entry in pellet_catalog(archive[config].decode('shift_jis')).items():
                path='user/Abe/Pellet/us/'+safe_name(entry['archive'])
                if path not in files:raise ValueError('Missing cargo archive')
                cargo[name]=dict(archive=path,model=entry['bmd'],value=int(entry['money']),weight=int(entry['min']),slots=int(entry['max']))
        caves=[];resources={}
        for cave in catalog['caves']:
            floors=[]
            for floor in cave['floors']:
                deps=floor_dependencies(cave['cave_id'],floor,registry,cargo,catalog['unit_pools'])
                for enemy in deps['enemies']:
                    name=enemy['enemy_id']
                    if name not in resources:
                        families=sorted(set(enemy['resource_families'].values()))
                        paths=sorted(p for p in files if any(p.startswith('enemy/data/'+family+'/') for family in families))
                        resources[name]=dict(resource_families=enemy['resource_families'],disc_files=paths,
                            material_dependencies=dict(model_archives=[p for p in paths if p.endswith('/model.szs')],
                                external_texture_files=[p for p in paths if p.endswith('.bti')],status='Source candidates; material feature support not evaluated.'),
                            availability='files_present' if paths else 'no_direct_files_requires_manager_review')
                    enemy['resource_dependency']=name
                for unit in deps['unit_candidates']:
                    paths=[f'{BASE}/arc/{safe_name(unit)}/{suffix}' for suffix in ('arc.szs','texts.szs')]
                    if any(path not in files for path in paths):raise ValueError('Missing unit dependency')
                    resources['unit:'+unit]=dict(disc_files=paths,material_dependencies=dict(model_archive=paths[0],status='Not decoded for material feature support.'))
                for item in deps['cargo']:
                    # Verify the specific model member, not just its archive name.
                    path=item['archive']
                    if path not in resources:
                        members=archive_files(read(path));resources[path]=dict(member_names=sorted(members))
                    matches=[name for name in resources[path]['member_names'] if name.lower()==item['model'].lower()]
                    if len(matches)!=1:raise ValueError('Missing or ambiguous cargo model member: '+path+':'+item['model'])
                    item['resolved_model_member']=matches[0]
                floors.append(deps)
            caves.append(dict(cave_id=cave['cave_id'],floors=floors))
    result=dict(schema=1,catalog_sha256=hashlib.sha256(raw).hexdigest(),source_sha256=hashes,caves=caves,
                resources=resources,limitations=['Definition dependency IDs are not spawned actor/receipt IDs.',
                    'Parent/helper closure is conservative; conditional source helper branches are not encounter counts.',
                    'Resource families/files are candidates, not proof every listed asset loads or converts.',
                    'No selected topology, placements or runtime support is implied.'])
    (output/'dependencies.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('catalog','iso','source','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=audit(a.catalog,a.iso,a.source,a.output)
    print(json.dumps(dict(caves=len(r['caves']),floor_definitions=sum(len(c['floors']) for c in r['caves']),resources=len(r['resources']))))
