"""BigTreasure retail motion event table (P2_RETAIL_EVENTS_1) for the vendored player (#246).

Lane-owned glue: encodes the 29 unique BigTreasure clips from a
``pikmin2_bigtreasure_assets`` import directory into the exact
P2_RETAIL_EVENTS_1 table format consumed by the verified retail event
player (#259, vendored at native/pc_port/pc_p2_retail_player.h with its
reader pc_p2_motion_events.h). The shared #257 encoder
(experimental/pikmin2_motion_events.py in the engine lane) rejects
duplicate registry rows; BigTreasure legitimately registers wait2.bca
twice with divergent event rows (30 slots / 29 unique clips), so this
lane emits the table keyed by unique clip, taking the first (loop-carrying)
registration and verifying duplicate rows against the import report's
per-slot record. No shared converter code is modified.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_engine_parms import parse_anim_mgr
from experimental.pikmin2_purple import bca_pose

MAX_CLIP_BYTES = 16 * 1024 * 1024


def encode(directory, report_path=None):
    """Validate every clip and emit the table bytes; nothing is written early."""
    directory = Path(directory)
    raw = (directory / 'enemyanimmgr.txt').read_bytes()
    rows = parse_anim_mgr(raw.decode('shift_jis'))['clips']
    slot_names = [r['file'].lower() for r in rows]
    if len(set(slot_names)) != 29 or len(rows) != 30:
        raise ValueError('Expected the 30-slot / 29-unique BigTreasure registry')
    slot_events = [[list(e) for e in r['events']] for r in rows]
    if report_path is not None:
        report = json.loads(Path(report_path).read_bytes())
        if report.get('anim_slot_events') != slot_events:
            raise ValueError('Registry diverges from the verified import report')
    digest = hashlib.sha256(raw).hexdigest()
    seen = {}
    for row in rows:
        name = row['file'].lower()
        if name not in seen:  # first registration carries the loop markers
            seen[name] = [list(e) for e in row['events']]
    lines = [f'P2_RETAIL_EVENTS_1 {digest} {len(seen)}']
    for name in sorted(seen, key=list(dict.fromkeys(slot_names)).index):
        events = seen[name]
        path = directory / name
        if not path.is_file():
            raise ValueError(f'Missing clip: {name}')
        if path.stat().st_size > MAX_CLIP_BYTES:
            raise ValueError('BCA exceeds budget')
        data = path.read_bytes()
        if len(data) < 72:
            raise ValueError('Truncated BCA')
        duration, _ = bca_pose(data, 0, struct.unpack_from('>H', data, 44)[0], allow_scale=True)
        if not 1 <= duration <= 10000 or data[40] > 4:
            raise ValueError('Unsupported BCA duration/attribute')
        if any(frame >= duration or frame < 0 for frame, _ in events):
            raise ValueError(f'Event outside clip {name}')
        lines.append(f'{name} {duration} {data[40]} {hashlib.sha256(data).hexdigest()} {len(events)}')
        lines.extend(f'{frame} {kind}' for frame, kind in events)
    return ('\n'.join(lines) + '\n').encode('ascii')


def write(directory, output, report_path=None):
    data = encode(directory, report_path)
    with Path(output).open('xb') as stream:  # never overwrite
        stream.write(data)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, default=None,
                        help='import bigtreasure.json for per-slot registry cross-check')
    args = parser.parse_args()
    data = write(args.directory, args.output, args.report)
    print(f'{len(data)} bytes, {data.count(chr(10).encode())} lines')
