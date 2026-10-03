"""Private legal-disc Pelplant conversion. Finite authored zero scales stay zero."""
import sys
from pathlib import Path
import argparse
bootstrap=argparse.ArgumentParser(add_help=False)
bootstrap.add_argument('--randomizer-root',type=Path,required=True)
bootstrap_args,_=bootstrap.parse_known_args()
ROOT = bootstrap_args.randomizer_root.resolve(strict=True)
sys.path.insert(0, str(ROOT))
import hashlib, json, math, struct
from experimental import pikmin2_flora_assets as flora
from experimental.pikmin2_rigid import local_matrix, joint_matrices
from experimental.pikmin2_convert import blocks
from experimental import pikmin2_rigid as rigid
from experimental import pikmin2_skinning as skinning

_apply = rigid.apply
normal_fallbacks = 0
def apply_collapsed(matrix, point, normal=False, singular_normal='error'):
    global normal_fallbacks
    value = _apply(matrix, point, normal, singular_normal)
    if normal and sum(v*v for v in value)<1e-12:
        # A completely collapsed authored surface has no unique normal.
        # Keep its normalized source direction for finite native interpolation.
        # Positions remain the exact zero-scale result, and this approximation
        # applies ONLY where the cofactor yields the zero vector.
        length=math.sqrt(sum(v*v for v in point))
        if not math.isfinite(length) or length<1e-12: raise ValueError('Invalid source normal')
        normal_fallbacks += 1
        return tuple(v/length for v in point)
    return value

def bca_pose_zero(data, frame, expected_joints, allow_scale=False):
    if len(data)<72 or data[:8]!=b'J3D1bca1' or struct.unpack_from('>I',data,8)[0]!=(len(data)+31)//32*32:
        raise ValueError('Expected framed BCA')
    b=data[32:]
    if b[:4]!=b'ANF1': raise ValueError('Expected full transform animation')
    duration,count=struct.unpack_from('>HH',b,10)
    if count!=expected_joints or duration<1: raise ValueError('Animation skeleton mismatch')
    table,scales,rotations,translations=struct.unpack_from('>4I',b,20)
    if table<36 or table+count*36>len(b): raise ValueError('Truncated BCA joint table')
    pose=[]
    for joint in range(count):
        r=[];t=[];scale=[]
        for axis in range(3):
            values=[]
            for component,(offset,fmt,size) in enumerate(((scales,'f',4),(rotations,'h',2),(translations,'f',4))):
                length,index=struct.unpack_from('>HH',b,table+joint*36+axis*12+component*4)
                if length<1: raise ValueError('Empty BCA track')
                at=index+min(max(int(frame),0),length-1)
                if offset<36 or offset+(index+length)*size>len(b): raise ValueError('Truncated BCA track')
                values.append(struct.unpack_from('>'+fmt,b,offset+at*size)[0])
            if not all(math.isfinite(v) for v in values): raise ValueError('Non-finite BCA transform')
            if not allow_scale and abs(values[0]-1)>1e-5: raise ValueError('Scaled animation not supported')
            # Zero scales hide authored geometry; do not inflate or substitute a rig.
            scale.append(values[0]);r.append(values[1]);t.append(values[2])
        matrix=local_matrix(r,t)
        for row in range(3):
            for column in range(3): matrix[row][column]*=scale[column]
        pose.append(matrix)
    return duration,pose

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--randomizer-root',type=Path,required=True)
    p.add_argument('--iso',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--pose-limit',type=int,default=12)
    p.add_argument('--amount',type=int,choices=(1,5,10,20),default=1,
                   help='Captured-pellet head/neck callbacks; amount1 also supplies uncaptured rig')
    a=p.parse_args()
    flora.SPECIES={'Pelplant':0}
    flora.bca_pose=bca_pose_zero
    rigid.apply=apply_collapsed
    flora.TOLERANCES['Pelplant']={'singular_normal':'transpose-adjugate'}
    original_world=rigid.joint_matrices
    def sized_world(model, local_overrides=None):
        world=original_world(model,local_overrides)
        if len(world)!=8: raise ValueError('Unexpected Pelplant skeleton')
        # J3DJoint::recursiveCalc calls phase1 AFTER children: modify only
        # these completed world matrices, never propagate scale to descendants.
        scale={1:1.,5:2.,10:3.5,20:4.8}[a.amount]
        for r in range(3):
            for c in range(3): world[5][r][c]*=scale
        thickness,length={1:(1.,1.),5:(1.,1.),10:(1.5,.85),20:(2.,.75)}[a.amount]
        for r,k in enumerate((thickness,length,thickness)):
            for c in range(3): world[1][r][c]*=k
        return world
    skinning.joint_matrices=sized_world
    report=flora.extract(a.iso,a.source,a.output,a.pose_limit)
    info=report['species']['Pelplant'];root=a.output/'Pelplant'
    model=blocks((root/'enemy.bmd').read_bytes())
    names=info['joints']; required=('headjnt','bodyjnt1','bodyjnt2')
    if any(n not in names for n in required): raise ValueError('Missing required source joint')
    lines=['P2_PELPLANT_BANK_1'];jointlines=['P2_PELPLANT_JOINTS_1'];joints={}
    for clip in info['clips']:
        if clip['status']!='converted' or any('file' not in v for v in clip['poses']):
            raise ValueError('Incomplete source clip '+clip['name']+': '+str(clip))
        stem='flora_Pelplant_size'+str(a.amount)+'_'+clip['name']
        poses=clip['poses'];frames=[v['frame'] for v in poses]
        for index,entry in enumerate(poses):
            previous=root/entry['file'];name=stem+f'_{index:02}.mod'
            previous.rename(root/name);entry['file']=name
        if frames[0]!=0 or frames[-1]!=clip['source_frames']-1: raise ValueError('Bad frame coverage')
        lines.append(f"clip {clip['name']} {len(poses)} {clip['source_frames']} {stem}")
        lines.append('frames '+clip['name']+' '+' '.join(map(str,frames)))
        lines.append('events '+clip['name']+' '+(','.join(f'{f}:{e}' for f,e in clip['events']) or '-'))
        raw=(root/(clip['name']+'.bca')).read_bytes()
        joints[clip['name']]=[]
        for frame in frames:
            _,pose=bca_pose_zero(raw,frame,len(names),True)
            matrices=sized_world(model,pose)
            joints[clip['name']].append({'frame':frame,'joints':{n:matrices[names.index(n)] for n in names}})
            for n in names:
                jointlines.append(f"joint {clip['name']} {frame} {n} "+' '.join(format(v,'.9g') for row in matrices[names.index(n)] for v in row))
    for index,node in enumerate(info['collision']):
        jointlines.append(f"collider {index} {node['joint']} {node['parent'] if node['parent'] is not None else -1} {node['id']} {node['code']} {node['attribute']} "+' '.join(format(v,'.9g') for v in [*node['offset'],node['radius']]))
    jointlines.append('parameters 50 '+ ' '.join(format(info['proper_retail'][v],'.9g') for v in ('fp01','fp02','fp03')))
    (a.output/'p2-pelplant-joints.txt').write_text('\n'.join(jointlines)+'\n',encoding='ascii')
    (a.output/'p2-pelplant-bank.txt').write_text('\n'.join(lines)+'\n',encoding='ascii')
    physical={'schema':1,'policy':'P2_PELPLANT_PHYSICAL_1','joints':names,
              'collision':info['collision'],'clips':joints,'proper_retail':info['proper_retail'],
              'zero_scales':'preserved exactly','singular_normals':'transpose-adjugate; zero cofactor uses normalized source normal; no geometry clamping',
              'collapsed_normal_fallbacks':normal_fallbacks,
              'native_runtime_validated':False}
    (a.output/'p2-pelplant-joints.json').write_text(json.dumps(physical,indent=2,sort_keys=True)+'\n')
    report['conversion_override']={'scope':'Pelplant only','authored_zero_scale':True,'singular_normal':'transpose-adjugate','collapsed_normal_fallbacks':normal_fallbacks,'undefined_normal_fallback':'normalized original source direction','captured_amount':a.amount,'head_scale':{1:1.,5:2.,10:3.5,20:4.8}[a.amount],'callback_phase':1,'callback_descendant_propagation':False}
    (a.output/'flora.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    hashes={str(f.relative_to(a.output)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(a.output.rglob('*')) if f.is_file()}
    (a.output/'sha256.json').write_text(json.dumps(hashes,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'poses':report['total_poses'],'bytes':report['total_pose_bytes'],'clips':len(info['clips']),'proper_retail':info['proper_retail'],'output':str(a.output)}))

if __name__=='__main__': main()
