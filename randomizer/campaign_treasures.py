"""Source-bound physical treasure staging, with explicit engineering positions.

These helpers build private data only. They do not activate a campaign, grant
receipts or authenticate a card. The runner/card owner must bind the resulting
descriptor digest before launch. Original retail placement/terrain acceptance
is separate from this deliberately labelled native-host staging.
"""
import hashlib
import math
import struct
from pathlib import Path

from experimental.pikmin2_treasure_catalog import RETAIL_DIGEST, verify_native_catalog
from .purple_campaign import split_records
from .white_treasure_campaign import receiver_row


def verified_entries(catalog):
    data = verify_native_catalog(catalog).read_text(encoding='ascii').splitlines()
    entries = {}
    for line in data[1:]:
        fields = line.split()
        entries[fields[0]] = dict(kind=fields[1], index=int(fields[3]), dictionary=int(fields[4]), value=int(fields[5]),
                                  minimum=int(fields[6]), maximum=int(fields[7]))
    return entries


def bounded_model(path):
    path = Path(path)
    if not path.is_file() or not 0 < path.stat().st_size <= 32 * 1024 * 1024:
        raise ValueError('Missing, empty or oversized private converted model')
    data = path.read_bytes()
    if not 0 < len(data) <= 32 * 1024 * 1024:
        raise ValueError('Private converted model changed during staging')
    return data


def prepare(stages, template, requests, catalog, models, pod, *, white_owned=False):
    """Return generator overrides/models/descriptor/facts without writing assets.

    requests: dictionaries with stage, id and explicit finite (x,y,z) position.
    models: id -> private converted original model path. stages: stage -> bytes.
    The caller must also refuse reserved UID collisions in scheduled .gen files.
    """
    entries = verified_entries(catalog)
    if not 1 <= len(requests) <= 201:
        raise ValueError('One to 201 explicit treasure placements required')
    if len(template) < 84 or template[72:76] != b'tlep':
        raise ValueError('Native physical Pellet template required')
    prepared = dict(stages)
    ids, placed, model_bytes = set(), [], {}
    for request in requests:
        stage, identity, position = request['stage'], request['id'], request['position']
        if type(stage) is not int or not 0 <= stage <= 4 or stage not in prepared:
            raise ValueError('Explicit supported source stage required')
        if identity not in entries or identity in ids or (white_owned and identity == 'dia_a_red'):
            raise ValueError('Unknown, duplicate or White-owned treasure identity')
        if len(position) != 3 or any(type(v) not in (float, int) or not math.isfinite(v) for v in position):
            raise ValueError('Explicit finite engineering position required')
        data = prepared[stage]
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('Oversized stage generator')
        rows = split_records(data)
        receiver = struct.unpack_from('<I', receiver_row(rows), 8)[0]
        uid = 0x54520000 + entries[identity]['dictionary']
        if uid == receiver or any(struct.unpack_from('<I', row, 8)[0] == uid for row in rows):
            raise ValueError('Reserved treasure generator identity already exists')
        row = bytearray(template)
        row[:8] = b'    0.0v'; struct.pack_into('<I', row, 8, uid)
        row[16:48] = ('P2 treasure ' + identity).encode('ascii')[:31].ljust(32, b'\0')
        try:
            struct.pack_into('>6f', row, 48, *position, 0, 0, 0)
        except (OverflowError, struct.error) as error:
            raise ValueError('Position outside native float range') from error
        row[80:84] = b'50rp'
        prepared[stage] = data[:20] + struct.pack('>I', len(rows) + 1) + data[24:] + bytes(row)
        if len(prepared[stage]) > 4 * 1024 * 1024:
            raise ValueError('Oversized staged generator')
        assert prepared[stage][24:24 + len(data) - 24] == data[24:]
        model_bytes[identity] = bounded_model(models[identity]); ids.add(identity)
        placed.append((stage, uid, receiver, identity))
    pod_bytes = bounded_model(pod)
    digest = lambda data: hashlib.sha256(data).hexdigest()
    lines = [f'P2_TREASURE_PLACEMENTS_1 {RETAIL_DIGEST} {digest(pod_bytes)} {len(placed)}']
    facts = []
    for stage, uid, receiver, identity in placed:
        lines.append(f'{stage} {uid} {receiver} {identity} {digest(model_bytes[identity])} {digest(prepared[stage])}')
        facts.append(dict(stage=stage, id=identity, cargo_uid=uid, receiver_uid=receiver,
                          **entries[identity], placement='explicit engineering position',
                          physical_delivery_accepted=False, native_SAVE_resume_accepted=False))
    descriptor = ('\n'.join(lines) + '\n').encode('ascii')
    if len(descriptor) > 65536:
        raise ValueError('Oversized placement descriptor')
    return dict(stages=prepared, models=model_bytes, pod=pod_bytes, descriptor=descriptor,
                source_digest=digest(descriptor), facts=facts, activated=False)
