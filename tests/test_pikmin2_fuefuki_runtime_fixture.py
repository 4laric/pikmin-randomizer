import struct
import pytest
from experimental.pikmin2_fuefuki_runtime_fixture import combine
from scripts.preview_pikmin2_room import records


def record(identity, kind):
    data = bytearray(100)
    data[:8] = b'    0.0v'
    struct.pack_into('<I', data, 8, identity)
    data[72:76] = kind
    return bytes(data)


def test_layer_preserves_squad_treasure_and_rejects_id_collision(tmp_path):
    path = tmp_path / 'default.gen'
    original = [record(i, b'ikip') for i in range(1, 21)] + [record(21, b'tlep')]
    header = b'1.0v' + struct.pack('>4f', -85, 0, 0, 45)
    path.write_bytes(header + struct.pack('>I', len(original)) + b''.join(original))
    actors = [record(245001, b'iket'), record(245002, b'iket')]
    combine(path, actors)
    assert records(path) == original + actors
    before = path.read_bytes()
    with pytest.raises(ValueError, match='collides'):
        combine(path, actors)
    assert path.read_bytes() == before
