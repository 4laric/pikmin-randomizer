"""Fuefuki retail motion event table (P2_RETAIL_EVENTS_1) for the lane FSM (#245).

Lane-owned glue: encodes the 10 FUEFUKIANIM clips from a
``pikmin2_fuefuki_assets`` import directory into the exact
P2_RETAIL_EVENTS_1 table format consumed by the vendored retail event player
(native/pc_port/pc_p2_retail_player.h, reader pc_p2_motion_events.h). The lane
FSM needs the authored KEYEVENT_2/3 and clip completion to advance its states;
without a source Beetle animation bank (#128) this table is the host feed.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from experimental.pikmin2_engine_parms import parse_anim_mgr
from experimental.pikmin2_purple import bca_pose

MAX_CLIP_BYTES = 16 * 1024 * 1024
EXPECTED_CLIPS = 10


def encode(directory, report_path=None):
    directory = Path(directory)
    raw = (directory / 'enemyanimmgr.txt').read_bytes()
    rows = parse_anim_mgr(raw.decode('shift_jis'))['clips']
    names = [row['file'].lower() for row in rows]
    if len(names) != EXPECTED_CLIPS or len(set(names)) != EXPECTED_CLIPS:
        raise ValueError('Expected the 10 unique Fuefuki registry clips')
    slot_events = [[list(e) for e in row['events']] for row in rows]
    if report_path is not None:
        report = json.loads(Path(report_path).read_bytes())
        registration = report['species']['Fuefuki']['registration']
        if registration != [[name[:-4], events] for name, events in zip(names, slot_events)]:
            raise ValueError('Registry diverges from the verified import report')
    digest = hashlib.sha256(raw).hexdigest()
    lines = [f'P2_RETAIL_EVENTS_1 {digest} {len(names)}']
    for name, events in zip(names, slot_events):
        path = directory / name
        if not path.is_file():
            raise ValueError(f'Missing clip: {name}')
        if path.stat().st_size > MAX_CLIP_BYTES:
            raise ValueError('BCA exceeds budget')
        data = path.read_bytes()
        if len(data) < 72:
            raise ValueError('Truncated BCA')
        # landing/landfail carry an authored singular joint scale; duration is
        # read without requiring a drawable pose.
        duration, _ = bca_pose(data, 0, struct.unpack_from('>H', data, 44)[0],
                               allow_scale=True, singular_scale='allow')
        if not 1 <= duration <= 10000 or data[40] > 4:
            raise ValueError('Unsupported BCA duration/attribute')
        if any(frame >= duration or frame < 0 for frame, _ in events):
            raise ValueError(f'Event outside clip {name}')
        lines.append(f'{name} {duration} {data[40]} {hashlib.sha256(data).hexdigest()} {len(events)}')
        lines.extend(f'{frame} {kind}' for frame, kind in events)
    return ('\n'.join(lines) + '\n').encode('ascii')


def write(directory, output, report_path=None):
    data = encode(directory, report_path)
    with Path(output).open('xb') as stream:
        stream.write(data)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--report', type=Path, default=None)
    args = parser.parse_args()
    data = write(args.directory, args.output, args.report)
    print(f'{len(data)} bytes, {data.count(chr(10).encode())} lines')
