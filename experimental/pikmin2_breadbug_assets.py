"""Local Breadbug family assets and reference parameters; no native actor install."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_sheargrub_assets import animation_rows,joints
from experimental.pikmin2_convert import convert
from experimental.pikmin2_purple import bca_pose


def sha(raw):return hashlib.sha256(raw).hexdigest()

def parameter_blocks(raw):
    clean=re.sub(r'#[^\r\n]*','',raw.decode('shift_jis'))
    blocks=[]
    for block in re.findall(r'\{\s*(.*?)\{_eof\}\s*\}',clean,re.S):
        pairs=re.findall(r'\{([a-zA-Z0-9_]{4})\}\s+4\s+([^\s{}]+)',block)
        if len({k for k,v in pairs})!=len(pairs):raise ValueError('Duplicate parameter within block')
        values={k:float(v) for k,v in pairs}
        if any(not math.isfinite(v) for v in values.values()):raise ValueError('Nonfinite parameter')
        blocks.append(values)
    if not blocks:raise ValueError('Missing parameter blocks')
    return blocks


def collision_nodes(raw,joint_count):
    clean=re.sub(r'#[^\r\n]*','',raw.decode('shift_jis'))
    tokens=re.findall(r'\{[^{}\s]{4}\}|[{}]|[^\s{}]+',clean);position=0;nodes=[]
    def pop():
        nonlocal position
        if position>=len(tokens):raise ValueError('Truncated collision tree')
        value=tokens[position];position+=1;return value
    def node(parent):
        count=int(pop());radius=float(pop());identifier=pop();code=pop();offset=[float(pop()) for _ in range(3)];joint=int(pop());attribute=int(pop())
        if not 0<=count<=100 or radius<0 or not all(math.isfinite(v) for v in [radius]+offset) or not 0<=joint<joint_count:raise ValueError('Invalid collision node')
        if not re.fullmatch(r'\{.{4}\}',identifier) or not re.fullmatch(r'\{.{4}\}',code):raise ValueError('Invalid collision identity')
        index=len(nodes);nodes.append(dict(parent=parent,radius=radius,id=identifier[1:-1],code=code[1:-1],offset=offset,joint=joint,attribute=attribute))
        if count:
            if pop()!='{':raise ValueError('Missing collision children')
            for _ in range(count):node(index)
            if pop()!='}':raise ValueError('Unclosed collision children')
    node(None)
    if position!=len(tokens):raise ValueError('Trailing collision tree')
    return nodes


def target_allowed(species,minimum,threshold):
    if species not in ('PanModoki','OoPanModoki') or type(minimum) is not int or minimum<1 or type(threshold) is not int or threshold<1:raise ValueError('Invalid cargo eligibility')
    return minimum<threshold if species=='PanModoki' else minimum>=threshold


def carry_strength(minimum,maximum):
    if type(minimum) is not int or type(maximum) is not int or not 1<=minimum<=maximum:raise ValueError('Invalid cargo weight')
    return (minimum+maximum)*.5


def extract(iso,output):
    output.mkdir(parents=True,exist_ok=False);index=disc_files(iso);hashes={}
    result=dict(schema=1,native_ready=False,species={},source_sha256=hashes)
    with iso.open('rb') as disc:
        def read(path):
            offset,size=index[path];disc.seek(offset);raw=disc.read(size)
            if len(raw)!=size:raise ValueError('Truncated source')
            hashes[path]=sha(raw);return raw
        params=archive_files(read('enemy/parm/enemyParms.szs'))
        for species in ('PanModoki','OoPanModoki','PanHouse'):
            root=output/species;root.mkdir();models=archive_files(read(f'enemy/data/{species}/model.szs'));model=models['enemy.bmd'];modelpath=root/'enemy.bmd';modelpath.write_bytes(model)
            names=joints(model);metadata={};parsed={}
            for filename in ('enemyparm.txt','enemycoll.txt','enemyanimmgr.txt','enemystoneinfo.txt'):
                key=species.lower()+'/'+filename
                if key not in params:continue
                raw=params[key];(root/filename).write_bytes(raw);metadata[filename]=sha(raw)
                if filename=='enemyparm.txt':parsed['parameter_blocks']=parameter_blocks(raw)
                if filename=='enemycoll.txt':parsed['collision']=collision_nodes(raw,len(names))
            clips=[]
            static_pose=None
            if species=='PanHouse':
                try:
                    convert(modelpath,root/'nest.mod',True,bake_rigid=True)
                    static_pose=dict(file='nest.mod',sha256=sha((root/'nest.mod').read_bytes()))
                except ValueError as error:static_pose=dict(unsupported_reason=str(error))
            if species!='PanHouse':
                motions=archive_files(read(f'enemy/data/{species}/anim.szs'))
                for row in animation_rows(params[species.lower()+'/enemyanimmgr.txt'].decode('shift_jis')):
                    raw=motions[row['file']];(root/row['file']).write_bytes(raw);clip=dict(row,sha256=sha(raw),status='source_only')
                    try:
                        duration,pose=bca_pose(raw,0,len(names),allow_scale=True);clip['source_frames']=duration
                        # One pose per clip is a converter feasibility probe, not playback.
                        name=Path(row['file']).stem+'.mod';conversion=convert(modelpath,root/name,True,bake_rigid=True,pose=pose)
                        clip.update(status='first_pose_converted',pose=name,pose_sha256=sha((root/name).read_bytes()))
                    except ValueError as error:clip['unsupported_reason']=str(error)
                    clips.append(clip)
            result['species'][species]=dict(model_sha256=sha(model),joints=names,metadata_sha256=metadata,clips=clips,static_pose=static_pose,**parsed,
                role='helper_only; no autonomous spawn' if species=='PanHouse' else 'source creature; arena hooks unimplemented')
    result['limitations']=['First pose per clip only; no skeletal animation/event playback.','Materials approximate; Giant texture-matrix setup requires separate validation.','No cargo ownership, nest lifetime, receiver damage, collision installation or corpse/delivery behavior implemented.','PanModokiNest39 is a resource alias, not an additional spawnable family member.']
    (output/'breadbugs.json').write_text(json.dumps(result,indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=extract(a.iso,a.output)
    print(json.dumps({k:dict(joints=len(v['joints']),clips=len(v['clips']),poses=sum(c['status']=='first_pose_converted' for c in v['clips']),collision_nodes=len(v['collision'])) for k,v in r['species'].items()}))
