"""Prepare a held-treasure descriptor from unchanged private source manifests.

This is a staging helper, not runtime admission. The native source parsers and
authenticated campaign selection remain authoritative. Nothing is activated or
written here; in particular, no enemy treasure code or generator is rewritten.
"""
import hashlib
import math
import re
import struct

from experimental.pikmin2_treasure_catalog import RETAIL_DIGEST
from .campaign_treasures import bounded_model, verified_entries


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _sha(text):
    return isinstance(text, str) and re.fullmatch('[0-9a-f]{64}', text) is not None


def _uid(key):
    return 0x52000000 | int.from_bytes(hashlib.sha256(key.encode('ascii')).digest()[:3], 'big')


def _original_rows(data, campaign):
    if not 45 <= len(data) <= 4 * 1024 * 1024 or data[:5] != b'P2OC1':
        raise ValueError('Bounded original P2OC1 source manifest required')
    payload = data[:-32]
    if hashlib.sha256(payload).digest() != data[-32:]:
        raise ValueError('Original source checksum mismatch')
    offset = 5

    def take(size):
        nonlocal offset
        if size > len(payload) - offset:
            raise ValueError('Truncated original source manifest')
        result = payload[offset:offset + size]; offset += size
        return result

    def word():
        return struct.unpack('<I', take(4))[0]

    def text(limit):
        size = word()
        if size > limit:
            raise ValueError('Oversized original source string')
        try:
            return take(size).decode('ascii')
        except UnicodeDecodeError as error:
            raise ValueError('Non-ASCII original source identity') from error

    if text(64) != campaign:
        raise ValueError('Original source belongs to another selected campaign')
    count = word()
    if not 1 <= count <= 65536:
        raise ValueError('Invalid original source row count')
    rows = {}
    for _ in range(count):
        course, member, index = text(255), text(2048), word()
        key = f'{course}/{member}#{index}'
        source, uid, birth, number, spawn = (word() for _ in range(5))
        geometry = struct.unpack('<9f', take(36))
        code = word()
        for _ in range(4): word()  # original number-pellet profile
        probability = struct.unpack('<f', take(4))[0]
        text(4)
        tails = word()
        if tails > 4096:
            raise ValueError('Oversized original source tail')
        for _ in range(tails): text(4096)
        word(); word(); word()  # literal reserved/respawn/calendar, unchanged
        if (course != 'tutorial' or uid != _uid(key) or uid in rows or index > 65535
                or source > 65535 or number > 10
                or any(not math.isfinite(value) for value in (*geometry, probability))):
            raise ValueError('Invalid or duplicate original source identity')
        rows[uid] = dict(uid=uid, source=source, code=code, key=key)
    if offset != len(payload):
        raise ValueError('Trailing original source data')
    return rows


def _receiver(data):
    if not 0 < len(data) <= 4 * 1024 * 1024:
        raise ValueError('Bounded original Onyon manifest required')
    try:
        fields = data.decode('ascii').split()
        if len(fields) < 2 or fields[0] != 'P2_ORIGINAL_ONYON_1':
            raise ValueError('Original typed Onyon manifest required')
        count = int(fields[1])
        if not 1 <= count <= 4096 or len(fields) != 2 + count * 19:
            raise ValueError('Invalid original Onyon manifest size')
        ship, uids, keys = None, set(), set()
        for i in range(count):
            row = fields[2 + i * 19:2 + (i + 1) * 19]
            uid, key, sha = int(row[0]), row[1], row[2]
            reserved, respawn, limit, kind, boot = map(int, row[5:10])
            position = tuple(map(float, row[10:19]))
            if (uid != _uid(key) or uid in uids or key in keys or not _sha(sha)
                    or not key.startswith('tutorial/') or row[3:5] != ['0002', '0001']
                    or reserved or respawn or limit < -1 or kind not in (0, 1, 2, 4)
                    or boot not in (0, 1) or any(not math.isfinite(v) for v in position)):
                raise ValueError('Invalid original Onyon source row')
            uids.add(uid); keys.add(key)
            if kind == 4 and key == 'tutorial/defaultgen.txt#0':
                ship = (uid, sha + ':' + key)
        if ship is None:
            raise ValueError('Literal tutorial ship receiver missing')
        return ship
    except (UnicodeError, OverflowError) as error:
        raise ValueError('Invalid original Onyon encoding') from error


def prepare(original, onyons, campaign, requests, catalog, models, pod):
    """Return unchanged source bytes and bound models/descriptor; never activate.

    requests contain uid, source, code and id. All four must match literal source
    and retail catalogue, including the original manager/index treasure code.
    """
    if not _sha(campaign) or not 1 <= len(requests) <= 201:
        raise ValueError('Selected campaign and one to 201 literal drops required')
    rows = _original_rows(original, campaign)
    receiver, receiver_identity = _receiver(onyons)
    entries = verified_entries(catalog)
    model_bytes, seen_uids, descriptor_rows, facts = {}, set(), [], []
    for request in requests:
        uid, source, code, identity = (request[name] for name in ('uid', 'source', 'code', 'id'))
        entry = entries.get(identity)
        row = rows.get(uid)
        if (any(type(v) is not int for v in (uid, source, code)) or not 0 <= source <= 255
                or row is None or entry is None or uid == receiver or uid in seen_uids
                or identity in model_bytes or row['source'] != source or row['code'] != code
                or code != (3 if entry['kind'] == 'otakara' else 4) * 256 + entry['index']):
            raise ValueError('Drop does not match unique literal source and retail identity')
        model_bytes[identity] = bounded_model(models[identity]); seen_uids.add(uid)
        descriptor_rows.append(f'{uid} {source} {code} {identity} {_digest(model_bytes[identity])}')
        facts.append(dict(row, id=identity, **entry, physical_delivery_accepted=False,
                          native_SAVE_resume_accepted=False))
    pod_bytes = bounded_model(pod)
    header = (f'P2_TREASURE_HELD_1 {RETAIL_DIGEST} {_digest(pod_bytes)} {campaign} '
              f'{_digest(original)} {_digest(onyons)} {receiver_identity} {receiver} tutorial {len(requests)}')
    descriptor = ('\n'.join([header, *descriptor_rows]) + '\n').encode('ascii')
    if len(descriptor) > 65536:
        raise ValueError('Oversized held treasure descriptor')
    return dict(original=original, onyons=onyons, models=model_bytes, pod=pod_bytes,
                descriptor=descriptor, source_digest=_digest(descriptor), facts=facts,
                activated=False)
