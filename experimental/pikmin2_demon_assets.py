"""Private Demon poses and mouth transforms; no installed captain capture."""
import argparse
import json
import math
from pathlib import Path
from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_breadbug_assets import sha, parameter_blocks
from experimental.pikmin2_sheargrub_assets import joints, animation_rows
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_skinning import draw_matrices


def frames_for(duration, events):
    if type(duration) is not int or not 1 <= duration <= 10000:
        raise ValueError('Invalid clip duration')
    frames = {0, duration-1}
    for frame, event in events:
        if type(frame) is not int or not 0 <= frame <= duration or type(event) is not int:
            raise ValueError('Invalid event frame')
        frames.add(min(frame, duration-1))
    # Include grab-window boundaries in every sufficiently long clip.
    frames.update(f for f in (10, 16, 17, 30) if f < duration)
    if len(frames) > 32:
        raise ValueError('Pose budget exceeded')
    return sorted(frames)


def extract(iso, output):
    index = disc_files(iso)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    with iso.open('rb') as disc:
        def read(path):
            offset, size = index[path]
            disc.seek(offset)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated disc entry')
            hashes[path] = sha(raw)
            return raw
        model = archive_files(read('enemy/data/Demon/model.szs'))['enemy.bmd']
        motions = archive_files(read('enemy/data/Demon/anim.szs'))
        parms = archive_files(read('enemy/parm/enemyParms.szs'))
    names = joints(model)
    mouth_names = ('rkamujnt', 'lkamujnt')
    if any(names.count(name) != 1 for name in mouth_names):
        raise ValueError('Missing or ambiguous mouth joint')
    (output/'enemy.bmd').write_bytes(model)
    for name in ('enemyparm.txt', 'enemycoll.txt', 'enemyanimmgr.txt'):
        (output/name).write_bytes(parms['demon/'+name])
    rows = animation_rows(parms['demon/enemyanimmgr.txt'].decode('shift_jis'))
    if not 1 <= len(rows) <= 32:
        raise ValueError('Clip budget exceeded')
    clips = []
    for row in rows:
        raw = motions[row['file']]
        (output/row['file']).write_bytes(raw)
        clip = dict(row, sha256=sha(raw), status='unsupported', poses=[])
        try:
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
            clip['source_frames'] = duration
            for frame in frames_for(duration, row['events']):
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                matrices = joint_matrices(blocks(model), pose)
                mouths = []
                for name in mouth_names:
                    matrix = matrices[names.index(name)]
                    if not all(math.isfinite(v) for r in matrix for v in r):
                        raise ValueError('Nonfinite mouth transform')
                    mouths.append(dict(joint=name, radius=15, matrix=matrix))
                path = output/(Path(row['file']).stem+f'_{frame:04}.mod')
                decoded = decode(model, True, bake_rigid=True, draw_matrices=draw_matrices(blocks(model), pose))
                conversion = write_model(decoded, path, 'enemy.bmd')
                conversion.update(source='enemy.bmd', output=path.name)
                path.with_suffix('.json').write_text(json.dumps(conversion, indent=2)+'\n', encoding='utf-8')
                clip['poses'].append(dict(frame=frame, file=path.name, sha256=sha(path.read_bytes()), mouths=mouths))
            clip['status'] = 'converted'
        except ValueError as error:
            clip['reason'] = str(error)
        clips.append(clip)
    result = dict(schema=1, species='Demon', enemy_id=32, native_ready=False,
                  source_sha256=hashes, model_sha256=sha(model), joints=names,
                  parameters=parameter_blocks(parms['demon/enemyparm.txt']), clips=clips,
                  limitations=['Baked sampled poses; no skeletal or event playback.',
                               'Mouth matrices are model-space before owner transform; radius15 is source world collision radius.',
                               'Approximate materials/TEV; visual fidelity unvalidated.',
                               'No live captain attachment, escape, flight or cleanup.'])
    (output/'demon.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.iso, args.output)
    print(json.dumps(dict(clips=len(result['clips']), converted=sum(c['status']=='converted' for c in result['clips']),
                         poses=sum(len(c['poses']) for c in result['clips']))))
