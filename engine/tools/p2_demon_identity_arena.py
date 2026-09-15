"""Lane-local (#242) dedicated captor spawn: post-process a prepared private
arena's ``chal0/default.gen`` so its single enemy generator carries the PC-only
``TEKI_P2Demon`` identity (type 35) instead of the Dwarf Bulborb placeholder
(``TEKI_Chappy`` type 3).

This deliberately does not edit the shared lane-03/lane-05 room stagers. The
lane runs the ordinary room stager first, then rewrites only the generated stage
file inside the lane-owned session directory. The engine already registers
``TEKI_P2Demon`` and selects it in ``pc_p2_demon_host.cpp``; this tool is the
missing spawn side that makes the ordinary generator actually carry it.

Record framing is the v0.1 generator fixture layout used by
``scripts/preview_pikmin2_room.py``: the file starts with ``1.0v`` plus a
big-endian record count at offset 20, and every top-level generator record
starts with four spaces followed by ``0.0v``. Inside a record, bytes 72..75 are
the reversed object id (``iket`` == ``teki``) and byte 80 is the v10 teki type
enum.
"""
import argparse
import re
import struct
from pathlib import Path

TEKI_CHAPPY = 3
TEKI_P2DEMON = 35
RECORD_MARK = b'    0.0v'
TEKI_OBJECT_ID = b'iket'


def record_starts(blob):
    starts = [match.start() for match in re.finditer(re.escape(RECORD_MARK), blob)]
    if not starts or starts[0] != 24:
        raise ValueError('unsupported generator framing')
    count = struct.unpack_from('>I', blob, 20)[0]
    if len(starts) != count:
        raise ValueError('generator record count mismatch')
    return starts


def patch_teki_identity(data, new_type=TEKI_P2DEMON):
    """Return ``(patched_bytes, old_type)`` for the one enemy generator record."""
    blob = bytearray(data)
    found = []
    for start in record_starts(blob):
        if blob[start + 72:start + 76] != TEKI_OBJECT_ID:
            continue
        found.append((start, blob[start + 80]))
    if len(found) != 1:
        raise ValueError('expected exactly one enemy generator, found %d' % len(found))
    if found[0][1] != TEKI_CHAPPY:
        raise ValueError('unexpected enemy generator type %d' % found[0][1])
    start, old_type = found[0]
    blob[start + 80] = new_type
    return bytes(blob), old_type


def patch_session(session, new_type=TEKI_P2DEMON):
    """Patch ``<session>/assets/dataDir/stages/chal0/default.gen`` in place."""
    path = Path(session) / 'assets/dataDir/stages/chal0/default.gen'
    original = path.read_bytes()
    patched, old_type = patch_teki_identity(original, new_type)
    path.write_bytes(patched)
    return path, old_type, new_type


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--type', type=int, default=TEKI_P2DEMON)
    args = parser.parse_args()
    path, old_type, new_type = patch_session(args.session, args.type)
    print('P2_DEMON_IDENTITY_PATCH file=%s old_type=%d new_type=%d' % (path, old_type, new_type), flush=True)


if __name__ == '__main__':
    main()
