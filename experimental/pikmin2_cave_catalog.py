"""General retail cave definition inventory, not selected/generated placements."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import BASE, parameters, safe_name, tree, unit_definition

RETAIL = ('tutorial_1','tutorial_2','tutorial_3','forest_1','forest_2','forest_3','forest_4',
          'yakushima_1','yakushima_2','yakushima_3','yakushima_4','last_1','last_2','last_3')
DROP_MODES={0:'none',1:'pikmin_or_leader',2:'pikmin',3:'leader',4:'carrying_pikmin',5:'earthquake'}


def integer(value,maximum=10000):
    if not isinstance(value,str) or not re.fullmatch(r'\d+',value):raise ValueError('Expected nonnegative integer')
    number=int(value)
    if number>maximum:raise ValueError('Integer exceeds catalog limit')
    return number


def number(value):
    try: result=float(value)
    except (ValueError,TypeError):raise ValueError('Expected numeric value') from None
    if not math.isfinite(result) or result<0:raise ValueError('Invalid nonnegative numeric value')
    return result


def enemy_token(raw, enemy_ids, treasure_ids):
    if not isinstance(raw,str) or not re.fullmatch(r'\$?[1-9]?[A-Za-z][A-Za-z0-9_]*',raw):
        raise ValueError('Malformed enemy token')
    name=raw;drop=0
    if name.startswith('$'):
        name=name[1:];drop=1
        if name[:1] in '123456789':drop=int(name[0]);name=name[1:]
    # TekiInfo::read splits at the FIRST underscore whose prefix is a known
    # enemy; underscores inside IDs such as KareOoinu_s are otherwise preserved.
    carried=None
    for i,c in enumerate(name):
        if c=='_' and name[:i] in enemy_ids:
            carried=name[i+1:];name=name[:i];break
    lookup={value.lower():value for value in enemy_ids}
    if name.lower() not in lookup:raise ValueError('Unknown enemy reference: '+name)
    name=lookup[name.lower()]
    if carried is not None and carried not in treasure_ids:raise ValueError('Unknown enemy cargo: '+carried)
    return dict(source_token=raw,enemy_id=name,carried_treasure=carried,drop_mode=drop,
                drop_semantics=DROP_MODES.get(drop,'source_accepts_unmapped_mode'))


def weighted_enemy(row,enemy_ids,treasure_ids):
    if len(row)!=3:raise ValueError('Invalid enemy record')
    result=enemy_token(row[0],enemy_ids,treasure_ids)
    weight=integer(row[1]);kind=integer(row[2],8)
    result.update(source_weight=weight,placement_type=kind)
    if kind==6:result.update(weight_semantics='plant_target_count',target_count=weight)
    else:result.update(weight_semantics='packed_minimum_and_weight',minimum_count=weight//10,selection_weight=weight%10)
    return result


def rows(node,width):
    if not isinstance(node,list) or not node:raise ValueError('Missing roster block')
    count=integer(node[0])
    if len(node)!=1+count*width or any(not isinstance(v,str) for v in node):raise ValueError('Malformed roster framing')
    return [node[1+i*width:1+(i+1)*width] for i in range(count)]


def parameter_block(node,strings=()):
    if not isinstance(node,list):raise ValueError('Expected parameter block')
    result=parameters(node)
    for at in range(0,len(node)-1,3):
        key,size,value=node[at:at+3]
        expected='-1' if key[0] in strings else '4'
        if size!=expected or not isinstance(value,str):raise ValueError('Parameter type mismatch')
    return result


def parse(text, enemy_ids, treasure_ids):
    nodes=tree(text)
    if len(nodes)<2 or not isinstance(nodes[0],list):raise ValueError('Missing cave header')
    header=parameter_block(nodes[0])
    if set(header)!={'c000'}:raise ValueError('Unsupported cave header')
    count=integer(nodes[1],128)
    if count<1 or integer(header['c000'],128)!=count:raise ValueError('Cave definition count mismatch')
    floors=[];cursor=2;occupied=set()
    known={f'f{i:03X}' for i in range(0x18)}-{'f00B','f00C','f00D','f00E','f00F'}
    for index in range(count):
        if cursor>=len(nodes) or not isinstance(nodes[cursor],list):raise ValueError('Missing floor parameters')
        p=parameter_block(nodes[cursor],('f008','f009','f00A'));cursor+=1
        if set(p)-known or not {'f000','f001','f008'}<=set(p):raise ValueError('Unsupported/incomplete floor parameters')
        for key,value in p.items():
            if key in ('f008','f009','f00A'):safe_name(value)
            elif key in ('f006','f016'):number(value)
            else:integer(value)
        first,last=integer(p['f000'],127),integer(p['f001'],127)
        if first>last or occupied.intersection(range(first,last+1)):raise ValueError('Overlapping/inverted floor range')
        occupied.update(range(first,last+1))
        version=integer(p.get('f015','0'))
        sections=4 if version>=1 else 3
        if cursor+sections>len(nodes):raise ValueError('Missing floor roster sections')
        enemies=[weighted_enemy(r,enemy_ids,treasure_ids) for r in rows(nodes[cursor],3)]
        treasures=[]
        for name,weight in rows(nodes[cursor+1],2):
            if name not in treasure_ids:raise ValueError('Unknown treasure reference: '+name)
            weight=integer(weight);treasures.append(dict(treasure_id=name,source_weight=weight,minimum_count=weight//10,selection_weight=weight%10))
        gates=[]
        for name,life,weight in rows(nodes[cursor+2],3):
            # Ordinary ItemGateMgr only. Electric gates are a separate manager.
            if not name.startswith('gate'):raise ValueError('Unknown cave gate type')
            gates.append(dict(gate_id=name,life=number(life),selection_weight=integer(weight)))
        caps=[]
        if version>=1:
            node=nodes[cursor+3]
            if not isinstance(node,list) or not node:raise ValueError('Missing cap block')
            capcount=integer(node[0]);at=1
            for _ in range(capcount):
                if at>=len(node):raise ValueError('Truncated cap record')
                empty=integer(node[at],255);at+=1
                cap=dict(empty=bool(empty),source_empty_byte=empty)
                if not empty:
                    cap['enemy']=weighted_enemy(node[at:at+3],enemy_ids,treasure_ids);at+=3
                caps.append(cap)
            if at!=len(node):raise ValueError('Trailing cap data')
        cursor+=sections
        floors.append(dict(definition_index=index,first_floor=first+1,last_floor=last+1,parameters=p,
                           enemies=enemies,treasures=treasures,gates=gates,caps=caps))
    if cursor!=len(nodes):raise ValueError('Trailing cave data')
    return dict(schema=1,definition_count=count,floor_count=len(occupied),floors=floors,generated=False,
                limitations=['Weights/counts are definition inputs, not final spawn instances or placements.',
                             'No seeded topology, hole selection, radial distribution or restart identity is generated.'])


def inventory(iso, source, output):
    """Audit14retail definitions and referenced unit pools against local catalogs."""
    output.mkdir(parents=True,exist_ok=False);catalog=disc_files(iso);hashes={}
    enemy_source=source/'src/plugProjectYamashitaU/enemyInfo.cpp'
    enemy_raw=enemy_source.read_bytes()
    enemy_ids=set(re.findall(r'\{"([A-Za-z0-9_]+)"',enemy_raw.decode('utf-8')))
    from experimental.pikmin2_pod import pellet_catalog
    with iso.open('rb') as disc:
        def read(path):
            at,size=catalog[path];disc.seek(at);data=disc.read(size)
            if len(data)!=size:raise ValueError('Truncated disc source')
            hashes[path]=hashlib.sha256(data).hexdigest();return data
        archive=archive_files(read('user/Abe/Pellet/us/pelletlist_us.szs'))
        treasure_ids=set()
        for name in ('otakara_config.txt','item_config.txt'):
            treasure_ids.update(pellet_catalog(archive[name].decode('shift_jis')))
        caves=[];units={}
        for name in RETAIL:
            path=BASE+'/caveinfo/'+name+'.txt'
            cave=parse(read(path).decode('shift_jis'),enemy_ids,treasure_ids)
            cave.update(cave_id=name,source=path)
            for floor in cave['floors']:
                pool=floor['parameters']['f008'];poolpath=BASE+'/units/'+pool
                if pool not in units:
                    definitions=unit_definition(read(poolpath).decode('shift_jis'))
                    for unit in definitions:
                        for suffix in ('arc.szs','texts.szs'):
                            if f'{BASE}/arc/{unit["name"]}/{suffix}' not in catalog:raise ValueError('Missing unit asset')
                    units[pool]=dict(source=poolpath,units=definitions)
            caves.append(cave)
    result=dict(schema=1,disc='GPVE01 revision0',caves=caves,unit_pools=units,source_sha256=hashes,
                enemy_catalog_sha256=hashlib.sha256(enemy_raw).hexdigest(),generated=False)
    (output/'catalog.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','source','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=inventory(a.iso,a.source,a.output)
    print(json.dumps(dict(caves=len(r['caves']),floors=sum(c['floor_count'] for c in r['caves']),unit_pools=len(r['unit_pools']))))
