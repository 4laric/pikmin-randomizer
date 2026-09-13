"""Reusable non-invincible lifecycle fixture for P2 registered proxies (#397).

Owned by the lifecycle/acceptance lane. It stages a family arena with the
current starting-squad overlay, frames the engine camera on a registered proxy
so its P1-proxy AI actually updates, asserts the target is not carrying
``TEKI_OPTION_INVINCIBLE``, drives the source damage receiver with repeated
Navi ``InteractAttack`` hits until death, then forces the scene's own
``Generator`` to respawn the same generator ID and re-runs the family
registration so cleanup/re-entry can be observed.

This is deliberately a **proxy** lifecycle harness: it proves the P1 host's
death/receiver path, the family's ``pc_p2_*_forget``/``reset`` hook and clean
re-registration. It does not claim source P2 FSM, receivers, rewards or
collision. Those remain BLOCKED on the family issues and #186.

Usage::

    py -3.12 -m experimental.pikmin2_lifecycle_runtime build \
        --native <native worktree> --build-dir <private build> --output <new dir> --head <sha>
    py -3.12 -m experimental.pikmin2_lifecycle_runtime run \
        --family long-legs --assets <P1 assets> --imported <manifest dir> \
        --output <new dir> --exe <fixture.exe>
"""
import argparse
import json
import os
import re
import subprocess
import uuid
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

FAMILIES = ('long-legs', 'waterwraith', 'flora')

# Phase frame numbers are deliberately spaced so one keyboard-free run can move
# through spawn -> movement -> death -> respawn -> re-entry without input.
APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,familyCount=0,deathFrame=-1,reentryFrame=-1,respawnInjected=0,reuseSlot=0;
 unsigned ids[8]={},controlId=0,target=0;
 Vector3f first[8];
 Teki* deadPtr=nullptr;Generator* targetGen=nullptr;
 Teki* find(unsigned id){Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
 void frameOn(Teki* t){if(cameraMgr&&cameraMgr->mCamera){cameraMgr->mCamera->setTarget(t);cameraMgr->mCamera->mControlsEnabled=false;}}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<30000,"lifecycle startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr||!cameraMgr||!cameraMgr->mCamera)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
  std::ifstream input("lifecycle-positions.txt");unsigned id;int type,registered;float x,y,z;
  while(input>>id>>type>>registered>>x>>y>>z){
   Teki* actor=find(id);require(actor,"lifecycle identity");
   require(actor->mTekiType==type,"lifecycle native type");
   Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"lifecycle birth XYZ");
   require(std::fabs(gen.x-x)<.02&&std::fabs(gen.y-y)<.02&&std::fabs(gen.z-z)<.02,"lifecycle generator XYZ");
   require(actor->isAlive(),"lifecycle not alive");
   const int inv=int(actor->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)!=0);
   std::printf("P2_LIFECYCLE_BIRTH id=%u type=%d registered=%d invincible=%d x=%.3f y=%.3f z=%.3f\n",id,type,registered,inv,birth.x,birth.y,birth.z);
   if(registered){require(familyCount<8,"lifecycle family overflow");ids[familyCount]=id;first[familyCount]=actor->mSRT.t;++familyCount;}
   else{require(controlId==0,"lifecycle duplicate control");controlId=id;}
  }
  require(familyCount>=1&&controlId!=0,"lifecycle roster incomplete");
  for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(a&&a->isAlive()&&!a->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){target=ids[i];break;}}
  require(target!=0,"lifecycle no mortal non-invincible target");
  {Teki* t=find(target);require(t,"lifecycle target missing");targetGen=t->mGenerator;frameOn(t);}
  std::printf("P2_LIFECYCLE_TARGET id=%u\n",target);
  std::printf("P2_LIFECYCLE_CAMERA target=%u\n",target);std::fflush(stdout);
 }
 if(observed>1&&observed<=300&&observed%60==0){Teki* t=find(ids[(observed/60)%familyCount]);if(t)frameOn(t);}
 if(observed==150){
  for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(!a)continue;Vector3f now=a->mSRT.t;
   std::printf("P2_LIFECYCLE_MOVE id=%u dist=%.3f\n",ids[i],std::hypot(now.x-first[i].x,now.z-first[i].z));}
  std::fflush(stdout);
 }
 if(observed>=2&&deathFrame<0){
  Teki* a=find(target);
  if(!a||!a->isAlive()){deathFrame=observed;std::printf("P2_LIFECYCLE_DEATH id=%u frame=%d\n",target,observed);std::fflush(stdout);}
  else{deadPtr=a;const bool hit=a->stimulate(InteractAttack(n,nullptr,100000,false));
   if(observed<40||observed%12==0)std::printf("P2_LIFECYCLE_ATTACK id=%u accepted=%d health=%.1f\n",target,int(hit),a->mHealth);}
 }
 if(deathFrame>=0&&reentryFrame<0&&observed<deathFrame+900){
  if(observed==deathFrame+1){
   Teki* c=find(target);std::printf("P2_LIFECYCLE_CLEANUP id=%u alive=%d\n",target,int(c&&c->isAlive()));
   unsigned long before=pc_p2_batch2_count()+pc_p2_long_legs_count();
   int regBefore=int(deadPtr&&(pc_p2_batch2_registered(deadPtr)||pc_p2_long_legs_registered(deadPtr)));
   pc_p2_batch2_forget(deadPtr);pc_p2_long_legs_forget(deadPtr);
   unsigned long after=pc_p2_batch2_count()+pc_p2_long_legs_count();
   int regAfter=int(deadPtr&&(pc_p2_batch2_registered(deadPtr)||pc_p2_long_legs_registered(deadPtr)));
   std::printf("P2_LIFECYCLE_FORGET id=%u before=%lu after=%lu registered_before=%d registered_after=%d\n",
               target,before,after,regBefore,regAfter);std::fflush(stdout);
  }
  Teki* fresh=find(target);
  if(!fresh&&!respawnInjected&&observed>=deathFrame+120&&targetGen){targetGen->init();respawnInjected=1;
   std::printf("P2_LIFECYCLE_RESPAWN_INJECT id=%u generator=%u\n",target,targetGen->_70);std::fflush(stdout);}
  if(fresh&&fresh->isAlive()){
   frameOn(fresh);
   pc_p2_batch2_setup();pc_p2_long_legs_setup();
   reentryFrame=observed;reuseSlot=int(fresh==deadPtr);
   std::printf("P2_LIFECYCLE_REENTRY id=%u frame=%d reused=%d\n",target,observed,reuseSlot);std::fflush(stdout);
  }
 }
 if(deathFrame>=0&&reentryFrame<0&&observed>=deathFrame+900){
  std::printf("P2_LIFECYCLE_BLOCKED no_respawn id=%u\n",target);std::fflush(stdout);std::_Exit(3);
 }
 if(reentryFrame>=0&&observed>=reentryFrame+120){
  int alive=0,moved=0;
  for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(!a)continue;if(a->isAlive())++alive;
   Vector3f now=a->mSRT.t;if(std::hypot(now.x-first[i].x,now.z-first[i].z)>=1.f)++moved;}
  Teki* c=find(controlId);const int controlAlive=int(c&&c->isAlive());
  std::printf("P2_LIFECYCLE_SUMMARY family=%d alive=%d moved=%d death=%d reentry=%d reused=%d control=%d\n",
              familyCount,alive,moved,deathFrame,reentryFrame,reuseSlot,controlAlive);
  require(moved>=1,"lifecycle no autonomous movement");
  std::printf("PASS P2_LIFECYCLE_RUNTIME\n");std::fflush(stdout);std::_Exit(0);
 }
 std::fflush(stdout);return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    if 'P2_LIFECYCLE_BIRTH' in source:
        raise ValueError('Already instrumented')
    head = ('#include <fstream>\n#include <cmath>\n#include <cstring>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "pc_p2_batch2.h"\n#include "pc_p2_long_legs.h"\n'
            '#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n')
    text = head + source[:start] + APP + source[end:]
    # The provenance builder replaces pc_main.cpp with this fixture, so the
    # production 960x540 centred-window policy (root a51b301 / native 1d5a242b)
    # does not run here. Apply the equivalent policy in this entrypoint and emit
    # the same log marker so adoption evidence is comparable.
    anchor = 'if(!pc_window_init("P2 room integration fixture",960,720))return 3;'
    if anchor not in text:
        raise ValueError('missing fixture window-init anchor')
    window = (anchor + '\n{int laneW=960,laneH=540;const char* laneRoomWin=std::getenv("PIKMIN_P2_ROOM_WINDOW");'
              'bool laneSmall=true;'
              'if(laneRoomWin&&(!std::strcmp(laneRoomWin,"0")||!std::strcmp(laneRoomWin,"off")))laneSmall=false;'
              'else if(laneRoomWin&&std::sscanf(laneRoomWin,"%dx%d",&laneW,&laneH)!=2){laneW=960;laneH=540;}'
              'if(laneSmall){pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);'
              'pc_window_set_window_size(laneW,laneH);pc_window_center();'
              'std::printf("[PC Port] Experimental preview window set to %dx%d windowed and centered '
              '(override with PIKMIN_P2_ROOM_WINDOW=WxH or =off).\\n",laneW,laneH);std::fflush(stdout);}}')
    return text.replace(anchor, window)


def build(native, build_dir, output, head):
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text()))
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe


def _arena(name, assets, imported, output):
    output = Path(output).resolve()
    if name == 'waterwraith':
        from experimental.pikmin2_waterwraith_arena import prepare
        return prepare(assets, imported, output)
    if name == 'flora':
        from experimental.pikmin2_flora_arena import prepare
        return prepare(assets, imported, output)
    if name == 'long-legs':
        from experimental.pikmin2_long_legs_arena import prepare
        return prepare(assets, imported, output)
    raise ValueError('Unknown lifecycle family: ' + name)


def adopt_existing(assets, run_dir, output):
    """Re-stage an already-installed private arena through the current overlay.

    Installed banks are preserved byte-for-byte; only the stage records are
    rebuilt so the current ``ensure_pikmin_squad`` starting squad is applied.
    This lets a lifecycle re-run avoid repeating disc extraction.
    """
    from scripts.preview_pikmin2_room import overlay
    assets = Path(assets).resolve()
    run_dir = Path(run_dir).resolve()
    src = run_dir / 'assets' / 'dataDir'
    overrides = {}
    for rel in ('stages/chal0.ini', 'stages/chal0/default.gen'):
        path = src / rel
        if not path.is_file():
            raise ValueError('Existing arena missing ' + rel)
        overrides['dataDir/' + rel] = path.read_bytes()
    for path in sorted((src / 'courses/pikmin2room').glob('*.mod')):
        overrides['dataDir/courses/pikmin2room/' + path.name] = path.read_bytes()
    new = output.resolve() / uuid.uuid4().hex
    new.mkdir(parents=True)
    overlay(assets, new / 'assets', overrides)
    for path in run_dir.glob('*.txt'):
        (new / path.name).write_bytes(path.read_bytes())
    if (run_dir / 'arena.json').is_file():
        (new / 'arena.json').write_bytes((run_dir / 'arena.json').read_bytes())
    (new / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    return new


def run(name, assets, imported, output, exe, timeout=300, existing=None):
    if existing is not None:
        run_dir = adopt_existing(assets, existing, output)
    else:
        run_dir = _arena(name, assets, imported, output)
        if name == 'long-legs':
            from experimental.pikmin2_long_legs_visual import convert, verify
            room = run_dir / 'assets/dataDir/courses/pikmin2room'
            convert(room)
            verify(room)
    manifest = json.loads((run_dir / 'arena.json').read_text())
    control = manifest['control']
    rows = [f"{a['generator']} {a['native_teki_type']} {int(a['species'] != control)} "
            + ' '.join(str(v) for v in a['expected_xyz'])
            for a in manifest['actors']]
    (run_dir / 'lifecycle-positions.txt').write_text('\n'.join(rows) + '\n')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy')
    log = run_dir / 'native.log'
    with log.open('w') as stream:
        try:
            code = subprocess.run([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                                  cwd=run_dir, env=env, stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    text = log.read_text(errors='replace')
    evidence = validate(text, code, manifest)
    evidence.update(family=name, exit_code=code, run=str(run_dir),
                    executable=builder.snapshot([Path(exe).resolve()]),
                    arena=builder.snapshot([run_dir / 'arena.json',
                                            run_dir / 'lifecycle-positions.txt']))
    (run_dir / 'lifecycle-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))
    return evidence


def validate(text, code, manifest):
    births = re.findall(r'P2_LIFECYCLE_BIRTH id=(\d+) type=(\d+) registered=(\d+) '
                        r'invincible=(\d)', text)
    moves = re.findall(r'P2_LIFECYCLE_MOVE id=(\d+) dist=(-?\d+\.\d+)', text)
    attacks = re.findall(r'P2_LIFECYCLE_ATTACK id=(\d+) accepted=(\d) health=(-?\d+\.\d+)', text)
    target = re.findall(r'P2_LIFECYCLE_TARGET id=(\d+)', text)
    death = re.findall(r'P2_LIFECYCLE_DEATH id=(\d+) frame=(\d+)', text)
    cleanup = re.findall(r'P2_LIFECYCLE_CLEANUP id=(\d+) alive=(\d)', text)
    forget = re.findall(r'P2_LIFECYCLE_FORGET id=(\d+) before=(\d+) after=(\d+) '
                        r'registered_before=(\d) registered_after=(\d)', text)
    inject = re.findall(r'P2_LIFECYCLE_RESPAWN_INJECT id=(\d+) generator=(\d+)', text)
    reentry = re.findall(r'P2_LIFECYCLE_REENTRY id=(\d+) frame=(\d+) reused=(\d)', text)
    summary = re.findall(r'P2_LIFECYCLE_SUMMARY family=(\d+) alive=(\d+) moved=(\d+) '
                         r'death=(-?\d+) reentry=(-?\d+) reused=(\d) control=(\d)', text)
    binds = re.findall(r'P2_(?:LONG_LEGS|BATCH2)_BIND', text)
    draws = re.findall(r'P2_(?:LONG_LEGS|BATCH2)_DRAW', text)
    life = summary[0] if summary else None
    checks = dict(
        completion=code == 0 and 'PASS P2_LIFECYCLE_RUNTIME' in text,
        birth_count=len(births) == len(manifest['actors']),
        all_mortal=bool(births) and all(b[3] == '0' for b in births),
        target_selected=bool(target),
        receiver_accepted=any(a[1] == '1' for a in attacks),
        health_reached_zero=any(float(a[2]) <= 0.0 for a in attacks),
        died=bool(death),
        cleaned_up=bool(cleanup) and cleanup[0][1] == '0',
        forget_hook=bool(forget) and forget[0][3] == '1' and forget[0][4] == '0'
                    and int(forget[0][2]) == int(forget[0][1]) - 1,
        respawned=bool(reentry),
        rebound=len(binds) >= 2,
        drew=bool(draws),
        reentry_alive=bool(life) and int(life[3]) >= 0 and int(life[4]) >= 0,
    )
    return dict(passed=all(checks.values()), checks=checks,
                control_alive_observed=bool(life) and int(life[6]) == 1,
                births=[list(b) for b in births], moves=moves, attacks=attacks,
                target=target, death=death, cleanup=cleanup, forget=forget,
                respawn_inject=inject,
                reentry=reentry, summary=life,
                bind_lines=len(binds), draw_lines=len(draws),
                failures=re.findall(r'FAIL p2 room: (.*)', text),
                unmeasured=['source P2 FSM', 'source receivers/rewards',
                            'transport/reward', 'campaign resume', 'mixed-scene performance'],
                injection='camera framing + repeated Navi InteractAttack(100000); respawn via '
                          'the staged actor\'s own Generator::init() after death')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    r = sub.add_parser('run')
    for name in ('assets', 'output', 'exe'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--imported', type=Path)
    r.add_argument('--existing', type=Path)
    r.add_argument('--family', choices=FAMILIES, required=True)
    r.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head)
    else:
        if args.existing is None and args.imported is None:
            parser.error('run requires --imported (fresh arena) or --existing (re-stage)')
        run(args.family, args.assets, args.imported, args.output, args.exe, args.timeout, args.existing)
