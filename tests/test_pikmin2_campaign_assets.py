import hashlib
import json
import struct

import pytest

from experimental.pikmin2_campaign_assets import HOPE_GENERATOR, SQUAD_LABEL, without_test_squad
from experimental.pikmin2_family_install import prepare_private_destination, _replay_from_cache


def record(label, kind=b'ikip', color=1):
    row = bytearray(100)
    row[:8] = b'    0.0v'
    row[16:48] = label.ljust(32, b'\0')
    row[48:72] = struct.pack('>6f', -679, -60, 2639, 0, 0, 0)
    row[72:84] = kind + b'0.0vp00\x04'
    struct.pack_into('>I', row, 84, 2)
    row[88:92] = b'p01\x04'
    struct.pack_into('>I', row, 92, color)
    return bytes(row)


def generator(*rows):
    return b'1.0v' + struct.pack('>4fI', -315, -37, 2022, 75, len(rows)) + b''.join(rows)


def test_removes_only_reserved_fixture_records():
    ordinary = record(b'retail sprout', color=2)
    enemy = record(b'ordinary enemy', kind=b'iket')
    data = generator(ordinary, record(SQUAD_LABEL), enemy, record(SQUAD_LABEL))
    expected = generator(ordinary, enemy)
    assert without_test_squad(data) == expected
    assert without_test_squad(expected) == expected
    assert without_test_squad(b'unrelated format') == b'unrelated format'


def test_txen_record_is_counted_in_rewritten_header():
    # Retail Hope: header counts four-space records plus the inactive `next`
    # record (txen); the harness copy's header had skipped that record.
    retail = [record(b'retail sprout %d' % i) for i in range(3)]
    txen = b'txen' + record(b'next')[4:]
    expected = generator(*retail, txen)
    assert struct.unpack_from('>I', expected, 20)[0] == 4
    dirty = generator(*retail, txen, record(SQUAD_LABEL), record(SQUAD_LABEL))
    assert without_test_squad(dirty) == expected
    miscounted = dirty[:20] + struct.pack('>I', 5) + dirty[24:]
    assert without_test_squad(miscounted) == expected
    with pytest.raises(ValueError):
        without_test_squad(dirty[:20] + struct.pack('>I', 4) + dirty[24:])


@pytest.mark.parametrize('data', [generator(record(SQUAD_LABEL, kind=b'iket')),
                                generator(record(SQUAD_LABEL, color=2)),
                                generator(record(SQUAD_LABEL))[:20] + struct.pack('>I', 2) + record(SQUAD_LABEL)])
def test_malformed_reserved_marker_fails_closed(data):
    with pytest.raises(ValueError):
        without_test_squad(data)


def test_private_campaign_and_cached_replay_preserve_source_and_fixture_mode(tmp_path):
    source = tmp_path / 'retail'
    path = source / HOPE_GENERATOR
    path.parent.mkdir(parents=True)
    ordinary = record(b'retail sprout')
    dirty = generator(ordinary, record(SQUAD_LABEL))
    path.write_bytes(dirty)
    expected = generator(ordinary)
    fresh = tmp_path / 'fresh'
    prepare_private_destination(fresh, source, campaign=True)
    assert (fresh / 'assets' / HOPE_GENERATOR).read_bytes() == expected
    assert path.read_bytes() == dirty
    # Fixture preparation retains its original intentional layout.
    fixture = tmp_path / 'fixture'
    prepare_private_destination(fixture, source)
    assert (fixture / 'assets' / HOPE_GENERATOR).read_bytes() == dirty
    # Model cache replay must apply the same correction to the private stage.
    cache = tmp_path / 'cache'
    (cache / 'tree').mkdir(parents=True)
    marker = cache / 'receipt.json'
    marker.write_text(json.dumps({'schema': 1, 'mode': 'identity-binding', 'files': {}, 'bindings': []}))
    replay = tmp_path / 'replay'
    _replay_from_cache(replay, cache, marker, source)
    assert (replay / 'assets' / HOPE_GENERATOR).read_bytes() == expected
    assert path.read_bytes() == dirty
    # The corrected file is independent, not a writable hardlink to source.
    (fresh / 'assets' / HOPE_GENERATOR).write_bytes(b'private edit')
    assert path.read_bytes() == dirty
