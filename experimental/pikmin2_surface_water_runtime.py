"""Serialize exact static tutorial volumes for the opt-in native water consumer."""
import math
from experimental.pikmin2_surface_physics import water_boxes


def serialize(text):
    boxes = water_boxes(text)
    if len(boxes) != 3:
        raise ValueError('Tutorial requires its three source volumes')
    lines = ['P2_SURFACE_WATER_1 tutorial 3']
    for box in boxes:
        values = box['min'] + box['max'] + [box['surface'], box['lowered_amount']]
        assert all(math.isfinite(v) for v in values)
        lines.append(str(box['id']) + ' ' + ' '.join(format(v, '.9g') for v in values))
    return ('\n'.join(lines) + '\n').encode('ascii')
