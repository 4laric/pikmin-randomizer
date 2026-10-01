from pathlib import Path
import argparse,hashlib,json,sys,struct,re
p=argparse.ArgumentParser(description='Stage fresh bounded two-captain scene reentry arenas; never launches a game.')
p.add_argument('--root',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--treasure-model',type=Path,required=True)
a=p.parse_args();sys.path.insert(0,str(a.root/'scripts'))
from preview_pikmin2_room import overlay,generator
assert not a.run_dir.exists(),'Use a new arena for each attempt'
gen=bytearray(generator(a.assets));struct.pack_into('>4f',gen,4,-290.3365,0,1505.612,90)
for i in [m.start() for m in re.finditer(b'    0.0v',gen)]:
 x,y,z,*off=struct.unpack_from('>6f',gen,i+48)
 ship=gen[i+16:i+48].startswith(b'preview ship')
 struct.pack_into('>6f',gen,i+48,-950 if ship else x-200,y,2000 if ship else z+1700,*off)
empty=b'1.0v'+struct.pack('>4fI',-290.3365,0,1505.612,90,0)
overrides={'dataDir/stages/chal0/default.gen':bytes(gen),'dataDir/courses/pikmin2room/treasure.mod':a.treasure_model.read_bytes()}
for f in (a.assets/'dataDir/stages/chal0').glob('*.gen'):overrides.setdefault('dataDir/stages/chal0/'+f.name,empty)
a.run_dir.mkdir(parents=True);overlay(a.assets,a.run_dir/'assets',overrides)
(a.run_dir/'adoption-inputs.json').write_text(json.dumps(dict(scope='P1 practice terrain, scripted real scene transition; no native save or cave claim',spawn=[-290.3365,0,1505.612],assets=str(a.assets),live_generator_pikmin=20,overrides={k:hashlib.sha256(v).hexdigest() for k,v in overrides.items()}),indent=2),encoding='utf-8')
print(a.run_dir)
