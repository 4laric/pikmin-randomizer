"""Compatibility audit for rigid-baked MOD pose pairs; never changes source banks."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

MAX_BYTES=16*1024*1024
MAX_VECTORS=65536


def decode(raw):
    if not raw or len(raw)>MAX_BYTES:raise ValueError('MOD byte budget exceeded')
    chunks={};at=0;order=[]
    while at<len(raw):
        if at%32 or at+8>len(raw):raise ValueError('Invalid chunk boundary')
        tag,size=struct.unpack_from('>II',raw,at);end=at+8+size
        if tag in chunks or end>len(raw) or end%32:raise ValueError('Invalid chunk size/identity')
        chunks[tag]=raw[at:end];order.append(tag);at=end
        if tag==65535 and at!=len(raw):raise ValueError('Trailing MOD data')
    if not order or order[-1]!=65535 or not {16,17,32,34,48,64,80,96}.issubset(chunks):
        raise ValueError('Missing required MOD chunks')
    arrays={}
    for tag in (16,17):
        data=chunks[tag]
        if len(data)<32:raise ValueError('Short vector chunk')
        count=struct.unpack_from('>I',data,8)[0]
        if not 1<=count<=MAX_VECTORS or len(data)!=((32+12*count+31)//32)*32:
            raise ValueError('Invalid vector count/budget')
        values=list(struct.iter_unpack('>3f',data[32:32+12*count]))
        if any(not math.isfinite(x) or abs(x)>1000000 for v in values for x in v):raise ValueError('Invalid vector')
        if tag==17 and any(sum(x*x for x in v)<1e-24 for v in values):raise ValueError('Zero normal')
        if any(data[12:32]) or any(data[32+12*count:]):raise ValueError('Nonzero vector padding')
        arrays[tag]=values
    mapping=chunks[64]
    if len(mapping)!=64 or struct.unpack_from('>I',mapping,8)[0]!=1 or any(mapping[12:]):
        raise ValueError('Expected direct baked joint-zero mapping')
    joint=chunks[96]
    if len(joint)<108 or struct.unpack_from('>I',joint,8)[0]!=1 or struct.unpack_from('>iI',joint,32)!=(-1,0):
        raise ValueError('Expected one baked root joint')
    if struct.unpack_from('>9f',joint,68)!=(1.,1.,1.,0.,0.,0.,0.,0.,0.):raise ValueError('Unbaked root transform')
    bounds=struct.unpack_from('>7f',joint,40)
    if any(not math.isfinite(v) for v in bounds):raise ValueError('Invalid bounds')
    if any(bounds[k]>bounds[k+3] for k in range(3)):raise ValueError('Inverted bounds')
    for v in arrays[16]:
        if any(v[k]<bounds[k]-1e-3 or v[k]>bounds[k+3]+1e-3 for k in range(3)):raise ValueError('Bounds exclude vertices')
    return chunks,order,arrays


def audit(a,b):
    ca,oa,va=decode(a);cb,ob,vb=decode(b)
    if oa!=ob:raise ValueError('Chunk layout differs')
    for tag in oa:
        if tag in (16,17):
            if len(va[tag])!=len(vb[tag]):raise ValueError('Vector counts differ')
        elif tag==96:
            # Only pose bounds/radius may differ. Joint transform/order must match.
            if ca[tag][:40]+ca[tag][68:]!=cb[tag][:40]+cb[tag][68:]:raise ValueError('Joint topology differs')
        elif ca[tag]!=cb[tag]:raise ValueError(f'Topology/resources differ: chunk {tag}')
    return dict(compatible=True,positions=len(va[16]),normals=len(va[17]),
                max_position_delta=max(math.dist(x,y) for x,y in zip(va[16],vb[16])),
                source_sha256=[hashlib.sha256(x).hexdigest() for x in (a,b)],
                limits='Identical indexing is necessary, not proof of semantic correspondence; pair poses from the same source bank.'),va,vb


def probe_text(va,vb):
    lines=[f'{len(va[16])} {len(va[17])}']
    for pose in (va,vb):
        for tag in (16,17):lines.extend(' '.join(format(x,'.9g') for x in v) for v in pose[tag])
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left',type=Path);parser.add_argument('right',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report,a,b=audit(args.left.read_bytes(),args.right.read_bytes())
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.output/'probe.txt').write_text(probe_text(a,b))
    print(json.dumps(report,indent=2))
