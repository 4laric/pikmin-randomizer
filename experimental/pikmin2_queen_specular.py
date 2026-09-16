"""Opt-in Queen bank: source diffuse UV1 and native BTK specular sidecar (#399)."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental import pikmin2_bulblax_material as material
from experimental.pikmin2_bulblax_bank import parse_bank, validate_files
from experimental.pikmin2_convert import Writer, blocks, decode, u16, u32
from experimental.pikmin2_material_srt import decode as decode_btk, bank_text
from experimental.pikmin2_frog_visual_audit import chunks, source_material

BTK = 'af0dde017624a5b30459b8ba55ed70a1d70de14f841ed58802b3b07565ef4eae'
POLICY = 'P2_QUEEN_SPECULAR_1'


def source_contract(model, btk):
    if hashlib.sha256(model).hexdigest() != material.SOURCES['Queen'] or hashlib.sha256(btk).hexdigest() != BTK:
        raise ValueError('Expected audited GPVE01 Queen BMD and BTK')
    report = decode_btk(btk)
    if report['duration'] != 30 or len(report['tracks']) != 1 or report['tracks'][0]['material'] != 'mat_queen_body':
        raise ValueError('Unexpected Queen material animation')
    metadata = source_material(model)[0]
    if metadata['tev_stage_count'] != 3 or material._shape_mapping(model) != [1, 0]:
        raise ValueError('Unexpected Queen material topology')
    stages = metadata['tev_stages']
    if stages[0]['rgb_arguments'] != [15,8,10,15] or stages[0]['rgb_scale'] != 1 or stages[1]['rgb_arguments'] != [15,10,8,0] or stages[1]['rgb_scale'] != 0:
        raise ValueError('Unsupported Queen combiner')
    b = blocks(model);m = b['MAT3'];r = u32(m,12)+u16(m,u32(m,16))*332
    gens = []
    for i in (0,1):
        at = u32(m,56)+u16(m,r+0x28+2*i)*4
        gens.append(list(m[at:at+3]))
    if gens != [[1,1,30],[1,5,60]]: raise ValueError('Unexpected Queen texgens')
    # Only UV/index topology is used below; positions/normals remain from each
    # verified posed MOD. Identity draw matrices avoid needing a skeletal pose.
    identity=[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]]
    decoded = decode(model, True, bake_rigid=True, draw_matrices=[identity for _ in range(u16(b['DRW1'],8))])
    return report, decoded, dict(source_bmd=material.SOURCES['Queen'], source_btk=BTK,
        body_shape=1, diffuse_texture=2, specular_texture=1, texgens=gens, source_stages=stages,
        omitted='Third color stage; source lighting rig is not reproduced')


def remap_uv(raw, arrays, shapes, body=1):
    """Bake source UV1 only for the body; position/normal chunks stay byte-identical."""
    found = chunks(raw)
    if body >= len(shapes) or 13 not in arrays or 14 not in arrays: raise ValueError('Missing source UV topology')
    offset = len(arrays[13]); values = arrays[13]+arrays[14]
    if len(values)>65535: raise ValueError('UV array exceeds native index range')
    if u32(found[24],8)!=offset: raise ValueError('Source/pose UV0 count mismatch')
    old_uv = b''.join(struct.pack('>2f',*v) for v in arrays[13])
    if found[24][32:32+len(old_uv)] != old_uv: raise ValueError('Source/pose UV0 differs')
    mesh = bytearray(found[80])
    if u32(mesh,8)!=len(shapes): raise ValueError('Source/pose shape count mismatch')
    at = 32
    for index, tris in enumerate(shapes):
        fields = struct.unpack_from('>4Ih4I',mesh,at)
        flags, triangles, size = fields[1],fields[-2],fields[-1]
        if triangles!=len(tris) or flags not in (9,13): raise ValueError('Unsupported native mesh')
        start = (at+34+31)//32*32
        if start+size>len(mesh) or mesh[start]!=0x90 or u16(mesh,start+1)!=3*len(tris): raise ValueError('Unsupported primitive framing')
        stride = 7+(2 if flags&4 else 0)
        for n,v in enumerate(v for tri in tris for v in tri):
            uv = start+3+n*stride+stride-2
            if uv+2>start+size or u16(mesh,uv)!=v[13]: raise ValueError('Source/pose vertex order mismatch')
            if index==body:
                if not 0<=v.get(14,-1)<len(arrays[14]): raise ValueError('Missing UV1 index')
                struct.pack_into('>H',mesh,uv,offset+v[14])
        at = start+size
    writer = Writer();writer.begin(24,len(values));writer.pad()
    for v in values: writer.put('2f',*v)
    writer.end()
    replacement = dict(found);replacement[24]=bytes(writer.data);replacement[80]=bytes(mesh)
    result = b''.join(replacement[tag] for tag in found)
    if any(chunks(result)[tag]!=data for tag,data in found.items() if tag not in (24,80)): raise AssertionError('Geometry/resources changed')
    return result


def prepare(imported, bank, output):
    imported, bank, output = map(Path,(imported,bank,output))
    model=(imported/'Queen/enemy.bmd').read_bytes();btk=(imported/'Queen/queenchappy_model.btk').read_bytes()
    animation, decoded, contract = source_contract(model,btk)
    if output.exists(): raise ValueError('Output must be fresh')
    material.prepare(imported,bank,output)
    report=json.loads((output/'bulblax-bank.json').read_text(encoding='utf-8'))
    parsed=parse_bank((output/'p2-bulblax-bank.txt').read_text())
    count=0
    for clip,info in parsed['Queen'].items():
        for i in range(info['poses']):
            path=output/'Queen'/f'bulblax_Queen_{clip}_{i:02}.mod'
            after=remap_uv(path.read_bytes(),decoded[1],decoded[2]);path.write_bytes(after)
            report['file_sha256'][path.name]=hashlib.sha256(after).hexdigest();count+=1
    data=bank_text(animation).encode('ascii');(output/'p2-queen-specular.txt').write_bytes(data)
    report['queen_specular']=dict(policy=POLICY, **contract, body_poses=count, diffuse_uv='source UV1 baked into host UV0',
        animation_sha256=hashlib.sha256(data).hexdigest(), clock='independent 30fps while alive', third_stage=False)
    report['material_profile']['fixes']['Queen']='Source UV1 diffuse base plus opt-in native BTK normal/specular layer'
    _,total=validate_files(output,parsed);report['queen_specular']['total_mod_bytes']=total
    (output/'bulblax-bank.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report['queen_specular']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('imported','bank','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();print(json.dumps(prepare(args.imported,args.bank,args.output),indent=2))
