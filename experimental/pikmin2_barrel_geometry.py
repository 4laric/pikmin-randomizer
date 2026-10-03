"""Private retail barrel sampled geometry; no animation events or gameplay claim.

ANK1 follows J3DAnimation::calcTransform/GetKeyFrameInterpolation: type 0 has
one tangent per key, type 1 has incoming/outgoing tangents; rotations truncate
the interpolation to s32, shift, then narrow to signed 16-bit turns.
"""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import struct

from experimental.pikmin2_convert import blocks, decode, write_model, u16
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import local_matrix
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_animation import resource_chunks

MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_POSES = 64
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


def section(data, magic, tag):
    if (len(data) < 68 or len(data) > MAX_SOURCE_BYTES or data[:8] != magic
            or struct.unpack_from('>I', data, 8)[0] != (len(data)+31)//32*32
            or struct.unpack_from('>I', data, 12)[0] != 1):
        raise ValueError('Invalid bounded single-section animation')
    b = data[32:]
    size = struct.unpack_from('>I', b, 4)[0]
    if b[:4] != tag or size < len(b) or size > (len(b)+31)//32*32:
        raise ValueError('Invalid animation section size/tag')
    return b


def key_animation(data, expected_joints):
    b = section(data, b'J3D1bck1', b'ANK1')
    attribute, shift, duration, joints, ns, nr, nt = struct.unpack_from('>BB5H', b, 8)
    if not 1 <= duration <= 10000 or joints != expected_joints or shift > 15:
        raise ValueError('Unsupported ANK1 skeleton/duration/rotation shift')
    offsets = struct.unpack_from('>4I', b, 20)
    sizes = (joints*54, ns*4, nr*2, nt*4)
    spans = []
    for at, size in zip(offsets, sizes):
        if at < 36 or at+size > len(b):
            raise ValueError('Truncated ANK1 table')
        if size:
            spans.append((at, at+size))
    spans.sort()
    if any(a[1] > c[0] for a, c in zip(spans, spans[1:])):
        raise ValueError('Overlapping ANK1 tables')
    arrays = [struct.unpack_from('>'+fmt*n, b, at) for at, n, fmt in
              zip(offsets[1:], (ns,nr,nt), ('f','h','f'))]
    if any(not math.isfinite(v) for a in arrays for v in a):
        raise ValueError('Nonfinite ANK1 key data')
    tracks = []
    times = set()
    for joint in range(joints):
        axes = []
        for axis in range(3):
            components = []
            for component in range(3):
                count, index, kind = struct.unpack_from('>3H', b,
                    offsets[0]+joint*54+axis*18+component*6)
                if kind not in (0,1):
                    raise ValueError('Unsupported ANK1 tangent type')
                length = count if count <= 1 else count*(3 if kind == 0 else 4)
                a = arrays[component]
                if index+length > len(a):
                    raise ValueError('ANK1 track outside declared array')
                values = a[index:index+length]
                if count > 1:
                    stride = 3 if kind == 0 else 4
                    t = values[::stride]
                    if any(x < 0 or x > duration for x in t) or any(x >= y for x,y in zip(t,t[1:])):
                        raise ValueError('Invalid ANK1 key time order/range')
                    times.update(t)
                components.append((count,kind,values))
            axes.append(components)
        tracks.append(axes)
    return {'duration':duration,'attribute':attribute,'rotation_shift':shift,
            'joints':joints,'key_times':sorted(times),'tracks':tracks}


def validate_full_animation(data, expected_joints):
    b = section(data,b'J3D1bca1',b'ANF1')
    duration,joints,ns,nr,nt = struct.unpack_from('>5H',b,10)
    if not 1 <= duration <= 10000 or not expected_joints <= joints <= 64:
        raise ValueError('Unsupported BCA skeleton/duration')
    offsets = struct.unpack_from('>4I',b,20)
    spans=[]
    for at,size in zip(offsets,(joints*36,ns*4,nr*2,nt*4)):
        if at<36 or at+size>len(b): raise ValueError('Truncated BCA declared array')
        if size: spans.append((at,at+size))
    spans.sort()
    if any(a[1]>c[0] for a,c in zip(spans,spans[1:])):
        raise ValueError('Overlapping BCA tables')
    arrays=[struct.unpack_from('>'+fmt*n,b,at) for at,n,fmt in
            zip(offsets[1:],(ns,nr,nt),('f','h','f'))]
    if any(not math.isfinite(v) for a in arrays for v in a):
        raise ValueError('Nonfinite BCA data')
    for joint in range(joints):
        for axis in range(3):
            for component in range(3):
                count,index=struct.unpack_from('>2H',b,offsets[0]+joint*36+axis*12+component*4)
                if count<1 or index+count>len(arrays[component]):
                    raise ValueError('BCA track outside declared array')
    return duration,joints


def key_value(track, frame, default):
    count, kind, v = track
    if count == 0: return default
    if count == 1: return v[0]
    stride = 3 if kind == 0 else 4
    times = v[::stride]
    if frame < times[0]: return v[1]
    if frame >= times[-1]: return v[(count-1)*stride+1]
    left = bisect.bisect_right(times, frame)-1
    a, b = left*stride, (left+1)*stride
    dt = v[b]-v[a]
    t = (frame-v[a])/dt
    # Shared tangent for type0; outgoing-left and incoming-right for type1.
    m0 = v[a+2 if kind == 0 else a+3]
    m1 = v[b+2]
    return ((2*t**3-3*t*t+1)*v[a+1] + (t**3-2*t*t+t)*dt*m0
            + (-2*t**3+3*t*t)*v[b+1] + (t**3-t*t)*dt*m1)


def key_pose(animation, frame):
    if not math.isfinite(frame) or not 0 <= frame <= animation['duration']:
        raise ValueError('ANK1 sample outside source duration')
    pose, singular = [], []
    for joint, axes in enumerate(animation['tracks']):
        scales = [key_value(a[0],frame,1.) for a in axes]
        rotations = [((int(key_value(a[1],frame,0.)) << animation['rotation_shift'])+32768)%65536-32768 for a in axes]
        translations = [key_value(a[2],frame,0.) for a in axes]
        if any(not math.isfinite(x) for x in scales+translations):
            raise ValueError('Nonfinite sampled ANK1 transform')
        if any(abs(x) < 1e-8 for x in scales): singular.append(joint)
        matrix = local_matrix(rotations, translations)
        for row in range(3):
            for col in range(3): matrix[row][col] *= scales[col]
        pose.append(matrix)
    return pose, singular


def convert(source, output, pose_limit=24):
    if not 2 <= pose_limit <= MAX_POSES: raise ValueError('Invalid pose limit')
    model = (source/'model.bmd').read_bytes()
    if not 0 < len(model) <= MAX_SOURCE_BYTES: raise ValueError('Model exceeds budget')
    mb = blocks(model); joints = u16(mb['JNT1'],8)
    if not 1 <= joints <= 64: raise ValueError('Unsupported barrel skeleton')
    raw = {name:(source/(name+suffix)).read_bytes() for name,suffix in [('wait','.bca'),('dead','.bck')]}
    dead = key_animation(raw['dead'], joints)
    _, wait_tracks = validate_full_animation(raw['wait'],joints)
    wait_duration, _ = bca_pose(raw['wait'],0,joints,allow_scale=True,singular_scale='allow',extra_tracks=True)
    if not 1 <= wait_duration <= 10000: raise ValueError('Invalid BCA duration')
    report = {'schema':'P2_BARREL_POSE_BANK_1','source_model_sha256':hashlib.sha256(model).hexdigest(),
              'joints':joints,'geometry_only':True,'gameplay_qualified':False,'animation_events':False,
              'normal_policy':'transpose-adjugate-zero (authored collapse retained)','clips':{}}
    # Decode every BCA integer frame to validate tracks even when not sampled.
    for frame in range(wait_duration):
        bca_pose(raw['wait'],frame,wait_tracks,allow_scale=True,singular_scale='allow')
    dead_singular=[]
    for frame in sorted(set(range(dead['duration']+1))|set(dead['key_times'])):
        _, singular=key_pose(dead,frame)
        if singular: dead_singular.append({'source_frame':frame,'joints':singular})
    output.mkdir(parents=True,exist_ok=False)
    reference = None; total = 0; topology = None
    for name, duration in [('wait',wait_duration),('dead',dead['duration'])]:
        last = duration-1 if name == 'wait' else duration
        frames = sorted(set(round(i*last/(pose_limit-1)) for i in range(pose_limit)))
        if name == 'dead': frames = sorted(set(frames+dead['key_times']))
        if len(frames) > MAX_POSES: raise ValueError('Source keyframe/sample union exceeds pose budget')
        info = {'source_sha256':hashlib.sha256(raw[name]).hexdigest(),'source_duration':duration,
                'source_attribute':raw[name][40],'source_key_times':dead['key_times'] if name=='dead' else [],'poses':[]}
        if name=='dead':
            info['rotation_shift']=dead['rotation_shift']
            info['singular_source_frames']=dead_singular
            info['terminal_frame_included']=True
        else:
            info['source_tracks']=wait_tracks
            info['unused_trailing_tracks']=wait_tracks-joints
        report['clips'][name] = info
        for index, frame in enumerate(frames):
            if name == 'dead': pose, singular = key_pose(dead, frame)
            else:
                _, pose = bca_pose(raw[name],frame,joints,allow_scale=True,singular_scale='allow',extra_tracks=True)
                singular = [j for j,m in enumerate(pose) if any(sum(m[r][c]**2 for r in range(3)) < 1e-16 for c in range(3))]
            decoded = decode(model,True,bake_rigid=True,draw_matrices=draw_matrices(mb,pose),singular_normal='transpose-adjugate-zero')
            current = (len(decoded[1][9]),len(decoded[1][10]),decoded[2],decoded[3])
            if topology is not None and current != topology: raise ValueError('Pose topology changed')
            topology = current
            path = output/f'{name}_{index:02}.mod'
            write_model(decoded,path,'retail barrel '+name)
            data = path.read_bytes(); total += len(data)
            if total > MAX_OUTPUT_BYTES: raise ValueError('Barrel bank exceeds byte budget')
            resources = resource_chunks(data)
            if reference is not None and reference != resources: raise ValueError('Pose materials/textures differ')
            reference = resources
            info['poses'].append({'file':path.name,'source_frame':frame,'sha256':hashlib.sha256(data).hexdigest(),
                                  'bytes':len(data),'singular_joints':singular})
    report['total_bytes'] = total
    rows=['P2_ORIGINAL_BARREL_GEOMETRY_1']
    for name,info in report['clips'].items():
        frames=[p['source_frame'] for p in info['poses']]
        if any(int(f)!=f for f in frames):
            raise ValueError('Native barrel bank requires integer source-frame samples')
        rows.append(' '.join(map(str,[name,len(frames),info['source_duration']]+[int(f) for f in frames])))
    (output/'barrel-bank.txt').write_text('\n'.join(rows)+'\n',encoding='ascii')
    (output/'barrel-bank.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pose-limit',type=int,default=24)
    args = parser.parse_args()
    print(json.dumps(convert(args.source,args.output,args.pose_limit),indent=2))
