"""Lane-21 Groink carcass transport stage helper tests (#198).

Guards the two staged inputs the natural carcass -> Pod receipt needs: the
`transport` sidecar token (so the native tail owns the carry) and the starting
squad expansion to 40 reds (the area-landing attack thins a 20-red squad before
the haul completes). No lane-specific paths or host assets are required.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experimental.pikmin2_groink_transport_run import SIDECAR, expand_squad  # noqa: E402


def _record(name, generator, model=b'p00\x04'):
    row = bytearray(b'    0.0v' + bytes(92))
    struct.pack_into('<I', row, 8, generator)
    row[16:48] = name.encode('ascii').ljust(32, b'\0')
    row[80:84] = model
    struct.pack_into('>6f', row, 48, 0.0, 30.0, 0.0, 0.0, 0.0, 0.0)
    return bytes(row)


def _write_gen(path, records):
    header = b'1.0v' + struct.pack('>4fI', 0.0, 0.0, 0.0, 0.0, len(records))
    path.write_bytes(header + b''.join(records))


def test_sidecar_token_requests_transport():
    assert SIDECAR.startswith('P2_GROINK_TEKI_1\n1\n')
    tokens = SIDECAR.split()
    assert tokens[-1] == 'transport'
    assert tokens[0] == 'P2_GROINK_TEKI_1'


def test_expand_squad_reaches_count_and_is_idempotent(tmp_path):
    gen = tmp_path / 'default.gen'
    _write_gen(gen, [_record('fixture starting squad', 100 + i) for i in range(2)])
    assert expand_squad(gen, 40) == 38
    # Existing 2 + added 38; a second pass adds nothing.
    assert expand_squad(gen, 40) == 0
    from scripts.preview_pikmin2_room import records
    entries = records(gen)
    assert len(entries) == 40
    assert all(e[16:48].startswith(b'fixture starting squad') for e in entries)
    assert len({struct.unpack_from('<I', e, 8)[0] for e in entries}) == 40


def test_expand_squad_zero_when_already_large(tmp_path):
    gen = tmp_path / 'default.gen'
    _write_gen(gen, [_record('fixture starting squad', 200 + i) for i in range(40)])
    assert expand_squad(gen, 40) == 0
