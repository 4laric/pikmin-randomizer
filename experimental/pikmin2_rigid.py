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


def apply(matrix,point,normal=False):
    return tuple(sum(matrix[r][k]*point[k] for k in range(3))+(0 if normal else matrix[r][3]) for r in range(3))


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
        if read(j,'3f',at+4)!=(1.,1.,1.): raise ValueError('Scaled rigid joints not supported')
        matrix=local_matrix(read(j,'3h',at+16),read(j,'3f',at+24)) if local_overrides is None else local_overrides[index]
        if parents[index] is not None: matrix=compose(world(parents[index]),matrix)
        matrices[index]=matrix;visiting.remove(index);return matrix
    return [world(i) for i in range(count)]


def bake(arrays,shapes,matrices):
    original={a:arrays[a] for a in (9,10)};converted={9:[],10:[]};cache={9:{},10:{}}
    for shape in shapes:
        for tri in shape:
            for vertex in tri:
                joint=vertex.pop(0)
                for attr in (9,10):
                    key=(joint,vertex[attr])
                    if key not in cache[attr]:
                        cache[attr][key]=len(converted[attr])
                        converted[attr].append(apply(matrices[joint],original[attr][vertex[attr]],normal=attr==10))
                    vertex[attr]=cache[attr][key]
    arrays.update(converted)
