"""Private Tank movie/display-list lifetime probes; no production behavior change."""

def once(source,old,new):
    if source.count(old)!=1:raise ValueError('Unexpected diagnostic source anchor')
    return source.replace(old,new)

def system_probe(source):
    source='#include "tank_heap_probe.h"\n'+source
    start=source.index('Shape* StdSystem::loadShape(');end=source.index('AnimData* StdSystem::findAnimation(',start)
    body=source[start:end]
    body=once(body,'addGfxObject(newInfo);','addGfxObject(newInfo);\n            tank_diag_register(result, modelPath, getHeapNum());')
    source=source[:start]+body+source[end:]
    return once(source,'mHeaps[heapIdx].reset(flag);','tank_diag_reset(heapIdx);\n    mHeaps[heapIdx].reset(flag);')

def graphics_probe(source):
    source='#include "tank_heap_probe.h"\n'+source
    return once(source,'GXCallDisplayList(list.mData, list.mDataLength);','tank_diag_submit(model, list.mData, list.mDataLength);\n            GXCallDisplayList(list.mData, list.mDataLength);')

def analyze_heap(text):
    import re
    lines=text.splitlines();draws=[];warnings=[]
    for number,line in enumerate(lines,1):
        if line.startswith('TANK_HEAP_DRAW '):
            m=re.fullmatch(r'TANK_HEAP_DRAW row=(\d+) shape=(\S+) list=(\S+) size=(\d+) original=([0-9a-f]+) now=([0-9a-f]+) reset=(\d+) name=(.+)',line)
            if not m:raise ValueError('Malformed pointer probe')
            row,shape,pointer,size,old,new,reset,name=m.groups()
            draws.append(dict(line=number,row=int(row),shape=shape,pointer=pointer,size=int(size),previous_hash=old,current_hash=new,changed=old!=new,after_owner_heap_reset=bool(int(reset)),name=name))
        if '[PC GX] DESYNC #' in line and 'vtxdesc:' not in line:
            warnings.append(dict(line=number,message=line,preceding_probe=draws[-1] if draws else None))
    if not warnings:raise ValueError('No parser warnings reproduced')
    return dict(warnings=warnings,changed_draws=[r for r in draws if r['changed']],reset_draws=[r for r in draws if r['after_owner_heap_reset']],caveat='Preceding probe is chronological evidence, not automatically exact warning ownership; unchanged repeated submissions are not logged.')
