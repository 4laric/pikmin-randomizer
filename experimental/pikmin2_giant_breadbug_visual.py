"""Verified Giant Breadbug/nest display profile. No actor or gameplay registration."""
import argparse
import json
from pathlib import Path
from experimental.pikmin2_breadbug_visual import sha, read_verified, placements_text
from experimental.pikmin2_breadbug_lane_install import verify_mod

CONFIG = 'p2-giant-breadbug-visual.txt'
MAX_MODEL = 2 * 1024 * 1024
MAX_BANK = 32 * 1024 * 1024


def prepare(lane_import, lane_profile, output, placements):
    """Bind source durations/frames to the exact previously staged lane models."""
    lines = placements_text(placements)
    source_raw = (lane_import / 'breadbug-lane.json').read_bytes()
    source = json.loads(source_raw)
    staged_raw = (lane_profile / 'breadbug-lane-profile.json').read_bytes()
    staged = json.loads(staged_raw)
    if source.get('schema') != 1 or source.get('lane') != 213 or staged.get('schema') != 1 or staged.get('lane') != 220:
        raise ValueError('Unsupported lane schema')
    if staged.get('source_import_sha256') != sha(source_raw):
        raise ValueError('Lane profile source mismatch')
    if source['classification']['39']['spawnable'] or source['classification']['83']['spawnable']:
        raise ValueError('Nest/helper cannot become an actor')
    files = {}; config = ['P2_GIANT_BREADBUG_VISUAL_1']; motions = []
    for label, stem in [('wait', 'wait1'), ('move', 'move1')]:
        matches = [c for c in source['species']['OoPanModoki']['clips'] if c['file'] == stem + '.bca']
        if len(matches) != 1: raise ValueError('Missing source clip')
        clip = matches[0]; duration = clip['source_frames']; poses = clip['poses']
        frames = [p['frame'] for p in poses]
        if clip['status'] != 'sampled_poses_converted' or type(duration) is not int or not 2 <= duration <= 10000 or not 2 <= len(frames) <= 12:
            raise ValueError('Unsupported clip budget')
        if any(type(f) is not int for f in frames) or frames != sorted(set(frames)) or frames[0] != 0 or frames[-1] != duration - 1:
            raise ValueError('Invalid frame samples')
        config.append(f'{label} {duration} {len(frames)} ' + ' '.join(map(str, frames)))
        for pose in poses:
            name = f"lane_ootake_{stem}_{pose['frame']:03}.mod"
            if staged['files'].get(name) != pose['sha256']: raise ValueError('Staged pose mismatch')
            files[name] = read_verified(lane_profile / 'models' / name, pose['sha256'])
        motions.append(dict(kind=label, duration=duration, frames=frames))
    nest = source['species']['PanHouse']['static_pose']
    name = 'lane_nest_nest.mod'
    if nest['file'] != 'nest.mod' or staged['files'].get(name) != nest['sha256']: raise ValueError('Nest mismatch')
    files[name] = read_verified(lane_profile / 'models' / name, nest['sha256'])
    for data in files.values():
        verify_mod(data)
        if len(data) > MAX_MODEL: raise ValueError('Model budget exceeded')
    if sum(map(len, files.values())) > MAX_BANK: raise ValueError('Bank budget exceeded')
    config += [str(len(lines)), *lines]
    raw = ('\n'.join(config) + '\n').encode('ascii')
    output.mkdir(parents=True, exist_ok=False); (output / 'models').mkdir()
    for name, data in files.items(): (output / 'models' / name).write_bytes(data)
    (output / CONFIG).write_bytes(raw)
    result = dict(schema=1, source_sha256=sha(source_raw), lane_profile_sha256=sha(staged_raw),
                  behavior='display_only_no_actor_collision_rewards', native_validated=False,
                  files={n:sha(d) for n,d in files.items()}, config_sha256=sha(raw),
                  clips=motions, placements=placements)
    (output / 'giant-breadbug-visual.json').write_bytes((json.dumps(result, indent=2)+'\n').encode())
    return result


def install(profile, run):
    metadata = json.loads((profile / 'giant-breadbug-visual.json').read_bytes())
    if metadata.get('schema') != 1 or metadata.get('behavior') != 'display_only_no_actor_collision_rewards': raise ValueError('Unsupported profile')
    config = read_verified(profile / CONFIG, metadata['config_sha256'])
    expected = {'lane_nest_nest.mod'}
    protocol = ['P2_GIANT_BREADBUG_VISUAL_1']
    for label, stem in [('wait','wait1'),('move','move1')]:
        clips = [c for c in metadata['clips'] if c['kind'] == label]
        if len(clips) != 1: raise ValueError('Invalid clip mapping')
        clip=clips[0];frames=clip['frames'];duration=clip['duration']
        if type(duration) is not int or not 2<=duration<=10000 or not isinstance(frames,list) or not 2<=len(frames)<=12 or any(type(f) is not int for f in frames) or frames!=sorted(set(frames)) or frames[0]!=0 or frames[-1]!=duration-1: raise ValueError('Invalid frames')
        protocol.append(f'{label} {duration} {len(frames)} '+' '.join(map(str,frames)))
        expected.update(f'lane_ootake_{stem}_{f:03}.mod' for f in frames)
    rows=placements_text(metadata['placements']);protocol += [str(len(rows)),*rows]
    if config!=('\n'.join(protocol)+'\n').encode('ascii'): raise ValueError('Config metadata mismatch')
    if set(metadata['files']) != expected: raise ValueError('Unexpected model set')
    files = {name:read_verified(profile/'models'/name,digest) for name,digest in metadata['files'].items()}
    for name, data in files.items():
        if Path(name).name != name or len(data)>MAX_MODEL: raise ValueError('Invalid model')
        verify_mod(data)
    if sum(map(len,files.values()))>MAX_BANK: raise ValueError('Bank budget exceeded')
    room=run/'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.resolve()!=room.absolute(): raise ValueError('Expected private directory')
    if (run/CONFIG).exists() or any((room/n).exists() for n in files): raise ValueError('Refusing overwrite')
    for name,data in files.items():
        (room/name).write_bytes(data)
        read_verified(room/name,sha(data))
    (run/CONFIG).write_bytes(config);read_verified(run/CONFIG,sha(config))
    return metadata


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lane-import',type=Path,required=True);p.add_argument('--lane-profile',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--placements',type=Path,required=True)
    a=p.parse_args();prepare(a.lane_import,a.lane_profile,a.output,json.loads(a.placements.read_bytes()))

if __name__=='__main__':main()
