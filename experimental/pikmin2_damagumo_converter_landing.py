'''Landing adapter for the committed #670 Damagumo converter artifacts (#685).

Reads the #670-derived artifact files read-only (never re-derives, never
duplicates the #670 converter): re-verifies each sha256 against the report
pins, validates structure against the integrated #678 hash-gated contract
(slot, enemy, joints, textures, clip rows) and the #638 arena staging
interface (arena_binding 312004 Damagumo), then emits a hashed
integration-ready packet for the single-writer integrator. Fail-closed:
any hash mismatch, structural defect or missing file raises.

No family/shared edits, no runtime, no ADMIT. All six gates UNTESTED.'''

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

LANE = 'damagumo-converter-artifact-landing'
ISSUE = 685
CONSUMER_ISSUE = 173
SLOT_ID = 312004

SOURCE_COMMITS = (
    '955be0ec06072d5bc5d14b69be9f8c62afdbaac9',
    '1848a8eea89da4bd26d5ac18b7ab7ea96569ae95',)

PINS = {
    'damagumo-family.json': 'f9ec5030890d72fba0c890b41407aa8788b6fac53223dd62f231a3259f68ef94',
    'Demon/enemy.bmd': '8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961',
    'damagumo-slot-312004.json': '61019a39bf255442e49cd5d03db6f16581ab5370ab401a346341f8d077c4e37c',}

CONTRACT = {
    'slot': 312004, 'enemy_id': 56, 'joint_count': 15, 'texture_count': 4,
    'row_max': {'landing': 69, 'wait': 75, 'flick': 69},
    'profile_prefix': 'f9ec5030', 'mesh_prefix': '8fc0ac7f', 'slot_prefix': '61019a39',}

class ArtifactError(ValueError):
    '''Raised for any hash mismatch, structural defect or missing file.'''


def sha256_file(path):
    with open(path, 'rb') as stream:
        out = hashlib.sha256()
        for block in iter(lambda: stream.read(65536), b''):
            out.update(block)
        return out.hexdigest()


def verify_artifact(directory, name, expected):
    path = Path(directory) / name
    if not path.is_file():
        raise ArtifactError('missing artifact file: ' + name)
    raw = path.read_bytes()
    canonical = raw.replace(b'\r\n', b'\n')
    observed = hashlib.sha256(canonical).hexdigest()
    if observed != expected:
        raise ArtifactError('hash mismatch for ' + name + ': observed ' + observed)
    return {'name': name, 'path': str(path), 'sha256': observed,
            'file_sha256': sha256_file(path),
            'line_endings': 'crlf' if raw != canonical else 'lf'}
def load_json(directory, name):
    try:
        return json.loads((Path(directory) / name).read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ArtifactError('unreadable artifact JSON ' + name + ': ' + str(error)) from error


def check_contract(slot_doc, family_doc):
    defects = []
    if slot_doc.get('slot') != CONTRACT['slot']:
        defects.append('slot id drift')
    if slot_doc.get('source_id') != CONTRACT['enemy_id']:
        defects.append('slot source_id drift')
    if slot_doc.get('model_sha256') != PINS['Demon/enemy.bmd']:
        defects.append('slot model hash drift')
    profile = family_doc.get('profiles', {}).get(str(CONTRACT['enemy_id']))
    if not isinstance(profile, dict):
        defects.append('family profile 56 absent')
        return defects
    for key, want in (('joint_count', CONTRACT['joint_count']),
                       ('embedded_texture_count', CONTRACT['texture_count']),
                       ('enemy_id', CONTRACT['enemy_id'])):
        if profile.get(key) != want:
            defects.append('profile ' + key + ' drift')
    if profile.get('model_sha256') != PINS['Demon/enemy.bmd']:
        defects.append('profile model hash drift')
    rows = profile.get('animation_rows', {})
    for clip, want_max in CONTRACT['row_max'].items():
        values = rows.get(clip)
        if not isinstance(values, list) or not values or max(values) != want_max:
            defects.append('animation row drift: ' + clip)
    return defects


def check_interface(slot_doc):
    defects = []
    if slot_doc.get('arena_binding') != '312004 Damagumo':
        defects.append('arena binding drift')
    if slot_doc.get('schema') != 1:
        defects.append('slot schema drift')
    return defects

def build_packet(directory, packet_out):
    records = [verify_artifact(directory, name, expected) for name, expected in PINS.items()]
    slot_doc = load_json(directory, 'damagumo-slot-312004.json')
    family_doc = load_json(directory, 'damagumo-family.json')
    defects = check_contract(slot_doc, family_doc) + check_interface(slot_doc)
    if defects:
        raise ArtifactError('contract/interface defects: ' + '; '.join(defects))
    packet = {'schema': 1, 'lane': LANE, 'issue': ISSUE, 'consumer_issue': CONSUMER_ISSUE,
              'slot': SLOT_ID, 'source_commits': list(SOURCE_COMMITS),
              'artifacts': records, 'contract': CONTRACT, 'defects': [],
              'placements_emitted': False}
    Path(packet_out).write_text(json.dumps(packet, indent=1, sort_keys=True), encoding='utf-8')
    print(json.dumps({'slot': SLOT_ID, 'artifacts': len(records), 'defects': [], 'packet': str(packet_out)}))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Land committed #670 artifacts via verified packet')
    parser.add_argument('--dir', required=True)
    parser.add_argument('--packet-out', required=True)
    args = parser.parse_args(argv)
    try:
        return build_packet(args.dir, args.packet_out)
    except ArtifactError as error:
        print('ERROR ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
