"""Optional engineering hole/geyser markers; not imported P2 actors."""
import math


def read_transitions(directory):
    """Read once, validate before launch, then hash and stage the same bytes."""
    if directory is None:
        return {}
    result = {}
    for floor, kind in ((1, 'hole'), (2, 'geyser')):
        data = (directory / f'floor{floor}.txt').read_bytes()
        words = data.decode('ascii').split()
        if len(words) != 6 or words[:2] != ['P2_CAVE_TRANSITION_1', kind]:
            raise ValueError(f'Invalid floor {floor} transition header')
        try:
            x, y, z, radius = map(float, words[2:])
        except ValueError as error:
            raise ValueError(f'Invalid floor {floor} transition coordinates') from error
        if (not all(math.isfinite(n) for n in (x, y, z, radius))
                or any(abs(n) > 100000 for n in (x, y, z)) or not 20 <= radius <= 150):
            raise ValueError(f'Invalid floor {floor} transition bounds')
        result[floor] = data
    return result
