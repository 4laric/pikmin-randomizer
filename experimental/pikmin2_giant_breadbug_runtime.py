"""Private Giant/nest visual acceptance; no gameplay actor or collision."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import uuid
from scripts import build_pikmin2_fixture as builder
from scripts.preview_pikmin2_room import records, generator, overlay
from experimental.pikmin2_giant_breadbug_visual import install, CONFIG
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
from experimental.pikmin2_generator_pose import write_position

APP=r'''class RoomApp : public PlugPikiApp {
 int frames=0,ready=0,actors=0,repairs=0;bool enabled=false,hold=false;std::string kind;
 int actorCount(){int count=0;Iterator i(tekiMgr);CI_LOOP(i){if(*i)++count;}return count;}
 void unchanged(){require(actorCount()==actors,"Giant display changed actor count");require(playerState->getCurrParts()==repairs,"Giant display changed repairs");require(pc_p2_preview_cargo_count()==0&&!pc_p2_preview_treasure(),"Giant display created cargo");}
 void load(){const int heap=gsys->setHeap(SYSHEAP_App);pc_p2_giant_breadbug_visual_setup();gsys->setHeap(heap);unchanged();}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000||hold,"Giant startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++ready;
 if(ready==1){actors=actorCount();repairs=playerState->getCurrParts();n->mKontroller=new FixtureController();for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
 std::ifstream mode("giant-runtime-mode.txt");mode>>kind;enabled=kind!="disabled";require(kind=="wait"||kind=="move"||kind=="nest"||kind=="disabled","Giant mode");std::ifstream holding("giant-keep-open.txt");hold=bool(holding);
 SDL_SetWindowTitle(SDL_GL_GetCurrentWindow(),"Giant Breadbug / nest - NONINTERACTIVE VISUAL DISPLAY (#229)");
 std::printf("P2_GIANT_BASELINE actors=%d cargo=%d repairs=%d\n",actors,pc_p2_preview_cargo_count(),repairs);}
 if(ready==30){
 if(enabled){std::ifstream source("giant-fixture-profile.txt");std::string a,b,c;std::getline(source,a);std::getline(source,b);std::getline(source,c);require(!c.empty(),"Giant profile source");
 float x=n->mSRT.t.x-55,z=n->mSRT.t.z+60,y=mapMgr->getMinY(x,z,true);require(std::isfinite(y)&&std::fabs(y-n->mSRT.t.y)<100,"Giant unreasonable ground");
 std::ofstream cfg("p2-giant-breadbug-visual.txt",std::ios::binary);cfg<<a<<'\n'<<b<<'\n'<<c<<"\n1\n229001 "<<kind<<' '<<x<<' '<<y<<' '<<z<<" 0\n";cfg.close();
 std::printf("P2_GIANT_GROUND id=229001 kind=%s x=%.6f y=%.6f z=%.6f yaw=0 scale=1\n",kind.c_str(),x,y,z);}
 load();}
 if(ready==60){capture("giant-pose-a.ppm");SDL_Delay(450);}
 if(ready==62){capture("giant-pose-b.ppm");unchanged();pc_p2_giant_breadbug_visual_reset();std::puts("P2_GIANT_RESET_REQUEST");}
 if(ready==65){capture("giant-reset.ppm");unchanged();load();std::puts("P2_GIANT_RELOAD_REQUEST");}
 if(ready==90){capture("giant-reload.ppm");unchanged();std::puts("PASS P2_GIANT_DISPLAY_RUNTIME noninteractive unchanged_actors_cargo_repairs");std::fflush(nullptr);if(!hold)std::_Exit(0);}
 std::fflush(stdout);return result;
 }};
'''


def instrument(source):
    start=source.index('class RoomApp : public PlugPikiApp {');end=source.index('int main(',start)
    return '#include <fstream>\n#include <string>\n#include "pc_p2_giant_breadbug_visual.h"\n'+source[:start]+APP+source[end:]


def build(native,build_dir,output,head):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    tutorial=output/'tutorial-private.inc'
    tutorial.write_text(instrument_tutorial((native/'src/plugPikiColin/newPikiGame.cpp').read_text(encoding='utf-8')),encoding='utf-8')
    room=output/'room.cpp'
    room.write_text(instrument((native/'tools/preview_p2_room.cpp').read_text(encoding='utf-8'))+'\n#include "tutorial-private.inc"\n',encoding='utf-8')
    return builder.build_fixture(build_dir,native,room,output/'build',head)


def stage(assets,profile,output,mode):
    if mode not in ('wait','move','nest','disabled'):raise ValueError('Invalid runtime mode')
    assets=assets.resolve();source=assets/'dataDir/stages/practice/default.gen';data=source.read_bytes();entries=records(source)
    # Add ordinary Reds solely to avoid extinction dialog in the display arena.
    raw=generator(assets);starts=[m.start() for m in re.finditer(b'    0.0v',raw)]
    rows=[raw[a:(starts[i+1] if i+1<len(starts) else len(raw))] for i,a in enumerate(starts)]
    template=next(r for r in rows if r[72:76]==b'ikip')
    for i in range(20):
        r=bytearray(template);struct.pack_into('<I',r,8,229100+i);r[16:48]=b'Giant visual arena Red'.ljust(32,b'\0');write_position(r,[10+i%5*12,30,1890+i//5*12]);entries.append(bytes(r))
    data=data[:20]+struct.pack('>I',len(entries))+b''.join(entries)
    run=output.resolve()/uuid.uuid4().hex;run.mkdir(parents=True)
    empty=data[:20]+struct.pack('>I',0)
    overrides={'dataDir/stages/chal0.ini':(assets/'dataDir/stages/practice.ini').read_bytes(),'dataDir/stages/chal0/default.gen':data,'dataDir/courses/pikmin2room/private-giant.txt':b'Noninteractive Giant display\n'}
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):overrides.setdefault('dataDir/stages/chal0/'+p.name,empty)
    overlay(assets,run/'assets',overrides);install(profile,run)
    (run/CONFIG).rename(run/'giant-fixture-profile.txt');(run/'giant-runtime-mode.txt').write_bytes((mode+'\n').encode());(run/'p2-cargo-free.txt').write_bytes(b'P2_CARGO_FREE_1\n')
    original={str(p.relative_to(assets)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (assets/'dataDir/courses/practice').rglob('*') if p.is_file()}
    for rel,digest in original.items():
        if hashlib.sha256((run/'assets'/rel).read_bytes()).hexdigest()!=digest:raise ValueError('Course changed')
    manifest=dict(scene='original P1 Impact Site',noninteractive=True,mode=mode,display_placement='Ground sampled near captain after startup; actual XYZ in native log',added_teki=0,added_ordinary_reds=20,course=original)
    (run/'giant-stage.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode());return run


def validate(text,code,mode):
    ready=text.count('P2_GIANT_BREADBUG_VISUAL_READY ');draw=text.count('P2_GIANT_BREADBUG_VISUAL_DRAW ')
    disabled=mode=='disabled'
    checks=dict(completion=code==0 and 'PASS P2_GIANT_DISPLAY_RUNTIME ' in text,
                setup=ready==(0 if disabled else 2),draw=draw==(0 if disabled else 2),
                reset=text.count('P2_GIANT_RESET_REQUEST')==1,reload=text.count('P2_GIANT_RELOAD_REQUEST')==1,
                ground=text.count('P2_GIANT_GROUND ')==(0 if disabled else 1),
                no_small_profile='P2_BREADBUG_VISUAL_READY ' not in text,
                no_rewards='P2_POD_COLLECT' not in text and 'P2_CARGO_READY' not in text)
    return dict(passed=all(checks.values()),checks=checks,exit_code=code,scope='Noninteractive display/reset, no actor or gameplay acceptance')


def run(assets,profile,output,exe):
    output.mkdir(parents=True,exist_ok=False);report={};env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
    for mode in ('wait','move','nest','disabled'):
        directory=stage(assets,profile,output/mode,mode)
        with (directory/'native.log').open('w') as log:
            try:code=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150).returncode
            except subprocess.TimeoutExpired:code='timeout'
        evidence=validate((directory/'native.log').read_text(errors='replace'),code,mode)
        if evidence['passed']:
            from PIL import Image
            captures={}
            for name in ('giant-pose-a','giant-pose-b','giant-reset','giant-reload'):
                path=directory/(name+'.ppm');image=Image.open(path);image.save(directory/(name+'.png'));captures[name]=builder.sha256(path)
            evidence['captures']=captures
        evidence['directory']=str(directory);evidence['exe']=builder.snapshot([exe]);report[mode]=evidence
        (output/'result.json').write_text(json.dumps(report,indent=2));print(mode,evidence['passed'],directory,flush=True)
        if not evidence['passed']:raise RuntimeError('Giant runtime failed; see preserved evidence')
    return report

def play(assets,profile,output,exe,mode):
    directory=stage(assets,profile,output,mode)
    (directory/'giant-keep-open.txt').write_bytes(b'Noninteractive visual display; close game window to exit.\n')
    print('Noninteractive Giant/nest display. Models do not have AI, collision or rewards.',flush=True)
    print('Disposable stage: '+str(directory),flush=True)
    env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy')
    with (directory/'native.log').open('w') as log:
        return subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,env=env,stdout=log,stderr=subprocess.STDOUT).returncode


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True);b=sub.add_parser('build');r=sub.add_parser('run');live=sub.add_parser('play')
    for key in ('native','build-dir','output'):b.add_argument('--'+key,type=Path,required=True)
    b.add_argument('--head',required=True)
    for key in ('assets','profile','output','exe'):r.add_argument('--'+key,type=Path,required=True)
    for key in ('assets','profile','output','exe'):live.add_argument('--'+key,type=Path,required=True)
    live.add_argument('--mode',choices=('wait','move','nest'),default='wait')
    a=p.parse_args()
    if a.command=='build':build(a.native.resolve(),a.build_dir.resolve(),a.output,a.head)
    elif a.command=='run':run(a.assets,a.profile,a.output,a.exe)
    else:raise SystemExit(play(a.assets,a.profile,a.output,a.exe,a.mode))
