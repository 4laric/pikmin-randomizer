"""Opt-in exact retail Qurione TEV preservation; geometry/lighting untouched."""
import argparse,hashlib,json,struct
from pathlib import Path
from experimental.pikmin2_convert import blocks,u16,u32
from experimental.pikmin2_qurione_material_audit import entry
SOURCE='e5d733bf28a8721ebd5ad325c368fabbb9cf18f500fab72fcf962a5fe2abc8ad'
def sha(raw):return hashlib.sha256(raw).hexdigest()

def descriptor(model):
    if sha(model)!=SOURCE:raise ValueError('Unrecognized retail Qurione model')
    b=blocks(model);m=b['MAT3'];h=b['INF1'];mapping={};material=None;at=u32(h,20)
    while True:
        kind,index=struct.unpack_from('>HH',h,at);at+=4
        if kind==0:break
        if kind==0x11:material=index
        if kind==0x12:
            if index in mapping or material is None:raise ValueError('Ambiguous shape mapping')
            mapping[index]=material
    if set(mapping)!={0,1} or set(mapping.values())!={0,1}:raise ValueError('Unexpected shape/material mapping')
    rows=[]
    for shape in range(2):
        i=mapping[shape];r=u32(m,12)+u16(m,u32(m,16)+2*i)*332
        stage=entry(m,92,u16(m,r+228),20);reg=entry(m,80,u16(m,r+220),8)
        if list(stage[1:10])!=[15,2,10,15,0,0,1,1,0]:raise ValueError('Unsupported TEV pattern')
        rows.append(dict(shape=shape,material=i,register0=list(struct.unpack('>4h',reg)),color=list(stage[1:10]),alpha=list(stage[10:19])))
    return rows

def patch(mod,rows):
    if len(rows)!=2 or [r['shape'] for r in rows]!=[0,1]:raise ValueError('Expected two source descriptors')
    result=bytearray(mod);at=0;found=[];changed=set()
    while at+8<=len(mod):
        tag,size=struct.unpack_from('>II',mod,at);end=at+8+size
        if end>len(mod):raise ValueError('Truncated MOD')
        if tag==48:found.append(at)
        at=end
    if at!=len(mod) or len(found)!=1:raise ValueError('Invalid MOD material chunk')
    start=found[0]
    if u32(mod,start+8)!=2 or u32(mod,start+12)!=2:raise ValueError('Unexpected MOD material counts')
    pos=(start+16+31)//32*32
    for row in rows:
        if row['register0'] not in ([226,226,226,255],[255,50,200,255]) or row['color']!=[15,2,10,15,0,0,1,1,0] or row['alpha'] not in ([7,1,5,7,0,0,0,1,0],[5,7,7,7,0,0,0,1,0]):raise ValueError('Unrecognized material descriptor')
        if u32(mod,pos+88)!=1 or mod[pos:pos+8]!=struct.pack('>4h',255,255,255,255):raise ValueError('Not original bounded exporter material')
        if list(mod[pos+100:pos+112])!=[15,15,15,10,0,0,0,1,0,0,0,0]:raise ValueError('Unexpected exported color stage')
        for offset,data in ((pos,struct.pack('>4h',*row['register0'])),(pos+100,bytes(row['color'])),(pos+112,bytes(row['alpha']))):
            result[offset:offset+len(data)]=data;changed.update(range(offset,offset+len(data)))
        pos+=124
    if any(a!=b and i not in changed for i,(a,b) in enumerate(zip(mod,result))):raise AssertionError('Nonmaterial mutation')
    return bytes(result)

def prepare(imported,output):
    model=(imported/'enemy.bmd').read_bytes();rows=descriptor(model);metadata=json.loads((imported/'qurione.json').read_text());files={}
    for clip in metadata['clips']:
        for p in clip['poses']:
            if Path(p['file']).name!=p['file']:raise ValueError('Unsafe pose path')
            raw=(imported/p['file']).read_bytes()
            if sha(raw)!=p['sha256']:raise ValueError('Pose hash mismatch')
            files[p['file']]=(raw,patch(raw,rows))
    output.mkdir(parents=True,exist_ok=False)
    report=dict(source_model_sha256=SOURCE,descriptor=rows,scope='TEV constants/ops only; source lighting not yet translated',files={})
    for name,(before,after) in files.items():
        (output/name).write_bytes(after);report['files'][name]=dict(before=sha(before),after=sha(after),changed_bytes=sum(a!=b for a,b in zip(before,after)))
    (output/'patch.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--imported',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.imported,a.output)
