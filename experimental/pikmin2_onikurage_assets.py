"""OniKurage (Greater Spotted Jellyfloat, source 72) ISO source-art extractor.

Wave 3 flyers (#960). The Greater Spotted Jellyfloat ships the same ten clips
as the Lesser (``enemy/data/OniKurage/{model,anim}.szs`` plus the ``onikurage/``
entry of ``enemy/parm/enemyParms.szs``), so this mirrors
``experimental/pikmin2_kurage_assets.py`` with the OniKurage source paths: it
pulls the source model and motions off the retail disc, bakes one representative
pose per source clip into the Open Nectar MOD the P1 actor loads
(``onikurage_<name>.mod``, see ``pikmin2_onikurage_content``) and writes a
schema-1 ``onikurage.json`` plus the ``identity.json`` the family installer
pre-flights. The retail clip lengths and key events are the registry's own
(identical to the Kurage: wait 35, move1 60, move2 30, type1 75, type2 20,
flick1 60, flick2 60, dead1 96, dead2 96, attack 120). Deterministic and
read-only; no retail bytes are committed.
"""
import argparse
import json
from pathlib import Path

from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_breadbug_assets import sha, parameter_blocks
from experimental.pikmin2_convert import blocks, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_sheargrub_assets import animation_rows, joints
from experimental.pikmin2_skinning import draw_matrices

SOURCE_ID = 72
SPECIES = 'OniKurage'
ENUM_NAME = 'OniKurage'
MANIFEST = 'onikurage.json'
IDENTITY = 'identity.json'
MODEL_PATH = 'enemy/data/OniKurage/model.szs'
ANIM_PATH = 'enemy/data/OniKurage/anim.szs'
PARM_PATH = 'enemy/parm/enemyParms.szs'
PARM_PREFIX = 'onikurage/'
PARM_FILES = ('enemyparm.txt', 'enemycoll.txt', 'enemyanimmgr.txt')

# Native visual loader contract (engine/pc_port/pc_p2_kurage_visual.cpp:35-48):
# (staged name, source clip, sampled frame). wait/attack are required; the rest
# are the optional per-motion poses.
REQUIRED_VISUALS = (('wait', 'wait.bca', 0), ('attack', 'attack.bca', 37))
OPTIONAL_VISUALS = (
    ('move1', 'move1.bca', 0),
    ('move2', 'move2.bca', 0),
    ('type1', 'type1.bca', 0),
    ('type2', 'type2.bca', 0),
    ('flick1', 'flick1.bca', 16),
    ('flick2', 'flick2.bca', 20),
    ('dead1', 'dead1.bca', 0),
    ('dead2', 'dead2.bca', 0),
)
VISUALS = REQUIRED_VISUALS + OPTIONAL_VISUALS


def extract(iso, output):
    """Extract Kurage's source model/motions and bake the native visual poses.

    Returns the schema-1 ``kurage.json`` document. ``output`` must not exist;
    every file written is derived from the disc read above it. A required clip
    that is absent from the retail registry, or that fails to bake, raises
    ``ValueError`` rather than yielding a manifest the native loader cannot use.
    """
    iso, output = Path(iso), Path(output)
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
        model = archive_files(read(MODEL_PATH))['enemy.bmd']
        motions = archive_files(read(ANIM_PATH))
        parms = archive_files(read(PARM_PATH))
    names = joints(model)
    (output / 'enemy.bmd').write_bytes(model)
    for name in PARM_FILES:
        (output / name).write_bytes(parms[PARM_PREFIX + name])
    rows = animation_rows(parms[PARM_PREFIX + 'enemyanimmgr.txt'].decode('shift_jis'))
    registered = {row['file'] for row in rows}
    for name, clip, _frame in REQUIRED_VISUALS:
        if clip not in registered:
            raise ValueError(f'Required OniKurage clip missing from the disc registry: {clip}')
    wanted = {}
    for _name, clip, frame in VISUALS:
        wanted.setdefault(clip, set()).add(frame)
    clips = []
    poses_by_key = {}
    for row in rows:
        raw = motions[row['file']]
        (output / row['file']).write_bytes(raw)
        clip = dict(row, sha256=sha(raw), status='unsupported', poses=[])
        try:
            duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
            clip['source_frames'] = duration
            sampled = []
            for frame in sorted(wanted.get(row['file'], ())):
                if not 0 <= frame < duration:
                    raise ValueError(f'Sample frame {frame} outside {row["file"]}')
                _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                path = output / (Path(row['file']).stem + f'_{frame:04d}.mod')
                decoded = decode(model, True, bake_rigid=True,
                                 draw_matrices=draw_matrices(blocks(model), pose))
                conversion = write_model(decoded, path, 'enemy.bmd')
                conversion.update(source='enemy.bmd', output=path.name)
                path.with_suffix('.json').write_text(
                    json.dumps(conversion, indent=2) + '\n', encoding='utf-8')
                sampled.append(dict(frame=frame, file=path.name,
                                    sha256=sha(path.read_bytes())))
            clip['poses'] = sampled
            clip['status'] = 'converted'
            for entry in sampled:
                poses_by_key[(row['file'], entry['frame'])] = entry
        except ValueError as error:
            clip['reason'] = str(error)
        clips.append(clip)
    visuals = []
    for name, clip, frame in VISUALS:
        entry = poses_by_key.get((clip, frame))
        if entry is None:
            if (name, clip, frame) in REQUIRED_VISUALS:
                raise ValueError(f'Required OniKurage visual did not bake: {name} ({clip}@{frame})')
            continue
        visuals.append(dict(name=name, clip=clip, frame=frame, pose=entry['file'],
                            sha256=entry['sha256']))
    result = dict(
        schema=1, species=SPECIES, enemy_id=SOURCE_ID, enum_name=ENUM_NAME,
        native_ready=False, source_sha256=hashes, model_sha256=sha(model),
        joints=names,
        parameters=parameter_blocks(parms[PARM_PREFIX + 'enemyparm.txt']),
        clips=clips, visuals=visuals,
        limitations=[
            'Baked sampled poses; the actor draws one static shape per FSM state.',
            'Approximate materials/TEV; visual fidelity unvalidated.',
        ])
    (output / MANIFEST).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    (output / IDENTITY).write_text(
        json.dumps(dict(schema=1, source_id=SOURCE_ID, enum_name=ENUM_NAME),
                   indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.iso, args.output)
    print(json.dumps(dict(clips=len(result['clips']),
                          converted=sum(c['status'] == 'converted' for c in result['clips']),
                          visuals=len(result['visuals']))))
