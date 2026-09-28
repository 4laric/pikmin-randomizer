"""Lane 35 seeded model for cave unit-pool partition and phased trunk growth.

This is the slot-model / validator piece of the cave wave, not a renderer or a
second generator path. It partitions a decoded floor unit pool into the frozen
segment/choke/leaf classes and grows a deterministic per-floor structural table
(grow segment A -> forced choke -> segment B from the choke's far door -> hole in
B). Geometry rerolls with a per-entry salt; the seeded table does not.

It consumes the retail unit pool from ``pikmin2_cave_catalog`` and the per-unit
hazard classification owned by lanes 34/36; it places no items (37) and authors
no alcove units (36).
"""
import argparse
import json
from pathlib import Path

SEGMENT='segment'
CHOKE='choke'
LEAF='leaf'
EXCLUDED='excluded'
NONE='none'
MAX_CHOKES_PER_FLOOR=2
DEFAULT_ATTEMPTS=64
MARKER='P2_CAVE_GROWTH'
OPPOSITE=(2,3,0,1)
MASK=0xFFFFFFFFFFFFFFFF


def _seed_state(seed,context):
    value=0xCBF29CE484222325
    for byte in f'{seed}|{context}'.encode('utf-8'):
        value^=byte;value=(value*0x100000001B3)&MASK
    return value


class SeededRandom:
    """splitmix64 stream keyed by an integer seed plus a stable text context."""
    def __init__(self,seed,context=''):
        self.state=_seed_state(seed,context)

    def next_u64(self):
        self.state=(self.state+0x9E3779B97F4A7C15)&MASK
        value=self.state
        value^=(value>>30);value=(value*0xBF58476D1CE4E5B9)&MASK
        value^=(value>>27);value=(value*0x94D049BB133111EB)&MASK
        return value^(value>>31)

    def below(self,count):
        if count<=0:raise ValueError('Random bound must be positive')
        return self.next_u64()%count


def partition_pool(units,hazards=None):
    """Classify a decoded pool: no doors excluded, one door leaf, hazard two-plus
    doors choke, otherwise hazard-free segment."""
    hazards=hazards or {}
    result=dict(segments=[],chokes=[],leaves=[],excluded=[],slot={},hazard={},choke_hazards=[])
    for unit in sorted(units,key=lambda row:row['name']):
        name=unit['name'];hazard=hazards.get(name,NONE);doors=len(unit['doors'])
        if doors==0:
            result['excluded'].append(name);result['slot'][name]=EXCLUDED
        elif doors==1:
            result['leaves'].append(name);result['slot'][name]=LEAF
        elif hazard!=NONE:
            result['chokes'].append(name);result['slot'][name]=CHOKE
            if hazard not in result['choke_hazards']:result['choke_hazards'].append(hazard)
        else:
            result['segments'].append(name);result['slot'][name]=SEGMENT
        result['hazard'][name]=hazard
    result['choke_hazards']=sorted(result['choke_hazards'])
    return result


def build_table(seed,cave_id,floor,partition,chokes=None):
    """The per-floor seeded table. ``chokes`` is the provider's authoritative
    ordered hazard list; when absent a stable seed draw supplies one."""
    if chokes is None:
        remaining=sorted(partition['choke_hazards'])
        chokes=[]
        if remaining:
            rng=SeededRandom(seed,f'{cave_id}:floor{floor}:table')
            count=1+rng.below(min(MAX_CHOKES_PER_FLOOR,len(remaining)))
            for _ in range(count):
                chokes.append(remaining.pop(rng.below(len(remaining))))
        else:
            chokes=[]
    chokes=list(chokes)
    if len(set(chokes))!=len(chokes):raise ValueError('Floor chokes must be distinct hazards')
    for hazard in chokes:
        if hazard not in partition['choke_hazards']:
            raise ValueError('No choke unit provides hazard: '+hazard)
    return dict(schema=1,seed=seed,cave_id=cave_id,floor=floor,chokes=chokes,
                choke_count=len(chokes),choke_hazards=list(partition['choke_hazards']))


def _units_by_name(units):
    return units if isinstance(units,dict) else {unit['name']:unit for unit in units}


def _adjacency(nodes,edges):
    graph={node['id']:set() for node in nodes}
    for edge in edges:
        graph[edge['a']].add(edge['b']);graph[edge['b']].add(edge['a'])
    return graph


def _reachable(graph,start,forbidden):
    seen={start};todo=[start]
    while todo:
        current=todo.pop()
        for neighbour in graph[current]:
            if neighbour==forbidden or neighbour in seen:continue
            seen.add(neighbour);todo.append(neighbour)
    return seen


def _open_direction(unit,door,rotation):
    return (unit['doors'][door]['direction']+rotation)%4


def _attach(nodes,edges,counter,unit,slot,frontier,connect,far):
    wanted=(frontier['direction']+2)%4
    rotation=(wanted-unit['doors'][connect]['direction'])%4
    node=dict(id=f'n{counter[0]}',unit=unit['name'],kind=unit['kind'],slot=slot,rotation=rotation)
    counter[0]+=1;nodes.append(node)
    edges.append(dict(a=frontier['node'],a_door=frontier['door'],b=node['id'],b_door=far))
    return node,rotation


def _frontier_from(node,unit,door_index,rotation):
    return dict(node=node['id'],door=door_index,direction=_open_direction(unit,door_index,rotation))


def _attempt(table,units,partition,rng):
    segments=partition['segments']
    rooms=[name for name in segments if units[name]['kind']==1]
    if not segments or not rooms:return None

    nodes=[];edges=[];counter=[0]
    entry_name=rooms[rng.below(len(rooms))];entry_unit=units[entry_name]
    entry=dict(id='n0',unit=entry_name,kind=entry_unit['kind'],slot=SEGMENT,rotation=0)
    nodes.append(entry);counter[0]=1
    start_door=rng.below(len(entry_unit['doors']))
    frontier=_frontier_from(entry,entry_unit,start_door,0)

    def grow(names,require_room):
        nonlocal frontier
        for index,name in enumerate(names):
            if index==0 and require_room:
                name=rooms[rng.below(len(rooms))]
            unit=units[name]
            connect=rng.below(len(unit['doors']))
            others=[door for door in range(len(unit['doors'])) if door!=connect]
            far=others[rng.below(len(others))] if others else connect
            node,rotation=_attach(nodes,edges,counter,unit,SEGMENT,frontier,connect,far)
            frontier=_frontier_from(node,unit,far,rotation)

    grow(list(segments[rng.below(len(segments))] for _ in range(1+rng.below(3))),False)
    for hazard in table['chokes']:
        candidates=[name for name in partition['chokes'] if partition['hazard'].get(name)==hazard and len(units[name]['doors'])>=2]
        if not candidates:return None
        unit=units[candidates[rng.below(len(candidates))]]
        connect=rng.below(len(unit['doors']))
        others=[door for door in range(len(unit['doors'])) if door!=connect]
        far=others[rng.below(len(others))]
        node,rotation=_attach(nodes,edges,counter,unit,CHOKE,frontier,connect,far)
        frontier=_frontier_from(node,unit,far,rotation)
    final_segment_start=counter[0]
    grow(list(segments[rng.below(len(segments))] for _ in range(1+rng.below(3))),True)

    hole_candidates=[node['id'] for node in nodes if node['slot']==SEGMENT and node['kind']==1
                     and int(node['id'][1:])>=final_segment_start]
    if not hole_candidates:return None
    return dict(nodes=nodes,edges=edges,entry=entry['id'],hole_host=hole_candidates[-1])


def _path_check(nodes,edges,entry,hole_host,chokes):
    graph=_adjacency(nodes,edges)
    if hole_host not in _reachable(graph,entry,None):
        return dict(ok=False,detail='hole unreachable',choke_count=0,expected_chokes=len(chokes),details=[])
    details=[];ok=True
    for node in nodes:
        if node['slot']!=CHOKE:continue
        blocked=hole_host not in _reachable(graph,entry,node['id'])
        details.append(dict(choke=node['id'],unit=node['unit'],on_every_path=blocked))
        if not blocked:ok=False
    choke_count=sum(1 for node in nodes if node['slot']==CHOKE)
    if choke_count<len(chokes):ok=False
    return dict(ok=ok,choke_count=choke_count,expected_chokes=len(chokes),details=details)


def grow_floor(table,units,partition,salt=0,max_attempts=DEFAULT_ATTEMPTS):
    """Grow one floor entry; retry on failure instead of shipping an ungated layout."""
    units=_units_by_name(units)
    last_reason='no segment or room unit available'
    for attempt in range(max_attempts):
        rng=SeededRandom(table['seed'],f"{table['cave_id']}:floor{table['floor']}:geometry:{salt}:{attempt}")
        layout=_attempt(table,units,partition,rng)
        if layout is None:
            last_reason='attempt produced no segment A, choke fit, or hole room'
            continue
        check=_path_check(layout['nodes'],layout['edges'],layout['entry'],layout['hole_host'],table['chokes'])
        if not check['ok']:
            last_reason='forced choke not on every path'
            continue
        layout.update(status='ok',attempt=attempt,salt=salt,table=table,path_check=check)
        return layout
    return dict(status='failed',reason=last_reason,attempts=max_attempts,salt=salt,table=table,
                nodes=[],edges=[],entry=None,hole_host=None,path_check=None)


def format_log(layout):
    table=layout['table'];lines=[]
    lines.append(f"{MARKER} seed={table['seed']} cave={table['cave_id']} floor={table['floor']} salt={layout['salt']}")
    lines.append(f"{MARKER} table chokes={table['chokes']} choke_hazards={table['choke_hazards']}")
    if layout['status']=='failed':
        lines.append(f"{MARKER} FAIL reason={layout['reason']} attempts={layout['attempts']}")
        return '\n'.join(lines)+'\n'
    lines.append(f"{MARKER} attempt={layout['attempt']} entry={layout['entry']} hole_host={layout['hole_host']}")
    for node in layout['nodes']:
        lines.append(f"{MARKER} node id={node['id']} unit={node['unit']} slot={node['slot']} kind={node['kind']} rotation={node['rotation']}")
    for edge in layout['edges']:
        lines.append(f"{MARKER} edge {edge['a']}:{edge['a_door']} -> {edge['b']}:{edge['b_door']}")
    for detail in layout['path_check']['details']:
        lines.append(f"{MARKER} path choke={detail['choke']} unit={detail['unit']} on_every_path={str(detail['on_every_path']).lower()}")
    lines.append(f"{MARKER} PASS choke_count={layout['path_check']['choke_count']} on_every_path=true")
    return '\n'.join(lines)+'\n'


def load_pool(catalog_path,cave_id,floor):
    catalog=json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    cave=next((row for row in catalog['caves'] if row['cave_id']==cave_id),None)
    if cave is None:raise ValueError('Unknown cave: '+cave_id)
    if floor<1 or floor>cave['floor_count']:raise ValueError('Floor out of range: '+str(floor))
    parameters=None
    for row in cave['floors']:
        if row['first_floor']<=floor<=row['last_floor']:parameters=row['parameters'];break
    if parameters is None:raise ValueError('No floor definition covers '+str(floor))
    pool=parameters['f008']
    if pool not in catalog['unit_pools']:raise ValueError('Unknown unit pool: '+pool)
    return pool,catalog['unit_pools'][pool]['units']


def load_hazards(path):
    if path is None:return {}
    return {str(name):str(hazard) for name,hazard in json.loads(Path(path).read_text(encoding='utf-8')).items()}


def reroll_differs(table,units,partition,salt,count):
    first=None;differs=False
    for step in range(count):
        layout=grow_floor(table,units,partition,salt+step)
        signature=[(node['id'],node['unit'],node['rotation']) for node in layout.get('nodes',[])]
        if first is None:first=signature
        elif signature!=first:differs=True
    return differs


def run(catalog_path,cave_id,floor,seed,salt=0,hazards=None,chokes=None,max_attempts=DEFAULT_ATTEMPTS,output=None,verify_salts=0):
    pool,units=load_pool(catalog_path,cave_id,floor)
    partition=partition_pool(units,hazards)
    table=build_table(seed,cave_id,floor,partition,chokes)
    layout=grow_floor(table,units,partition,salt,max_attempts)
    result=dict(schema=1,pool=pool,seed=seed,cave_id=cave_id,floor=floor,
                hazards=hazards or {},partition=partition,table=table,
                layout={key:value for key,value in layout.items() if key!='table'},
                generated='model',native_validated=False)
    if verify_salts:
        result['reroll_geometry_differs']=reroll_differs(table,units,partition,salt,verify_salts)
    log=format_log(layout)
    if output is not None:
        output=Path(output);output.mkdir(parents=True,exist_ok=True)
        (output/'growth.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        (output/'growth.log').write_text(log,encoding='utf-8')
    return result,log


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=Path,required=True)
    parser.add_argument('--cave',default='forest_1')
    parser.add_argument('--floor',type=int,default=1)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--salt',type=int,default=0)
    parser.add_argument('--hazards',type=Path)
    parser.add_argument('--chokes')
    parser.add_argument('--attempts',type=int,default=DEFAULT_ATTEMPTS)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--verify-salts',type=int,default=0)
    args=parser.parse_args()
    chokes=args.chokes.split(',') if args.chokes else None
    result,log=run(args.catalog,args.cave,args.floor,args.seed,args.salt,
                   load_hazards(args.hazards),chokes,args.attempts,args.output,args.verify_salts)
    print(log,end='')
    print(json.dumps(dict(pool=result['pool'],status=result['layout']['status'],
                          chokes=result['table']['chokes'],generated=result['generated'])))
