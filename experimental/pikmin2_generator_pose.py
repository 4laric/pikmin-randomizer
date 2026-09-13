"""P1 generator common pose is position plus offset, never Euler rotation."""
import math
import struct


def write_position(record, position):
    if len(record)<72 or len(position)!=3 or any(not math.isfinite(x) for x in position):
        raise ValueError('Invalid generator position')
    struct.pack_into('>6f',record,48,*position,0,0,0)
    validate_position(record,position)


def validate_position(record, expected):
    if len(record)<72 or len(expected)!=3:raise ValueError('Truncated generator pose')
    position=struct.unpack_from('>3f',record,48);offset=struct.unpack_from('>3f',record,60)
    effective=tuple(a+b for a,b in zip(position,offset))
    if offset!=(0.,0.,0.) or any(not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>.01 for a,b in zip(effective,expected)):
        raise ValueError('Generator effective position mismatch or unexpected offset')
    return effective
