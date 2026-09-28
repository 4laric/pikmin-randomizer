"""Bounded sampled Snow animation protocol; no gameplay animation events."""
import struct

CLIPS = ('wait1', 'move1', 'attack', 'dead', 'flick')
MAX_POSES = 24
CLIP_BYTES = 512 * 1024
TOTAL_BYTES = 2 * 1024 * 1024


def sample_frames(duration, limit=MAX_POSES):
    if type(duration) is not int or not 1 <= duration <= 10000 or not 2 <= limit <= MAX_POSES:
        raise ValueError('Invalid Snow sample limit/duration')
    count = min(limit, duration)
    return [round(i * (duration - 1) / max(1, count - 1)) for i in range(count)]


def parse_bank(text):
    tokens = iter(text.split())
    try:
        header = next(tokens)
        if header not in ('P2_SNOW_1', 'P2_SNOW_2'):
            raise ValueError('Invalid Snow bank version')
        result = {}
        for name in CLIPS:
            if next(tokens) != name:
                raise ValueError('Invalid Snow clip order')
            count, duration = int(next(tokens)), int(next(tokens))
            if not 1 <= count <= (12 if header.endswith('1') else MAX_POSES) or not 1 <= duration <= 10000:
                raise ValueError('Invalid Snow clip bounds')
            frames = ([int(next(tokens)) for _ in range(count)] if header.endswith('2') else None)
            if frames is not None and (frames[0] != 0 or frames[-1] != duration-1 or
                                       any(a >= b for a, b in zip(frames, frames[1:]))):
                raise ValueError('Invalid Snow source frames')
            result[name] = {'poses': count, 'source_frames': duration, 'frames': frames}
        if next(tokens, None) is not None:
            raise ValueError('Trailing Snow bank data')
        return result
    except (StopIteration, TypeError) as exc:
        raise ValueError('Truncated Snow bank') from exc


def resource_chunks(data):
    """Static render resources must match before native material aliasing."""
    at = 0
    tag = None
    found = {}
    while at + 8 <= len(data):
        tag, size = struct.unpack_from('>II', data, at)
        end = at + 8 + size
        if end > len(data):
            raise ValueError('Truncated Snow MOD chunk')
        if tag in (32, 34, 48):
            if tag in found:
                raise ValueError('Duplicate Snow render resource')
            found[tag] = data[at:end]
        at = end
        if tag == 65535:
            break
    if at != len(data) or tag != 65535 or set(found) != {32, 34, 48}:
        raise ValueError('Incomplete Snow MOD resources')
    return b''.join(found[tag] for tag in (32, 34, 48))


def validate_files(directory, bank):
    paths, total, reference = [], 0, None
    for name, info in bank.items():
        clip_bytes = 0
        for index in range(info['poses']):
            path = directory / f'snow_{name}_{index:02}.mod'
            size = path.stat().st_size
            clip_bytes += size
            total += size
            if not size or clip_bytes > CLIP_BYTES or total > TOTAL_BYTES:
                raise ValueError('Snow pose bank exceeds byte budget')
            resources = resource_chunks(path.read_bytes())
            if reference is not None and resources != reference:
                raise ValueError('Snow pose render resources differ')
            reference = resources
            paths.append(path)
    return paths, total
