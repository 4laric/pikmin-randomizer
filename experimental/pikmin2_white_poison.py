"""Prepare opt-in White swallow poison from the user's GPVE01 revision 0 disc."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_breadbug_assets import parameter_blocks

ARCHIVE = 'enemy/parm/enemyParms.szs'
MEMBER = 'chappy/enemyparm.txt'


def generator_id(token):
    if not re.fullmatch(r'[0-9]+', token) or int(token) > 0xffffffff:
        raise ValueError('Generator ID must be an unsigned 32-bit decimal')
    return int(token)


def source_profile(raw):
    blocks = parameter_blocks(raw)
    if len(blocks) != 3 or blocks[2] != {'fp01': 30.0, 'fp02': 750.0}:
        raise ValueError('Unexpected retail Chappy proper parameters; require fp02=750')
    return {'proper_parameters': blocks[2], 'poison_damage': blocks[2]['fp02']}


def extract(iso, output, predator_generators):
    ids = list(predator_generators)
    if not 1 <= len(ids) <= 32 or any(type(value) is not int or not 0 <= value <= 0xffffffff for value in ids):
        raise ValueError('Predator generator IDs must be 1 to 32 unsigned 32-bit integers')
    if len(ids) != len(set(ids)):
        raise ValueError('Predator generator IDs must be unique')
    catalog = disc_files(iso)
    with iso.open('rb') as stream:
        offset, size = catalog[ARCHIVE]
        stream.seek(offset)
        archive = stream.read(size)
    raw = archive_files(archive)[MEMBER]
    report = source_profile(raw)
    report.update(schema=1, disc='GPVE01', revision=0,
                  archive=ARCHIVE, archive_sha256=hashlib.sha256(archive).hexdigest(),
                  member=MEMBER, member_sha256=hashlib.sha256(raw).hexdigest(),
                  predator_generators=ids, native_family='TEKI_Swallow',
                  scope='Successful White mouth consumption only; gas is not implemented')
    config = ('P2_WHITE_POISON_1\ndamage 750\npredator_generators '
              + str(len(ids)) + ' ' + ' '.join(map(str, ids)) + '\n')
    report['config_sha256'] = hashlib.sha256(config.encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'p2-white-poison.txt').write_bytes(config.encode())
    (output / 'white-poison.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--predator-generators', type=generator_id, nargs='+', required=True)
    args = parser.parse_args()
    print(json.dumps(extract(args.iso, args.output, args.predator_generators), indent=2))
