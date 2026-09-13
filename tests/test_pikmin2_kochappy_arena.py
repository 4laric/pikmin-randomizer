import struct
from unittest.mock import patch
from experimental.pikmin2_kochappy_arena import roster


def entry(kind=b'iket',identity=1):
    r=bytearray(100);r[:8]=b'    0.0v';struct.pack_into('<I',r,8,identity);r[72:76]=kind
    return bytes(r)


def test_two_actors_and_control_not_aliased(tmp_path):
    source=tmp_path/'dataDir/stages/practice/default.gen';source.parent.mkdir(parents=True)
    source.write_bytes(b'1.0v'+struct.pack('>4fI',47,30,1919,180,1))
    with patch('experimental.pikmin2_kochappy_arena.records',return_value=[entry(b'goal')]),patch('experimental.pikmin2_kochappy_arena.generator',return_value=b'x'*24+entry()):
        data,actors=roster(tmp_path)
    assert struct.unpack_from('>I',data,20)[0]==3
    assert [a['species'] for a in actors]==['Kochappy','P1 Chappy']
    assert len({a['generator'] for a in actors})==2
    for a in actors:
        assert a['offset']==[0,0,0] and not a['source_yaw_applied']
        assert len(a['position'])==3


def test_collision_rejected(tmp_path):
    import pytest
    source=tmp_path/'dataDir/stages/practice/default.gen';source.parent.mkdir(parents=True);source.write_bytes(bytes(24))
    with patch('experimental.pikmin2_kochappy_arena.records',return_value=[entry(identity=186001)]),patch('experimental.pikmin2_kochappy_arena.generator',return_value=b'x'*24+entry()):
        with pytest.raises(ValueError,match='collision'):roster(tmp_path)
