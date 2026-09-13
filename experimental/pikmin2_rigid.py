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


SINGULAR_NORMAL_MODES=('error','transpose-adjugate')

def apply(matrix,point,normal=False,singular_normal='error'):
    if singular_normal not in SINGULAR_NORMAL_MODES:
        raise ValueError(f'Unsupported singular normal mode {singular_normal!r}')
    if normal:
        a,b,c=matrix[0][:3];d,e,f=matrix[1][:3];g,h,i=matrix[2][:3]
        cof=((e*i-f*h,f*g-d*i,d*h-e*g),(c*h-b*i,a*i-c*g,b*g-a*h),(b*f-c*e,c*d-a*f,a*e-b*d))
        det=a*cof[0][0]+b*cof[0][1]+c*cof[0][2]
        if abs(det)<1e-12:
            if singular_normal=='error':raise ValueError('Singular normal transform')
            # Transpose-adjugate (unnormalized cofactor) generalizes the
            # inverse-transpose to singular matrices; the result is normalized
            # below, so the missing 1/det scale is irrelevant.
            result=tuple(sum(cof[r][k]*point[k] for k in range(3)) for r in range(3))
        else:
            result=tuple(sum(cof[r][k]*point[k] for k in range(3))/det for r in range(3))
        length=math.sqrt(sum(v*v for v in result))
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


MISSING_NORMAL_MODES=('error','compute','default')

def bake(arrays,shapes,matrices,missing_normals='error',singular_normal='error'):
    if missing_normals not in MISSING_NORMAL_MODES:
        raise ValueError(f'Unsupported missing normals mode {missing_normals!r}')
    if singular_normal not in SINGULAR_NORMAL_MODES:
        raise ValueError(f'Unsupported singular normal mode {singular_normal!r}')
    original={a:arrays.get(a,[]) for a in (9,10)};converted={9:[],10:[]};cache={9:{},10:{}}
    missing=[]
    for shape in shapes:
        for tri in shape:
            for vertex in tri:
                joint=vertex.pop(0)
                for attr in (9,10):
                    if attr==10 and attr not in vertex:
                        if missing_normals=='error':
                            # Strict path: surface the missing normal attribute
                            # exactly like the original implementation.
                            raise KeyError(10)
                        missing.append(vertex)
                        continue
                    key=(joint,vertex[attr])
                    if key not in cache[attr]:
                        cache[attr][key]=len(converted[attr])
                        converted[attr].append(apply(matrices[joint],original[attr][vertex[attr]],normal=attr==10,singular_normal=singular_normal))
                    vertex[attr]=cache[attr][key]
    if missing:
        if missing_normals=='default':
            converted[10].append((0.,1.,0.))
            for vertex in missing: vertex[10]=len(converted[10])-1
        else:
            # 'compute': area-weighted accumulation of baked face normals per
            # baked position (unnormalized cross products weight by area).
            sums={}
            for shape in shapes:
                for tri in shape:
                    (ax,ay,az),(bx,by,bz),(cx,cy,cz)=[converted[9][v[9]] for v in tri]
                    ux,uy,uz=bx-ax,by-ay,bz-az;vx,vy,vz=cx-ax,cy-ay,cz-az
                    normal=(uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx)
                    for v in tri:
                        acc=sums.get(v[9],(0.,0.,0.))
                        sums[v[9]]=tuple(acc[k]+normal[k] for k in range(3))
            resolved={}
            for vertex in missing:
                position=vertex[9]
                if position not in resolved:
                    acc=sums.get(position,(0.,0.,0.))
                    length=math.sqrt(sum(v*v for v in acc))
                    resolved[position]=len(converted[10])
                    converted[10].append(tuple(v/length for v in acc) if length else (0.,1.,0.))
                vertex[10]=resolved[position]
    arrays.update(converted)
