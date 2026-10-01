"""Source-bound single-treasure haul plan; static support is not native carrying proof."""
import heapq
import json
import math
from experimental.pikmin2_assets import disc_files
from experimental.pikmin2_assembly import transform
from experimental.pikmin2_beasts_floor3 import source_floor,economy,sha
from experimental.pikmin2_collision import ground_height
from experimental.pikmin2_pod import pellet_catalog

TREASURE='dia_c_green'
INSTANCE='forest_1:floor3:treasure:dia_c_green:0'
POD=(-85,-280)
SELECTIONS={
    'dia_c_green':(2,'room_north_1_hiba_tsuchi',0,1),
    'donutswhite':(0,'room_block1_3_hiba_tsuchi',2,0),
}


def directed_route(routes,start,end):
    nodes={p['id']:p for p in routes}
    if len(nodes)!=len(routes) or start not in nodes or end not in nodes:
        raise ValueError('Invalid route identities')
    if any(link not in nodes for node in routes for link in node['links']):
        raise ValueError('Unknown route destination')
    queue=[(0,start,[start])];best={start:0}
    while queue:
        distance,current,path=heapq.heappop(queue)
        if distance!=best[current]:continue
        if current==end:return path
        for following in nodes[current]['links']:
            cost=distance+math.dist(nodes[current]['position'],nodes[following]['position'])
            if cost<best.get(following,float('inf')):
                best[following]=cost;heapq.heappush(queue,(cost,following,path+[following]))
    raise ValueError('No directed source route to Pod anchor')


def support(room,points):
    probes=[]
    for segment,(a,b) in enumerate(zip(points,points[1:])):
        dx,dz=b[0]-a[0],b[2]-a[2];length=math.hypot(dx,dz)
        steps=max(1,math.ceil(length/10))
        for step in range(steps+1):
            for lateral in (-25,0,25):
                x=a[0]+dx*step/steps-(dz/length*lateral if length else 0)
                z=a[2]+dz*step/steps+(dx/length*lateral if length else 0)
                y=ground_height(room['vertices'],room['triangles'],x,z)
                if y is None:raise ValueError('Haul route strip lacks floor support')
                probes.append(dict(segment=segment,step=step,lateral=lateral,position=[x,y,z]))
    return probes


def terrain_observations(probes):
    """Report vertical changes without inventing a native traversability threshold."""
    previous={};changes=[]
    for probe in probes:
        key=(probe['segment'],probe['lateral'])
        if key in previous:
            before=previous[key]
            changes.append(dict(segment=key[0],lateral=key[1],
                from_step=before['step'],to_step=probe['step'],
                height_change=probe['position'][1]-before['position'][1]))
        previous[key]=probe
    return dict(min_height=min(p['position'][1] for p in probes),
        max_height=max(p['position'][1] for p in probes),
        largest_step=max(changes,key=lambda c:abs(c['height_change'])) if changes else None,
        native_traversability_verified=False)


def prepare(iso,catalog_path,units,assembly,treasure_package,output,*,treasure=TREASURE):
    if not isinstance(treasure,str) or treasure not in SELECTIONS:
        raise ValueError('Unknown floor3 haul treasure')
    room_index,unit_name,slot,row_index=SELECTIONS[treasure]
    instance=f'forest_1:floor3:treasure:{treasure}:0'
    craw=catalog_path.read_bytes();catalog=json.loads(craw);floor=source_floor(catalog)
    iraw=(units/'units.json').read_bytes();imported=json.loads(iraw)
    araw=(assembly/'assembly.json').read_bytes();assembled=json.loads(araw)
    praw=(treasure_package/'floor3.json').read_bytes();package=json.loads(praw)
    if (assembled['policy']!='P2_BEASTS_FLOOR3_ASSEMBLY_1' or assembled['catalog_sha256']!=sha(craw)
            or assembled['import_sha256']!=sha(iraw) or imported['catalog_sha256']!=sha(craw)
            or package['catalog_sha256']!=sha(craw) or package['source_definition']!=floor):
        raise ValueError('Haul source provenance differs')
    for name,digest in assembled['output_sha256'].items():
        if sha((assembly/name).read_bytes())!=digest:raise ValueError('Assembly changed')
    name,turn,offset=assembled['layout'][room_index]
    if name!=unit_name:raise ValueError('Expected selected source room instance')
    local_raw=(units/'units'/name/'collision.json').read_bytes()
    if sha(local_raw)!=imported['units'][name]['output_sha256']['collision.json']:
        raise ValueError('Source room changed')
    spawn=json.loads(local_raw)['spawns'][slot]
    if spawn['type']!=2:raise ValueError('Selected slot is not a source treasure point')
    room=json.loads((assembly/'collision.json').read_bytes())
    position=transform(spawn['position'],turn,offset)
    position[1]=ground_height(room['vertices'],room['triangles'],position[0],position[2])
    pod=[POD[0],ground_height(room['vertices'],room['triangles'],*POD),POD[1]]
    if position[1] is None or pod[1] is None:raise ValueError('Haul anchor lacks support')
    nearest=lambda point:min(room['routes'],key=lambda r:math.dist(point,r['position']))['id']
    path=directed_route(room['routes'],nearest(position),nearest(pod))
    nodes={p['id']:p for p in room['routes']}
    points=[position]+[nodes[i]['position'] for i in path]+[pod]
    probes=support(room,points)
    cargo=package['treasures'][treasure]
    model=(treasure_package/'treasures'/treasure/'treasure.mod').read_bytes()
    if sha(model)!=cargo['model_sha256'] or cargo['instance_id']!=instance:
        raise ValueError('Treasure model/identity changed')
    sources=dict(imported['source_sha256'])
    for name,digest in package['source_sha256'].items():
        if name in sources and sources[name]!=digest:raise ValueError('Conflicting source hashes')
        sources[name]=digest
    index=disc_files(iso)
    with iso.open('rb') as disc:
        def read(name):
            offset,size=index[name];disc.seek(offset);raw=disc.read(size)
            if len(raw)!=size:raise ValueError('Truncated source')
            return raw
        for name,digest in sources.items():
            if sha(read(name))!=digest:raise ValueError('Disc source changed')
        row=pellet_catalog(read('user/Abe/Pellet/us/otakara_config.txt').decode('shift_jis'))[treasure]
        if row!=cargo['source_config'] or economy(row)!={k:cargo[k] for k in ('value','weight','slots')}:
            raise ValueError('Treasure source economy differs')
    result=dict(schema=1,policy='P2_BEASTS_FLOOR3_HAUL_PLAN_1',cave='forest_1',floor=3,
        catalog_sha256=sha(craw),assembly_sha256=sha(araw),treasure_package_sha256=sha(praw),source_sha256=sources,
        cargo=dict(instance=instance,model=treasure,source_row=row_index,source_slot=slot,source_unit=unit_name,
            source_spawn=spawn,position=position,model_sha256=sha(model),**economy(row)),
        pod=pod,route=dict(waypoint_ids=path,points=points,width=50,probes=probes),
        native_ready=False,campaign_reward_authorized=False,
        limitations=['Explicit engineering placement from source type2 slot; not retail seeded selection.',
            'Directed graph and floor-strip support only; actor clearance/native transport must be tested separately.',
            'Engineering instance receipt only; no cave checkpoint, campaign reward or floor progression.',
            'Other source treasure, hazards and actors omitted.'])
    if treasure=='donutswhite':
        result['terrain_observations']=terrain_observations(probes)
        result['limitations'] += [
            'Raised source platform and vertical probe changes require native transport validation.',
            'The 50-unit strip does not cover the full donut model footprint or attached carriers.']
    output.mkdir(parents=True,exist_ok=False)
    (output/'haul.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
