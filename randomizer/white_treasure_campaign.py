"""Explicit original-diamond assets for ordinary White campaign staging.

Original P1 records/parameters remain unchanged. Native WhiteTreasure owns the
one source cargo's rendering, 15..25 physical carrying and completed Pod receipt.
Engineering placement still requires native terrain/route/SAVE acceptance.
"""
import hashlib
import math
import struct
from pathlib import Path
from .purple_campaign import split_records

PROFILE = ['P2_POD_1', 'dia_a_red', '180', '15', '25', 'Kochappy', '2']

def bank_files(bank):
    bank = Path(bank)
    result = {}
    for name, bound in [('p2-pod.txt', 512), ('treasure.mod', 32 * 1024 * 1024), ('pod.mod', 32 * 1024 * 1024)]:
        path = bank / name
        if not path.is_file() or not 0 < path.stat().st_size <= bound:
            raise ValueError('Missing/empty/oversized original diamond bank file: ' + name)
        value = path.read_bytes()
        if not 0 < len(value) <= bound:
            raise ValueError('Changed original diamond bank file: ' + name)
        result[name] = value
    if result['p2-pod.txt'].decode('ascii').split() != PROFILE:
        raise ValueError('Original dia_a_red value180/minimum15/maximum25 descriptor required')
    return result

def receiver_row(rows):
    matches = []
    for row in rows:
        if row[:8] != b'    0.0v' or len(row) < 92 or row[72:80] != b'meti1.0v':
            continue
        length = struct.unpack_from('>I', row, 80)[0]
        if length != 4 or row[84:88] != b'goal':
            continue
        end = row.find(b'tnip0.0v', 88)
        if end < 0:
            raise ValueError('Unsupported native item birth framing')
        fields = [i for i in range(88, end - 7) if row[i:i+4] == b'p00\x04']
        if len(fields) != 1:
            raise ValueError('Unsupported native Onion colour framing')
        if struct.unpack_from('>I', row, fields[0] + 4)[0] == 1:
            matches.append(row)
    if len(matches) != 1 or not struct.unpack_from('<I', matches[0], 8)[0]:
        raise ValueError('One active original Red receiver with a native generator identity required')
    return matches[0]

def append_cargo(data, template, stage):
    if type(stage) is not int or not 0 <= stage <= 4:
        raise ValueError('Invalid diamond stage')
    rows = split_records(data)
    receiver = receiver_row(rows)
    uid = 0x57545200 + stage
    if any(struct.unpack_from('<I', row, 8)[0] == uid for row in rows):
        raise ValueError('Reserved diamond identity already exists')
    if len(template) < 84 or template[72:76] != b'tlep':
        raise ValueError('Original native physical Pellet generator template required')
    x, y, z = struct.unpack_from('>3f', data, 4)
    if not all(math.isfinite(v) for v in (x, y, z)):
        raise ValueError('Finite source landing origin required')
    row = bytearray(template)
    row[:8] = b'    0.0v'
    struct.pack_into('<I', row, 8, uid)
    row[16:48] = b'campaign P2 dia_a_red'.ljust(32, b'\0')
    # Separate cargo from all three Ivory capture areas and idle initial Reds.
    struct.pack_into('>6f', row, 48, x - 225, y, z + 250, 0, 0, 0)
    row[80:84] = b'50rp'  # Existing native physical host; retail provider replaces its profile/render.
    result = data[:20] + struct.pack('>I', len(rows) + 1) + data[24:] + bytes(row)
    assert result[24:24 + len(data) - 24] == data[24:]
    return result, uid, struct.unpack_from('<I', receiver, 8)[0]

def sidecars(files, stage, cargo, receiver):
    hashes = [hashlib.sha256(files[n]).hexdigest() for n in ('p2-pod.txt', 'treasure.mod', 'pod.mod')]
    return {'p2-pod.txt': files['p2-pod.txt'], 'p2-white-treasure-campaign.txt':
            ('P2_WHITE_TREASURE_CAMPAIGN_1 ' + ' '.join(map(str, (stage, cargo, receiver))) + ' ' + ' '.join(hashes) + '\n').encode('ascii')}
