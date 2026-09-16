"""Bounded source Sheargrub visual bank; native gameplay events remain untouched."""
import argparse
import hashlib
import json
from pathlib import Path
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_convert import convert
from experimental.pikmin2_animation import sample_frames, resource_chunks

MAX_POSES = 12
CLIP_BYTES = 256 * 1024
TOTAL_BYTES = 2 * 1024 * 1024
BASE = {'Dead':'dead','Damage':'dead_p','WaitAct1':'appear','WaitAct2':'dive','Move1':'move','Attack':'attack1'}
CLIPS = {'UjiA':('dead','dead_p','appear','dive','move','attack1','type5'),
         'UjiB':('dead','dead_p','appear','dive','move','attack1','attack2','eat','type5')}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def mapping(species):
    if species not in CLIPS:
        raise ValueError('Unknown Sheargrub species')
    result = dict(BASE)
    if species == 'UjiB':
        result.update(Type1='attack2', Type2='eat')
    return result


def checked(path, expected):
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError('Source hash mismatch: ' + str(path))
    return data


def prepare(imported, output, limit=MAX_POSES):
    if type(limit) is not int or not 2 <= limit <= MAX_POSES:
        raise ValueError('Pose cap must be 2..12')
    source = json.loads((imported/'sheargrubs.json').read_text())
    if source.get('schema') != 1 or set(source.get('species', {})) != set(CLIPS):
        raise ValueError('Unsupported source manifest')
    # Validate complete input before creating any output.
    inputs = {}
    for species, wanted in CLIPS.items():
        info = source['species'][species]
        model = checked(imported/species/'enemy.bmd', info['model_sha256'])
        joint_names = joints(model)
        if joint_names != info['joints']:
            raise ValueError('Joint identity mismatch')
        registry = checked(imported/species/'enemyanimmgr.txt', info['metadata_sha256']['enemyanimmgr.txt'])
        rows = animation_rows(registry.decode('shift_jis'))
        if tuple(Path(r['file']).stem for r in rows) != wanted:
            raise ValueError('Source clip roster/order mismatch')
        clips = info['clips']
        if [c['file'] for c in clips] != [r['file'] for r in rows]:
            raise ValueError('Source clip manifest mismatch')
        prepared = []
        for row, clip in zip(rows, clips):
            raw = checked(imported/species/row['file'], clip['sha256'])
            duration, _ = bca_pose(raw, 0, len(joint_names), allow_scale=True)
            prepared.append((row, raw, duration))
        inputs[species] = (model, joint_names, registry, prepared)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema=1, policy='P2_UJI_VISUAL_BANK_1', native_ready=False,
                  source_manifest_sha256=sha((imported/'sheargrubs.json').read_bytes()), species={},
                  gameplay_events_executed=False, total_bytes=0)
    for species, (model, names, registry, clips) in inputs.items():
        folder = output/species
        folder.mkdir()
        model_path = folder/'source.bmd'
        model_path.write_bytes(model)
        bank = dict(model_sha256=sha(model), registry_sha256=sha(registry), motion_mapping=mapping(species),
                    waiting_policy='appear frame0; native invisibility unchanged', corpse_policy='dead final frame',
                    unmapped_source_clips=['type5'], clips=[])
        reference = None
        for row, raw, duration in clips:
            clip = dict(name=Path(row['file']).stem, source_sha256=sha(raw), source_frames=duration,
                        events=row['events'], poses=[])
            clip_bytes = 0
            for index, frame in enumerate(sample_frames(duration, limit)):
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                filename = f"uji_{species}_{clip['name']}_{index:02}.mod"
                convert(model_path, folder/filename, True, bake_rigid=True, pose=pose)
                data = (folder/filename).read_bytes()
                resources = resource_chunks(data)
                if reference is not None and resources != reference:
                    raise ValueError('Animated pose changes render resources')
                reference = resources
                clip_bytes += len(data)
                report['total_bytes'] += len(data)
                if clip_bytes > CLIP_BYTES or report['total_bytes'] > TOTAL_BYTES:
                    raise ValueError('Sheargrub pose bank exceeds byte cap')
                clip['poses'].append(dict(file=filename, frame=frame, bytes=len(data), sha256=sha(data)))
            bank['clips'].append(clip)
        report['species'][species] = bank
    (output/'animation-bank.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pose-limit', type=int, default=MAX_POSES)
    args = parser.parse_args()
    result = prepare(args.imported, args.output, args.pose_limit)
    print(json.dumps({'bytes':result['total_bytes'], 'clips':{s:len(v['clips']) for s,v in result['species'].items()}}))
