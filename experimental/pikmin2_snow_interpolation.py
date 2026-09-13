"""Private Snow interpolation lifecycle and populated-scene fixture (#327)."""
from pathlib import Path
from experimental.pikmin2_snow_lifecycle import instrument as lifecycle
from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
from scripts import build_pikmin2_fixture as builder

PROBE=r'''#include "pc_p2_pose_bank.h"
#include "pc_p2_enemy.h"
#include <chrono>
#include "timing/pc_tick_profiler.h"
#include "Pcam/Camera.h"
#include "Pcam/CameraManager.h"
#include <fstream>
#include <algorithm>
static std::map<std::string,std::vector<p2pose::Baked>> probeBank;
static unsigned geometryChecks=0;
static void verifySnow(BTeki* enemy){
 p2pose::Pose actual;std::string clip;float frame;bool corpse;
 if(!pc_p2_snow_geometry(enemy,actual,clip,frame,corpse))return;
 if(probeBank.empty()){
  std::ifstream manifest("p2-snow.txt");std::vector<p2animation::Clip> clips;require(p2animation::parse(manifest,clips),"probe manifest");
  for(const auto& c:clips)for(int i=0;i<c.count;++i){char path[160];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/snow_%s_%02d.mod",c.name.c_str(),i);
   std::ifstream file(path,std::ios::binary);std::vector<unsigned char> raw((std::istreambuf_iterator<char>(file)),{});p2pose::Baked pose;require(p2pose::decodeBaked(raw,pose),"probe bank decode");probeBank[c.name].push_back(std::move(pose));}
 }
 std::ifstream manifest("p2-snow.txt");std::vector<p2animation::Clip> clips;require(p2animation::parse(manifest,clips),"probe timing");
 const p2animation::Clip* timing=nullptr;for(const auto& c:clips)if(c.name==clip)timing=&c;require(timing,"probe clip");
 p2pose::Interval span;require(p2pose::bracket(timing->frames,frame,span),"probe bracket");p2pose::Pose expected;
 require(p2pose::blend(probeBank[clip][span.left].pose,probeBank[clip][span.right].pose,span.weight,expected),"probe blend");
 if(corpse)require(frame==timing->frames.back()&&clip=="dead","corpse did not hold final pose");
 require(actual.positions.size()==expected.positions.size()&&actual.normals.size()==expected.normals.size(),"probe sizes");
 for(bool normal:{false,true}){const auto& a=normal?actual.normals:actual.positions;const auto& e=normal?expected.normals:expected.positions;
  for(size_t i=0;i<a.size();++i)require(std::fabs(a[i].x-e[i].x)<.0002f&&std::fabs(a[i].y-e[i].y)<.0002f&&std::fabs(a[i].z-e[i].z)<.0002f,"actor geometry differs");}
 ++geometryChecks;
}
static double lastIdleMs=0;
static bool profileSnow(Navi* n){
 static bool enabled=bool(std::ifstream("p2-snow-profile.txt"));if(!enabled)return false;
 static int frame=0;static std::vector<double> times;static bool interpolated=bool(std::ifstream("p2-snow-interpolation.txt"));
 if(++frame==1){n->mKontroller=new FixtureController();times.reserve(600);for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);}
 if(frame==1){require(cameraMgr&&cameraMgr->mCamera,"profile camera");auto* c=cameraMgr->mCamera;c->mControlsEnabled=false;PcamMotionInfo info=c->mTargetMotionInfo;info.mDistance=1100;info.mFov=55;info.mAngle=60;c->startMotion(info);}
 // Controlled populated-scene microbenchmark: preserve separated placements.
 // Native AI and rendering run, but free roaming/combat is tested separately.
 static std::map<Creature*,Vector3f> placements;
 if(frame==1){Iterator p(pikiMgr);CI_LOOP(p){auto* actor=static_cast<Piki*>(*p);placements.emplace(actor,actor->mSRT.t);}
  Iterator e(tekiMgr);CI_LOOP(e){auto* actor=static_cast<Teki*>(*e);placements.emplace(actor,actor->mSRT.t);}}
 for(const auto& entry:placements){entry.first->mSRT.t=entry.second;entry.first->mVelocity.set(0,0,0);entry.first->mTargetVelocity.set(0,0,0);}
 if(frame==120){capture("snow-profile-start.ppm");pc_tick_profiler_reset();}
 if(frame==120||frame==720){int pikmin=0,snow=0,ordinary=0;Iterator p(pikiMgr);CI_LOOP(p){if(static_cast<Piki*>(*p)->isAlive())++pikmin;}
  Iterator e(tekiMgr);CI_LOOP(e){auto* t=static_cast<Teki*>(*e);if(!t->isAlive())continue;if(pc_p2_enemy_name(t))++snow;else ++ordinary;}
  std::printf("P2_SNOW_PROFILE_COUNTS frame=%d pikmin=%d snow=%d ordinary=%d\n",frame,pikmin,snow,ordinary);
  require(pikmin==100&&snow==4&&ordinary==4,"populated scene changed population");
 }
 if(frame>120)times.push_back(lastIdleMs);
 if(frame==720){
  std::ofstream stats("tick-stats.json");stats<<"{";bool comma=false;
  for(auto region:{kPcTickUpdate,kPcTickRenderAll,kPcTickDoneRender,kPcTickWhole}){auto v=pc_tick_profiler_stats(region,33.333);require(v.samples==600,"profile sample count");
   if(comma)stats<<",";comma=true;stats<<"\""<<pc_tick_region_name(region)<<"\":{\"samples\":"<<v.samples<<",\"mean_ms\":"<<v.mean<<",\"median_ms\":"<<v.median<<",\"p95_ms\":"<<v.p95<<",\"p99_ms\":"<<v.p99<<",\"worst_ms\":"<<v.worst<<",\"over_33ms\":"<<v.overBudget<<"}";}
  stats<<"}";stats.close();capture("snow-profile.ppm");std::ofstream csv("frame-times.csv");csv<<"idle_ms\n";for(auto t:times)csv<<t<<'\n';csv.close();
  std::puts("PASS P2_SNOW_PROFILE samples=600");std::fflush(nullptr);std::_Exit(0);}
 return true;
}
'''

def build(native,build_dir,output,head,*,probe=None):
 output=output.resolve();output.mkdir(parents=True,exist_ok=False)
 source=lifecycle((native/'tools/preview_p2_room.cpp').read_text())
 # Helper uses fixture-local require/capture/controller declarations.
 at=source.index('class RoomApp : public PlugPikiApp {')
 source=source[:at]+(PROBE if probe is None else probe)+source[at:]
 source=source.replace('int result=PlugPikiApp::idle();require(++frames', 'auto idleStart=std::chrono::steady_clock::now();int result=PlugPikiApp::idle();lastIdleMs=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-idleStart).count();require(++frames')
 source=source.replace('Navi* n=naviMgr->getNavi();if(!n ||', 'Navi* n=naviMgr->getNavi();if(n && profileSnow(n))return result;if(!n ||')
 source=source.replace('if(snowRenderFixture(n))return result;', 'if(enemy && phase>=3 && phase<=6 && ticks%15==0)verifySnow(enemy);\n        if(snowRenderFixture(n))return result;')
 source=source.replace('const int credited=pc_p2_preview_pokos();',"""std::printf("P2_SNOW_GEOMETRY_CHECKS count=%u\\n",geometryChecks);
                if(std::ifstream("p2-snow-interpolation.txt")){require(geometryChecks>5,"no geometry validation");p2pose::Pose absent;std::string clip;float frame;bool carried;pc_p2_snow_forget(enemy);require(!pc_p2_snow_geometry(enemy,absent,clip,frame,carried),"forgotten actor still bound");pc_p2_snow_reset();require(!pc_p2_snow_geometry(enemy,absent,clip,frame,carried),"reset actor still bound");}
                const int credited=pc_p2_preview_pokos();""")
 (output/'tutorial-private.inc').write_text(instrument_tutorial((native/'src/plugPikiColin/newPikiGame.cpp').read_text()))
 (output/'room.cpp').write_text('#include "pc_p2_animation.h"\n'+source+'\n#include "tutorial-private.inc"\n')
 return builder.build_fixture(build_dir,native,output/'room.cpp',output/'build',head)


def stage_profile(assets,converted,pod,snow,output):
 import struct
 from scripts.preview_pikmin2_room import records
 from experimental.pikmin2_snow_lifecycle import prepare
 from experimental.pikmin2_enemy import install
 run=prepare(assets,converted,pod,snow,output)
 stage=run/'assets/dataDir/stages/chal0.ini';stage.write_bytes(stage.read_bytes().replace(b'navi_start -85.0 0.0',b'navi_start -200.0 140.0'))
 path=run/'assets/dataDir/stages/chal0/default.gen';raw=path.read_bytes();rows=records(path)
 piki=next(r for r in rows if r[72:76]==b'ikip');enemy=next(r for r in rows if r[72:76]==b'iket')
 result=[r for r in rows if r[72:76] not in (b'ikip',b'iket')]
 def add(template,identity,x,z,kind=None):
  row=bytearray(template);struct.pack_into('<I',row,8,identity);struct.pack_into('>6f',row,48,x,0,z,0,0,0)
  if kind is not None:row[80]=kind
  result.append(bytes(row))
 for i in range(100):add(piki,327000+i,-220+i%10*5,120+i//10*5)
 ids=[]
 for i in range(8):
  identity=327200+i;add(enemy,identity,100+i%4*42,-220+i//4*65,3 if i<4 else 4 if i<6 else 0)
  if i<4:ids.append(identity)
 path.write_bytes(raw[:20]+struct.pack('>I',len(result))+b''.join(result))
 install(snow,run,ids)
 (run/'p2-snow-profile.txt').write_text('100 Reds, four Snow, two native Bulborbs, two native Wollywogs.\n')
 return run


def execute(exe,run,*,profile=False,timeout=180):
 import ctypes,json,os,subprocess,time,hashlib
 if (run/'native.log').exists() or (run/'result.json').exists():raise ValueError('Run must be fresh')
 class Memory(ctypes.Structure):
  _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(n,ctypes.c_size_t) for n in ['peak_ws','ws','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile','private']]
 def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
 env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy',PIKMIN_TICK_STATS='1' if profile else '0')
 expected=sha(exe);peak_ws=peak_private=0;started=time.monotonic()
 with (run/'native.log').open('w') as log:
  process=subprocess.Popen([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   while process.poll() is None:
    mem=Memory();mem.cb=ctypes.sizeof(mem)
    if ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(int(process._handle)),ctypes.byref(mem),mem.cb):
     peak_ws=max(peak_ws,mem.peak_ws);peak_private=max(peak_private,mem.private)
    if time.monotonic()-started>timeout:raise TimeoutError('Native fixture timed out')
    time.sleep(.2)
  except BaseException:
   process.kill();process.wait();raise
 text=(run/'native.log').read_text(errors='replace')
 report=dict(exit=process.returncode,exe_sha256=expected,exe_unchanged=sha(exe)==expected,elapsed_seconds=time.monotonic()-started,peak_working_set_bytes=peak_ws,peak_private_bytes=peak_private)
 if profile:
  report['passed']=process.returncode==0 and 'PASS P2_SNOW_PROFILE samples=600' in text
  if report['passed']:report['timing']=json.loads((run/'tick-stats.json').read_text())
 else:
  from experimental.pikmin2_snow_lifecycle import evidence
  ledger=run/'p2-economy.txt'
  report['lifecycle']=evidence(text,process.returncode,ledger.read_text() if ledger.exists() else None,expected,expected)
  report['passed']=report['lifecycle']['passed']
 report['passed']=report['passed'] and report['exe_unchanged']
 (run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 return report


if __name__=='__main__':
 import argparse,json
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
 b=sub.add_parser('build')
 for name in ['native','build-dir','output']:b.add_argument('--'+name,type=Path,required=True)
 b.add_argument('--head',required=True)
 r=sub.add_parser('run')
 for name in ['assets','converted','pod','snow','exe','output']:r.add_argument('--'+name,type=Path,required=True)
 r.add_argument('--profile',action='store_true');r.add_argument('--interpolate',action='store_true')
 args=p.parse_args()
 if args.command=='build':build(args.native.resolve(),args.build_dir.resolve(),args.output,args.head)
 else:
  from experimental.pikmin2_snow_lifecycle import prepare
  args.output.mkdir(parents=True,exist_ok=False)
  run=(stage_profile if args.profile else prepare)(args.assets.resolve(),args.converted.resolve(),args.pod.resolve(),args.snow.resolve(),args.output/'stage')
  if args.interpolate:(run/'p2-snow-interpolation.txt').write_text('P2_SNOW_INTERPOLATION_1\n')
  (args.output/'run.txt').write_text(str(run)+'\n')
  report=execute(args.exe.resolve(),run,profile=args.profile);print(json.dumps(report,indent=2))
  if not report['passed']:raise SystemExit(1)
