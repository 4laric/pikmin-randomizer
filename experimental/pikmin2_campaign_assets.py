"""Exclude explicitly labelled harness Pikmin from private campaign assets.

The native campaign already supplies twenty starters in the selected Onion.
Some local asset sets also contain a harness-only field squad beyond Hope's
landing wall. Never rewrite the shared asset input to remove it.
"""
from pathlib import Path
import re
import struct

HOPE_GENERATOR = 'dataDir/stages/stage1/default.gen'
SQUAD_LABEL = b'campaign red pikmin'.ljust(32, b'\0')


def without_test_squad(data):
    if SQUAD_LABEL not in data:
        return data
    # Generator::read consumes `count` records in order; an inactive `next`
    # record (stored `txen0.0v`) is a real record and must stay counted.
    starts = [m.start() for m in re.finditer(rb'(?:    |txen)0\.0v', data)]
    spaced = sum(data[s:s + 4] == b'    ' for s in starts)
    # Some harness copies were written with a header that skipped txen rows.
    if (len(data) < 24 or data[:4] != b'1.0v' or not starts or starts[0] != 24
            or struct.unpack_from('>I', data, 20)[0] not in (len(starts), spaced)):
        raise ValueError('Unsupported Hope generator containing campaign test squad')
    rows = [data[start:(starts[i + 1] if i + 1 < len(starts) else len(data))]
            for i, start in enumerate(starts)]
    kept = []
    for row in rows:
        if row[16:48] != SQUAD_LABEL:
            kept.append(row)
            continue
        # Fail closed if this reserved marker appears on a different actor.
        if (row[72:84] != b'ikip0.0vp00\x04' or row[88:92] != b'p01\x04'
                or len(row) < 96 or struct.unpack_from('>I', row, 84)[0] != 2
                or struct.unpack_from('>I', row, 92)[0] != 1):
            raise ValueError('Unexpected actor using campaign test squad label')
    return data[:20] + struct.pack('>I', len(kept)) + b''.join(kept)


def campaign_overrides(retail_assets):
    source = Path(retail_assets) / HOPE_GENERATOR
    if not source.is_file():
        return {}
    original = source.read_bytes()
    clean = without_test_squad(original)
    return {HOPE_GENERATOR: clean} if clean != original else {}
