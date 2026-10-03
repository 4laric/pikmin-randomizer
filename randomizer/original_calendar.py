"""Retail surface generator load planning, in native day-counter units.

Source: projectPiki/pikmin2 29bc5478edffa2c963c88fdd261d876d055aa2b0,
gameStages.cpp LimitGenInfo::read and baseGameSection.cpp generator loading.
Plans do not instantiate actors, restore generator caches, or mutate save flags.
"""
from pathlib import PurePosixPath

import re


def tree(text):
    tokens = iter(re.findall(r"[{}]|[^\s{}]+", "\n".join(line.split("#")[0] for line in text.splitlines())))
    def block(nested=False):
        result = []
        for token in tokens:
            if token == "}":
                if not nested:
                    raise ValueError("Unexpected closing brace")
                return result
            result.append(block(True) if token == "{" else token)
        if nested:
            raise ValueError("Unclosed definition block")
        return result
    return block()


def course_schedule(text, course):
    values = tree(text)
    rows = [row for row in values[1:] if isinstance(row, list)
            and row[:2] == ['name', course]]
    if len(rows) != 1:
        raise ValueError('Expected exactly one source course declaration')
    row = rows[0]
    try:
        at = row.index('end') + 1
        result = dict(course=course, day_units='native_counter', nonloop=[], loop=[])
        for category in ('nonloop', 'loop'):
            count = int(row[at])
            at += 1
            if not 0 <= count <= 64:
                raise ValueError('Invalid source schedule count')
            names = set()
            for index in range(count):
                name, minimum, maximum, expiry = row[at:at+4]
                at += 4
                if (not isinstance(name, str) or not name or '\\' in name
                        or ':' in name or PurePosixPath(name).name != name
                        or name in ('.', '..') or name in names):
                    raise ValueError('Unsafe or duplicate source schedule name')
                minimum, maximum, expiry = int(minimum), int(maximum), int(expiry)
                if not 0 <= minimum <= maximum <= 0x7fffffff or not -1 <= expiry <= 0x7fffffff:
                    raise ValueError('Invalid source schedule day range')
                names.add(name)
                result[category].append(dict(index=index, member=category+'/'+name,
                                             minimum_day=minimum, maximum_day=maximum,
                                             expiry_day=expiry))
        return result
    except (IndexError, TypeError) as error:
        raise ValueError('Truncated source generator calendar') from error


def validate_members(schedule, members):
    available = set(members)
    required = {'defaultgen.txt'} | {row['member'] for category in ('nonloop', 'loop')
                                    for row in schedule[category]}
    missing = sorted(required - available)
    if missing:
        raise ValueError('Missing declared generator files: '+', '.join(missing))


def _flags(flags, count):
    flags = frozenset(flags)
    if any(type(index) is not int or not 0 <= index < count for index in flags):
        raise ValueError('Invalid persisted generator flag index')
    return flags


def _day(value):
    if type(value) is not int or not 0 <= value <= 0x7fffffff:
        raise ValueError('Invalid native day counter')


def load_plan(schedule, members, native_day, *, course_visited,
              nonloop_loaded=(), loop_loaded=()):
    """Plan files in original load order after the course cache is restored.

    Loaded flags are per-course declaration indices, not filenames or hashes.
    The consumer must persist flags for successful loads and use advance_loop_flags
    when advancing the native day. This function leaves input state unchanged.
    """
    _day(native_day)
    if type(course_visited) is not bool:
        raise ValueError('Invalid persisted course visited flag')
    available = set(members)
    validate_members(schedule, available)
    nonloop = _flags(nonloop_loaded, len(schedule['nonloop']))
    loops = _flags(loop_loaded, len(schedule['loop']))
    result = []
    for member in ('defaultgen.txt', 'plantsgen.txt', 'initgen.txt'):
        if member in available and (member != 'initgen.txt' or not course_visited):
            result.append(dict(member=member, category=member[:-7], index=None, expiry_day=-1))
    for category, loaded in (('nonloop', nonloop), ('loop', loops)):
        for row in schedule[category]:
            if row['index'] in loaded:
                continue
            minimum, maximum, expiry = row['minimum_day'], row['maximum_day'], row['expiry_day']
            today = native_day
            if category == 'loop':
                if native_day < 30:
                    continue
                minimum, maximum, today = minimum % 30, maximum % 30, native_day % 30
                expiry = expiry - 30 + (native_day // 30)*30
            if minimum <= today <= maximum:
                result.append(dict(member=row['member'], category=category,
                                   index=row['index'], expiry_day=expiry))
    daily = 'day/'+str(native_day % 30)+'.txt'
    if daily in available:
        result.append(dict(member=daily, category='day', index=None, expiry_day=-1))
    return result


def advance_loop_flags(loaded, next_native_day):
    """Original day-increment reset; call for each course after advancing a day."""
    _day(next_native_day)
    return frozenset() if next_native_day % 30 == 0 else frozenset(loaded)


def expired(expiry_day, native_day):
    _day(native_day)
    if type(expiry_day) is not int or not -0x80000000 <= expiry_day <= 0x7fffffff:
        raise ValueError('Invalid generator expiry day')
    return expiry_day != -1 and expiry_day < native_day


def stage_calendar(courses, stages, campaign):
    """Canonical immutable native table; activation flags remain in the card."""
    import hashlib
    source_sha = hashlib.sha256(stages).hexdigest()
    lines = [f'P2_SOURCE_CALENDAR 1 {campaign} {source_sha} 4']
    for course, members in courses:
        schedule = course_schedule(stages.decode('cp932'), course)
        validate_members(schedule, (member['member'] for member in members))
        lines.append(f'{course} {len(members)}')
        for member in sorted(members, key=lambda value: value['member']):
            lines.append(f"{member['member']} {member['source_sha256']} {len(member['records'])}")
            for record in member['records']:
                lines.append(f"{record['generator_uid']} {record['actor']['index']} {record['actor']['kind']}")
        for category in ('nonloop', 'loop'):
            lines.append(str(len(schedule[category])))
            for row in schedule[category]:
                lines.append(f"{row['member']} {row['minimum_day']} {row['maximum_day']} {row['expiry_day']}")
    lines.append('END')
    return ('\n'.join(lines) + '\n').encode('ascii')
