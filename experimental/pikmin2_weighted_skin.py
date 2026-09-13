"""Export bounded weighted draw palettes; Groink is the first source reference."""
import argparse,hashlib,json,math
from pathlib import Path
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_convert import blocks,decode,u16,u32
from experimental.pikmin2_skinning import _envelopes,draw_matrices
from experimental.pikmin2_attachments import bank_text
from experimental.pikmin2_sheargrub_assets import joints
from experimental.pikmin2_purple import bca_pose

IDENTITY=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]

def mesh_text(model):
    b=blocks(model);count=len(joints(model))
    if not 1<=count<=128:raise ValueError('Joint limit exceeded')
    # Reuse strict DRW1/EVP1 source validation before reading references.
    matrices=draw_matrices(b,[IDENTITY for _ in range(count)])
    if not 1<=len(matrices)<=512:raise ValueError('Draw palette limit exceeded')
    envelopes,inverse=_envelopes(b['EVP1'],count);d=b['DRW1'];palette=[]
    for i in range(len(matrices)):
        kind=d[u32(d,12)+i];ref=u16(d,u32(d,16)+2*i)
        entries=[(ref,1.,IDENTITY)] if kind==0 else [(j,w,inverse[j]) for j,w in envelopes[ref]]
        if len(entries)>8 or len({j for j,_,_ in entries})!=len(entries):raise ValueError('Unsupported envelope influence count/duplicate joint')
        palette.append(entries)
    bindings={}
    # Identity draw transforms preserve authored source vectors and stable output
    # indices. They do not approximate or reconstruct source inverse bind data.
    _,arrays,_,_=decode(model,True,bake_rigid=True,draw_matrices=[IDENTITY for _ in matrices],bindings=bindings)
    if any(len(bindings[a])!=len(arrays[a]) or not 1<=len(bindings[a])<=65536 for a in (9,10)):raise ValueError('Invalid binding coverage')
    rows=[f'P2_SKIN_WEIGHTED_1 {count} {len(bindings[9])} {len(bindings[10])} {len(palette)}']
    for entries in palette:
        rows.append(str(len(entries)))
        for j,w,m in entries:rows.append(str(j)+' '+format(w,'.9g')+' '+' '.join(format(v,'.9g') for row in m for v in row))
    for attr in (9,10):rows += [str(j)+' '+' '.join(format(v,'.9g') for v in value) for j,value in bindings[attr]]
    text='\n'.join(rows)+'\n'
    if len(text)>8*1024*1024:raise ValueError('Mesh byte budget exceeded')
    return text,dict(joints=count,draws=len(palette),weighted_draws=sum(len(e)>1 for e in palette),max_influences=max(map(len,palette)),positions=len(bindings[9]),normals=len(bindings[10]))

def export(iso,output):
    index=disc_files(iso)
    with iso.open('rb') as f:
        def read(path):
            offset,size=index[path];f.seek(offset);return archive_files(f.read(size))
        model=read('enemy/data/MiniHoudai/model.szs')['enemy.bmd']
        animations={Path(n).stem:v for n,v in read('enemy/data/MiniHoudai/anim.szs').items() if n.endswith('.bca')}
    timing={}
    for n,raw in animations.items():
        duration,_=bca_pose(raw,0,len(joints(model)),allow_scale=True)
        timing[n]=dict(source_frames=duration,frames=list(range(duration)))
    text,report=mesh_text(model);bank=bank_text(model,animations,timing)
    output.mkdir(parents=True,exist_ok=False)
    for n,data in [('skin.txt',text.encode('ascii')),('attachments.txt',bank.encode('ascii')),('source.bmd',model)]:
        (output/n).write_bytes(data);report[n+'_sha256']=hashlib.sha256(data).hexdigest()
    for n,raw in animations.items():(output/(n+'.bca')).write_bytes(raw)
    report.update(clips={n:dict(frames=v['source_frames'],sha256=hashlib.sha256(animations[n]).hexdigest()) for n,v in timing.items()},scope='Groink CPU skinning reference; no aim callbacks, material animation or actor adoption')
    (output/'weighted.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iso',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(export(a.iso,a.output),indent=2))
