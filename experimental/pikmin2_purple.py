"""Bounded local Purple model/BCA pose-bank preview, not a general animation runtime."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
import struct
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_convert import blocks,convert,u32,u16
from experimental.pikmin2_rigid import local_matrix,joint_matrices


def bca_pose(data,frame,expected_joints):
    # Retail archives omit the final alignment padding counted in some BCA headers.
    if len(data)<72 or data[:8]!=b'J3D1bca1' or struct.unpack_from('>I',data,8)[0]!=(len(data)+31)//32*32:
        raise ValueError('Expected framed BCA')
    b=data[32:]
    if b[:4]!=b'ANF1':raise ValueError('Expected full transform animation')
    duration,count=struct.unpack_from('>HH',b,10)
    if count!=expected_joints or duration<1:raise ValueError('Animation skeleton mismatch')
    table,scales,rotations,translations=struct.unpack_from('>4I',b,20)
    if table<36 or table+count*36>len(b):raise ValueError('Truncated BCA joint table')
    pose=[]
    for joint in range(count):
        r=[];t=[]
        for axis in range(3):
            values=[]
            for component,(offset,fmt,size) in enumerate(((scales,'f',4),(rotations,'h',2),(translations,'f',4))):
                length,index=struct.unpack_from('>HH',b,table+joint*36+axis*12+component*4)
                if length<1:raise ValueError('Empty BCA track')
                at=index+min(max(int(frame),0),length-1)
                if offset<36 or offset+(index+length)*size>len(b):raise ValueError('Truncated BCA track')
                values.append(struct.unpack_from('>'+fmt,b,offset+at*size)[0])
            if not all(math.isfinite(v) for v in values):raise ValueError('Non-finite BCA transform')
            if abs(values[0]-1)>1e-5:raise ValueError('Scaled animation not supported')
            r.append(values[1]);t.append(values[2])
        pose.append(local_matrix(r,t))
    return duration,pose


def extract(iso,output):
    output.mkdir(parents=True,exist_ok=False)
    key='user/Kando/piki/pikis.szs';catalog=disc_files(iso);offset,size=catalog[key];hashes={}
    with iso.open('rb') as f:
        f.seek(offset);data=f.read(size)
        def params(path):
            offset,size=catalog[path];f.seek(offset);raw=f.read(size);hashes[path]=hashlib.sha256(raw).hexdigest();return raw.decode('shift_jis')
        pikis=params('user/Abe/piki/pikiParms.txt');navi=params('user/Abe/piki/naviParms.txt')
    def value(text,key):
        matches=re.findall(r'\{'+key+r'\}\s+4\s+(\S+)',text)
        if len(matches)!=1 or not math.isfinite(float(matches[0])):raise ValueError('Missing or ambiguous source parameter')
        return float(matches[0])
    stats=[value(pikis,k) for k in ('P002','P005','P003')]+[value(navi,'q000')]+[value(pikis,k) for k in ('p001','P018','P019','P020','P021')]
    archive=archive_files(data)
    model=output/'purple.bmd';model.write_bytes(archive['piki_model/piki_p2_black.bmd'])
    skeleton=blocks(model.read_bytes());joints=struct.unpack_from('>H',skeleton['JNT1'],8)[0]
    material=skeleton['MAT3'];names=u32(material,20)
    labels=[material[names+u16(material,names+6+4*i):].split(b'\0',1)[0] for i in range(u16(material,names))]
    if labels!=[b'body1',b'eye1']:raise ValueError('Unexpected Purple material mapping')
    # This source model has an untextured body colored by TEV register 0.
    # Preserve its base hue in our deliberately simplified material pipeline.
    body_color=struct.unpack_from('>4h',material,u32(material,80))
    rows=['P2_PURPLE_1','stats '+' '.join(map(str,stats))];report={}
    # Immutable meshes avoid changing a cached display list's vertex data in place.
    for name in ('wait','walk','attack1'):
        clip=archive['motion/'+name+'.bca'];duration,_=bca_pose(clip,0,joints)
        frames=min(12,duration);rows.append(f'{name} {frames} {duration/30:.6f}')
        for i in range(frames):
            _,pose=bca_pose(clip,i*duration//frames,joints)
            convert(model,output/f'purple_{name}_{i:02}.mod',True,bake_rigid=True,pose=pose,material_colors=[body_color,(255,255,255,255)])
        report[name]={'source_frames':duration,'sampled_poses':frames,'sha256':hashlib.sha256(clip).hexdigest()}
    # Leaf/bud/flower use the source attachment's world transform each pose.
    for growth,name in enumerate(('leaf','bud_red','flower_red')):
        source=output/(name+'.bmd');source.write_bytes(archive['happa_model/'+name+'.bmd'])
        convert(source,output/f'purple_happa_{growth}.mod',True,bake_rigid=True)
    for name in report:
        clip=archive['motion/'+name+'.bca'];n=report[name]['sampled_poses'];duration=report[name]['source_frames']
        for i in range(n):
            _,pose=bca_pose(clip,i*duration//n,joints)
            matrix=joint_matrices(skeleton,pose)[8]
            rows.append('happa '+name+' '+str(i)+' '+' '.join(str(v) for row in matrix for v in row))
    (output/'p2-purple.txt').write_text('\n'.join(rows)+'\n')
    hashes[key]=hashlib.sha256(data).hexdigest()
    result={'schema':1,'source_sha256':hashes,'body_color':body_color,'source_stats':dict(zip(('movement','carry_speed_power','attack','throw_height','run_speed','carry_max_factor','carry_min_factor','bud_bonus','flower_bonus'),stats)),'joints':joints,'motions':report,
            'limitations':['Sampled immutable pose bank, no blending or source animation events.','P2 species metadata is separate from legacy P1 storage; no checkpoint support.']}
    (output/'purple.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iso',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(extract(a.iso,a.output),indent=2))
