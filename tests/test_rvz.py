"""RVZ container decoding with a synthetic uncompressed image (no zstd needed) and the junk generator."""
import importlib.util
import struct
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rvz", ROOT / "launcher" / "rvz.py")
rvz = importlib.util.module_from_spec(spec)
sys.modules["rvz"] = rvz
spec.loader.exec_module(rvz)

SEED = bytes(range(1, 69))


def test_generator_is_deterministic_and_forward_matches_stream():
    a, b = rvz.LaggedFibonacci(), rvz.LaggedFibonacci()
    a.set_seed(SEED)
    b.set_seed(SEED)
    stream = a.get_bytes(5000)
    b.forward(2100)  # Skip across a block boundary, then continue in lockstep.
    assert b.get_bytes(2900) == stream[2100:]
    assert len(set(stream)) > 100  # Looks like padding noise, not a constant.
    c = rvz.LaggedFibonacci()
    c.set_seed(bytes(68))
    assert c.get_bytes(64) != stream[:64]


def test_unpack_mixes_literal_and_junk_runs():
    lfg = rvz.LaggedFibonacci()
    lfg.set_seed(SEED)
    lfg.forward(0x1234 % rvz.SECTOR)
    junk = lfg.get_bytes(300)
    literal = bytes(range(256)) * 2
    packed = struct.pack(">I", len(literal)) + literal + struct.pack(">I", 0x80000000 | 300) + SEED
    assert rvz.unpack_rvz(packed, 0x1234 - len(literal)) == literal + junk


def synthetic_rvz(path, chunk_size, disc):
    """Uncompressed RVZ: one raw-data entry covering the disc, one group per chunk, last group packed."""
    groups_data = []
    n_groups = (len(disc) + chunk_size - 1) // chunk_size
    body = bytearray()
    table_pos = 0x48 + 0xDC
    raw_entry = struct.pack(">QQII", 0x80, len(disc) - 0x80, 0, n_groups)
    group_table_size = n_groups * 12
    data_start = table_pos + len(raw_entry) + group_table_size
    data_start += (-data_start) % 4
    cursor = data_start
    entries = []
    for i in range(n_groups):
        chunk = disc[i * chunk_size:(i + 1) * chunk_size]
        if i == n_groups - 1:
            # Pack the final chunk as one literal run so the packed path is exercised without junk.
            payload = struct.pack(">I", len(chunk)) + chunk
            entries.append(struct.pack(">III", cursor // 4, len(payload), len(payload)))
        elif not any(chunk):
            payload = b""
            entries.append(struct.pack(">III", cursor // 4, 0, 0))
        else:
            payload = chunk
            entries.append(struct.pack(">III", cursor // 4, len(payload), 0))
        groups_data.append(payload)
        cursor += len(payload) + (-len(payload)) % 4
    disc_struct = bytearray(0xDC)
    struct.pack_into(">IIII", disc_struct, 0, 1, 0, 0, chunk_size)
    disc_struct[0x10:0x90] = disc[:0x80]
    struct.pack_into(">IIQ", disc_struct, 0x90, 0, 0, 0)
    struct.pack_into(">IQIIQI", disc_struct, 0xB4, 1, table_pos, len(raw_entry), n_groups, table_pos + len(raw_entry), group_table_size)
    head = bytearray(0x48)
    head[:4] = b"RVZ\x01"
    struct.pack_into(">III", head, 4, 0x01000000, 0x00030000, len(disc_struct))
    struct.pack_into(">QQ", head, 0x24, len(disc), cursor)
    out = bytearray(head + disc_struct + raw_entry + b"".join(entries))
    out += bytes(data_start - len(out))
    for payload in groups_data:
        out += payload + bytes((-len(payload)) % 4)
    path.write_bytes(out)


def test_convert_synthetic_image_roundtrip(tmp_path):
    chunk = 0x8000
    disc = bytearray(chunk * 3 + 1000)
    disc[:6] = b"GPIE01"
    disc[7] = 1
    for i in range(0x80, chunk):
        disc[i] = i & 0xFF
    # Second chunk stays all zero (group data_size 0); third and fourth carry patterns.
    for i in range(chunk * 2, len(disc)):
        disc[i] = (i * 7) & 0xFF
    image = tmp_path / "game.rvz"
    synthetic_rvz(image, chunk, bytes(disc))
    info = rvz.describe(image)
    assert info == dict(game_id="GPIE01", revision=1, iso_size=len(disc), compression="none", chunk_size=chunk, groups=4)
    progress = []
    out = rvz.convert_to_iso(image, tmp_path / "game.iso", lambda done, total: progress.append((done, total)))
    assert out.read_bytes() == bytes(disc)
    assert progress[-1] == (len(disc), len(disc)) and not (tmp_path / "game.iso.partial").exists()
    with pytest.raises(rvz.RvzError):
        rvz.describe(tmp_path / "game.iso")
