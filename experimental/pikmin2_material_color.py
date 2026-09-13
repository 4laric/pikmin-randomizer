"""Bounded BRK/TRK1 color animation import; source names are not host indices."""
import hashlib
import json
from pathlib import Path
import re
import struct

def decode(data):
    def fail():raise ValueError('Unsupported or malformed BRK/TRK1')
    if len(data)<120 or len(data)>4*1024*1024 or data[:8]!=b'J3D1brk1' or struct.unpack_from('>II',data,8)!=(len(data),1):fail()
    size=struct.unpack_from('>I',data,36)[0]
    if data[32:36]!=b'TRK1' or size<88 or 32+size>len(data) or len(data)-32-size>31:fail()
    block=data[32:32+size]
    def unpack(fmt,at):
        if at<0 or at+struct.calcsize(fmt)>len(block):fail()
        return struct.unpack_from(fmt,block,at)
    attr,_,duration,nc,nk,*counts=unpack('>BBh10H',8)
    if attr not in (0,2) or not 1<=duration<=32767 or not 1<=nc+nk<=128:fail()
    offsets=unpack('>14I',32)
    def region(at,n):
        if at<88 or at+n>len(block):fail()
    tracks=[];identities=set();total=0
    for kind,count in enumerate((nc,nk)):
        if not count:continue
        table,remap,names=offsets[kind],offsets[2+kind],offsets[4+kind]
        region(table,count*28);region(remap,count*2);region(names,4+4*count)
        if unpack('>H',names)[0]!=count:fail()
        arrays=[]
        for channel in range(4):
            n=counts[kind*4+channel];at=offsets[6+kind*4+channel]
            if n:region(at,n*2)
            arrays.append(list(unpack('>'+str(n)+'h',at)) if n else [])
        for i in range(count):
            relative=unpack('>H',names+6+i*4)[0]
            if relative<4+4*count or names+relative>=len(block):fail()
            end=block.find(b'\0',names+relative)
            if end<0:fail()
            try:name=block[names+relative:end].decode('ascii')
            except UnicodeDecodeError:fail()
            register=block[table+i*28+24]
            if not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',name) or register>(3 if kind else 2) or (name,kind,register) in identities:fail()
            identities.add((name,kind,register));curves=[]
            for channel in range(4):
                n,start,tangent=unpack('>3H',table+i*28+channel*6);array=arrays[channel]
                if n>4096 or tangent not in (0,1):fail()
                if n==0:curve=[[0,0,0,0]]
                elif n==1:
                    if start>=len(array):fail()
                    curve=[[0,array[start],0,0]]
                else:
                    width=3+tangent
                    if start+n*width>len(array):fail()
                    curve=[]
                    for j in range(n):
                        row=array[start+j*width:start+(j+1)*width];time,value,ti=row[:3]
                        if time<0 or time>duration or (curve and time<=curve[-1][0]):fail()
                        curve.append([time,value,ti,row[3] if tangent else ti])
                curves.append(curve);total+=len(curve)
                if total>65536:fail()
            tracks.append(dict(material=name,kind=kind,register=register,curves=curves))
    return dict(schema=1,policy='P2_MATERIAL_COLOR_1',source_sha256=hashlib.sha256(data).hexdigest(),duration=duration,attribute=attr,tracks=tracks)

def bank_text(report):
    lines=[report['policy'],report['source_sha256'],f"{report['duration']} {report['attribute']} {len(report['tracks'])}"]
    for t in report['tracks']:
        lines.append(f"{t['material']} {t['kind']} {t['register']}")
        for curve in t['curves']:
            lines.append(str(len(curve)));lines.extend(' '.join(map(str,k)) for k in curve)
    return '\n'.join(lines)+'\n'

def export(source,output):
    report=decode(Path(source).read_bytes());output=Path(output);output.mkdir(parents=True,exist_ok=False)
    (output/'material-color.txt').write_text(bank_text(report),encoding='ascii')
    (output/'material-color.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(export(a.source,a.output),indent=2))
