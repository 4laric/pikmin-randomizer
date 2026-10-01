"""Lane-49 cave converter water-volume sidecar contract.

Converts a per-unit P2 ``texts/waterbox.txt`` comment/brace tree into the
fail-closed sidecar the lane-49 converter emits alongside a decoded room, and
validates that sidecar against the room's horizontal bounds. The common
``texts/waterbox.txt`` parser is reused from
:mod:`experimental.pikmin2_surface_physics`; this module never reimplements it.
"""
from collections.abc import Mapping

from experimental.pikmin2_surface_physics import water_boxes


WATER_SCHEMA = 1

_WATER_QUERY = 'xz_sphere_overlap_and_center_y_le_surface_minus_3_no_bottom_test'
_ROOM_EPSILON = 1.0


def water_unit_sidecar(text):
    """Build the lane-49 water sidecar record for one unit's waterbox source."""
    try:
        boxes = water_boxes(text)
    except ValueError as error:
        raise ValueError(f'Unparseable waterbox source: {error}') from error
    return {
        'schema': WATER_SCHEMA,
        'source': 'Game::SeaMgr/AABBWaterBox',
        'boxes': boxes,
        'count': len(boxes),
        'empty': len(boxes) == 0,
        'surface': max((box['surface'] for box in boxes), default=None),
        'runtime_min_y': min((box['runtime_min_y'] for box in boxes), default=None),
        'query': _WATER_QUERY,
        'dynamic_lowering_supported': False,
        'native_consumer_implemented': False,
    }


def validate_water_sidecar(sidecar, room):
    """Fail-closed validation of a sidecar against a decoded room's bounds.

    Only X/Z are constrained (room bounds expanded by ``_ROOM_EPSILON``); P2
    water boxes may extend arbitrarily below the floor, so Y is not tested.
    """
    if not isinstance(sidecar, Mapping):
        raise ValueError('Water sidecar must be a mapping')
    if sidecar.get('schema') != WATER_SCHEMA:
        raise ValueError(f'Unsupported water sidecar schema: {sidecar.get("schema")!r}')
    boxes = sidecar.get('boxes')
    if not isinstance(boxes, list):
        raise ValueError('Water sidecar boxes must be a list')
    if sidecar.get('count') != len(boxes):
        raise ValueError(
            f'Water sidecar count {sidecar.get("count")!r} does not match {len(boxes)} boxes')
    if not isinstance(room, Mapping) or not isinstance(room.get('bounds'), Mapping):
        raise ValueError('Room is missing decoded bounds')
    bounds = room['bounds']
    low, high = bounds.get('min'), bounds.get('max')
    if (not isinstance(low, list) or not isinstance(high, list)
            or len(low) != 3 or len(high) != 3):
        raise ValueError('Room bounds must provide 3D min/max')
    for index, box in enumerate(boxes):
        if not isinstance(box, Mapping) or 'min' not in box or 'max' not in box:
            raise ValueError(f'Water box {index} is missing min/max')
        box_min, box_max = box['min'], box['max']
        for axis, label in ((0, 'X'), (2, 'Z')):
            if box_min[axis] < low[axis] - _ROOM_EPSILON:
                raise ValueError(
                    f'Water box {index} min {label} {box_min[axis]} is below room bounds '
                    f'{low[axis] - _ROOM_EPSILON}')
            if box_max[axis] > high[axis] + _ROOM_EPSILON:
                raise ValueError(
                    f'Water box {index} max {label} {box_max[axis]} is above room bounds '
                    f'{high[axis] + _ROOM_EPSILON}')
    return True
