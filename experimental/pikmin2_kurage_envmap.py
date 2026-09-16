"""Source-bound two-stage Jellyfloat export for the opt-in native P2 envmap mode."""
import argparse,json,struct
from pathlib import Path
from experimental.pikmin2_convert import blocks,u16,u32,Writer
from experimental.pikmin2_qurione_material_audit import entry
from experimental.pikmin2_kurage_material_patch import descriptor as base_descriptor,patch as base_patch,sha


def descriptor(model):
    rows=base_descriptor(model);m=blocks(model)['MAT3']
    for i,row in enumerate(rows):
        r=u32(m,12)+u16(m,u32(m,16)+2*i)*332
        if entry(m,88,m[r+4],1)!=b'\x02':raise ValueError('Expected two TEV stages')
        gens=[entry(m,56,u16(m,r+40+2*k),4) for k in range(2)]
        if [list(x[:3]) for x in gens]!=[[1,4,60],[1,1,33]]:raise ValueError('Unsupported texgen')
        matrix=entry(m,64,u16(m,r+72+2),100)
        if matrix[:2]!=bytes([1,6]):raise ValueError('Unsupported texture matrix mode')
        row['center']=list(struct.unpack_from('>2f',matrix,4))
        row['scale']=list(struct.unpack_from('>2f',matrix,16))
        rotation=struct.unpack_from('>h',matrix,24)[0]
        if rotation!=0:raise ValueError('Unaudited source rotation')
        row['translation']=list(struct.unpack_from('>2f',matrix,28))
        row['stages']=[]
        for k in range(2):
            order=entry(m,76,u16(m,r+188+2*k),4)
            if list(order[:3])!=[k,k,4]:raise ValueError('Unsupported texture order')
            if u16(entry(m,72,u16(m,r+132+2*k),2),0)!=k:raise ValueError('Unsupported texture binding')
            stage=entry(m,92,u16(m,r+228+2*k),20)
            row['stages'].append(dict(order=list(order[:3]),color=list(stage[1:10]),alpha=list(stage[10:19]),
                                      kcolor=m[r+156+k],kalpha=m[r+172+k]))
        row['konst']=b''.join(entry(m,84,u16(m,r+148+2*k),4) for k in range(4)).hex()
    return rows


def patch(mod,rows):
    # Verifies the original bounded one-stage layout; first stage uses source data.
    base_patch(mod,rows)
    at=0
    while u32(mod,at)!=48:at+=8+u32(mod,at+4)
    end=at+8+u32(mod,at+4);pos=(at+16+31)//32*32+248
    w=Writer();w.begin(48,2,2);w.pad()
    for row in rows:
        for reg in row['registers']:w.put('4hIfII',*reg,0,0.,0,0)
        w.data+=bytes.fromhex(row['konst']);w.put('I',2)
        for i,stage in enumerate(row['stages']):
            w.data+=bytes([0,*stage['order'],stage['kcolor'],stage['kalpha'],0,0])
            w.data+=bytes(stage['color']+[0,0,0])+bytes(stage['alpha']+[0,0,0])
    for row in rows:
        if pos+152>end or u32(mod,pos+76)!=1 or mod[pos+80:pos+84]!=bytes([0,1,4,10]) or u32(mod,pos+84)!=1:
            raise ValueError('Unsupported generated material record')
        w.data+=mod[pos:pos+76];w.put('I',2)
        w.data+=bytes([0,1,4,10,1,1,1,0]);w.put('I',2)
        first=mod[pos+88:pos+152]
        if u32(first,0)!=0 or u32(first,12)!=255:raise ValueError('Unsupported diffuse texture data')
        w.data+=first
        w.put('IHH4BIIf7fIII',1,0,0,0xE6,2,0,0,0,0,0.,*row['scale'],0.,*row['translation'],*row['center'],0,0,0)
        pos+=152
    w.end()
    return mod[:at]+bytes(w.data)+mod[end:]


def prepare(model,mod,output):
    source=Path(model).read_bytes();before=Path(mod).read_bytes();rows=descriptor(source);after=patch(before,rows)
    output=Path(output);output.mkdir(parents=True,exist_ok=False);(output/'patched.mod').write_bytes(after)
    report=dict(source_sha256=sha(source),before=sha(before),after=sha(after),materials=rows,
                requires='Native P2 mode6 marker 0xE6 support; old executables do not reproduce its matrix',
                limitations='Static source SRT, sampled geometry, source lighting/BTK not translated')
    (output/'patch.json').write_text(json.dumps(report,indent=2)+'\n');return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('model','mod','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();prepare(a.model,a.mod,a.output)
