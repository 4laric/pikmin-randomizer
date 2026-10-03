from pathlib import Path
import sys, struct, json, hashlib
import argparse
cli=argparse.ArgumentParser(description='Stage a private legal-asset Pelplant runtime arena; no game launch.')
for name in ('randomizer-root','legal-assets','baseline','generator-parser','pack','output'):
 cli.add_argument('--'+name,required=True,type=Path)
args=cli.parse_args()
root=args.randomizer_root.resolve()
sys.path.insert(0,str(root));sys.path.insert(0,str(args.generator_parser.resolve().parent))
import p1_challenge_gen_record_thinner as parser
from scripts.preview_pikmin2_room import overlay
legal=args.legal_assets.resolve()
baseline=args.baseline.resolve()
raw=baseline.read_bytes();head,rows=parser.parse_gen(raw)
entries=[v['bytes'] for v in rows];pikis=[v for v in entries if v[72:76]==b'ikip']
assert len(pikis)==20
assert all(struct.unpack_from('>I',v,84)[0]==2 and struct.unpack_from('>I',v,92)[0]==1 for v in pikis)
goals=[v for v in entries if v[72:76]==b'meti' and v[16:48].split(b'\0')[0] in (b'red goal',b'ufo goal')]
assert len(goals)==2, [(v[16:48],v[72:76]) for v in entries]
palm=bytearray(next(v for v in entries if v[72:76]==b'iket' and v[80]==7))
start=palm.index(b'nota0.0v',80);off=palm.index(b'p00\x04',start)+4
struct.pack_into('>I',palm,off,0)
selected=goals+pikis+[bytes(palm)]
data=raw[:20]+struct.pack('>I',len(selected))+b''.join(selected)
_,parsed=parser.parse_gen(data);assert len(parsed)==len(selected)
stage=(legal/'dataDir/stages/stage1.ini').read_bytes()
# PlayerState iterates STAGE_COUNT StageInfo nodes without a null guard.
# Preserve the retail list and change only the fixture's first course.
stage_list=(legal/'dataDir/stages/stages.ini').read_bytes()
start=stage_list.index(b'new_map'); begin=stage_list.index(b'{',start)
depth=1; end=begin+1
while depth:
 if stage_list[end]==123:depth+=1
 elif stage_list[end]==125:depth-=1
 end+=1
import re
assert [int(v) for v in re.findall(rb'^\s*id\s+(\d+)',stage_list,re.M)][:5]==list(range(5))
stage_list=stage_list[:start]+b'new_map visible { name "Pelplant fixture on legal P1 forest" id 0 file stages/p2_tutorial.ini generator { } }'+stage_list[end:]
empty=b'1.0v'+struct.pack('>4fI',*head['navi'],head['direction'],0)
pack=args.pack.resolve();dest=args.output.resolve()
assert not dest.is_relative_to(legal),'output must remain outside legal assets'
dest.mkdir(exist_ok=False)
overrides={
 'dataDir/stages/stages.ini':stage_list,
 'dataDir/stages/p2_tutorial.ini':stage,
 'dataDir/stages/p2_tutorial/default.gen':data,
 'dataDir/stages/p2_tutorial/plants.gen':empty}
overrides.update({str(f.relative_to(pack/'assets')).replace('\\','/'):f.read_bytes() for f in (pack/'assets').rglob('*') if f.is_file()})
overlay(legal,dest/'assets',overrides)
for f in pack.glob('*.txt'):(dest/f.name).write_bytes(f.read_bytes())
receipt={'legal_assets':str(legal),'source_baseline_sha256':hashlib.sha256(raw).hexdigest(),
 'arena_generator_sha256':hashlib.sha256(data).hexdigest(),'literal_pikmin_records':20,
 'formation':2,'native_color':1,'physical_pack_sha256':hashlib.sha256((pack/'sha256.json').read_bytes()).hexdigest(),
 'P1_Palm_preload_count':0,'source0_original_positions':False,
 'retail_stage_list_preserved':True,'native_stage_ids':[0,1,2,3,4],
 'stages_ini_sha256':hashlib.sha256(stage_list).hexdigest(),
 'stage_geometry':'legal P1 forest, engineering fixture only',
 'fixture_placements':{'one':[-460,2155],'five':[-600,2155],'ten':[-700,2155]},
 'ordinary_Onion':True,'Pod':False,
 'launch_arguments':['--experimental-pikmin2-surface','tutorial'],
 'environment':{'PIKMIN_RANDOMIZER_MANUAL_START':'1','PIKMIN_P2_ROOM_WINDOW':'960x540'},
 'runtime_gameplay':False}
(dest/'arena.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
