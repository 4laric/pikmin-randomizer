"""Private fixed-view material comparison from copied #201 fixture inputs."""
import argparse,json,os,re,subprocess
from pathlib import Path
from scripts import build_pikmin2_fixture as builder
from experimental.pikmin2_frog_arena import prepare

def matched_evidence(text):
 rows=[dict(re.findall(r'(\w+)=([^\s]+)',line)) for line in text.splitlines() if line.startswith('P2_FROG_MATERIAL_COMPARE ')]
 if len(rows)!=4 or {(r.get('kind'),r.get('corrected')) for r in rows}!={('0','0'),('0','1'),('1','0'),('1','1')}:raise ValueError('Missing or duplicate comparison case')
 for r in rows:
  if any(r.get(k)!=v for k,v in {'pose':'wait1_0','scale':'1','yaw':'0','eye':'0,80,500','target':'0,20,0'}.items()) or int(r['x'])!=-75+100*int(r['kind'])+50*int(r['corrected']):raise ValueError('Comparison transforms differ')
 for key in ('ambient','fov','aspect'):
  if any(key not in r for r in rows) or len({r[key] for r in rows})!=1:raise ValueError('Comparison light/projection differs')
 return dict(cases=rows,matched_pose_depth_scale_projection=True,shared_ambient=True,source_lighting_parity=False)


def instrument(text):
 anchor='    if(seen.size()!=wanted.size())std::abort();loadAnimation(banks);'
 draw='    int kind=it->second;int motion=actor->mTekiAnimator->getCurrentMotionIndex();'
 if text.count(anchor)!=1 or text.count(draw)!=1:raise ValueError('Copied family changed')
 text=text.replace('std::map<PelletView*,int> actors;','std::map<PelletView*,int> actors;Shape* comparison[2]={};')
 text=text.replace(anchor,anchor+'''
    for(int k=0;k<2;++k){std::string path="courses/pikmin2room/comparison_"+std::string(ids[k])+".mod";comparison[k]=gameflow.loadShape(path.c_str(),true);if(!comparison[k])std::abort();for(int i=0;i<comparison[k]->mTexAttrCount;++i)if(comparison[k]->mTexAttrList[i].mTexture)comparison[k]->mTexAttrList[i].mTexture->attach();}''')
 diagnostic=r'''
    if(!corpse){Matrix4f view;view.makeLookat(Vector3f(0,80,500),Vector3f(0,20,0),nullptr);
     for(int corrected=0;corrected<2;++corrected){Shape* fixed=corrected?comparison[kind]:animated[kind].at("wait1").front();
      Matrix4f world,modelView;world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),Vector3f(-75+100*kind+50*corrected,0,0));view.multiplyTo(world,modelView);
      fixed->updateAnim(gfx,modelView,nullptr,actor);fixed->drawshape(gfx,*gfx.mCamera,nullptr);
      static bool logged[2][2]={{false,false},{false,false}};if(!logged[kind][corrected]){logged[kind][corrected]=true;std::printf("P2_FROG_MATERIAL_COMPARE kind=%d corrected=%d pose=wait1_0 scale=1 yaw=0 eye=0,80,500 target=0,20,0 x=%d ambient=%u,%u,%u fov=%.4f aspect=%.4f\n",kind,corrected,-75+100*kind+50*corrected,gfx.mAmbientColour.r,gfx.mAmbientColour.g,gfx.mAmbientColour.b,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio);}}
     return true;
    }
'''
 return text.replace(draw,draw+diagnostic)


def build(previous,output):
 previous=previous.resolve();output=output.resolve();output.mkdir(parents=True,exist_ok=False)
 base=json.loads((previous/'baseline/provenance.json').read_text());old=json.loads((previous/'instrumentation.json').read_text())
 headers={p:v for p,v in base['inputs'].items() if Path(p).suffix.lower() in ('.h','.hpp','.inc')};builder.check_snapshot(headers)
 source=previous/'family.cpp';builder.check_snapshot({str(source):old['instrumented'][str(source)]})
 private=output/'family.cpp';private.write_text(instrument(source.read_text()))
 compile=[str(private) if a==str(source) else a for a in old['commands'][0]]
 compile[builder.option_index(compile,'-o')]=str(output/'family.obj');compile[builder.option_index(compile,'-MF')]=str(output/'family.d')
 link=[str(output/'family.obj') if a==str(previous/'family.obj') else a for a in old['commands'][-1]]
 link[builder.option_index(link,'-o')]=str(output/'compare.exe');link=[('-Wl,--out-implib,'+str(output/'compare.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
 objects=[Path(a) for a in link if a.endswith(('.obj','.a')) and not a.startswith('-') and a!=str(output/'family.obj')]
 captured=builder.snapshot(objects+[Path(compile[0]),private]);env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''))
 for label,command in [('compile',compile),('link',link)]:
  code,text=builder.run(command,Path(base['build']),env);(output/(label+'.log')).write_text(text)
  if code:raise RuntimeError(label+' failed')
 builder.check_snapshot(headers);builder.check_snapshot(captured)
 report=dict(status='built',mode='historical copied201 objects plus matching headers; not latest-head build',observed_source=base['observed_source'],headers=headers,inputs=captured,commands=[compile,link],artifacts=builder.snapshot([output/'compare.exe',output/'family.obj']))
 (output/'provenance.json').write_text(json.dumps(report,indent=2));return report


def run(assets,bank,profile,output,exe):
 from experimental.pikmin2_frog_material_profile import POLICY
 from experimental.pikmin2_frog_visual_audit import chunks
 import hashlib
 metadata=json.loads((profile/'frogs.json').read_text()).get('material_profile',{})
 if metadata.get('policy')!=POLICY or metadata.get('source_manifest_sha256')!=hashlib.sha256((bank/'frogs.json').read_bytes()).hexdigest():raise ValueError('Comparison profile/source mismatch')
 for species in ('Frog','MaroFrog'):
  name=f'frog_{species}_wait1_00.mod';before=chunks((bank/species/name).read_bytes());after=chunks((profile/species/name).read_bytes())
  if set(before)!=set(after) or any(before[t]!=after[t] for t in before if t!=48):raise ValueError('Comparison changed nonmaterial bytes')
 stage=prepare(assets,bank,output/'stages');manifest=json.loads((stage/'frog-arena.json').read_text())
 (stage/'frog-positions.txt').write_bytes(''.join(f"{a['generator']} {a['native_type']} {int(i<2)} "+' '.join(map(str,a['position']))+'\n' for i,a in enumerate(manifest['actors'])).encode())
 from experimental.pikmin2_frog_install import plan
 plan(profile,[(201001,'Frog'),(201002,'MaroFrog')])
 room=stage/'assets/dataDir/courses/pikmin2room'
 for species in ('Frog','MaroFrog'):(room/f'comparison_{species}.mod').write_bytes((profile/species/f'frog_{species}_wait1_00.mod').read_bytes())
 env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
 with (stage/'native.log').open('w') as log:
  try:code=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=stage,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
  except subprocess.TimeoutExpired:code='timeout'
 report=dict(exit_code=code,scope='Diagnostic fixed model matrices and pose, unchanged shared frame/light state; not gameplay placement or source lighting parity',assets=builder.snapshot([room/f'comparison_{s}.mod' for s in ('Frog','MaroFrog')]),executable=builder.snapshot([exe]))
 report['comparison']=matched_evidence((stage/'native.log').read_text(errors='replace'))
 (stage/'compare.json').write_text(json.dumps(report,indent=2));print(stage,flush=True);return report

if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);b=sub.add_parser('build');r=sub.add_parser('run')
 for n in ('previous','output'):b.add_argument('--'+n,type=Path,required=True)
 for n in ('assets','bank','profile','output','exe'):r.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 if a.command=='build':build(a.previous,a.output)
 else:run(a.assets,a.bank,a.profile,a.output,a.exe)
