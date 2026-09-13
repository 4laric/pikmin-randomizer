"""Opt-in Frog MAT3-to-PVW diagnostic profile; host lighting is still approximate."""
import argparse,copy,hashlib,json,struct
from pathlib import Path
from experimental.pikmin2_convert import blocks,u16,u32
from experimental.pikmin2_frog_visual_audit import chunks,emitted_material,source_material
from experimental.pikmin2_frog_install import plan

POLICY='P2_FROG_SOURCE_MATERIAL_1'
SOURCES={'Frog':'8b6461d3358286620d9e774c824f1f7cfaca978d762c4fd23d1427471a445aab',
         'MaroFrog':'353f8e50e56f5d1fb3812b10c73fb0b6bd72739965e25d2e592b306324390129'}
# Full hashes intentionally bind this first profile to the audited source models.
LIMITS=['PVW diffuse light mask is fixed to3, source body mask is1.',
        'PVW specular channel uses host global material color, not source body204.',
        'Ambient/light environment remains P1; no source lighting parity claimed.']

def profile(model,species):
    if species not in SOURCES or hashlib.sha256(model).hexdigest()!=SOURCES[species]:raise ValueError('Unrecognized Frog source')
    b=blocks(model);m=b['MAT3'];metadata=source_material(model);materials=[]
    for i,info in enumerate(metadata):
        r=u32(m,12)+u16(m,u32(m,16)+2*i)*332
        lit=bool(info['channels'][0]['enabled']);control=0x93 if lit else 0
        stages=[]
        for j in range(info['tev_stage_count']):
            a=u32(m,92)+u16(m,r+0xe4+2*j)*20;o=u32(m,76)+u16(m,r+0xbc+2*j)*4
            stages.append(bytes([0,*m[o:o+3],m[r+0x9c+j],m[r+0xac+j],0,0])+m[a+1:a+10]+bytes(3)+m[a+10:a+19]+bytes(3))
        materials.append(dict(material=i,rgba=info['material_rgba'][0],control=control,stages=stages))
    hierarchy=b['INF1'];at=u32(hierarchy,20);current=None;mapping={}
    while True:
        kind,index=struct.unpack_from('>HH',hierarchy,at);at+=4
        if kind==0:break
        if kind==0x11:current=index
        if kind==0x12:
            if index in mapping or current is None or current>=len(materials):raise ValueError('Invalid source shape/material mapping')
            mapping[index]=current
    if sorted(mapping)!=list(range(len(mapping))):raise ValueError('Noncontiguous source shapes')
    return [materials[mapping[i]] for i in range(len(mapping))]

def rewrite(raw,materials):
    original=chunks(raw);parsed=emitted_material(raw);block=original[48];count=len(parsed)
    if len(materials)!=count:raise ValueError('Source/baked material count mismatch')
    tev=[];records=[];start=32+124*count
    for i,material in enumerate(materials):
        if material['control'] not in (0,0x93) or len(material['stages']) not in (1,2) or any(len(s)!=32 for s in material['stages']):raise ValueError('Unsupported Frog profile')
        r=start+152*i
        if u32(block,r+76)!=1 or u32(block,r+84)!=1 or len(block)<r+152:raise ValueError('Expected one texture per Frog material')
        # Only static material and lighting fields change; preserve pixel/texture state.
        record=bytearray(block[r:r+152]);color=bytes(material['rgba'])
        record[8:12]=color;record[16:20]=color;struct.pack_into('>I',record,36,material['control'])
        old=block[32+124*i:32+124*i+88]
        tev.append(old+struct.pack('>I',len(material['stages']))+b''.join(material['stages']));records.append(record)
    body=block[8:32]+b''.join(tev)+b''.join(records);body+=bytes((-(8+len(body)))%32)
    changed=struct.pack('>II',48,len(body))+body
    result=b''.join(changed if tag==48 else data for tag,data in original.items())
    after=chunks(result)
    if any(original[t]!=after[t] for t in original if t!=48):raise AssertionError('Nonmaterial bytes changed')
    return result

def describe(materials):
    return [dict(shape=i,material=m['material'],rgba=m['rgba'],lighting_control=m['control'],stages=[dict(order=list(s[1:4]),color=list(s[8:17]),alpha=list(s[20:29])) for s in m['stages']]) for i,m in enumerate(materials)]

def prepare(imported,output):
    if output.exists():raise ValueError('Refusing existing profile output')
    _,_,digest=plan(imported,[(201001,'Frog'),(201002,'MaroFrog')])
    report=copy.deepcopy(json.loads((imported/'frogs.json').read_text()));files=[];total=0;descriptions={}
    for species in ('Frog','MaroFrog'):
        model=(imported/species/'enemy.bmd').read_bytes();materials=profile(model,species);descriptions[species]=describe(materials)
        for clip in report['species'][species]['clips']:
            for pose in clip['poses']:
                before=(imported/species/pose['file']).read_bytes();after=rewrite(before,materials)
                pose.update(bytes=len(after),sha256=hashlib.sha256(after).hexdigest());total+=len(after)
                files.append((species,pose['file'],after))
    report['total_pose_bytes']=total
    report['material_profile']=dict(policy=POLICY,source_manifest_sha256=digest,source_parity=False,host_limits=LIMITS,geometry_unchanged=True,shapes=descriptions)
    output.mkdir(parents=True)
    for species,name,data in files:
        target=output/species/name;target.parent.mkdir(exist_ok=True);target.write_bytes(data)
    (output/'frogs.json').write_bytes((json.dumps(report,sort_keys=True,indent=2)+'\n').encode())
    plan(output,[(201001,'Frog'),(201002,'MaroFrog')])
    return report['material_profile']

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('imported','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.imported,a.output)))
