"""Current-source private Bulblax display acceptance and noninteractive local launcher."""
import argparse,json,os,re,struct,subprocess,uuid
from collections import Counter
from pathlib import Path
from scripts import build_pikmin2_fixture as builder
from scripts.preview_pikmin2_room import records,generator,overlay
from experimental.pikmin2_generator_pose import write_position
from experimental.pikmin2_bulblax_visual import install,CONFIG
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial

APP=r'''class DisplayCameraTarget : public Creature {
public:DisplayCameraTarget():Creature(nullptr){mHealth=1;}
 void refresh(Graphics&) override{} void doKill() override{}
};
class RoomApp : public PlugPikiApp {
 int frames=0,ready=0,actors=0,repairs=0;bool enabled=false,hold=false;int enemy=0;std::string mode;
 int pauseTicks=0;std::uint32_t displayId=0;float pausedFrame=0;bool testedPause=false;
 int actorCount(){int count=0;Iterator i(tekiMgr);CI_LOOP(i){if(*i)++count;}return count;}
 void unchanged(){require(actorCount()==actors,"Bulblax display changed Teki count");require(playerState->getCurrParts()==repairs,"Bulblax display changed repairs");require(pc_p2_preview_cargo_count()==0&&!pc_p2_preview_treasure(),"Bulblax display created cargo");}
 void load(){const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_bulblax_visual_setup();gsys->setHeap(heap);unchanged();}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"Bulblax startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(pauseTicks){float frame=-1;require(pc_p2_bulblax_visual_frame(displayId,frame)&&frame==pausedFrame,"retail advanced while paused");
  if(++pauseTicks==10){gameflow.mPauseAll=false;gameflow.mIsUIOverlayActive=true;std::puts("P2_BULBLAX_SIM_PAUSE_ALL_PASS");}
  if(pauseTicks==20){gameflow.mIsUIOverlayActive=false;pauseTicks=0;testedPause=true;std::puts("P2_BULBLAX_SIM_UI_PAUSE_PASS");}else return result;
 }
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;++ready;
 if(ready==1){actors=actorCount();repairs=playerState->getCurrParts();n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
 std::ifstream input("bulblax-runtime-mode.txt");input>>mode;enabled=mode!="disabled";require(mode=="Queen"||mode=="Baby"||mode=="KingChappy"||mode=="disabled","Bulblax runtime mode");std::ifstream holding("bulblax-keep-open.txt");hold=bool(holding);
 int red=0,blue=0,other=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* a=static_cast<Piki*>(*p);if(a->isAlive()){if(a->mColor==Red)++red;else if(a->mColor==Blue)++blue;else++other;}}require(red==5&&blue==5&&other==0,"Bulblax starting5red5blue");
 SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Bulblax family - NONINTERACTIVE SAMPLED DISPLAY (#235)");std::printf("P2_BULBLAX_BASELINE actors=%d cargo=0 repairs=%d red=%d blue=%d\n",actors,repairs,red,blue);
 }
 if(ready==30){
 std::ifstream raw("bulblax-fixture-profile.txt");auto p=p2bulblax::read(raw);require(p.displays.size()==1,"Bulblax single display fixture");auto d=p.displays[0];displayId=d.id;auto c=p.clips[d.clip];enemy=c.enemy;
 float ground=mapMgr->getMinY(d.x,d.z,true);require(std::isfinite(ground)&&std::fabs(ground-d.y)<40,"Bulblax display ground divergence");std::printf("P2_BULBLAX_GROUND id=%u enemy=%d x=%.6f y=%.6f z=%.6f ground=%.6f yaw=%.3f scale=1\n",d.id,enemy,d.x,d.y,d.z,ground,d.yaw);
 require(cameraMgr&&cameraMgr->mCamera,"Bulblax camera missing");auto* target=new DisplayCameraTarget();float height=enemy==30?85.f:enemy==53?50.f:8.f;target->mSRT.t=Vector3f(d.x,d.y+height,d.z);auto* camera=cameraMgr->mCamera;camera->setTarget(target);camera->mControlsEnabled=false;
 PcamMotionInfo info=camera->mTargetMotionInfo;info.mDistance=enemy==30?1100.f:enemy==53?450.f:180.f;info.mFov=40;info.mAngle=35;info.mNaviWatchWeight=0;info.mWatchAdjustment=0;camera->startMotion(info);
 std::printf("P2_BULBLAX_CAMERA target=%.6f,%.6f,%.6f requested_distance=%.1f fov=40 angle=35 camera_only_unregistered=1\n",target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z,info.mDistance);
 if(enabled){std::ifstream src("bulblax-fixture-profile.txt",std::ios::binary);std::ofstream dst("p2-bulblax-visual.txt",std::ios::binary);dst<<src.rdbuf();dst.close();}load();}
 if(ready==80&&pc_p2_bulblax_visual_frame(displayId,pausedFrame)){gameflow.mPauseAll=true;pauseTicks=1;}
 if(ready==82&&testedPause){float frame=-1;require(pc_p2_bulblax_visual_frame(displayId,frame)&&frame!=pausedFrame,"retail did not resume");std::puts("P2_BULBLAX_SIM_RESUME_PASS");}
 if(ready==120)capture("bulblax-pose-a.ppm");
 if(ready==140){capture("bulblax-pose-b.ppm");unchanged();pc_p2_bulblax_visual_reset();float frame=-1;require(!pc_p2_bulblax_visual_frame(displayId,frame),"retail survived reset");std::puts("P2_BULBLAX_RESET_REQUEST");}
 if(ready==145){capture("bulblax-reset.ppm");unchanged();load();std::puts("P2_BULBLAX_RELOAD_REQUEST");}
 if(ready==200){capture("bulblax-reload.ppm");unchanged();std::puts("PASS P2_BULBLAX_DISPLAY_RUNTIME noninteractive unchanged_actors_cargo_repairs");std::fflush(nullptr);if(!hold)std::_Exit(0);}
 std::fflush(stdout);return result;
 }};
'''


def instrument(source):
    start=source.index('class RoomApp : public PlugPikiApp {');end=source.index('int main(',start)
    includes='#include <fstream>\n#include <string>\n#include "pc_p2_bulblax_visual.h"\n#include "pc_p2_bulblax_visual_policy.h"\n#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n'
    return includes+source[:start]+APP+source[end:]


def build(native,build_dir,output,head):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    (output/'tutorial-private.inc').write_text(instrument_tutorial((native/'src/plugPikiColin/newPikiGame.cpp').read_text(encoding='utf-8')),encoding='utf-8')
    room=output/'room.cpp';room.write_text(instrument((native/'tools/preview_p2_room.cpp').read_text(encoding='utf-8'))+'\n#include "tutorial-private.inc"\n',encoding='utf-8')
    return builder.build_fixture(build_dir,native,room,output/'build',head)


def stage(assets,profile,output,mode,retail_sources=None):
    retail_data=None
    if retail_sources is not None:
        from experimental.pikmin2_motion_events import encode
        retail_species='Queen' if mode=='disabled' else mode
        retail_data=encode(Path(retail_sources)/retail_species)
    assets=assets.resolve();source=assets/'dataDir/stages/practice/default.gen';data=source.read_bytes();entries=records(source)
    raw=generator(assets);starts=[m.start() for m in re.finditer(b'    0.0v',raw)];rows=[raw[a:(starts[i+1] if i+1<len(starts) else len(raw))] for i,a in enumerate(starts)]
    template=next(r for r in rows if r[72:76]==b'ikip')
    for i in range(10):
        row=bytearray(template);struct.pack_into('<I',row,8,235100+i);row[16:48]=b'Bulblax5red5blue fixture'.ljust(32,b'\0');write_position(row,[10+i%5*12,30,1890+i//5*12]);struct.pack_into('>I',row,92,1 if i<5 else 0);entries.append(bytes(row))
    data=data[:20]+struct.pack('>I',len(entries))+b''.join(entries)
    run=output.resolve()/uuid.uuid4().hex;run.mkdir(parents=True);empty=data[:20]+struct.pack('>I',0)
    overrides={'dataDir/stages/chal0.ini':(assets/'dataDir/stages/practice.ini').read_bytes(),'dataDir/stages/chal0/default.gen':data,'dataDir/courses/pikmin2room/private-bulblax.txt':b'Noninteractive Bulblax display\n'}
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):overrides.setdefault('dataDir/stages/chal0/'+p.name,empty)
    overlay(assets,run/'assets',overrides);result=install(profile,run,species='Queen' if mode=='disabled' else mode)
    (run/CONFIG).rename(run/'bulblax-fixture-profile.txt');(run/'bulblax-runtime-mode.txt').write_bytes((mode+'\n').encode());(run/'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    original={str(p.relative_to(assets)):builder.sha256(p) for p in (assets/'dataDir/courses/practice').rglob('*') if p.is_file()}
    for rel,digest in original.items():
        if builder.sha256(run/'assets'/rel)!=digest:raise ValueError('Course changed')
    result.update(scene='original P1 Impact Site',noninteractive=True,mode=mode,starting_squad={'red':5,'blue':5},added_teki=0,course_sha256=original)
    if retail_data is not None:
        path=run/f'p2-bulblax-retail-{retail_species}.txt';path.write_bytes(retail_data)
        result['retail_table']={'file':path.name,'sha256':builder.sha256(path)}
    (run/'bulblax-stage.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());return run


def validate(text,code,mode):
    enabled=mode!='disabled';expected={'Queen':30,'Baby':31,'KingChappy':53,'disabled':30}[mode]
    rows=re.findall(r'P2_BULBLAX_VISUAL_DRAW enemy=(\d+) clip=(\w+) pose=(\d+) source_frame=(\d+)',text)
    ready=re.findall(r'P2_BULBLAX_VISUAL_READY id=(\d+) enemy=(\d+) species=(\w+) clip=(\w+) xyz=([^ ]+)',text)
    checks=dict(completion=code==0 and 'PASS P2_BULBLAX_DISPLAY_RUNTIME ' in text,setup=len(ready)==(2 if enabled else 0),draw=bool(rows)==enabled,species=all(int(r[0])==expected for r in rows),sample_changes=(len({r[2] for r in rows})>=2 if enabled else True),reset=text.count('P2_BULBLAX_RESET_REQUEST')==1,reload=text.count('P2_BULBLAX_RELOAD_REQUEST')==1,baseline='red=5 blue=5' in text,ground=text.count('P2_BULBLAX_GROUND ')==1,no_rewards='P2_CARGO_READY' not in text and 'P2_POD_COLLECT' not in text)
    return dict(passed=all(checks.values()),checks=checks,draws=rows,ready=ready,exit_code=code,scope='Display only; no boss actor/gameplay acceptance')


def placement_evidence(text,placements,enabled):
    rows=re.findall(r'P2_BULBLAX_VISUAL_READY id=(\d+) enemy=(\d+) species=(\w+) clip=(\w+) xyz=([^ ]+) yaw=([^ ]+) scale=1 noninteractive=1',text)
    expected=[]
    from experimental.pikmin2_bulblax_assets import SPECIES
    for p in placements:expected.append((str(p['placement_id']),str(SPECIES[p['species']]),p['species'],p['clip'],p['xyz'],p.get('yaw',0)))
    wanted=expected*2 if enabled else []
    if len(rows)!=len(wanted):raise ValueError('Display identity count mismatch')
    for row,want in zip(rows,wanted):
        if row[:4]!=want[:4] or any(abs(float(a)-b)>0.00001 for a,b in zip(row[4].split(','),want[4])) or abs(float(row[5])-want[5])>0.00001:raise ValueError('Display source identity/XYZ/yaw changed')
    return dict(exact_source_identity_xyz_yaw=True,ready_rows=rows)


def retail_evidence(text, mode, clips, source):
    from experimental.pikmin2_motion_events import registry
    expected_id={'Queen':30,'Baby':31,'KingChappy':53,'disabled':30}[mode]
    rows=re.findall(r'P2_BULBLAX_RETAIL_EVENT enemy=(\d+) clip=(\w+) frame=(\d+) type=(\d+)',text)
    allowed={}
    if mode!='disabled':
        authored=dict(registry((Path(source)/mode/'enemyanimmgr.txt').read_bytes()))
        for clip in clips:
            if clip['species']==mode:
                allowed[clip['name']]=set(authored[clip['name']+'.bca'])|{(clip['duration'],1000)}
    return dict(retail_setup=text.count('P2_BULBLAX_RETAIL_READY ')==(0 if mode=='disabled' else 2),
                retail_events=bool(rows)==(mode!='disabled'),
                retail_source_events=all(int(enemy)==expected_id and (int(frame),int(kind)) in allowed.get(name,set()) for enemy,name,frame,kind in rows),
                retail_reload_events=('P2_BULBLAX_RETAIL_EVENT ' in text.split('P2_BULBLAX_RELOAD_REQUEST')[-1])==(mode!='disabled'))


def run(assets,profile,output,exe,retail_sources=None):
    output.mkdir(parents=True,exist_ok=False);report={};env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
    for mode in ('Queen','Baby','KingChappy','disabled'):
        directory=stage(assets,profile,output/mode,mode,retail_sources)
        with (directory/'native.log').open('w') as log:
            try:code=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
            except subprocess.TimeoutExpired:code='timeout'
        text=(directory/'native.log').read_text(errors='replace');e=validate(text,code,mode)
        if retail_sources is not None:
            staged=json.loads((directory/'bulblax-stage.json').read_bytes())
            e['checks'].update(retail_evidence(text,mode,staged['clips'],retail_sources))
            e['checks']['simulation_pause']=all((marker in text)==(mode!='disabled') for marker in ('P2_BULBLAX_SIM_PAUSE_ALL_PASS','P2_BULBLAX_SIM_UI_PAUSE_PASS','P2_BULBLAX_SIM_RESUME_PASS'))
            e['retail_table']=staged['retail_table']
            e['passed']=all(e['checks'].values())
        e['gx_warnings']=[line for line in text.splitlines() if 'GX' in line and 'warning' in line.lower()]
        if e['passed']:e['placement_evidence']=placement_evidence(text,json.loads((directory/'bulblax-stage.json').read_bytes())['placements'],mode!='disabled')
        if e['passed']:
            from PIL import Image
            e['captures']={}
            for name in ('bulblax-pose-a','bulblax-pose-b','bulblax-reset','bulblax-reload'):
                path=directory/(name+'.ppm');Image.open(path).save(directory/(name+'.png'));e['captures'][name]=builder.sha256(path)
        e.update(directory=str(directory),exe=builder.snapshot([exe]));report[mode]=e;(output/'result.json').write_text(json.dumps(report,indent=2));print(mode,e['passed'],directory,flush=True)
        if not e['passed']:raise RuntimeError('Bulblax runtime failed; evidence preserved')
    baseline=Counter(report['disabled']['gx_warnings'])
    for e in report.values():
        e['new_gx_warnings']=dict(Counter(e['gx_warnings'])-baseline)
        e['checks']['gx_matches_disabled']=not e['new_gx_warnings'];e['passed']=all(e['checks'].values())
    (output/'result.json').write_text(json.dumps(report,indent=2))
    return report


def play(assets,profile,output,exe,mode):
    directory=stage(assets,profile,output,mode);(directory/'bulblax-keep-open.txt').write_bytes(b'Noninteractive display; close window to exit.\n')
    print('Noninteractive sampled Bulblax display. No boss AI, collision or rewards.\n'+str(directory),flush=True)
    env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
    with (directory/'native.log').open('w') as log:return subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT).returncode

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);b=sub.add_parser('build');r=sub.add_parser('run');live=sub.add_parser('play')
    for key in ('native','build-dir','output'):b.add_argument('--'+key,type=Path,required=True)
    b.add_argument('--head',required=True)
    for parser in (r,live):
        for key in ('assets','profile','output','exe'):parser.add_argument('--'+key,type=Path,required=True)
    r.add_argument('--retail-sources',type=Path)
    live.add_argument('--mode',choices=('Queen','Baby','KingChappy'),default='Queen');a=p.parse_args()
    if a.command=='build':build(a.native.resolve(),a.build_dir.resolve(),a.output,a.head)
    elif a.command=='run':run(a.assets,a.profile,a.output,a.exe,a.retail_sources)
    else:raise SystemExit(play(a.assets,a.profile,a.output,a.exe,a.mode))
