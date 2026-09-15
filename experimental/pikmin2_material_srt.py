"""Bounded BTK/TTK1 texture SRT import. No actor/material binding is inferred."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct


def decode(data):
    def fail():
        raise ValueError('Unsupported or malformed BTK/TTK1')
    if len(data) < 128 or len(data) > 16*1024*1024 or data[:8] != b'J3D1btk1': fail()
    if struct.unpack_from('>II', data, 8) != (len(data), 1): fail()
    size = struct.unpack_from('>I', data, 36)[0]
    if data[32:36] != b'TTK1' or size < 96 or 32+size > len(data) or len(data)-32-size > 31: fail()
    block = data[32:32+size]
    def unpack(fmt, offset):
        if offset < 0 or offset+struct.calcsize(fmt) > len(block): fail()
        return struct.unpack_from(fmt, block, offset)
    attr, shift, duration, tracks, scales, rotations, translations = unpack('>BBh4H', 8)
    if attr not in (0, 2) or shift > 15 or not 1 <= duration <= 32767 or tracks % 3 or not 1 <= tracks//3 <= 128: fail()
    if any(unpack('>4H',52)) or any(unpack('>8I',60)) or unpack('>I',92)[0] != 0: fail()
    table, remap, names, slots, centers, scale, rotation, translation = unpack('>8I',20)
    count = tracks//3
    def region(offset, n):
        if offset < 96 or offset+n > len(block): fail()
        return block[offset:offset+n]
    region(table, tracks*18); region(remap,count*2); region(slots,count); region(centers,count*12)
    region(names,4+count*4)
    if unpack('>H',names)[0] != count: fail()
    values=[]
    for offset, n, code in ((scale,scales,'f'),(rotation,rotations,'h'),(translation,translations,'f')):
        region(offset,n*struct.calcsize('>'+code))
        array=list(unpack('>'+str(n)+code,offset))
        if any(not math.isfinite(v) or abs(v)>1e6 for v in array): fail()
        values.append(array)
    def curve(axis, kind):
        n, offset, tangent = unpack('>3H',table+axis*18+kind*6)
        if n>4096 or tangent not in (0,1): fail()
        array=values[kind]
        if n == 0: return [[0.0,1.0 if kind==0 else 0.0,0.0,0.0]]
        if n == 1:
            if offset>=len(array): fail()
            return [[0.0,float(array[offset]),0.0,0.0]]
        width=3+tangent
        if offset+n*width>len(array): fail()
        result=[]
        for i in range(n):
            row=array[offset+i*width:offset+(i+1)*width]
            t,v,ti=row[:3];to=row[3] if tangent else ti
            if t<0 or t>duration or (result and t<=result[-1][0]): fail()
            result.append(list(map(float,(t,v,ti,to))))
        return result
    result=[]; identities=set(); total_keys=0
    for i in range(count):
        offset=unpack('>H',names+6+i*4)[0]
        if offset<4+count*4 or names+offset>=len(block): fail()
        end=block.find(b'\0',names+offset)
        if end<0: fail()
        try: name=block[names+offset:end].decode('ascii')
        except UnicodeDecodeError: fail()
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',name): fail()
        slot=block[slots+i]
        if slot>9 or (name,slot) in identities: fail()
        identities.add((name,slot))
        center=list(unpack('>3f',centers+12*i))
        if any(not math.isfinite(v) or abs(v)>1e6 for v in center): fail()
        # Validate even axes J3D ignores; active order is scale X/Y, rotation Z, translation X/Y.
        axes=[[curve(i*3+axis,kind) for kind in range(3)] for axis in range(3)]
        active=[axes[0][0],axes[1][0],axes[2][1],axes[0][2],axes[1][2]]
        total_keys += sum(map(len,active))
        if total_keys > 65536: fail()
        result.append(dict(material=name,slot=slot,center=center,curves=active))
    return dict(schema=1,policy='P2_MATERIAL_SRT_1',source_sha256=hashlib.sha256(data).hexdigest(),duration=duration,attribute=attr,rotation_shift=shift,tracks=result)


def bank_text(report):
    lines=[report['policy'],report['source_sha256'],f"{report['duration']} {report['attribute']} {report['rotation_shift']} {len(report['tracks'])}"]
    for track in report['tracks']:
        lines.append(f"{track['material']} {track['slot']} "+' '.join(format(v,'.9g') for v in track['center']))
        for curve in track['curves']:
            lines.append(str(len(curve)))
            lines.extend(' '.join(format(v,'.9g') for v in key) for key in curve)
    return '\n'.join(lines)+'\n'


def export(source, output):
    report=decode(Path(source).read_bytes())
    output=Path(output)
    if output.exists(): raise ValueError('Output must be fresh')
    output.mkdir(parents=True)
    (output/'material-srt.txt').write_text(bank_text(report),encoding='ascii')
    (output/'material-srt.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();r=export(args.source,args.output);print(json.dumps(dict(tracks=len(r['tracks']),source_sha256=r['source_sha256'])))
