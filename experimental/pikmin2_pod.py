"""Local Research Pod and one source-configured treasure for the economy preview."""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_cave import safe_name, tree
from experimental.pikmin2_convert import convert


def pellet_catalog(text):
    nodes=tree(text)
    if not nodes or int(nodes[0])!=len(nodes)-1: raise ValueError('Pellet config count mismatch')
    result={}
    for block in nodes[1:]:
        fields={};cursor=0
        while cursor<len(block) and block[cursor]!='end':
            key=block[cursor];cursor+=1;count=3 if key=='offset' else 1
            if key in fields or cursor+count>len(block): raise ValueError('Invalid pellet parameter')
            fields[key]=block[cursor] if count==1 else block[cursor:cursor+count];cursor+=count
        if cursor!=len(block)-1 or block[cursor]!='end' or fields['name'] in result:
            raise ValueError('Invalid pellet config terminator or duplicate name')
        result[fields['name']]=fields
    return result


def extract(iso,output,treasure='dia_a_red'):
    if treasure not in ('dia_a_red','tape_yellow','map01'):
        raise ValueError('Choose an Emergence treasure')
    output.mkdir(parents=True,exist_ok=False);catalog=disc_files(iso);hashes={}
    with iso.open('rb') as disc:
        def read(path):
            offset,size=catalog[path];disc.seek(offset);data=disc.read(size)
            if len(data)!=size: raise ValueError('Truncated local asset')
            hashes[path]=hashlib.sha256(data).hexdigest();return data
        configs=pellet_catalog(read('user/Abe/Pellet/us/otakara_config.txt').decode('shift_jis'))
        corpses=pellet_catalog(read('user/Abe/Pellet/us/carcass_config.txt').decode('shift_jis'))
        selected=configs[treasure];corpse=corpses['Kochappy']
        for source,directory in [('user/Kando/pod/arc.szs','pod'),
                                 ('user/Abe/Pellet/us/'+safe_name(selected['archive']),'treasure')]:
            for name,data in archive_files(read(source)).items():
                target=output/directory/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        pod=convert(output/'pod/pot.bmd',output/'pod.mod',True,bake_rigid=True)
        treasure_model=output/'treasure'/safe_name(selected['bmd'])
        item=convert(treasure_model,output/'treasure.mod',True,bake_rigid=True)
        # P1 pellets sit at their bottom, whereas this P2 model's pivot is central.
        item=convert(treasure_model,output/'treasure.mod',True,y_offset=-item['bounds'][1],bake_rigid=True)
        money,weight,capacity=[int(selected[k]) for k in ('money','min','max')]
        # Carry strength may exceed physical slots (e.g. Purple-dependent treasures).
        if not 0<=money<=1000000 or not 1<=weight<=1000 or not 1<=capacity<=96: raise ValueError('Invalid treasure economy')
        (output/'p2-pod.txt').write_text(f'P2_POD_1\n{treasure} {money} {weight} {capacity}\nKochappy {int(corpse["money"])}\n')
        result=dict(schema=1,treasure=selected,corpse=corpse,pod=pod,model=item,source_sha256=hashes,
                    limitations=['Static bind pose; no animation, effects or texture-matrix playback.',
                                 'Independent receipt ledger is not a cave/world save.',
                                 'One selected treasure and native Dwarf corpse scaffold only.'])
        (output/'pod.json').write_text(json.dumps(result,indent=2));return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iso',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--treasure',default='dia_a_red',choices=('dia_a_red','tape_yellow','map01'))
    a=p.parse_args();r=extract(a.iso,a.output,a.treasure)
    print(json.dumps({key:r['treasure'][key] for key in ('name','money','min','max')}))
