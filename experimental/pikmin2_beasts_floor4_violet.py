"""Source-bound floor4 Violet placement plan; no retail generation or gameplay."""
import argparse
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files,disc_files
from experimental.pikmin2_assembly import transform
from experimental.pikmin2_beasts_final_floors import source_manifest,sha
from experimental.pikmin2_beasts_lifecycle_reference import proper_slots
from experimental.pikmin2_collision import ground_height

IDENTITY='forest_1:floor4:BlackPom:0'
GENERATOR=62002


def generation_context(population):
    if type(population) is not int or not 0<=population<=2147483647:
        raise ValueError('Expected nonnegative int32 global-plus-cave Purple population')
    return dict(cave='forest_1',floor=4,mode='story',global_plus_cave_purple=population,
        context_source='caller_supplied_generation_snapshot',native_global_population_verified=False,
        spawned_generators=[GENERATOR],conversion_budgets={IDENTITY:5},
        suppression_applies=False,source_rule='Pom::Mgr::birth: zero-based floor3 is not <2; cave f_01 is not t_01')


def prepare(iso,catalog_path,units,assembly,output,global_purple_count,selected=(2,0)):
    context=generation_context(global_purple_count)
    catalog_raw=catalog_path.read_bytes();catalog=json.loads(catalog_raw)
    floor=source_manifest(catalog)[3]['source_definition']
    imported_raw=(units/'units.json').read_bytes();imported=json.loads(imported_raw)
    assembled_raw=(assembly/'assembly.json').read_bytes();assembled=json.loads(assembled_raw)
    if (assembled['policy']!='P2_BEASTS_FLOOR4_ASSEMBLY_1' or assembled['floor']!=4
            or assembled['catalog_sha256']!=sha(catalog_raw) or assembled['import_sha256']!=sha(imported_raw)
            or imported['catalog_sha256']!=sha(catalog_raw) or imported['cave_id']!='forest_1'):
        raise ValueError('Floor4 assembly/catalog/import provenance differs')
    for name,digest in assembled['output_sha256'].items():
        if sha((assembly/name).read_bytes())!=digest:raise ValueError('Assembly input changed')
    room=json.loads((assembly/'collision.json').read_bytes())
    candidates=[]
    for instance,(name,turn,offset) in enumerate(assembled['layout']):
        raw=(units/'units'/name/'collision.json').read_bytes()
        if sha(raw)!=imported['units'][name]['output_sha256']['collision.json']:
            raise ValueError('Source room collision changed')
        for slot,spawn in enumerate(json.loads(raw)['spawns']):
            if spawn['type']!=8:continue
            point=transform(spawn['position'],turn,offset)
            ground=ground_height(room['vertices'],room['triangles'],point[0],point[2])
            candidates.append(dict(instance=instance,unit=name,source_slot=slot,source=spawn,
                transformed_position=point,ground=ground,position=[point[0],ground,point[2]] if ground is not None else None,
                yaw=(spawn['angle']+turn*90)%360,selected=False))
    if (not isinstance(selected,(tuple,list)) or len(selected)!=2
            or any(type(i) is not int or i<0 for i in selected)):
        raise ValueError('Expected instance/source-slot selection')
    chosen=[c for c in candidates if (c['instance'],c['source_slot'])==tuple(selected)]
    if len(chosen)!=1 or chosen[0]['ground'] is None:raise ValueError('Selected source slot lacks floor support')
    chosen[0]['selected']=True
    sources=dict(catalog['source_sha256'])
    for name,digest in imported['source_sha256'].items():
        if name in sources and sources[name]!=digest:raise ValueError('Conflicting source provenance')
        sources[name]=digest
    index=disc_files(iso)
    with iso.open('rb') as disc:
        def read(name):
            offset,size=index[name];disc.seek(offset);raw=disc.read(size)
            if len(raw)!=size:raise ValueError('Truncated disc source')
            return raw
        for name,digest in sources.items():
            if sha(read(name))!=digest:raise ValueError('Disc source changed')
        archive=read('enemy/parm/enemyParms.szs')
        params=archive_files(archive)['pom/enemyparm.txt']
        capacity=proper_slots(params)
        if capacity!=5:raise ValueError('Unsupported Pom capacity')
    result=dict(schema=1,policy='P2_BEASTS_FLOOR4_VIOLET_PLAN_1',cave='forest_1',floor=4,
        catalog_sha256=sha(catalog_raw),assembly_sha256=sha(assembled_raw),source_sha256=sources,
        pom_archive_sha256=sha(archive),pom_parameter_sha256=sha(params),slots_per_flower=capacity,
        source_definition=floor,generation_context=context,candidates=candidates,
        flower=dict(identity=IDENTITY,generator_id=GENERATOR,**chosen[0]),
        native_ready=False,retail_generation=False,
        limitations=['One explicitly selected source type8 slot in an authored assembly; not seeded retail selection.',
            'Source Y is grounded using collision support; yaw is recorded, not proof of native orientation.',
            'No Chappy, Hiba, cap helpers, plants, treasure, reward or floor transition is installed.',
            'Population is declared, not read from a native campaign; runtime conversion proof is separate.'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'violet.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','catalog','units','assembly','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--global-purple-count',type=int,required=True)
    args=parser.parse_args()
    prepare(args.iso,args.catalog,args.units,args.assembly,args.output,args.global_purple_count)
    print(args.output/'violet.json')
