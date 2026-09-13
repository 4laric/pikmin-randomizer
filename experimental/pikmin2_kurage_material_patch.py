"""Explicit Jellyfloat first-TEV-stage preservation; envmap stage remains omitted."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from experimental.pikmin2_convert import blocks, u16, u32
from experimental.pikmin2_qurione_material_audit import entry

SOURCES = {
    '1a35df81d829a9409804307a7eb8011905cbdfb73985585869cc1b79af4b734b': 'Kurage',
    '169ad044cc18a8db7cf679b7908b9b4dea3ba95ede80b0530959b33311b7ba8f': 'OniKurage',
}
COLOR = [15, 9, 2, 10, 0, 0, 0, 1, 0]
ALPHA = [7, 5, 4, 1, 0, 0, 0, 1, 0]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def descriptor(model):
    if sha(model) not in SOURCES:
        raise ValueError('Unrecognized Jellyfloat source model')
    b = blocks(model); m = b['MAT3']; h = b['INF1']
    mapping = {}; material = None; at = u32(h, 20)
    while True:
        kind, index = struct.unpack_from('>HH', h, at); at += 4
        if kind == 0: break
        if kind == 0x11: material = index
        if kind == 0x12:
            if index in mapping or material is None: raise ValueError('Ambiguous shape mapping')
            mapping[index] = material
    if mapping != {0: 0, 1: 1} or u16(m, 8) != 2:
        raise ValueError('Unexpected Jellyfloat layout')
    rows = []
    for i in range(2):
        r = u32(m, 12) + u16(m, u32(m, 16) + 2*i)*332
        stage = entry(m, 92, u16(m, r+228), 20)
        order = entry(m, 76, u16(m, r+188), 4)
        if list(stage[1:10]) != COLOR or list(stage[10:19]) != ALPHA or list(order[:3]) != [0,0,4]:
            raise ValueError('Unsupported source stage')
        regs = [list(struct.unpack('>4h', entry(m, 80, u16(m, r+220+2*k), 8))) for k in range(3)]
        rows.append(dict(registers=regs, color=COLOR[:], alpha=ALPHA[:]))
    return rows


def patch(mod, rows):
    if len(rows) != 2: raise ValueError('Expected two source materials')
    result = bytearray(mod); at = 0; found = []; changed = set()
    while at+8 <= len(mod):
        tag, size = struct.unpack_from('>II', mod, at); end = at+8+size
        if end > len(mod): raise ValueError('Truncated MOD')
        if tag == 48: found.append((at, end))
        at = end
    if at != len(mod) or len(found) != 1: raise ValueError('Invalid MOD layout')
    start, end = found[0]
    if u32(mod,start+8) != 2 or u32(mod,start+12) != 2: raise ValueError('Unexpected material counts')
    pos = (start+16+31)//32*32
    for row in rows:
        if pos+124 > end or u32(mod,pos+88) != 1: raise ValueError('Expected single-stage exporter layout')
        if mod[pos+92:pos+124] != bytes([0,0,0,4,0,0,0,0,15,8,10,15,0,0,0,1,0,0,0,0,7,4,5,7,0,0,0,1,0,0,0,0]):
            raise ValueError('Not original diffuse exporter material')
        if row['color'] != COLOR or row['alpha'] != ALPHA or len(row['registers']) != 3:
            raise ValueError('Unsupported descriptor')
        edits = [(pos+24*k, struct.pack('>4h', *reg)) for k,reg in enumerate(row['registers'])]
        edits += [(pos+100,bytes(row['color'])), (pos+112,bytes(row['alpha']))]
        for offset,data in edits:
            result[offset:offset+len(data)] = data; changed.update(range(offset,offset+len(data)))
        pos += 124
    if len(result) != len(mod) or any(a != b and i not in changed for i,(a,b) in enumerate(zip(mod,result))):
        raise AssertionError('Nonmaterial mutation')
    return bytes(result)


def prepare(model, mod, output):
    source = Path(model).read_bytes(); before = Path(mod).read_bytes()
    rows = descriptor(source); after = patch(before, rows)
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    (output/'patched.mod').write_bytes(after)
    report = dict(species=SOURCES[sha(source)], source_sha256=sha(source), before=sha(before), after=sha(after),
                  changed_bytes=sum(a!=b for a,b in zip(before,after)), materials=rows,
                  preserved='Geometry, textures and pixel state unchanged; source first TEV stage and registers restored',
                  omitted='Second NORMAL/environment TEV stage, its texture matrix and source lighting fidelity')
    (output/'patch.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('model','mod','output'): p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args(); print(json.dumps(prepare(a.model,a.mod,a.output),indent=2))
