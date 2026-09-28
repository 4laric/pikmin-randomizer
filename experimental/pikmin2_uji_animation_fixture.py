"""Private instrumented Uji renderer plus grounded lifecycle acceptance."""
import argparse,json,os,subprocess
from pathlib import Path
from experimental.pikmin2_uji_grounded_fixture import instrument as room_instrument,stage,validate as lifecycle
from experimental.pikmin2_uji_animation_install import install
from scripts import build_pikmin2_fixture as builder


def instrument_family(text):
    anchor='int kind=it->second.species;Shape* shape=shapes[kind][corpse?1:0];'
    select='shape=animated[kind].at(name).at(timing[kind].at(name).index(phase,corpse));'
    draw='if(!shape)std::abort();shape->updateAnim'
    if any(text.count(s)!=1 for s in (anchor,select,draw)):raise ValueError('Family instrumentation anchor changed')
    text=text.replace(anchor,anchor+'const char* selected="static";size_t selectedIndex=0;')
    text=text.replace(select,'selected=name;selectedIndex=timing[kind].at(name).index(phase,corpse);'+select)
    trace='''static std::set<std::string> observed;std::string key=std::to_string(kind)+":"+std::to_string(int(corpse))+":"+selected+":"+std::to_string(selectedIndex);
    if(observed.insert(key).second)std::printf("P2_UJI_VISUAL species=%s corpse=%d clip=%s pose=%zu native_motion=%d\\n",ids[kind],int(corpse),selected,selectedIndex,actor->mTekiAnimator->getCurrentMotionIndex());
    '''
    return text.replace(draw,trace+draw)


def build(native,build_dir,output,head):
    native=native.resolve();build_dir=build_dir.resolve();output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    room=output/'room.cpp';room.write_text(room_instrument((native/'tools/preview_p2_room.cpp').read_text()))
    record=builder.build_fixture(build_dir,native,room,output/'baseline',head)
    family=native/'pc_port/pc_p2_sheargrub.cpp';private=output/'family.cpp';private.write_text(instrument_family(family.read_text()))
    compile=list(record['commands'][-2]);compile=[str(private) if a==str(room) else a for a in compile]
    compile[builder.option_index(compile,'-o')]=str(output/'family.obj')
    compile[builder.option_index(compile,'-MF')]=str(output/'family.d')
    link=list(record['commands'][-1]);targets=[i for i,a in enumerate(link) if a.endswith('-pc_p2_sheargrub.cpp.obj')]
    if len(targets)!=1:raise ValueError('Expected one private family object')
    link[targets[0]]=str(output/'family.obj');link[builder.option_index(link,'-o')]=str(output/'fixture.exe')
    link=[('-Wl,--out-implib,'+str(output/'fixture.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
    env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''))
    audit=dict(original_family=builder.snapshot([family]),instrumented=builder.snapshot([private]),commands=[compile,link],freshness_checks=[])
    for name,command in [('family-compile',compile),('family-link',link)]:
        code,text=builder.run(command,build_dir,env);(output/(name+'.log')).write_text(text)
        if code:raise RuntimeError(name+' failed')
    builder.require_fresh(Path(record['toolchain']['ninja']['path']),build_dir,audit['freshness_checks'])
    builder.check_snapshot(record['inputs']);builder.check_snapshot(record['fixture_inputs']);builder.check_snapshot(record['configuration_inputs']);builder.check_snapshot(audit['original_family']);builder.check_snapshot(audit['instrumented'])
    if builder.git_state(native)!=record['observed_source']:raise RuntimeError('Native changed during private replacement')
    audit['artifacts']=builder.snapshot([output/'fixture.exe',output/'family.obj']);audit['status']='built'
    (output/'instrumentation.json').write_text(json.dumps(audit,indent=2)+'\n')


def validate(log,animated):
    import re
    result=lifecycle(log)
    rows=re.findall(r'P2_UJI_VISUAL species=(Uji[AB]) corpse=([01]) clip=(\w+) pose=(\d+)',log)
    for species in ('UjiA','UjiB'):
        own=[r for r in rows if r[0]==species]
        if animated:
            if not any(r[1]=='1' and r[2]=='dead' for r in own):raise ValueError('Animated corpse missing')
            if not any(len({r[3] for r in own if r[2]==clip and r[1]=='0'})>=2 for clip in ('appear','move','dead')):raise ValueError('No changing source poses')
        elif not own or any(r[2]!='static' for r in own) or {r[1] for r in own}!={'0','1'}:raise ValueError('Static fallback not observed')
    result.update(animated=animated,visual_samples=len(rows));return result


def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 b=sub.add_parser('build')
 for n in ('native','build-dir','output'):b.add_argument('--'+n,type=Path,required=True)
 b.add_argument('--head',required=True)
 r=sub.add_parser('run')
 for n in ('assets','assembly','pod','content','uji','output','exe','bank'):r.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 if a.command=='build':build(a.native,a.build_dir,a.output,a.head);return
 for animated in (False,True):
  run=stage(a);print(run,flush=True)
  if animated:install(a.bank,run)
  env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
  with (run/'native.log').open('w') as log:res=subprocess.run([str(a.exe.resolve()),'--experimental-pikmin2-room'],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=420)
  if res.returncode:raise RuntimeError('Native failed: '+str(run))
  evidence=validate((run/'native.log').read_text(),animated);(run/'animation-acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n');print(evidence,flush=True)

if __name__=='__main__':main()
