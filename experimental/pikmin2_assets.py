"""Narrow local-disc extractor for the experimental Pikmin 2 room preview."""
from pathlib import Path
import struct

ROOM_PATH='user/Mukki/mapunits/arc/room_4x4a_4_conc'

def u32(data,offset): return struct.unpack_from('>I',data,offset)[0]

def decompress(data):
    if data[:4]!=b'Yaz0': return data
    size=u32(data,4)
    if size>32*1024*1024: raise ValueError('Archive exceeds preview limit')
    out=bytearray();pos=16
    while len(out)<size:
        mask=data[pos];pos+=1
        for bit in range(8):
            if len(out)==size: break
            if mask & (128>>bit):out.append(data[pos]);pos+=1
            else:
                a,b=data[pos:pos+2];pos+=2;distance=((a&15)<<8)|b;count=a>>4
                if count==0:count=data[pos]+18;pos+=1
                else:count+=2
                if distance>=len(out) or len(out)+count>size:raise ValueError('Invalid Yaz0 backreference')
                for _ in range(count):out.append(out[-distance-1])
    return bytes(out)

def archive_files(data):
    data=decompress(data)
    if data[:4]!=b'RARC':raise ValueError('Expected RARC archive')
    base=u32(data,8);payload=base+u32(data,12)
    nodes=base+u32(data,base+4);entries=base+u32(data,base+12);strings=base+u32(data,base+20)
    node_count=u32(data,base);entry_count=u32(data,base+8)
    files={};visited=set()
    def walk(index,prefix):
        if index>=node_count or index in visited:raise ValueError('Invalid archive directory graph')
        visited.add(index);p=nodes+index*16
        count=struct.unpack_from('>H',data,p+10)[0];first=u32(data,p+12)
        if first+count>entry_count:raise ValueError('Invalid archive directory span')
        for i in range(first,first+count):
            e=entries+i*20;tag=u32(data,e+4);offset=strings+(tag&0xffffff)
            name=data[offset:data.index(0,offset)].decode('shift_jis')
            if name in ('.','..'):continue
            if not name or any(c in name for c in '/\\:'):raise ValueError('Unsafe archive filename')
            target=prefix+name;offset=u32(data,e+8);length=u32(data,e+12)
            if (tag>>24)&2:walk(offset,target+'/')
            else:
                start=payload+offset
                if start+length>len(data) or target in files:raise ValueError('Invalid archive file span')
                files[target]=data[start:start+length]
    walk(0,'')
    return files

def disc_files(iso):
    size=iso.stat().st_size
    with iso.open('rb') as file:
        header=file.read(0x440)
        if header[:6]!=b'GPVE01' or header[7]!=0:raise ValueError('Preview supports US GPVE01 revision 0')
        offset,length=struct.unpack_from('>II',header,0x424)
        if offset+length>size or length>16*1024*1024:raise ValueError('Invalid disc filesystem')
        file.seek(offset);data=file.read(length)
    count=u32(data,8);names=data[count*12:];stack=[('',count)];result={}
    if count*12>len(data):raise ValueError('Invalid filesystem count')
    for i in range(1,count):
        while stack and i>=stack[-1][1]:stack.pop()
        if not stack:raise ValueError('Invalid directory bounds')
        tag,offset,length=struct.unpack_from('>III',data,12*i);index=tag&0xffffff
        name=names[index:names.index(0,index)].decode('shift_jis')
        if not name or name in ('.','..') or any(c in name for c in '/\\:'):raise ValueError('Unsafe disc filename')
        path=stack[-1][0]+name
        if tag>>24:
            if length<=i or length>count:raise ValueError('Invalid directory range')
            stack.append((path+'/',length))
        else:
            if offset+length>size or path in result:raise ValueError('Invalid disc file')
            result[path]=(offset,length)
    return result

def extract_preview(iso,output):
    catalog=disc_files(iso);output.mkdir(parents=True,exist_ok=True)
    sources={ROOM_PATH+'/arc.szs':'arc',ROOM_PATH+'/texts.szs':'texts','user/Abe/Pellet/us/bolt.szs':'treasure'}
    with iso.open('rb') as file:
        for source,folder in sources.items():
            offset,length=catalog[source];file.seek(offset)
            for name,data in archive_files(file.read(length)).items():
                target=output/folder/name
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iso',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();extract_preview(args.iso,args.output)
