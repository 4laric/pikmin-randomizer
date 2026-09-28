"""Source-bound Honeywisp TEV audit; no recolor or shared converter mutation."""
import argparse,hashlib,json,struct
from pathlib import Path
from experimental.pikmin2_convert import blocks,u16,u32,decode
from experimental.pikmin2_purple import bca_pose

def sha(b):return hashlib.sha256(b).hexdigest()
def entry(m,table,index,size):
    if index==65535:return None
    base=u32(m,table);end=min([u32(m,o) for o in range(12,132,4) if u32(m,o)>base]+[len(m)])
    start=base+index*size
    if not base or start<base or start+size>end:raise ValueError('Material reference outside table')
    return m[start:start+size]

def tev_rgb(register,raster,scale=2):
    if len(register)!=4 or len(raster)!=4 or any(type(v)is not int or not 0<=v<=255 for v in [*register,*raster]) or scale!=2:raise ValueError('Expected audited RGBA8 inputs and source scale2')
    # Floating reference, not bit-exact hardware TEV rounding; lit RASC is input.
    return [min(255.,scale*register[i]*raster[i]/255.) for i in range(3)]

def audit(imported):
    manifest=json.loads((imported/'qurione.json').read_text());raw=(imported/'enemy.bmd').read_bytes()
    if sha(raw)!=manifest['model_sha256'] or manifest['source_id']!=16:raise ValueError('Wrong source model')
    b=blocks(raw);m=b['MAT3'];rows=[]
    if u16(m,8)!=2 or u16(b['TEX1'],8)!=0:raise ValueError('Unexpected Honeywisp material/texture count')
    for i in range(2):
        r=u32(m,12)+u16(m,u32(m,16)+2*i)*332
        if r+332>len(m):raise ValueError('Truncated material')
        def refs(table,offset,count,size):return [entry(m,table,u16(m,r+offset+2*k),size) for k in range(count)]
        stagecount=entry(m,88,m[r+4],1)[0]
        stages=refs(92,228,stagecount,20)
        if stagecount!=1 or list(stages[0][1:10])!=[15,2,10,15,0,0,1,1,0]:raise ValueError('Unsupported source TEV expression')
        registers=[list(struct.unpack('>4h',x)) if x else None for x in refs(80,220,4,8)]
        rows.append(dict(material=i,colors=[list(x) if x else None for x in refs(32,8,2,4)],channels=[list(x) if x else None for x in refs(40,12,4,8)],ambient=[list(x) if x else None for x in refs(44,20,2,4)],registers=registers,stages=[list(x) for x in stages],orders=[list(x) for x in refs(76,188,stagecount,4)],white_raster_reference=tev_rgb(registers[0],[255]*4)))
    clip=manifest['clips'][0];animation=(imported/clip['file']).read_bytes()
    if sha(animation)!=clip['source_sha256']:raise ValueError('Wrong animation')
    _,pose=bca_pose(animation,0,len(manifest['joints']),allow_scale=True)
    _,arrays,shapes,_=decode(raw,True,True,pose)
    for i,shape in enumerate(shapes):rows[i]['vertex_rgba']=sorted({tuple(arrays[11][v[11]]) for t in shape for v in t})
    modpath=imported/clip['poses'][0]['file'];mod=modpath.read_bytes()
    if sha(mod)!=clip['poses'][0]['sha256']:raise ValueError('Wrong baked pose')
    at=0;emitted=[]
    while at+8<=len(mod):
        tag,size=struct.unpack_from('>II',mod,at)
        if at+8+size>len(mod):raise ValueError('Truncated MOD chunk')
        if tag==48:
            count=u32(mod,at+8);pos=(at+16+31)//32*32
            if count!=2:raise ValueError('Unexpected MOD material count')
            for i in range(count):
                # Writer emits three 24-byte color registers,16 konst bytes,stage count.
                register=list(struct.unpack_from('>4h',mod,pos));stage=pos+92
                if u32(mod,pos+88)!=1:raise ValueError('Unexpected MOD stage count')
                emitted.append(dict(register0=register,order=list(mod[stage:stage+8]),color_stage=list(mod[stage+8:stage+20]),alpha_stage=list(mod[stage+20:stage+32])))
                pos=stage+32
            break
        at+=8+size
    if len(emitted)!=2:raise ValueError('Missing MOD material audit')
    return dict(mod_sha256=sha(mod),emitted_materials=emitted,source_model_sha256=sha(raw),texture_count=0,materials=rows,source_rgb_expression='clamp(2 * C0 * lit_RASC)',exported_rgb_expression='RASC',exported_registers='white',source_lighting='enabled; ambient and light-channel configuration not reproduced by restricted exporter',proposal='Preserve this exact untextured one-stage C0*RASC scale2 expression plus alpha and channel state; no guessed tint or scale',native_validation='pending',host_glow='Separate P1 effects remain active; source material mismatch exists independently')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--imported',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit(a.imported);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
