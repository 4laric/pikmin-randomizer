"""Local-disc static hole/geyser visuals for the experimental cave transition."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_convert import convert, blocks, u16, u32, decode, write_model
from experimental.pikmin2_rigid import local_matrix

SOURCES = {
    'hole': ('user/Kando/objects/dungeon_hole/arc.szs', 'dungeon_hole.bmd'),
    'geyser': ('user/Kando/objects/kanketusen/arc.szs', 'kanketusen.bmd'),
}


def bind_pose(model):
    """Bake source local SRT, including the geyser's 1.163055 vertical scale."""
    joints=blocks(model)['JNT1'];pose=[]
    for index in range(u16(joints,8)):
        remap=u32(joints,16)
        record=u16(joints,remap+2*index) if remap else index
        at=u32(joints,12)+record*64
        if joints[at+2]!=0:raise ValueError('Transition joint scale compensation unsupported')
        scale=struct.unpack_from('>3f',joints,at+4)
        rotation=struct.unpack_from('>3h',joints,at+16)
        translation=struct.unpack_from('>3f',joints,at+24)
        if not all(math.isfinite(v) for v in (*scale,*translation)) or any(abs(v)<1e-8 for v in scale):
            raise ValueError('Invalid transition joint transform')
        matrix=local_matrix(rotation,translation)
        for row in range(3):
            for column in range(3):matrix[row][column]*=scale[column]
        pose.append(matrix)
    return pose


def convert_visible(source,target,kind):
    data=source.read_bytes();pose=bind_pose(data)
    if kind!='hole':return convert(source,target,approximate_materials=True,bake_rigid=True,pose=pose)
    # ItemHole::changeMaterial always hides its flag joint. Keep only the
    # audited main shape; reject changed layouts rather than showing a flag.
    b,arrays,shapes,mats=decode(data,True,True,pose)
    j=b['JNT1'];names=u32(j,20)
    labels=[j[names+u16(j,names+6+4*i):].split(bytes([0]),1)[0] for i in range(u16(j,names))]
    h=b['INF1'];tokens=[]
    for at in range(u32(h,20),len(h)-3,4):
        kind_id,index=struct.unpack_from('>HH',h,at)
        if kind_id==0:break
        if kind_id in (0x10,0x12):tokens.append((kind_id,index))
    if labels!=[b'dungeon_hole',b'flag'] or tokens!=[(16,0),(18,0),(16,1),(18,1)] or len(shapes)!=2:
        raise ValueError('Unexpected hole flag visibility layout')
    shapes=shapes[:1];mats=mats[:1]
    b['_render_states']=b['_render_states'][:1];b['_draw_order']=[0]
    # Remove hidden flag vertices too, so exported bounds describe visible rim.
    for attr,values in list(arrays.items()):
        used=sorted({v[attr] for shape in shapes for tri in shape for v in tri if attr in v})
        remap={old:new for new,old in enumerate(used)}
        arrays[attr]=[values[i] for i in used]
        for shape in shapes:
            for tri in shape:
                for vertex in tri:
                    if attr in vertex:vertex[attr]=remap[vertex[attr]]
    report=write_model((b,arrays,shapes,mats),target,str(source))
    report['hidden_source_joints']=['flag'];report['rigid_bind_pose_baked']=True
    target.with_suffix('.json').write_text(json.dumps(report,indent=2))
    return report


def extract(iso, output):
    """Preserve source model origin: exposed source states have zero bury depth."""
    output.mkdir(parents=True, exist_ok=False)
    catalog = disc_files(iso)
    result = dict(schema=1, models={}, source_sha256={},
                  limitations=['Static bind pose only: geyser animation and water particles are omitted.',
                               'Source collision platforms, buried/emerging states, sound and lifecycle FSM are not imported.',
                               'Visuals attach to existing engineering anchors; they do not establish retail placement fidelity.'])
    with iso.open('rb') as disc:
        for kind,(archive,model) in SOURCES.items():
            offset,size = catalog[archive]
            disc.seek(offset); data = disc.read(size)
            if len(data)!=size: raise ValueError('Truncated transition archive')
            result['source_sha256'][archive] = hashlib.sha256(data).hexdigest()
            files = archive_files(data)
            if model not in files: raise ValueError('Missing transition model')
            source = output/(kind+'.bmd')
            source.write_bytes(files[model])
            target = output/('cave_'+kind+'.mod')
            report = convert_visible(source,target,kind)
            result['models'][kind] = dict(file=target.name, sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                source_model=model, source_model_sha256=hashlib.sha256(files[model]).hexdigest(),
                bounds=report['bounds'], hidden_source_joints=report.get('hidden_source_joints',[]), placement=dict(y_offset=0, scale=1, yaw_degrees=0),
                material_policy=report.get('material_policy'),
                omitted_archive_files=sorted(name for name in files if name!=model))
    (output/'transition-assets.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(extract(args.iso,args.output),indent=2))
