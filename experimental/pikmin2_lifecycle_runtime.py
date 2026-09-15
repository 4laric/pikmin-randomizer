"""Reusable non-invincible lifecycle fixture for P2 registered proxies (#397).

Owned by the lifecycle/acceptance lane. It stages a family arena with the
current starting-squad overlay, frames the engine camera on a registered proxy
so its P1-proxy AI actually updates, asserts the target is not carrying
``TEKI_OPTION_INVINCIBLE``, drives the source damage receiver with repeated
Navi ``InteractAttack`` hits until death, then disposes the corpse pellet so the
ENGINE death funnel (``Pellet::doKill -> BTeki::viewKill -> kill -> doKill ->
pc_p2_forget_teki``) clears the family registration -- the fixture itself never
calls a family ``*_forget``. It then forces the scene's own ``Generator`` to
respawn the same generator ID (late birth) and re-runs the family registration.

``--cycles N`` runs the death->forget->respawn->re-entry leg N times on the same
family, asserting no registry growth (each re-entry leaves exactly one live
registration, read through the family ``_count``), no reward growth (cargo-free
arena) and an untouched control actor. Movement (gate 2) is sampled on the
FIRST-BORN actor before the first lethal attack, with no Pikmin reset-position
lure. ``--teardown {manager-reset,scene-teardown}`` selects which reset the
family runs at the teardown point after the cycles: the manager-reset path calls
the family's own ``_reset`` then re-enters through ``_setup``, while the
scene-teardown path drives the REAL section teardown through the host
``GameCoreSection::exitStage`` (reached by tree-walking ``gameflow.mGameSection``,
the same mechanism the shipping demon/kurage fixtures use), which nulls naviMgr
and clears every family in one ``pc_p2_reset_all_teki()``, then exits -- the
in-process section re-enter (menu/map-select transition) remains a lane-01
concern. The evidence JSON labels which mode produced which surviving references.

This is deliberately a **proxy** lifecycle harness: the lethal damage value is
injected (``InteractAttack(100000)``, a real receiver hit) and the corpse
disposal trigger is injected (the cargo-free arena has no Onion/Pod), but every
forget/teardown signal is the real engine seam. It does not claim source P2 FSM,
receivers, rewards or collision -- those remain on the family issues and #186.

Usage::

    py -3.12 -m experimental.pikmin2_lifecycle_runtime build \
        --native <native worktree> --build-dir <private build> --output <new dir> \
        --head <sha> --family dwarf-orange
    py -3.12 -m experimental.pikmin2_lifecycle_runtime run \
        --family dwarf-orange --assets <P1 assets> --output <new dir> --exe <fixture.exe> \
        --bank <bank dir> --profile <profile dir> --cycles 2 --teardown scene-teardown
"""
import argparse
import json
import os
import re
import subprocess
import uuid
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

FAMILIES = ('long-legs', 'waterwraith', 'flora', 'dwarf-orange', 'sokkuri')
TEARDOWN_MODES = ('manager-reset', 'scene-teardown')

# Per-family native registration hooks. The three original families all bind
# through the batch2/long-legs proxy modules; dwarf-orange and sokkuri bind
# through their own modules. ``count`` is the read-only registry size and
# ``reset`` clears that family alone; both are used at the teardown point so
# the two teardown modes are directly comparable.
_BATCH2_LONG_LEGS = dict(
    include='#include "pc_p2_batch2.h"\n#include "pc_p2_long_legs.h"\n',
    registered='(pc_p2_batch2_registered(deadPtr)||pc_p2_long_legs_registered(deadPtr))',
    count='(pc_p2_batch2_count()+pc_p2_long_legs_count())',
    reset='pc_p2_batch2_reset();pc_p2_long_legs_reset();',
    rebind='pc_p2_batch2_rebind();pc_p2_long_legs_setup();',
    bind_re=r'P2_(?:LONG_LEGS|BATCH2)_BIND',
    draw_re=r'P2_(?:LONG_LEGS|BATCH2)_DRAW',
)

FAMILY_HOOKS = {
    'long-legs': dict(_BATCH2_LONG_LEGS),
    'waterwraith': dict(_BATCH2_LONG_LEGS),
    'flora': dict(_BATCH2_LONG_LEGS),
    'dwarf-orange': dict(
        include='#include "pc_p2_dwarf_orange.h"\n',
        registered='pc_p2_dwarf_orange_registered(deadPtr)',
        count='pc_p2_dwarf_orange_count()',
        reset='pc_p2_dwarf_orange_reset();',
        rebind='pc_p2_dwarf_orange_setup();',
        # dwarf_orange has no *_BIND marker; the family setup re-emits the enemy
        # ready line, so two of them (initial + re-entry) is the rebound signal.
        bind_re=r'P2_ENEMY_READY species=BlueKochappy',
        draw_re=r'P2_DWARF_ORANGE_DRAW',
    ),
    'sokkuri': dict(
        include='#include "pc_p2_sokkuri.h"\n',
        registered='pc_p2_sokkuri_registered(deadPtr)',
        count='pc_p2_sokkuri_count()',
        reset='pc_p2_sokkuri_reset();',
        rebind='pc_p2_sokkuri_setup();',
        bind_re=r'P2_SOKKURI_BIND',
        draw_re=r'P2_SOKKURI_STATE',
    ),
}

# Phase frame numbers are deliberately spaced so one keyboard-free run can move
# through spawn -> movement -> death -> corpse-dispose -> respawn -> re-entry ->
# (next cycle | teardown) -> summary without input. ``__REGISTERED_EXPR__`` (on
# deadPtr), ``__COUNT_EXPR__`` (family registry size), ``__RESET_CALL__``
# (family-only reset) and ``__REBIND_CALL__`` are substituted per family; no
# family ``*_forget`` is ever called by the fixture. ``totalCycles``/
# ``teardownScene`` are read from lifecycle-config.txt.
APP = r'''static GameCoreSection* lifecycleFindCore(CoreNode* node,int depth=0){
    if(!node||depth>20)return nullptr;
    if(auto* core=dynamic_cast<GameCoreSection*>(node))return core;
    for(auto* c=node->Child();c;c=c->Next()){if(auto* core=lifecycleFindCore(c,depth+1))return core;}
    return nullptr;
}
class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,familyCount=0,deathFrame=-1,reentryFrame=-1,respawnInjected=0,reuseSlot=0,disposed=0,cycleMarked=0,moveObserved=0;
 int totalCycles=1,cycleDone=0,teardownScene=0,finishing=0,readyFrame=0,pendingTeardown=0;
 unsigned ids[8]={},controlId=0,target=0;
 Vector3f first[8];
 Teki* deadPtr=nullptr;Generator* targetGen=nullptr;Pellet* corpsePtr=nullptr;
 Teki* find(unsigned id){Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a&&a->isAlive()&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
 void frameOn(Teki* t){if(cameraMgr&&cameraMgr->mCamera){cameraMgr->mCamera->setTarget(t);cameraMgr->mCamera->mControlsEnabled=false;}}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<40000,"lifecycle startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!mapMgr||!cameraMgr||!cameraMgr->mCamera||!pelletMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  std::ifstream cfg("lifecycle-config.txt");if(cfg>>totalCycles>>teardownScene){if(totalCycles<1)totalCycles=1;}
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
  int livePikis=0;Iterator pi(pikiMgr);CI_LOOP(pi){Piki* p=static_cast<Piki*>(*pi);if(p&&p->isAlive())++livePikis;}
  require(livePikis>0,"lifecycle starting squad missing");
  std::printf("P2_LIFECYCLE_SQUAD alive=%d\n",livePikis);
  for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(a&&a->isAlive()&&!a->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){target=ids[i];break;}}
  require(target!=0,"lifecycle no mortal non-invincible target");
  {Teki* t=find(target);require(t,"lifecycle target missing");targetGen=t->mGenerator;frameOn(t);}
  std::printf("P2_LIFECYCLE_TARGET id=%u\n",target);
  std::printf("P2_LIFECYCLE_CAMERA target=%u\n",target);std::fflush(stdout);
 }
 if(finishing){
  if(observed>=readyFrame+120){
   int alive=0;
   for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(a&&a->isAlive())++alive;}
   Teki* c=find(controlId);const int controlAlive=int(c&&c->isAlive());
   std::printf("P2_LIFECYCLE_SUMMARY family=%d alive=%d moved=%d death=%d reentry=%d reused=%d control=%d\n",
               familyCount,alive,moveObserved,deathFrame,reentryFrame,reuseSlot,controlAlive);
   require(controlAlive==1,"control actor did not survive repeatable teardown");
   std::printf("PASS P2_LIFECYCLE_RUNTIME\n");std::fflush(stdout);std::_Exit(0);
  }
  std::fflush(stdout);return result;
 }
 if(observed>1&&observed<=300&&observed%60==0){Teki* t=find(ids[(observed/60)%familyCount]);if(t)frameOn(t);}
 if(observed>=2&&cycleMarked==0){std::printf("P2_LIFECYCLE_CYCLE cycle=%d\n",cycleDone+1);cycleMarked=1;std::fflush(stdout);}
 // Natural movement of the FIRST-BORN actor, sampled before any lethal attack
 // (no Pikmin resetPosition lure; Gate 2 is the first-born actor's locomotion).
 if(deathFrame<0&&cycleDone==0&&observed==30){
  for(int i=0;i<familyCount;++i){Teki* a=find(ids[i]);if(!a)continue;Vector3f now=a->mSRT.t;
   const float d=std::hypot(now.x-first[i].x,now.z-first[i].z);
   if(d>=1.f)moveObserved=1;
   std::printf("P2_LIFECYCLE_MOVE id=%u dist=%.3f\n",ids[i],d);}
  std::fflush(stdout);
 }
 // Lethal receiver hits start only after the first-born movement window so Gate
 // 2 is natural; later cycles engage immediately.
 if(observed>=((cycleDone==0)?40:2)&&deathFrame<0){
  Teki* a=find(target);
  if(!a){deathFrame=observed;std::printf("P2_LIFECYCLE_DEATH id=%u frame=%d\n",target,observed);std::fflush(stdout);}
  else{deadPtr=a;const bool hit=a->stimulate(InteractAttack(n,nullptr,100000,false));
   if(observed<110||observed%12==0)std::printf("P2_LIFECYCLE_ATTACK id=%u accepted=%d health=%.1f\n",target,int(hit),a->mHealth);}
 }
 if(deathFrame>=0&&reentryFrame<0&&observed<deathFrame+900){
  if(observed==deathFrame+1){
   Teki* c=find(target);std::printf("P2_LIFECYCLE_CLEANUP id=%u alive=%d\n",target,int(c&&c->isAlive()));
   const int regAtDeath=int(deadPtr&&(__REGISTERED_EXPR__));
   std::printf("P2_LIFECYCLE_FORGET id=%u registered_at_death=%d\n",target,regAtDeath);std::fflush(stdout);
  }
  if(!corpsePtr){Iterator pellets(pelletMgr);CI_LOOP(pellets){Pellet* p=static_cast<Pellet*>(*pellets);if(p&&p->isAlive()&&p->mPelletView==static_cast<PelletView*>(deadPtr)){corpsePtr=p;break;}}}
  if(corpsePtr&&!disposed&&observed>=deathFrame+60){
   // Engine corpse-disposal funnel (no Onion in the cargo-free arena, so the
   // disposal trigger is injected): Pellet::doKill -> BTeki::viewKill ->
   // kill(false) -> doKill -> pc_p2_forget_teki. No family *_forget here.
   corpsePtr->kill(false);
   const int regAfter=int(deadPtr&&(__REGISTERED_EXPR__));
   std::printf("P2_LIFECYCLE_FORGET id=%u registered_after_dispose=%d engine=doKill\n",target,regAfter);
   require(regAfter==0,"engine doKill did not forget at corpse disposal");
   disposed=1;std::fflush(stdout);
  }
  Teki* fresh=find(target);
  if(!fresh&&!respawnInjected&&observed>=deathFrame+120&&targetGen&&disposed){targetGen->init();respawnInjected=1;
   std::printf("P2_LIFECYCLE_RESPAWN_INJECT id=%u generator=%u\n",target,targetGen->_70);std::fflush(stdout);}
  if(fresh&&fresh->isAlive()){
   frameOn(fresh);
   __REBIND_CALL__
   reentryFrame=observed;reuseSlot=int(fresh==deadPtr);
   std::printf("P2_LIFECYCLE_REENTRY id=%u frame=%d reused=%d\n",target,observed,reuseSlot);std::fflush(stdout);
   const int cnt=int(__COUNT_EXPR__);
   std::printf("P2_LIFECYCLE_REGISTRY cycle=%d count=%d\n",cycleDone+1,cnt);std::fflush(stdout);
   require(cnt==1,"family registry did not remain at one registration across cycles");
   ++cycleDone;
   if(cycleDone>=totalCycles){pendingTeardown=observed+20;}
   else{deathFrame=-1;reentryFrame=-1;respawnInjected=0;disposed=0;corpsePtr=nullptr;deadPtr=nullptr;cycleMarked=0;}
  }
 }
 // Teardown follows the last re-entry (both modes reset the family registry, and
 // the manager-reset mode then re-enters through the family _setup so the
 // registry returns to exactly one; the scene-teardown mode drives the REAL
 // section teardown through the host GameCoreSection::exitStage and then exits).
 if(pendingTeardown>0&&observed>=pendingTeardown&&!finishing){
  pendingTeardown=0;
  std::printf("P2_LIFECYCLE_REWARD pokos=%d\n",pc_p2_preview_pokos());std::fflush(stdout);
  const int refsBefore=int(__COUNT_EXPR__);
  std::printf("P2_LIFECYCLE_TEARDOWN_MODE mode=%s\n",teardownScene?"scene-teardown":"manager-reset");std::fflush(stdout);
  if(teardownScene){
   GameCoreSection* core=lifecycleFindCore(gameflow.mGameSection);
   require(core!=nullptr,"host section core node");
   // exitStage invalidates manager/stage-heap objects; assert the family is
   // still registered BEFORE the exit so the drop to 0 is a real clear and
   // not a vacuous 0==0 (mirrors native tools/p2_kurage_runtime.cpp:297-301).
   require(refsBefore>=1,"scene exit requires a live family registration before exitStage");
   core->exitStage();
   const int refsAfter=int(__COUNT_EXPR__);
   const int naviNull=int(naviMgr==nullptr);
   std::printf("P2_LIFECYCLE_SCENE_EXIT host=exitStage refs_before=%d refs_after=%d navi_null=%d\n",refsBefore,refsAfter,naviNull);
   require(refsAfter==0&&naviNull==1,"host exitStage did not clear family registries");
   std::printf("PASS P2_LIFECYCLE_RUNTIME\n");std::fflush(stdout);std::_Exit(0);
  }else{
   __RESET_CALL__
   const int refsAfter=int(__COUNT_EXPR__);
   std::printf("P2_LIFECYCLE_TEARDOWN refs_before=%d refs_after=%d\n",refsBefore,refsAfter);
   require(refsAfter==0,"teardown did not clear family registry");
   __REBIND_CALL__
   const int post=int(__COUNT_EXPR__);
   std::printf("P2_LIFECYCLE_REGISTRY cycle=%d count=%d\n",cycleDone+1,post);std::fflush(stdout);
   require(post==1,"teardown re-entry did not re-register exactly one family actor");
   std::fflush(stdout);readyFrame=observed;finishing=1;
  }
 }
 if(deathFrame>=0&&reentryFrame<0&&observed>=deathFrame+900){
  std::printf("P2_LIFECYCLE_BLOCKED no_respawn id=%u\n",target);std::fflush(stdout);std::_Exit(3);
 }
 std::fflush(stdout);return result;
}};
'''


def instrument(source, family='long-legs'):
    hooks = FAMILY_HOOKS[family]
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    if 'PASS P2_LIFECYCLE_RUNTIME' in source:
        raise ValueError('Already instrumented')
    head = ('#include <fstream>\n#include <cmath>\n#include <cstring>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "pc_p2_teki_lifetime.h"\n'
            '#include "GameCoreSection.h"\n'
            + hooks['include'] +
            '#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n')
    probe = (APP.replace('__REGISTERED_EXPR__', hooks['registered'])
                .replace('__COUNT_EXPR__', hooks['count'])
                .replace('__RESET_CALL__', hooks['reset'])
                .replace('__REBIND_CALL__', hooks['rebind']))
    text = head + source[:start] + probe + source[end:]
    # The provenance builder replaces pc_main.cpp with this fixture, so the
    # production 960x540 centred-window policy (root a51b301 / native 1d5a242b)
    # does not run here. Apply the equivalent policy in this entrypoint and emit
    # the same log marker so adoption evidence is comparable.
    anchor = 'if(!pc_window_init("P2 room integration fixture",960,720))return 3;'
    if anchor not in text:
        if 'pc_window_init("P2 room integration fixture",windowWidth,windowHeight)' in text and 'pc_window_center();' in text and 'Experimental preview window set to' in text:
            return text  # Current native replacement-main already supplies the policy.
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


def build(native, build_dir, output, head, family='long-legs'):
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text(), family))
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe


def _arena(name, assets, imported, output, bank, profile):
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
    if name == 'dwarf-orange':
        from experimental.pikmin2_dwarf_orange_arena import prepare
        run_dir = prepare(assets, bank, profile, output)
        # Normalize the family manifest to the shared harness shape: the
        # dwarf-orange arena emits generator/species/native_family but not the
        # top-level control or per-actor native_teki_type the harness reads.
        manifest_path = run_dir / 'arena.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['control'] = 'P1 Chappy'
        for actor in manifest['actors']:
            actor['native_teki_type'] = 3  # TEKI_Chappy
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        return run_dir
    if name == 'sokkuri':
        from experimental.pikmin2_ground_lifecycle_behavior import prepare
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


def run(name, assets, imported, output, exe, timeout=300, existing=None, bank=None, profile=None,
        cycles=1, teardown='manager-reset'):
    if existing is not None:
        run_dir = adopt_existing(assets, existing, output)
    else:
        run_dir = _arena(name, assets, imported, output, bank, profile)
        if name == 'long-legs':
            from experimental.pikmin2_long_legs_visual import convert, verify
            room = run_dir / 'assets/dataDir/courses/pikmin2room'
            convert(room)
            verify(room)
    manifest = json.loads((run_dir / 'arena.json').read_text())
    control = manifest['control']
    # sokkuri runs on the six-species ground arena: scope the harness to the
    # Sokkuri source actor + the ordinary control (the co-staged ground species
    # are foreign and ignored by this harness).
    target_species = {'sokkuri': 'Sokkuri'}.get(name)
    actors = ([a for a in manifest['actors']
               if a['species'] == target_species or a['species'] == control]
              if target_species else manifest['actors'])
    rows = [f"{a['generator']} {a['native_teki_type']} {int(a['species'] != control)} "
            + ' '.join(str(v) for v in a['expected_xyz'])
            for a in actors]
    (run_dir / 'lifecycle-positions.txt').write_text('\n'.join(rows) + '\n')
    (run_dir / 'lifecycle-config.txt').write_text(f"{cycles} {1 if teardown == 'scene-teardown' else 0}\n")
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
    vmanifest = dict(manifest, actors=actors)
    evidence = validate(text, code, vmanifest, name, cycles, teardown)
    evidence.update(family=name, exit_code=code, run=str(run_dir),
                    executable=builder.snapshot([Path(exe).resolve()]),
                    arena=builder.snapshot([run_dir / 'arena.json',
                                            run_dir / 'lifecycle-positions.txt']))
    (run_dir / 'lifecycle-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))
    return evidence


def validate(text, code, manifest, name='long-legs', cycles=1, teardown='manager-reset'):
    hooks = FAMILY_HOOKS.get(name, _BATCH2_LONG_LEGS)
    births = re.findall(r'P2_LIFECYCLE_BIRTH id=(\d+) type=(\d+) registered=(\d+) '
                        r'invincible=(\d)', text)
    moves = re.findall(r'P2_LIFECYCLE_MOVE id=(\d+) dist=(-?\d+\.\d+)', text)
    attacks = re.findall(r'P2_LIFECYCLE_ATTACK id=(\d+) accepted=(\d) health=(-?\d+\.\d+)', text)
    target = re.findall(r'P2_LIFECYCLE_TARGET id=(\d+)', text)
    death = re.findall(r'P2_LIFECYCLE_DEATH id=(\d+) frame=(\d+)', text)
    cleanup = re.findall(r'P2_LIFECYCLE_CLEANUP id=(\d+) alive=(\d)', text)
    forget_at_death = re.findall(r'P2_LIFECYCLE_FORGET id=(\d+) registered_at_death=(\d)', text)
    forget_dispose = re.findall(r'P2_LIFECYCLE_FORGET id=(\d+) registered_after_dispose=(\d) engine=doKill', text)
    inject = re.findall(r'P2_LIFECYCLE_RESPAWN_INJECT id=(\d+) generator=(\d+)', text)
    reentry = re.findall(r'P2_LIFECYCLE_REENTRY id=(\d+) frame=(\d+) reused=(\d)', text)
    summary = re.findall(r'P2_LIFECYCLE_SUMMARY family=(\d+) alive=(\d+) moved=(\d+) '
                         r'death=(-?\d+) reentry=(-?\d+) reused=(\d) control=(\d)', text)
    binds = re.findall(hooks['bind_re'], text)
    draws = re.findall(hooks['draw_re'], text)
    cycle = re.findall(r'P2_LIFECYCLE_CYCLE cycle=(\d+)', text)
    registry = [(int(n), int(c)) for n, c in re.findall(
        r'P2_LIFECYCLE_REGISTRY cycle=(\d+) count=(\d+)', text)]
    reward = re.findall(r'P2_LIFECYCLE_REWARD pokos=(-?\d+)', text)
    tmode = re.findall(r'P2_LIFECYCLE_TEARDOWN_MODE mode=(\S+)', text)
    tdown = re.findall(r'P2_LIFECYCLE_TEARDOWN refs_before=(\d+) refs_after=(\d+)', text)
    life = summary[0] if summary else None
    scene_exit = re.findall(r'P2_LIFECYCLE_SCENE_EXIT host=exitStage refs_before=(\d+) '
                            r'refs_after=(\d+)(?: navi_null=(\d+))?', text)

    # Per-cycle registries are marked cycle=1..N; the manager-reset post-teardown
    # re-entry is cycle=N+1 (family _reset then _setup), while scene-teardown only
    # reports refs_after=0 via the host exitStage and then exits.
    per_cycle = [c for n, c in registry if 1 <= n <= cycles]
    post_teardown = [c for n, c in registry if n == cycles + 1]

    # Gate 2 movement: the MOVE probe samples the FIRST-BORN actor before the
    # first lethal attack, so a MOVE marker with dist >= 1 must precede the first
    # DEATH (no resetPosition lure).
    first_death = text.find('P2_LIFECYCLE_DEATH ')
    moved_first_born = False
    if first_death >= 0:
        for m in re.finditer(r'P2_LIFECYCLE_MOVE id=(\d+) dist=(-?\d+\.\d+)', text):
            if m.start() < first_death and float(m.group(2)) >= 1.0:
                moved_first_born = True
                break

    teardown_cleared = bool(tdown) and tdown[0][1] == '0'
    teardown_reentry = len(post_teardown) == 1 and post_teardown[0] == 1
    # Scene teardown is a real clear only if the family was registered (>=1)
    # before exitStage and 0 after; a bare refs_after==0 is not proof.
    scene_teardown_ok = (bool(scene_exit) and int(scene_exit[0][0]) >= 1
                         and scene_exit[0][1] == '0')
    # Address reuse is observed from the REENTRY markers (present in both
    # teardown modes), not the SUMMARY line (which the scene path never prints).
    reused_observed = any(r[2] == '1' for r in reentry)

    reward_ok = True
    if cycles >= 2:
        registry_growth_ok = len(per_cycle) == cycles and all(c == 1 for c in per_cycle)
        reward_ok = bool(reward) and int(reward[0]) <= 0
    elif teardown == 'manager-reset':
        # single cycle is non-vacuous: teardown cleared it AND re-entry re-registered one
        registry_growth_ok = teardown_cleared and teardown_reentry
    else:
        # single-cycle scene teardown: registries dropped to zero via the host exitStage
        registry_growth_ok = scene_teardown_ok

    checks = dict(
        completion=code == 0 and 'PASS P2_LIFECYCLE_RUNTIME' in text,
        birth_count=len(births) == len(manifest['actors']),
        all_mortal=bool(births) and all(b[3] == '0' for b in births),
        target_selected=bool(target),
        receiver_accepted=any(a[1] == '1' for a in attacks),
        health_reached_zero=any(float(a[2]) <= 0.0 for a in attacks),
        died=bool(death),
        cleaned_up=bool(cleanup) and cleanup[0][1] == '0',
        corpse_retained=bool(forget_at_death) and forget_at_death[0][1] == '1',
        engine_forgot=bool(forget_dispose) and forget_dispose[0][1] == '0',
        respawned=bool(reentry),
        rebound=len(binds) >= 2,
        drew=bool(draws),
        moved_first_born=moved_first_born,
        reused_observed=reused_observed,
        teardown_mode=bool(tmode) and tmode[0] == teardown,
        registry_growth=registry_growth_ok,
        reward=reward_ok,
    )
    if teardown == 'scene-teardown':
        checks['scene_teardown'] = scene_teardown_ok
    else:
        checks['control_untouched'] = bool(life) and int(life[6]) == 1
        checks['teardown_cleared'] = teardown_cleared
        checks['teardown_reentry'] = teardown_reentry

    # moved_first_born (gate 2) and reused_observed (address reuse) are hard
    # gates: a run whose first-born actor never moved >=1 unit, or whose freed
    # generator slot was not reused, is not a pass.
    passed = all(checks.values())
    return dict(passed=passed, checks=checks,
                cycles=cycles, teardown_mode=teardown,
                registry_growth_ok=registry_growth_ok,
                scene_teardown_ok=scene_teardown_ok,
                moved_first_born=moved_first_born,
                control_alive_observed=bool(life) and int(life[6]) == 1,
                births=[list(b) for b in births], moves=moves, attacks=attacks,
                target=target, death=death, cleanup=cleanup,
                forget_at_death=forget_at_death, forget_dispose=forget_dispose,
                respawn_inject=inject,
                reentry=reentry, summary=life,
                reused_observed=reused_observed,
                cycle_markers=cycle, registry=registry, reward=reward,
                teardown_markers=tdown, scene_exit_markers=scene_exit,
                bind_lines=len(binds), draw_lines=len(draws),
                failures=re.findall(r'FAIL p2 room: (.*)', text),
                unmeasured=['source P2 FSM', 'source receivers/rewards',
                            'transport/reward', 'campaign resume', 'mixed-scene performance',
                            'full menu/map-select section re-enter (scene mode drives the host '
                            'GameCoreSection::exitStage then exits; in-place re-enter needs the '
                            'pc_p2_input_script section transition, a lane-01 concern)'],
                injection='repeated Navi InteractAttack(100000) via the receiver; corpse '
                          'disposal trigger injected (no Onion in cargo-free arena); respawn via '
                          'the staged actor\'s own Generator::init() after death')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--family', choices=FAMILIES, default='long-legs')
    r = sub.add_parser('run')
    for name in ('assets', 'output', 'exe'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--imported', type=Path)
    r.add_argument('--existing', type=Path)
    r.add_argument('--bank', type=Path)
    r.add_argument('--profile', type=Path)
    r.add_argument('--family', choices=FAMILIES, required=True)
    r.add_argument('--cycles', type=int, default=1)
    r.add_argument('--teardown', choices=TEARDOWN_MODES, default='manager-reset')
    r.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.family)
    else:
        if args.family == 'dwarf-orange':
            if not args.bank or not args.profile:
                parser.error('dwarf-orange requires --bank and --profile')
        elif args.existing is None and args.imported is None:
            parser.error('run requires --imported (fresh arena) or --existing (re-stage)')
        run(args.family, args.assets, args.imported, args.output, args.exe,
            args.timeout, args.existing, args.bank, args.profile, args.cycles, args.teardown)
