"""Restricted static J3D BMD -> Open Nectar MOD proof-of-concept.
Material shading is reduced to vertex color times a diffuse texture.
Identity-root models are accepted by default; static rigid bind-pose baking is
opt-in. This is not a general J3D exporter.
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

def texture_layout(kind, width, height):
    # GX tiled base-level bytes; MOD's format enumeration differs from GX.
    layouts={0:(3,8,8,32),1:(4,8,4,32),2:(5,8,4,32),3:(6,4,4,32),
             4:(0,4,4,32),5:(2,4,4,32),6:(7,4,4,64),14:(1,8,8,32)}
    if kind not in layouts or width<=0 or height<=0:
        raise ValueError('Unsupported texture format or dimensions')
    fmt,bw,bh,size=layouts[kind]
    return fmt,((width+bw-1)//bw)*((height+bh-1)//bh)*size

def blocks(data):
    if data[:8] != b'J3D2bmd3' or u32(data,8) != len(data): raise ValueError('Expected complete J3D2bmd3')
    result={}; at=32
    for _ in range(u32(data,12)):
        size=u32(data,at+4)
        if size<8 or at+size>len(data): raise ValueError('Invalid block length')
        result[data[at:at+4].decode('ascii')]=data[at:at+size]; at+=size
    return result

def pixel_state(m, r):
    """Translate MAT3 pixel-engine state to the native PVW bit fields."""
    def entry(table, index, size):
        start=u32(m,table)+index*size
        end=min([u32(m,i) for i in range(12,132,4) if u32(m,i)>u32(m,table)]+[len(m)])
        if not u32(m,table) or start+size>end:
            raise ValueError('Invalid material pixel-state reference')
        return m[start:start+size]
    test,func,write,_=entry(116,m[r+6],4)
    mode,src,dst,logic=entry(112,u16(m,r+0x148),4)
    comp0,ref0,op,comp1,ref1,*_=entry(108,u16(m,r+0x146),8)
    if test>1 or write>1 or func>7 or mode>3 or src>7 or dst>7 or logic>15 or comp0>7 or comp1>7 or op>3:
        raise ValueError('Unsupported material pixel state')
    category=m[r]&7
    if category not in (1,2,4): raise ValueError('Unsupported material draw category')
    return ((category<<8)|1, 1,
            comp0|(ref0<<4)|(op<<16)|(comp1<<20)|(ref1<<24),
            test|(write<<1)|(func<<8), mode|(src<<4)|(dst<<8)|(logic<<12))

def diffuse_slot(m, r):
    """Prefer an explicit untransformed UV0 diffuse stage over a noise input.

    Snow uses its first textures for a view-dependent sparkle calculation.
    The restricted exporter cannot reproduce that calculation, but can retain
    its actual texture-times-vertex-color base instead of displaying raw noise.
    """
    count=m[u32(m,88)+m[r+4]]
    for i in range(count):
        stage=u32(m,92)+u16(m,r+0xe4+2*i)*20
        color=list(m[stage+1:stage+10])
        if color not in ([15,10,8,15,0,0,0,1,0],[15,8,10,15,0,0,0,1,0]):continue
        order=u32(m,76)+u16(m,r+0xbc+2*i)*4
        coord,slot=m[order:order+2]
        if coord>=8 or slot>=8:continue
        gen=u32(m,56)+u16(m,r+0x28+2*coord)*4
        if list(m[gen:gen+3])==[1,4,60]:return slot
    return 0

def decode(data, approximate_materials=False, bake_rigid=False, pose=None):
    b=blocks(data); j=b['JNT1']; d=b['DRW1']
    if u16(b['EVP1'],8)!=0: raise ValueError('Skinned envelopes not supported')
    if not bake_rigid and (u16(j,8)!=1 or u16(d,8)!=1 or d[u32(d,12)]!=0 or u16(d,u32(d,16))!=0): raise ValueError('Only one rigid joint supported')
    jo=u32(j,12)
    if not bake_rigid and (unpack(j,'3f',jo+4)!=(1.,1.,1.) or unpack(j,'3h',jo+16)!=(0,0,0) or unpack(j,'3f',jo+24)!=(0.,0.,0.)): raise ValueError('Non-identity joint transform')
    if bake_rigid:
        from experimental.pikmin2_rigid import joint_matrices
        matrices=joint_matrices(b,pose)
        draw_joints=[u16(d,u32(d,16)+2*i) for i in range(u16(d,8))]
        if any(d[u32(d,12)+i]!=0 or joint>=len(matrices) for i,joint in enumerate(draw_joints)):
            raise ValueError('Non-rigid draw matrix')
    v=b['VTX1']; formats={}; at=u32(v,8)
    while u32(v,at)!=255:
        attr,count,kind=unpack(v,'III',at); formats[attr]=(count,kind,v[at+12]); at+=16
    offsets={9:u32(v,12),10:u32(v,16),11:u32(v,24),12:u32(v,28),
             **{13+i:u32(v,32+4*i) for i in range(8)}}
    arrays={}
    for attr,(count,kind,shift) in formats.items():
        if attr not in offsets or (attr not in (9,10,11,13) and not approximate_materials):
            raise ValueError(f'Unsupported vertex attribute {attr}')
        start=offsets[attr]; end=min([x for x in offsets.values() if x>start]+[len(v)])
        if attr in (11,12):
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
        if s[rec]!=0 and not (bake_rigid and s[rec]==3): raise ValueError('Unsupported shape matrix type')
        groups,desc,mi,di=unpack(s,'4H',rec+2); attrs=[]; at=u32(s,24)+desc
        while u32(s,at)!=255:
            attr,kind=unpack(s,'II',at); at+=8
            if (attr not in (0,9,10,11,13) and not (approximate_materials and attr in (12,*range(14,21))) and not (bake_rigid and approximate_materials and attr==1)) or kind not in (1,2,3): raise ValueError('Unsupported display-list attribute')
            if kind==1 and attr not in ((0,1) if bake_rigid else (0,)): raise ValueError('Direct non-matrix attribute unsupported')
            attrs.append((attr,kind))
        triangles=[];matrix_slots={}
        for gi in range(groups):
            if bake_rigid:
                _,matrix_count,first=unpack(s,'HHI',u32(s,36)+(mi+gi)*8)
                for slot in range(matrix_count):
                    draw=u16(s,u32(s,28)+2*(first+slot))
                    if draw!=65535:
                        if draw>=len(draw_joints): raise ValueError('Invalid rigid draw reference')
                        matrix_slots[slot]=draw_joints[draw]
            size,off=unpack(s,'II',u32(s,40)+(di+gi)*8); at=u32(s,32)+off; end=at+size
            while at<end:
                op=s[at]; at+=1
                if op==0: continue
                if op not in (0x80,0x90,0x98,0xA0): raise ValueError(f'Unsupported primitive {op:#x}')
                count=u16(s,at); at+=2; verts=[]
                for _ in range(count):
                    vv={};matrix_slot=0
                    for attr,kind in attrs:
                        value=s[at] if kind in (1,2) else u16(s,at); at+=1 if kind in (1,2) else 2
                        if attr==0:
                            if bake_rigid:
                                if value%3: raise ValueError('Invalid matrix slot')
                                matrix_slot=value//3
                            elif value!=0: raise ValueError('Non-root matrix reference')
                        elif attr==1 and bake_rigid:
                            pass # texture matrix animation omitted in explicit approximation mode
                        else:
                            if value>=len(arrays[attr]): raise ValueError('Vertex index out of range')
                            vv[attr]=value
                    if bake_rigid:
                        if matrix_slot not in matrix_slots: raise ValueError('Missing rigid matrix slot')
                        vv[0]=matrix_slots[matrix_slot]
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
    hierarchy=b['INF1']; at=u32(hierarchy,20); mat=0; mapping={}; order=[]
    while True:
        typ,idx=unpack(hierarchy,'HH',at); at+=4
        if typ==0: break
        if typ==0x11: mat=idx
        if typ==0x12:
            mapping[idx]=mat;order.append(idx)
    if sorted(order)!=list(range(len(shapes))): raise ValueError('Expected each shape once in draw hierarchy')
    b['_draw_order']=order
    m=b['MAT3']; materials=[]; states=[]
    for i in range(u16(m,8)):
        r=u32(m,12)+u16(m,u32(m,16)+2*i)*332
        if not approximate_materials and m[u32(m,88)+m[r+4]]!=1: raise ValueError('Only single-stage materials supported')
        if not approximate_materials:
            indirect=u32(m,24)
            if indirect and (m[indirect+i*312] or m[indirect+i*312+1]): raise ValueError('Indirect textures unsupported')
            if any(u16(m,r+132+2*k)!=65535 for k in range(1,8)): raise ValueError('Multiple texture inputs unsupported')
        slot=diffuse_slot(m,r) if approximate_materials else 0
        tex=u16(m,r+132+2*slot); tex=-1 if tex==65535 else u16(m,u32(m,72)+tex*2)
        materials.append(tex)
        states.append(pixel_state(m,r))
    b['_render_states']=[states[mapping[i]] for i in range(len(shapes))]
    if bake_rigid:
        from experimental.pikmin2_rigid import bake
        # Primitive strips/fans share vertex dictionaries; bake each reference independently.
        shapes=[[[dict(v) for v in tri] for tri in shape] for shape in shapes]
        bake(arrays,shapes,matrices)
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

def convert(source, output, approximate_materials=False, y_offset=0.0, bake_rigid=False, pose=None, material_colors=None):
    if pose is not None and not bake_rigid: raise ValueError('Animation pose requires rigid baking')
    report=write_model(decode(Path(source).read_bytes(), approximate_materials,bake_rigid,pose),output,str(source),y_offset,material_colors)
    report['rigid_bind_pose_baked']=bake_rigid
    Path(output).with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def write_model(decoded, output, source, y_offset=0.0, material_colors=None):
    if not math.isfinite(y_offset): raise ValueError("Y offset must be finite")
    b,a,shapes,mats=decoded; w=Writer()
    states=b['_render_states']
    if len(states)!=len(shapes): raise ValueError('Expected pixel state for every shape')
    colors=material_colors if material_colors is not None else [(255,255,255,255)]*len(shapes)
    if len(colors)!=len(shapes) or any(len(c)!=4 or any(type(v)!=int or not 0<=v<=255 for v in c) for c in colors):
        raise ValueError('Expected one RGBA8 material color per shape')
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
        if t[r+8]!=0: raise ValueError('Paletted textures unsupported')
        fmt,size=texture_layout(kind,width,height); start=r+u32(t,r+28)
        if start+size>len(t):raise ValueError('Truncated texture')
        w.put('HH7I',width,height,fmt,1,0,0,0,0,size);w.data+=t[start:start+size]
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
        w.put('Ii4BI',states[i][0],tex,*colors[i],i)
        w.put('4BIfII',*colors[i],0,0.,0,0)
        w.put('If',0x1800 if 11 in a else 0,0.)
        w.put('4I',*states[i][1:])
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
    # Native material traversal walks the joint list backwards within each pass.
    # J3D hierarchy order matters for depth-write-disabled terrain overlays.
    for i in reversed(b['_draw_order']):w.put('HH',i,i)
    w.end();w.begin(65535);w.end()
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(w.data)
    report={'source':str(source),'output':str(output),'vertices':len(a[9]),'triangles':sum(map(len,shapes)),'shapes':len(shapes),'textures':texture_count,'bounds':bounds,'y_offset':y_offset,'discarded_attributes':[k for k in a if k not in (9,10,11,13)],'material_policy':'vertex color times identifiable UV0 diffuse texture (first texture fallback); original TEV not reproduced','pixel_state_policy':'source blend, alpha compare, depth test/write, draw category and hierarchy order preserved'}
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--approximate-materials',action='store_true');p.add_argument('--y-offset',type=float,default=0.0,help='Translate render vertices vertically; collision is converted separately');args=p.parse_args()
    print(json.dumps(convert(args.source,args.output,args.approximate_materials,args.y_offset),indent=2))
