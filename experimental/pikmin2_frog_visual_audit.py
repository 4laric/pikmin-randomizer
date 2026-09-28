"""Read-only Frog source/baked geometry and material audit; no corrective export."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from experimental.pikmin2_convert import blocks,decode,u16,u32
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_skinning import draw_matrices

def chunks(raw,allow_source_footer=False):
    result={};at=0
    while at+8<=len(raw):
        tag,size=struct.unpack_from('>II',raw,at);end=at+8+size
        if end>len(raw) or tag in result:raise ValueError('Invalid MOD chunk')
        result[tag]=raw[at:end];at=end
        if tag==65535:break
    footer=raw[at:]
    if (footer and not (allow_source_footer and footer.startswith(b'// '))) or 65535 not in result:raise ValueError('Incomplete MOD')
    return result

def vertices(raw,allow_source_footer=False):
    block=chunks(raw,allow_source_footer)[16];count=u32(block,8)
    if not 1<=count<=1000000 or 32+count*12>len(block):raise ValueError('Invalid vertex array')
    values=[struct.unpack_from('>3f',block,32+i*12) for i in range(count)]
    if any(not math.isfinite(x) for v in values for x in v):raise ValueError('Nonfinite vertex')
    return values

def bounds(values):return [min(v[k] for v in values) for k in range(3)]+[max(v[k] for v in values) for k in range(3)]

def emitted_material(raw):
    b=chunks(raw)[48]
    # Audited writer layout: one single-stage TEV block per shape, static colors.
    count=u32(b,8)
    if not 1<=count<=32 or u32(b,12)!=count:raise ValueError('Expected generated material layout')
    for i in range(count):
        if u32(b,120+124*i)!=1:raise ValueError('Expected single-stage generated TEV')
    r=32+124*count;result=[]
    for i in range(count):
        if u32(b,r)&1==0 or u32(b,r+20)!=0:raise ValueError('Expected static generated PVW material')
        control=u32(b,r+36)
        result.append(dict(rgba=list(b[r+8:r+12]),lighting_control=control,diffuse_enabled=bool(control&1),specular_enabled=bool(control&2),stage_count=1,lighting_offset_in_chunk=r+36))
        texgens=u32(b,r+76);texture_count=u32(b,r+80+4*texgens)
        if texgens>1 or texture_count>1:raise ValueError('Unexpected generated texture layout')
        r+=84+4*texgens+64*texture_count
    if r>len(b):raise ValueError('Truncated generated material')
    return result

def source_material(model):
    m=blocks(model)['MAT3'];out=[]
    for i in range(u16(m,8)):
        r=u32(m,12)+u16(m,u32(m,16)+2*i)*332;channels=[]
        for c in range(4):
            index=u16(m,r+12+2*c)
            if index==65535:channels.append(None);continue
            a=u32(m,40)+index*8
            if a+8>len(m):raise ValueError('Truncated source channel')
            channels.append(dict(zip(('enabled','material_source','light_mask','diffuse_function','attenuation_function','ambient_source'),m[a:a+6])))
        colors=[]
        for c in range(2):
            index=u16(m,r+8+2*c);a=u32(m,32)+4*index
            if index==65535:colors.append(None)
            elif a+4>len(m):raise ValueError('Truncated source material color')
            else:colors.append(list(m[a:a+4]))
        stages=[]
        for stage in range(m[u32(m,88)+m[r+4]]):
            a=u32(m,92)+u16(m,r+0xe4+2*stage)*20;o=u32(m,76)+u16(m,r+0xbc+2*stage)*4
            if a+20>len(m) or o+4>len(m):raise ValueError('Truncated TEV data')
            stages.append(dict(order=list(m[o:o+3]),rgb_arguments=list(m[a+1:a+5]),rgb_operation=m[a+5],rgb_bias=m[a+6],rgb_scale=m[a+7],rgb_clamp=m[a+8],rgb_register=m[a+9]))
        out.append(dict(channel_count=m[u32(m,36)+m[r+2]],tev_stage_count=len(stages),channels=channels,material_rgba=colors,tev_stages=stages))
    return out

def audit(imported,assets,output):
    if output.exists():raise ValueError('Refusing existing audit output')
    manifest=json.loads((imported/'frogs.json').read_text());result=dict(schema=1,species={},changes_applied=False)
    for species,p1 in [('Frog','frog'),('MaroFrog','frow')]:
        root=imported/species;model=(root/'enemy.bmd').read_bytes()
        if hashlib.sha256(model).hexdigest()!=manifest['species'][species]['model_sha256']:raise ValueError('Source model hash mismatch')
        clip=next(c for c in manifest['species'][species]['clips'] if c['name']=='wait1');pose=clip['poses'][0]
        if pose['file']!=f'frog_{species}_wait1_00.mod' or pose['frame']!=0:raise ValueError('Unexpected audit pose')
        raw=(root/pose['file']).read_bytes();animation_bytes=(root/'wait1.bca').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pose['sha256']:raise ValueError('Pose hash mismatch')
        if hashlib.sha256(animation_bytes).hexdigest()!=clip['source_sha256']:raise ValueError('Source animation hash mismatch')
        b=blocks(model);_,animation=bca_pose(animation_bytes,pose['frame'],u16(b['JNT1'],8),allow_scale=True)
        original=decode(model,True,bake_rigid=True,draw_matrices=draw_matrices(b,animation))[1][9];converted=vertices(raw)
        if len(original)!=len(converted):raise ValueError('Vertex count changed')
        error=max(abs(a-b) for v,w in zip(original,converted) for a,b in zip(v,w))
        if error>1e-5:raise ValueError('Source pose geometry changed')
        control=assets/f'dataDir/tekis/{p1}/{p1}.mod';p1raw=control.read_bytes()
        result['species'][species]=dict(source_bounds=bounds(original),baked_bounds=bounds(converted),max_vertex_error=error,vertex_count=len(converted),source_materials=source_material(model),emitted_material=emitted_material(raw),p1_control_raw_vertex_bounds=bounds(vertices(p1raw,allow_source_footer=True)),p1_bounds_caveat='Raw P1 vertex-array space; animated joint transforms and perspective are not accounted for. Not a valid automatic scale ratio.',sha256=dict(source=hashlib.sha256(model).hexdigest(),baked=hashlib.sha256(raw).hexdigest(),p1=hashlib.sha256(p1raw).hexdigest()))
    output.mkdir(parents=True);(output/'audit.json').write_bytes((json.dumps(result,sort_keys=True,indent=2)+'\n').encode());return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('imported','assets','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.imported,a.assets,a.output)))
