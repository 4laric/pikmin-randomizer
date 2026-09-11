"""Audit campaign spawn records from user assets; never copy models or raw payloads.

Disk offsets identify records within a hashed source file. Decoded cache keys
are diagnostic only: collisions must not be used to choose a replacement.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import struct

STAGES = ('practice', 'stage1', 'stage2', 'stage3', 'last')
PAIRS = ((3, 31), (4, 32), (18, 19))
VERSION = 'campaign-slots-v1'


class Reader:
    def __init__(self, data, offset=0): self.data, self.offset = data, offset
    def take(self, n):
        if n < 0 or self.offset + n > len(self.data): raise ValueError('truncated generator')
        result = self.data[self.offset:self.offset+n]; self.offset += n
        return result
    def integer(self): return struct.unpack('>i', self.take(4))[0]
    def floats(self, n):
        values = struct.unpack('>' + 'f' * n, self.take(n * 4))
        if not all(math.isfinite(v) for v in values): raise ValueError('non-finite generator coordinate/parameter')
        return list(values)
    def ident(self): return self.take(4)[::-1].decode('ascii')
    def parameters(self):
        values = {}
        while True:
            header = self.take(4)
            if header == b'\xff' * 4: return values
            key, size = header[:3].decode('ascii'), header[3]
            if not size or key in values: raise ValueError('invalid or duplicate parameter')
            values[key] = self.take(size).hex()


def param_int(params, key, default=0):
    return int.from_bytes(bytes.fromhex(params[key]), 'big', signed=True) if key in params else default


def schedules(text):
    text = re.sub(r'//[^\n]*', '', text)
    result = {stage: {} for stage in STAGES}
    for block in text.split('new_map')[1:]:
        file = re.search(r'\bfile\s+stages/(\w+)\.ini', block)
        if not file or file[1] not in result: continue
        for name, first, last, expiry in re.findall(r'\bgenfile\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)', block):
            if name in result[file[1]]: raise ValueError('duplicate scheduled file')
            first, last, expiry = int(first)+1, int(last)+1, int(expiry)+1
            if first > last: raise ValueError('inverted activation window')
            result[file[1]][name] = dict(mode='limited-once', first_day=first, last_activation_day=last, expires_after_day=expiry)
    return result


def schedule_for(name, limited):
    if name in limited: return limited[name]
    if name == 'init.gen': return dict(mode='first-visit', first_day=1, last_activation_day=None, expires_after_day=None)
    if name in ('default.gen', 'plants.gen'): return dict(mode='every-visit', first_day=1, last_activation_day=None, expires_after_day=None)
    if re.fullmatch(r'\d+\.gen', name):
        day = int(name[:-4]) + 1
        return dict(mode='daily-file', first_day=day, last_activation_day=day, expires_after_day=None)
    return dict(mode='inactive-file', first_day=None, last_activation_day=None, expires_after_day=None)


def records(data, stage, file):
    if data[:4] not in (b'0.0v', b'1.0v'): raise ValueError('unsupported generator file version')
    found = []
    for match in re.finditer(b'iket|ssob', data):
        pos = match.start(); start = pos - 72
        if start < 20 or data[start+4:start+8] != b'0.0v': raise ValueError(f'invalid enemy record framing at {file}:{pos}')
        r = Reader(data, start)
        name = r.take(4).hex(); r.take(8)  # version and unused editor word
        flags = r.integer(); r.take(32)  # memo contains editor garbage; not identity
        position, offset = r.floats(3), r.floats(3)
        kind = r.ident(); version = int.from_bytes(r.take(4), 'little')
        if kind == 'teki':
            if version != 10: raise ValueError('unsupported Teki personality version')
            species = r.take(1)[0]
            pellet_kind, pellet_color = struct.unpack('bb', r.take(2))
            pellet_id = r.ident()
            ints = [r.integer() for _ in range(5)]; floats = r.floats(5)
            payload = dict(pellet_kind=pellet_kind, pellet_color=pellet_color, pellet_id=pellet_id,
                           pellet_min=ints[0], pellet_max=ints[1], nectar_min=ints[2], nectar_max=ints[3],
                           parameter0=ints[4], size=floats[0], strength=floats[1], territory=floats[2],
                           pellet_chance=floats[3], nectar_chance=floats[4])
        else:
            if version != 2: raise ValueError(f'unsupported boss version {version}')
            word = r.integer() & 0xffffffff
            species = word & 15
            payload = dict(item_index=(word >> 4) & 3, item_color=(word >> 6) & 3,
                           item_count=(word >> 8) & 15, pellet_index=(word >> 12)-1)
        object_params = r.parameters()
        area = r.ident(); area_version = r.ident(); area_offset = r.floats(3); area_params = r.parameters()
        spawn_type = r.ident(); type_version = r.ident(); type_params = r.parameters()
        if area_version != 'v0.0' or type_version != 'v0.0': raise ValueError('unsupported area/type version')
        if area not in ('pint', 'circ', 'rect') or spawn_type not in ('1one', 'aton', 'irnd'): raise ValueError('unsupported area/type')
        count_max = 1 if spawn_type == '1one' else param_int(type_params, 'p01' if spawn_type == 'irnd' else 'p00', 1)
        count_min = param_int(type_params, 'p00', 1) if spawn_type == 'irnd' else count_max
        reasons = []
        if kind == 'boss': reasons.append('boss-manager encounter or non-enemy; adapter required')
        elif payload['pellet_id'] != 'none': reasons.append('named drop')
        if kind == 'teki' and payload['parameter0'] != 0: reasons.append('special personality parameter')
        pair = next((pair for pair in PAIRS if species in pair), None) if kind == 'teki' else None
        if not pair: reasons.append('outside currently exercised family pairs')
        if count_min != 1 or count_max != 1: reasons.append('group/count adapter required')
        if area != 'pint': reasons.append('distributed spawn area requires footprint audit')
        found.append(dict(id=f'{stage}/{file}@{start}', stage=stage, file=file, offset=start, end=r.offset,
                          kind=kind, species=species, generator_name=name, carry_flags=flags,
                          position=position, offset_position=offset,
                          cache_position=[int(int(p)+o) for p,o in zip(position,offset)],
                          personality=payload, object_parameters=object_params, area=area, area_offset=area_offset,
                          area_parameters=area_params, spawn_type=spawn_type, count_min=count_min, count_max=count_max,
                          respawn_days=param_int(type_params, 'b00'), face_adjust=param_int(type_params, 'b01'),
                          type_parameters=type_params, candidate_family=list(pair) if pair else [], exclusions=reasons))
    for previous, current in zip(found, found[1:]):
        if current['offset'] < previous['end']: raise ValueError('overlapping records')
    return found


def audit(assets):
    base = assets / 'dataDir/stages'
    limits = schedules((base / 'stages.ini').read_text(encoding='shift_jis'))
    files, slots = [], []
    for stage, folder in enumerate(STAGES):
        for path in sorted((base / folder).glob('*.gen')):
            if not re.fullmatch(r'(default|init|plants|\d+(?:-\d+)?)\.gen', path.name): continue
            data = path.read_bytes(); schedule = schedule_for(path.name, limits[folder])
            rows = records(data, stage, path.name)
            files.append(dict(stage=stage, file=path.name, sha256=hashlib.sha256(data).hexdigest(), schedule=schedule, slots=len(rows)))
            for row in rows:
                row['schedule'] = schedule
                first, last = schedule['first_day'], schedule['last_activation_day']
                row['activation_days'] = [d for d in range(2, 30) if first is not None and d >= first and (last is None or d <= last)]
                if not row['activation_days']: row['exclusions'].append('not activated under repeat-day29 campaign')
                row['terrain_audit'] = 'unknown; native anchor samples do not prove clearance or delivery route'
            slots.extend(rows)
    keys = defaultdict(list)
    for row in slots:
        if row['activation_days']:
            keys[(row['stage'], row['kind'], row['species'], *row['cache_position'])].append(row['id'])
    collisions = [ids for ids in keys.values() if len(ids) > 1]
    facts = dict(version=VERSION, files=files, slots=slots, cache_key_collisions=collisions)
    facts['sha256'] = hashlib.sha256(json.dumps(facts, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return facts


def main():
    p=argparse.ArgumentParser();p.add_argument('assets',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--check',action='store_true');args=p.parse_args()
    facts=audit(args.assets)
    if args.check:
        if json.loads(args.output.read_text(encoding='utf-8')) != facts: raise ValueError('spawn catalog differs from assets')
    else:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8')
    print(len(facts['files']),'files;',len(facts['slots']),'enemy/boss-manager records;',len(facts['cache_key_collisions']),'ambiguous cache keys')
    print('Potential point/single family candidates:',sum(not s['exclusions'] for s in facts['slots']))
    print('Kinds:',dict(Counter(s['kind'] for s in facts['slots'])))
    print('Catalog',facts['sha256'])

if __name__=='__main__':main()
