"""Static rigid-joint bind poses. No envelopes, skinning or animation playback."""
import math
import struct


def local_matrix(rotation, translation):
    # J3DGetTranslateRotateMtx: Z * Y * X, signed 16-bit turns.
    rx,ry,rz=[a*math.pi/32768 for a in rotation]
    sx,cx,sy,cy,sz,cz=math.sin(rx),math.cos(rx),math.sin(ry),math.cos(ry),math.sin(rz),math.cos(rz)
    return [[cz*cy,cz*sy*sx-sz*cx,cz*sy*cx+sz*sx,translation[0]],
            [sz*cy,sz*sy*sx+cz*cx,sz*sy*cx-cz*sx,translation[1]],
            [-sy,cy*sx,cy*cx,translation[2]]]


def compose(parent,child):
    return [[sum(parent[r][k]*child[k][c] for k in range(3))+(parent[r][3] if c==3 else 0)
             for c in range(4)] for r in range(3)]


def apply(matrix,point,normal=False,singular_normal="error"):
    if singular_normal not in ("error","transpose-adjugate"): raise ValueError("Invalid singular-normal policy")
    if normal:
        a,b,c=matrix[0][:3];d,e,f=matrix[1][:3];g,h,i=matrix[2][:3]
        cof=((e*i-f*h,f*g-d*i,d*h-e*g),(c*h-b*i,a*i-c*g,b*g-a*h),(b*f-c*e,c*d-a*f,a*e-b*d))
        det=a*cof[0][0]+b*cof[0][1]+c*cof[0][2]
        if abs(det)<1e-12:
            if singular_normal=='error':raise ValueError('Singular normal transform')
            divisor=-1. if det<0 else 1.
        else:divisor=det
        result=tuple(sum(cof[r][k]*point[k] for k in range(3))/divisor for r in range(3))
        length=math.sqrt(sum(v*v for v in result))
        if not length and abs(det)<1e-12:raise ValueError('Singular transform annihilates normal')
        return tuple(v/length for v in result) if length else result
    return tuple(sum(matrix[r][k]*point[k] for k in range(3))+matrix[r][3] for r in range(3))


def joint_matrices(blocks, local_overrides=None):
    def read(b,fmt,at): return struct.unpack_from('>'+fmt,b,at)
    j=blocks['JNT1'];h=blocks['INF1'];count=read(j,'H',8)[0]
    at=read(h,'I',20)[0];stack=[];current=None;parents={}
    while True:
        kind,index=read(h,'HH',at);at+=4
        if kind==0: break
        if kind==1: stack.append(current)
        elif kind==2:
            if not stack: raise ValueError('Unbalanced joint hierarchy')
            current=stack.pop()
        elif kind==0x10:
            if index>=count or index in parents: raise ValueError('Invalid joint hierarchy')
            parents[index]=stack[-1] if stack else None;current=index
    if stack or set(parents)!=set(range(count)): raise ValueError('Incomplete joint hierarchy')
    matrices={};visiting=set()
    def world(index):
        if index in matrices: return matrices[index]
        if index in visiting: raise ValueError('Cyclic joints')
        visiting.add(index)
        remap=read(j,'I',16)[0];record=index if not remap else read(j,'H',remap+2*index)[0]
        at=read(j,'I',12)[0]+64*record
        if local_overrides is None and read(j,'3f',at+4)!=(1.,1.,1.): raise ValueError('Scaled rigid joints not supported')
        matrix=local_matrix(read(j,'3h',at+16),read(j,'3f',at+24)) if local_overrides is None else local_overrides[index]
        if parents[index] is not None: matrix=compose(world(parents[index]),matrix)
        matrices[index]=matrix;visiting.remove(index);return matrix
    return [world(i) for i in range(count)]


def bake(arrays,shapes,matrices,missing_normals='error',singular_normal='error'):
    if missing_normals not in ('error','compute','default'):raise ValueError('Invalid missing-normal policy')
    if singular_normal not in ('error','transpose-adjugate'):raise ValueError('Invalid singular-normal policy')
    seen=set()
    for shape in shapes:
        for tri in shape:
            for i,vertex in enumerate(tri):
                if id(vertex) in seen:tri[i]=dict(vertex)
                else:seen.add(id(vertex))
    original={9:arrays[9],10:arrays.get(10,[])};converted={9:[],10:[]};cache={9:{},10:{}}
    # Preserve original topology keys, including UV/color seams and shape boundaries.
    pending=[];sums={}
    for si,shape in enumerate(shapes):
        for ti,tri in enumerate(shape):
            corners=[]
            for vertex in tri:
                topology=(si,tuple(sorted(vertex.items())))
                joint=vertex.pop(0);missing=10 not in vertex
                if missing and missing_normals=='error':raise ValueError('Missing display-list normal')
                for attr in (9,10):
                    if attr==10 and missing:continue
                    key=(joint,vertex[attr])
                    if key not in cache[attr]:
                        cache[attr][key]=len(converted[attr])
                        converted[attr].append(apply(matrices[joint],original[attr][vertex[attr]],normal=attr==10,singular_normal=singular_normal))
                    vertex[attr]=cache[attr][key]
                corners.append((vertex,topology,missing))
            if any(c[2] for c in corners):
                p,q,r=[converted[9][v[9]] for v,_,_ in corners]
                u=[q[i]-p[i] for i in range(3)];v=[r[i]-p[i] for i in range(3)]
                face=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
                for vertex,key,missing in corners:
                    if not missing:continue
                    pending.append((vertex,key));acc=sums.setdefault(key,[0.,0.,0.])
                    for i in range(3):acc[i]+=face[i]
    indices={}
    for vertex,key in pending:
        if key not in indices:
            normal=sums[key];length=math.sqrt(sum(x*x for x in normal))
            if missing_normals=='default':normal=(0.,1.,0.)
            elif length>0:normal=tuple(x/length for x in normal)
            else:raise ValueError('Cannot compute normal for degenerate geometry')
            indices[key]=len(converted[10]);converted[10].append(normal)
        vertex[10]=indices[key]
    arrays.update(converted)
