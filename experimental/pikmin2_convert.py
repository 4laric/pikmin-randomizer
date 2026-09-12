"""Restricted static J3D BMD -> Open Nectar MOD proof-of-concept.
Material shading is deliberately reduced to vertex color times the first texture.
Only rigid, identity-root models are accepted; this is not a general J3D exporter.
"""
from pathlib import Path
import argparse
import json
import math
import struct

def unpack(b, fmt, at=0):
    try: return struct.unpack_from('>'+fmt, b, at)
    except struct.error as exc: raise ValueError('Truncated model') from exc

def u32(b, at): return unpack(b,'I',at)[0]
def u16(b, at): return unpack(b,'H',at)[0]
def pack(fmt,*v): return struct.pack('>'+fmt,*v)

def blocks(data):
    if data[:8] != b'J3D2bmd3' or u32(data,8) != len(data): raise ValueError('Expected complete J3D2bmd3')
    result={}; at=32
    for _ in range(u32(data,12)):
        size=u32(data,at+4)
        if size<8 or at+size>len(data): raise ValueError('Invalid block length')
        result[data[at:at+4].decode('ascii')]=data[at:at+size]; at+=size
    return result

def decode(data, approximate_materials=False):
    b=blocks(data); j=b['JNT1']; d=b['DRW1']
    if u16(j,8)!=1 or u16(b['EVP1'],8)!=0 or u16(d,8)!=1 or d[u32(d,12)]!=0 or u16(d,u32(d,16))!=0: raise ValueError('Only one rigid joint supported')
    jo=u32(j,12)
    if unpack(j,'3f',jo+4)!=(1.,1.,1.) or unpack(j,'3h',jo+16)!=(0,0,0) or unpack(j,'3f',jo+24)!=(0.,0.,0.): raise ValueError('Non-identity joint transform')
    v=b['VTX1']; formats={}; at=u32(v,8)
    while u32(v,at)!=255:
        attr,count,kind=unpack(v,'III',at); formats[attr]=(count,kind,v[at+12]); at+=16
    offsets={9:u32(v,12),10:u32(v,16),11:u32(v,24),13:u32(v,32)}
    arrays={}
    for attr,(count,kind,shift) in formats.items():
        if attr not in offsets: raise ValueError(f'Unsupported vertex attribute {attr}')
        start=offsets[attr]; end=min([x for x in offsets.values() if x>start]+[len(v)])
        if attr==11:
            if kind!=5: raise ValueError('Only RGBA8 colors supported')
            stride=4; values=[tuple(v[x:x+4]) for x in range(start,end-stride+1,stride)]
        else:
            dim=3 if attr in (9,10) else 2
            if kind not in (3,4): raise ValueError('Only S16/F32 vertex data supported')
            fmt=('h' if kind==3 else 'f')*dim; stride=struct.calcsize('>'+fmt)
            values=[tuple(z/(2**shift) if kind==3 else z for z in unpack(v,fmt,x)) for x in range(start,end-stride+1,stride)]
        arrays[attr]=values
    s=b['SHP1']; shapes=[]
    for si in range(u16(s,8)):
        rec=u32(s,12)+u16(s,u32(s,16)+2*si)*40
        if s[rec]!=0: raise ValueError('Unsupported shape matrix type')
        groups,desc,mi,di=unpack(s,'4H',rec+2); attrs=[]; at=u32(s,24)+desc
        while u32(s,at)!=255:
            attr,kind=unpack(s,'II',at); at+=8
            if attr not in (0,9,10,11,13) or kind not in (1,2,3): raise ValueError('Unsupported display-list attribute')
            if kind==1 and attr!=0: raise ValueError('Direct non-matrix attribute unsupported')
            attrs.append((attr,kind))
        triangles=[]
        for gi in range(groups):
            size,off=unpack(s,'II',u32(s,40)+(di+gi)*8); at=u32(s,32)+off; end=at+size
            while at<end:
                op=s[at]; at+=1
                if op==0: continue
                if op not in (0x80,0x90,0x98,0xA0): raise ValueError(f'Unsupported primitive {op:#x}')
                count=u16(s,at); at+=2; verts=[]
                for _ in range(count):
                    vv={}
                    for attr,kind in attrs:
                        value=s[at] if kind in (1,2) else u16(s,at); at+=1 if kind in (1,2) else 2
                        if attr==0:
                            if value!=0: raise ValueError('Non-root matrix reference')
                        else:
                            if value>=len(arrays[attr]): raise ValueError('Vertex index out of range')
                            vv[attr]=value
                    verts.append(vv)
                if op==0x90:
                    if count%3: raise ValueError('Partial triangle')
                    triangles.extend(verts[i:i+3] for i in range(0,count,3))
                elif op==0x80:
                    if count%4: raise ValueError('Partial quad')
                    for i in range(0,count,4): triangles.extend(([verts[i],verts[i+1],verts[i+2]],[verts[i],verts[i+2],verts[i+3]]))
                elif op==0x98:
                    triangles.extend([verts[i+(i%2)],verts[i+1-(i%2)],verts[i+2]] for i in range(count-2))
                else: triangles.extend([verts[0],verts[i],verts[i+1]] for i in range(1,count-1))
            if at!=end: raise ValueError('Primitive packet overrun')
        shapes.append(triangles)
    hierarchy=b['INF1']; at=u32(hierarchy,20); mat=0; mapping={}
    while True:
        typ,idx=unpack(hierarchy,'HH',at); at+=4
        if typ==0: break
        if typ==0x11: mat=idx
        if typ==0x12: mapping[idx]=mat
    m=b['MAT3']; materials=[]
    for i in range(u16(m,8)):
        r=u32(m,12)+u16(m,u32(m,16)+2*i)*332
        if not approximate_materials and m[u32(m,88)+m[r+4]]!=1: raise ValueError('Only single-stage materials supported')
        if not approximate_materials:
            indirect=u32(m,24)
            if indirect and (m[indirect+i*312] or m[indirect+i*312+1]): raise ValueError('Indirect textures unsupported')
            if any(u16(m,r+132+2*k)!=65535 for k in range(1,8)): raise ValueError('Multiple texture inputs unsupported')
        tex=u16(m,r+132); tex=-1 if tex==65535 else u16(m,u32(m,72)+tex*2)
        materials.append(tex)
    # Array blocks carry alignment padding; only referenced entries are vertices.
    for attr in arrays:
        used=[v[attr] for tris in shapes for tri in tris for v in tri if attr in v]
        arrays[attr]=arrays[attr][:max(used)+1] if used else []
    return b,arrays,shapes,[materials[mapping[i]] for i in range(len(shapes))]

class Writer:
    def __init__(self): self.data=bytearray()
    def put(self,fmt,*v): self.data+=pack(fmt,*v)
    def pad(self): self.data+=b'\0'*((-len(self.data))%32)
    def begin(self,tag,*counts):
        self.pad(); self.start=len(self.data); self.put('II',tag,0)
        for n in counts:self.put('I',n)
    def end(self):
        self.pad(); struct.pack_into('>I',self.data,self.start+4,len(self.data)-self.start-8)

def convert(source, output, approximate_materials=False, y_offset=0.0):
    if not math.isfinite(y_offset): raise ValueError("Y offset must be finite")
    b,a,shapes,mats=decode(Path(source).read_bytes(), approximate_materials); w=Writer()
    a[9]=[(x,y+y_offset,z) for x,y,z in a[9]]
    w.begin(0);w.pad();w.put('II',0,0);w.end()
    for attr,tag,fmt in ((9,16,'3f'),(10,17,'3f'),(11,19,'4B'),(13,24,'2f')):
        if attr not in a: continue
        w.begin(tag,len(a[attr]));w.pad()
        for vertex in a[attr]:w.put(fmt,*vertex)
        w.end()
    t=b['TEX1']; texture_count=u16(t,8)
    w.begin(32,texture_count);w.pad()
    for i in range(texture_count):
        r=u32(t,12)+32*i; kind=t[r]; width,height=unpack(t,'HH',r+2)
        if kind not in (0,14) or t[r+8]!=0: raise ValueError('Only unpaletted I4/CMPR textures supported')
        size=((width+7)//8)*((height+7)//8)*32; start=r+u32(t,r+28)
        if start+size>len(t):raise ValueError('Truncated texture')
        w.put('HH7I',width,height,1 if kind==14 else 3,1,0,0,0,0,size);w.data+=t[start:start+size]
    w.end();w.begin(34,texture_count);w.pad()
    for i in range(texture_count):
        r=u32(t,12)+32*i
        if t[r+6] not in (0,1,2) or t[r+7] not in (0,1,2): raise ValueError('Unsupported texture wrap')
        wrap={0:1,1:0,2:2}
        w.put('4Hf',i,0,wrap[t[r+6]]|(wrap[t[r+7]]<<8),0,0.)
    w.end()
    # Each shape gets a deliberately simple static PVW material.
    w.begin(48,len(shapes),len(shapes));w.pad()
    for tex in mats:
        for _ in range(3):w.put('4hIfII',255,255,255,255,0,0.,0,0)
        w.data+=bytes([255])*16;w.put('I',1)
        w.data+=bytes([0,0 if tex>=0 else 255,0 if tex>=0 else 255,4,0,0,0,0])
        w.data+=bytes([15,8,10,15,0,0,0,1,0,0,0,0] if tex>=0 else [15,15,15,10,0,0,0,1,0,0,0,0])
        w.data+=bytes([7,4,5,7,0,0,0,1,0,0,0,0] if tex>=0 else [7,7,7,5,0,0,0,1,0,0,0,0])
    for i,tex in enumerate(mats):
        w.put('Ii4BI',257,tex,255,255,255,255,i)
        w.put('4BIfII',255,255,255,255,0,0.,0,0)
        w.put('If',0x1800 if 11 in a else 0,0.)
        w.put('4I',0,0,0,0)
        w.put('I3fI',0,1.,1.,1.,1 if tex>=0 else 0)
        if tex>=0:w.data+=bytes([0,1,4,10])
        w.put('I',1 if tex>=0 else 0)
        if tex>=0:
            w.put('IHH4BIIf7fIII',tex,0,0,0,0,0,0,255,0,0.,1.,1.,0.,0.,0.,0.,0.,0,0,0)
    w.end();w.begin(64,1);w.pad();w.put('h',0);w.end()  # Direct joint 0; negative entries select envelopes.
    w.begin(80,len(shapes));w.pad()
    for tris in shapes:
        hascolor=11 in tris[0][0]; hasuv=13 in tris[0][0]; flags=1|(4 if hascolor else 0)|(8 if hasuv else 0)
        dl=bytearray(pack('BH',0x90,len(tris)*3))
        for tri in tris:
            for v in tri:
                dl+=pack('BHH',0,v[9],v[10])
                if hascolor:dl+=pack('H',v[11])
                if hasuv:dl+=pack('H',v[13])
        dl+=b'\0'*((-len(dl))%32)
        w.put('4Ih4I',0,flags,1,1,0,1,0,len(tris),len(dl));w.pad();w.data+=dl
    w.end();w.begin(96,1);w.pad()
    bounds=[min(v[k] for v in a[9]) for k in range(3)]+[max(v[k] for v in a[9]) for k in range(3)]
    w.put('iI6ff9fI',-1,0,*bounds,0.,1.,1.,1.,0.,0.,0.,0.,0.,0.,len(shapes))
    for i in range(len(shapes)):w.put('HH',i,i)
    w.end();w.begin(65535);w.end()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(w.data)
    report={'source':str(source),'output':str(output),'vertices':len(a[9]),'triangles':sum(map(len,shapes)),'shapes':len(shapes),'textures':texture_count,'bounds':bounds,'y_offset':y_offset,'material_policy':'static vertex color multiplied by first texture; original TEV not reproduced'}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--approximate-materials',action='store_true');p.add_argument('--y-offset',type=float,default=0.0,help='Translate render vertices vertically; collision is converted separately');args=p.parse_args()
    print(json.dumps(convert(args.source,args.output,args.approximate_materials,args.y_offset),indent=2))
