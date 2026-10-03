"""Original course records selected for native loading (#148).

Consumes raw CP932 members and the retail calendar; never the stale summary
inventory. Native actor construction/cache application remains the consumer's
responsibility. Opaque species tails and nonenemy records remain explicit.
"""
from copy import deepcopy
import hashlib
import math
from pathlib import PurePosixPath

from experimental.pikmin2_generator_calendar import load_plan
from experimental.pikmin2_generator_objects import enemy_object
from experimental.pikmin2_surface_pocket import generators


def course_generators(schedule, payloads, native_day, *, course_visited,
                      nonloop_loaded=(), loop_loaded=()):
    """Return complete selected member batches, with stable per-record identities.

    Identities include course/member/index, independent of day, selected files,
    dictionary ordering or actor survivors. The full source catalog is checked
    for collisions before selection. Neither save flags nor input bytes change.
    This is not proof that a species, tail, birth mode or drop is implemented.
    """
    course = schedule['course']
    if course != 'tutorial':
        raise ValueError('Only the source-qualified tutorial course is implemented')
    if (not isinstance(payloads, dict) or len(payloads) > 256
            or any(not isinstance(name, str) for name in payloads)):
        raise ValueError('Invalid course source member inventory')
    catalog, ids = {}, set()
    for member, raw in sorted(payloads.items()):
        path = PurePosixPath(member)
        if (not isinstance(member, str) or path.is_absolute() or '\\' in member
                or ':' in member or '..' in path.parts or str(path) != member
                or not member.endswith('.txt')):
            raise ValueError('Unsafe original generator member')
        if not isinstance(raw, bytes) or len(raw) > 8 * 1024 * 1024:
            raise ValueError('Invalid original generator bytes: ' + member)
        parsed = generators(raw.decode('cp932'))
        if not math.isfinite(parsed['header_direction']):
            raise ValueError('Invalid original generator header direction: ' + member)
        records = []
        for actor in parsed['actors']:
            key = f'{course}/{member}#{actor["index"]}'
            # Separate from P1/seed/fixture IDs; collision is a refusal, not probing.
            uid = 0x52000000 | (int.from_bytes(hashlib.sha256(key.encode('utf8')).digest()[:3], 'big'))
            if uid in ids:
                raise ValueError('Original course generator identity collision: ' + key)
            ids.add(uid)
            record = dict(source_key=key, generator_uid=uid, actor=deepcopy(actor))
            if actor['kind'] == 'teki':
                record['enemy'] = enemy_object(actor)
            records.append(record)
        catalog[member] = dict(member=member, source_sha256=hashlib.sha256(raw).hexdigest(),
                               header_start=parsed['header_start'],
                               header_direction=parsed['header_direction'], records=records)
    plan = load_plan(schedule, catalog, native_day, course_visited=course_visited,
                     nonloop_loaded=nonloop_loaded, loop_loaded=loop_loaded)
    return [dict(**catalog[row['member']], load=deepcopy(row)) for row in plan]
