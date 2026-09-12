"""Optional source-count Uji proxies in the authored Hole of Beasts scene."""
import argparse,json,hashlib,re,struct
from pathlib import Path
from experimental.pikmin2_beasts_content import stage
from experimental.pikmin2_sheargrub_install import install
from experimental.pikmin2_collision import ground_height
from scripts.preview_pikmin2_room import generator,records


def roster(content,room):
    rows=[r for r in content['enemies'] if r['source']['enemy_id'] in ('UjiA','UjiB')]
    if [(r['source']['enemy_id'],r['source']['minimum_count']) for r in rows]!=[('UjiB',4),('UjiA',2),('UjiA',2),('UjiA',2)]:raise ValueError('Unexpected source Uji definitions')
    # Authored choice among already transformed source candidates, not retail RNG.
    singles=[s for s in enumerate(room['spawns']) if s[1]['instance']==2 and s[1]['type']==1]
    groups=[s for s in enumerate(room['spawns']) if s[1]['instance']==2 and s[1]['type']==0]
    if len(singles)!=6 or len(groups)!=5:raise ValueError('Unexpected authored-room source slots')
    selected=[singles[i] for i in (0,1,3,4)]
    selected_groups=[groups[i] for i in (0,2,4)]
    result=[]
    for row_index,row in enumerate(rows):
        species=row['source']['enemy_id'];count=row['source']['minimum_count']
        for local in range(count):
            slot_index,slot=selected[local] if species=='UjiB' else selected_groups[row_index-1]
            offset=[0,0,0] if species=='UjiB' else [(-15 if local==0 else 15),0,0]
            if species=='UjiA' and not slot['min']<=count<=slot['max']:raise ValueError('Group exceeds source slot count')
            if offset[0]**2+offset[2]**2 > slot['radius']**2:raise ValueError('Engineering offset exceeds source radius')
            position=[a+b for a,b in zip(slot['position'],offset)]
            height=ground_height(room['vertices'],room['triangles'],position[0],position[2])
            if height is None or abs(height-position[1])>.1:raise ValueError('Source placement lacks matching ground')
            result.append(dict(instance_id=row['definition_id']+f':instance:{local}',generator=61000+len(result),species=species,
                source_slot_index=slot_index,source_slot=slot,engineering_offset=offset,position=position,angle=slot['angle'],corpse_value=1 if species=='UjiA' else 2))
    return result


def prepare(assets,assembly,pod,content_import,uji_import,output):
    content=json.loads((content_import/'content.json').read_text());room=json.loads((assembly/'collision.json').read_text());actors=roster(content,room)
    run=stage(assets,assembly,pod,content_import,output)
    path=run/'assets/dataDir/stages/chal0/default.gen';raw=path.read_bytes();entries=records(path)
    used={struct.unpack_from('<I',r,8)[0] for r in entries}
    if used&{r['generator'] for r in actors}:raise ValueError('Native generator collision')
    scaffold=generator(assets);starts=[m.start() for m in re.finditer(b'    0.0v',scaffold)]+[len(scaffold)]
    template=next(scaffold[a:b] for a,b in zip(starts,starts[1:]) if scaffold[a+16:a+48].rstrip(b'\0')==b'preview dwarf bulborb')
    install(uji_import,run,[(r['generator'],r['species']) for r in actors])
    for actor in actors:
        entry=bytearray(template);struct.pack_into('<I',entry,8,actor['generator']);entry[80]=18 if actor['species']=='UjiA' else 19
        entry[16:48]=f'proxy {actor["species"]} {actor["generator"]}'.encode().ljust(32,b'\0')
        struct.pack_into('>6f',entry,48,*actor['position'],0,actor['angle'],0);entries.append(entry)
    header=bytearray(raw[:24]);struct.pack_into('>I',header,20,len(entries));path.write_bytes(header+b''.join(entries))
    report=dict(schema=1,actors=actors,source_content_sha256=hashlib.sha256((content_import/'content.json').read_bytes()).hexdigest(),
        assembly_sha256=hashlib.sha256((assembly/'assembly.json').read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        native_validated=False,retail_generation=False,limitations=['P1 Kabekui proxy AI/collision with static P2 poses.','Transformed source candidate positions with authored selection/group offsets.','Plants and descent remain unsupported.'])
    (run/'beasts-uji-roster.json').write_text(json.dumps(report,indent=2)+'\n')
    actual={struct.unpack_from('<I',r,8)[0]:r[80] for r in records(path) if struct.unpack_from('<I',r,8)[0] in {a['generator'] for a in actors}}
    if actual!={a['generator']:18 if a['species']=='UjiA' else 19 for a in actors}:raise ValueError('Staged native identity mismatch')
    return run


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','assembly','pod','content-import','uji-import','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(prepare(a.assets.resolve(),a.assembly,a.pod,a.content_import,a.uji_import,a.output))
