"""Stage the Demon (Bumbling Snitchbug, source 32) native host files into a run.

Demon::Obj is a Sarai::Obj subclass (pikmin2 ``Demon.h``): it runs the Sarai
eleven-state FSM with captain targeting, its own model/animations and its own
parms. The native side is the Sarai host with the Demon species profile
(``engine/pc_port/pc_p2_sarai_manager.cpp`` ``buildHost`` with
``kDemonProfile``), which fails closed with ``bound=0 reason=host`` unless the
run directory carries every file it opens:

* ``assets/dataDir/courses/pikmin2room/demon0.mod``: byte copy of the attack1
  frame-0 pose mesh (rest mesh; the host switches to the sampled banks).
* ``assets/dataDir/courses/pikmin2room/demon_<clip>_<frame>.mod``: every
  sampled pose mesh of every clip.
* ``demon-<clip>-poses.txt`` for all twelve retail clips (wait1, move1,
  attack1, waitact2, waitact1, flick, type1..type5, dead):
  ``P2_DEMON_POSES_2`` banks (frame, mesh basename, 24 mouth floats).
* ``demon-attack-mouths.txt``: ``P2_DEMON_MOUTHS_1`` bank of attack1.
* ``demon-retail-events.txt``: ``P2_RETAIL_EVENTS_1`` table (every clip,
  source durations and key events verbatim from ``demon/enemyanimmgr.txt``).
* ``demon-parms.txt``: ``P2_DEMON_PARMS_1`` with the retail
  ``demon/enemyparm.txt`` general (``fp00`` life, ``fp09`` territory, ...) and
  proper (Sarai ``fp01``..``fp41``) parameter values.

The bank encodings reuse ``experimental.pikmin2_sarai_install`` exactly (same
native parsers). Nothing is converted or extracted here; a missing or
mismatched source file raises ``StagingError`` and never fabricates a pose, an
event or a parameter. Idempotent like the Sarai adapter.
"""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_staging import StagingError
from experimental import pikmin2_sarai_install as sarai

SOURCE_ID = 32
SPECIES = 'Demon'
MANIFEST = 'demon.json'
ROOM = sarai.ROOM
REST_MOD = 'demon0.mod'
MOUTH_CLIP = 'attack1.bca'
MOUTH_TXT = 'demon-attack-mouths.txt'
EVENTS_TXT = 'demon-retail-events.txt'
PARMS_TXT = 'demon-parms.txt'
PARMS_MAGIC = 'P2_DEMON_PARMS_1'
# Sarai.h AnimID order (SARAIANIM_Wait .. SARAIANIM_Carry): every clip the
# native host can start, each staged as its own bank.
CLIPS = ('wait1.bca', 'move1.bca', 'attack1.bca', 'waitact2.bca', 'waitact1.bca', 'flick.bca',
         'type1.bca', 'type2.bca', 'type3.bca', 'type4.bca', 'dead.bca', 'type5.bca')
# General parms the native profile reads (EnemyParmsBase ids) and the Sarai
# ProperParms ids (Sarai.h). All must be present in the retail blocks.
GENERAL_KEYS = ('fp00', 'fp06', 'fp08', 'fp28', 'fp09', 'fp10', 'fp12', 'fp13',
                'fp16', 'fp17', 'fp18', 'fp24')
PROPER_KEYS = ('fp01', 'fp02', 'fp03', 'fp04', 'fp05', 'fp06', 'fp11', 'fp12',
               'fp21', 'fp22', 'fp23', 'fp31', 'fp32', 'fp41')


def bank_name(clip):
    return f'demon-{Path(clip).stem}-poses.txt'


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _load_manifest(source):
    path = Path(source) / MANIFEST
    if not path.is_file():
        raise StagingError(f'Demon manifest missing for identity content: {path}')
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError) as error:
        raise StagingError(f'Demon manifest unreadable for identity content: {path}') from error
    if document.get('schema') != 1 or document.get('species') != SPECIES \
            or document.get('enemy_id') != SOURCE_ID:
        raise StagingError(f'Demon manifest identity mismatch for identity content: {path}')
    if not isinstance(document.get('clips'), list) or not document['clips']:
        raise StagingError(f'Demon manifest carries no clips for identity content: {path}')
    return document, raw


def _parms_payload(document, digest):
    blocks = document.get('parameters')
    if not isinstance(blocks, list) or len(blocks) != 3:
        raise StagingError('Demon parameter blocks missing (expected shake/general/proper)')
    general, proper = blocks[1], blocks[2]
    rows = []
    for scope, keys, block in (('general', GENERAL_KEYS, general), ('proper', PROPER_KEYS, proper)):
        for key in keys:
            value = block.get(key) if isinstance(block, dict) else None
            if type(value) not in (int, float):
                raise StagingError(f'Demon {scope} parameter missing: {key}')
            rows.append(f'{scope} {key} {sarai._fmt(value)}')
    text = '\n'.join([PARMS_MAGIC, digest, str(len(rows))] + rows) + '\n'
    return text.encode('ascii')


def plan(source):
    """Validate everything and return ``(text_files, mesh_files, digest)``; never writes."""
    source = Path(source)
    document, raw = _load_manifest(source)
    digest = _sha(raw)
    text_files, mesh_files = {}, {}
    for clip in CLIPS:
        text_files[bank_name(clip)] = sarai._pose_bank_payload(document, digest, clip)
        for pose in sarai._clip_poses(document, clip):
            if not pose['file'].startswith('demon_'):
                raise StagingError(f'Demon pose mesh is not demon_-prefixed: {pose["file"]}')
            data = sarai._mesh_bytes(source, clip, pose)
            if pose['file'] in mesh_files and mesh_files[pose['file']] != data:
                raise StagingError(f'Demon pose mesh name collision: {pose["file"]}')
            mesh_files[pose['file']] = data
    mouths = sarai._clip_poses(document, MOUTH_CLIP)
    text_files[MOUTH_TXT] = sarai._bank_text(
        sarai.MOUTHS_MAGIC, digest,
        [(pose['frame'], *sarai._mouth_values(pose, MOUTH_CLIP)) for pose in mouths])
    text_files[EVENTS_TXT], _registry = sarai._events_payload(document)
    text_files[PARMS_TXT] = _parms_payload(document, digest)
    if mouths[0]['frame'] != 0:
        raise StagingError('Demon rest pose is not attack1 frame 0')
    mesh_files[REST_MOD] = mesh_files[mouths[0]['file']]
    return text_files, mesh_files, digest


def stage_demon_host(source, run):
    """Stage every native Demon host file from an extracted ``<content>/Demon`` tree."""
    source, run = Path(source), Path(run)
    if not run.is_dir():
        raise StagingError(f'Demon run directory missing: {run}')
    room = run / ROOM
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Demon room directory missing for run staging: {room}')
    text_files, mesh_files, digest = plan(source)
    targets = dict(text_files)
    targets.update({str(ROOM / name): payload for name, payload in mesh_files.items()})
    conflicts = sorted(name for name, payload in targets.items()
                       if (run / name).is_file() and (run / name).read_bytes() != payload)
    if conflicts:
        raise StagingError('Refusing conflicting Demon host staging: ' + ', '.join(conflicts))
    if all((run / name).is_file() for name in targets):
        staged = 'existing_identical'
    else:
        for name, payload in targets.items():
            (run / name).write_bytes(payload)
        staged = 'written'
    return dict(species=SPECIES, source_id=SOURCE_ID, staged=staged, manifest_sha256=digest,
                files={name: _sha(payload) for name, payload in targets.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    receipt = stage_demon_host(args.source, args.run)
    print(json.dumps(dict(receipt, files=len(receipt['files'])), sort_keys=True, indent=2))
