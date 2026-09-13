"""Actual beetle registry acceptance; source FSM is explicitly outside scope."""
import argparse,json,re,os,subprocess,hashlib
from pathlib import Path
from experimental import pikmin2_kogane_runtime as prior
from experimental.pikmin2_kogane_native import emit

_base_instrument=prior.instrument

def instrument(source):
 s=_base_instrument(source);s='#include "pc_p2_kogane.h"\n'+s
 marker='   Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();'
 addition=r'''   int expected=id==219001?9:id==219002?10:id==219003?11:-1;
   require(pc_p2_kogane_source_id(actor)==expected,"typed beetle source ID");
   require((pc_p2_kogane_name(actor)!=nullptr)==(expected>=0),"ordinary control name fallback");
   std::printf("P2_KOGANE_ID id=%u source_id=%d control=%d\n",id,pc_p2_kogane_source_id(actor),int(expected<0));
'''
 if s.count(marker)!=1:raise ValueError('Prior fixture changed')
 s=s.replace(marker,addition+marker)
 s=s.replace(' if(observed==300){',r''' if(observed==1){Vector3f p(-50,30,1750);p.y=mapMgr->getMinY(p.x,p.z,true);n->resetPosition(p);}
 if(observed==60)capture("kogane-binding.ppm");
 if(observed==300){''')
 return s.replace('behavior=unregistered','behavior=P1_visual_binding_source_FSM_pending')

def build(native,build_dir,output,head):
 old=prior.instrument;prior.instrument=instrument
 try:
  prior.build(native,build_dir,output,head)
 finally:prior.instrument=old

def validate(text,code):
 rows=[tuple(map(int,m)) for m in re.findall(r'P2_KOGANE_ID id=(\d+) source_id=(-?\d+) control=(\d+)',text)]
 checks=dict(completed=code==0 and 'PASS P2_KOGANE_RUNTIME' in text,typed=rows==[(219001,9,0),(219002,10,0),(219003,11,0),(219004,-1,1)],draw='P2_KOGANE_DRAW corpse=0' in text)
 return dict(passed=all(checks.values()),checks=checks,scope='Native source-ID registration and visual binding; P1 host AI retained',unmeasured=['source FSM','flips/drops/gas','material fidelity','manager reset/reentry'])

def run(assets,bank,output,exe):
 stage=prior.prepare(assets,bank,output/'stages');m=json.loads((stage/'arena.json').read_text())
 emit(bank,stage,m,hashlib.sha256((bank/'beetles.json').read_bytes()).hexdigest())
 (stage/'kogane-positions.txt').write_bytes(''.join(str(a['generator'])+' '+' '.join(map(str,a['expected_xyz']))+'\n' for a in m['actors']).encode())
 env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
 with (stage/'native.log').open('w') as log:
  try:code=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90).returncode
  except subprocess.TimeoutExpired:code='timeout'
 r=validate((stage/'native.log').read_text(errors='replace'),code);r.update(stage=str(stage),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),exit_code=code);(stage/'binding-evidence.json').write_text(json.dumps(r,indent=2));return r
if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);b=sub.add_parser('build');r=sub.add_parser('run')
 for name in ('native','build-dir','output'):b.add_argument('--'+name,type=Path,required=True)
 b.add_argument('--head',required=True)
 for name in ('assets','bank','output','exe'):r.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args()
 if a.command=='build':build(a.native,a.build_dir,a.output,a.head)
 else:print(json.dumps(run(a.assets,a.bank,a.output,a.exe)))
