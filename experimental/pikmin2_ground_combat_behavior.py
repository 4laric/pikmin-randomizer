"""Sokkuri (79) + Armor (15) natural-combat death/corpse/cleanup/re-entry (#165).

Upgrades the injected evidence in
:mod:`experimental.pikmin2_ground_lifecycle_behavior` (which writes
``mHealth=0``) to a **natural** fight: the live starting squad is redeployed in
``FreeMode`` around the two registered native actors and the engine's own Pikmin
attack path does the damage. No health, state or event is written by the fixture.

A private replacement-main fixture (built against a Ninja-fresh private
``pikmin_*`` exactly like :mod:`experimental.pikmin2_elecbug_immunity_behavior`):

* waits for the cargo-free ground arena, finds the two registered actors by
  generator (Sokkuri 346005, Armor 346001) and reads their starting health,
* repositions the captain between them and puts every live Pikmin into
  ``FreeMode`` in a ring around them (the same stimulus the Kochappy combat
  fixture uses); the fixture never sets health or forces a death,
* observes a strictly partial health drop, then ``mHealth<=0``, the host corpse
  pellet whose ``mPelletView`` is the actor, and the source death markers,
* calls the production teardown ``pc_p2_*_forget`` and proves both module
  registries return to zero,
* respawns each species from its own generator (``mGenType->init``) and re-runs
  ``pc_p2_*_setup``; the probe proves a fresh pointer is bound and the old
  pointer is gone.

If no actor loses health within the bounded window the run fails
``no_natural_damage`` rather than injecting — that is the honest outcome when the
host damage path does not yet accept Pikmin attacks. The ground arena is
cargo-free with no Pod, so reward/delivery stays ``untested`` and belongs to the
lifecycle/reward lane (#397).
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_batch2_families import FAMILIES
from experimental.pikmin2_ground_lifecycle_behavior import (
    ARMOR_ID, ARMOR_INDEX, ARMOR_POSITION, CFG, DEFAULT_POSITIONS,
    SOKKURI_ID, SOKKURI_INDEX, SOKKURI_POSITION,
)
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

MIDPOINT = (((SOKKURI_POSITION[0] + ARMOR_POSITION[0]) / 2.0),
            ARMOR_POSITION[1],
            ((SOKKURI_POSITION[2] + ARMOR_POSITION[2]) / 2.0))
SQUAD_RADIUS = 36.0
DEATH_MARKERS = {
    'Sokkuri': f'P2_COMBAT_DEATH species=Sokkuri generator={SOKKURI_ID} source_id=79',
    'Armor': f'P2_COMBAT_DEATH species=Armor generator={ARMOR_ID} source_id=15',
}
CORPSE_MARKERS = {
    'Sokkuri': f'P2_COMBAT_CORPSE species=Sokkuri generator={SOKKURI_ID}',
    'Armor': f'P2_COMBAT_CORPSE species=Armor generator={ARMOR_ID}',
}

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,stage=0;
 Teki* sokkuri=nullptr;Teki* armor=nullptr;
 Generator* sokkuriGen=nullptr;Generator* armorGen=nullptr;
 Teki* freshSokkuri=nullptr;Teki* freshArmor=nullptr;
 Pellet* sokkuriCorpse=nullptr;Pellet* armorCorpse=nullptr;
 float sokMax=0.0f,armMax=0.0f;
 bool sokDamage=false,armDamage=false,sokDead=false,armDead=false;
 Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
 Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
 int liveSquad(){int n=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())++n;}return n;}
 void deploy(Navi* n){int count=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;
  float a=float(count)*(6.2831853f/20.0f);
  Vector3f pt=Vector3f(-80.0f+36.0f*std::sin(a),0.0f,1850.0f+36.0f*std::cos(a));
  pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++count;}
  std::printf("P2_COMBAT_DEPLOY squad=%d\n",count);std::fflush(stdout);}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<90000,"ground combat startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(stage==0){
  sokkuri=byGenerator(346005);armor=byGenerator(346001);
  require(sokkuri&&armor,"registered Sokkuri/Armor actors present");
  require(pc_p2_sokkuri_registered(sokkuri)&&pc_p2_sokkuri_count()==1,"sokkuri registered exactly once");
  require(pc_p2_armor_registered(armor)&&pc_p2_armor_count()==1,"armor registered exactly once");
  int squad=liveSquad();require(squad>=1,"live starting squad");
  sokkuriGen=sokkuri->mGenerator;armorGen=armor->mGenerator;sokMax=sokkuri->mHealth;armMax=armor->mHealth;
  std::printf("P2_COMBAT_READY squad=%d sokkuri_health=%.1f armor_health=%.1f\n",squad,sokMax,armMax);
  std::fflush(stdout);stage=1;return result;
 }
 if(stage==1){
  Vector3f mid=Vector3f(-80.0f,30.0f,1850.0f);mid.y=mapMgr->getMinY(mid.x,mid.z,true);n->resetPosition(mid);
  deploy(n);
  std::printf("P2_COMBAT_STIMULUS tick=%d captain_free_deploy=1\n",observed);std::fflush(stdout);
  stage=2;return result;
 }
 if(stage==2){
  if(sokkuri&&sokkuri->mHealth<sokMax&&sokkuri->mHealth>0.0f&&!sokDamage){sokDamage=true;std::printf("P2_COMBAT_DAMAGE species=Sokkuri health=%.1f max=%.1f\n",sokkuri->mHealth,sokMax);std::fflush(stdout);}
  if(armor&&armor->mHealth<armMax&&armor->mHealth>0.0f&&!armDamage){armDamage=true;std::printf("P2_COMBAT_DAMAGE species=Armor health=%.1f max=%.1f\n",armor->mHealth,armMax);std::fflush(stdout);}
  if(sokkuri&&sokkuri->mHealth<=0.0f&&!sokDead){sokDead=true;std::printf("P2_COMBAT_DEATH species=Sokkuri generator=346005 source_id=79\n");std::fflush(stdout);}
  if(armor&&armor->mHealth<=0.0f&&!armDead){armDead=true;std::printf("P2_COMBAT_DEATH species=Armor generator=346001 source_id=15\n");std::fflush(stdout);}
  if(!sokkuriCorpse){sokkuriCorpse=corpseOf(sokkuri);if(sokkuriCorpse){std::printf("P2_COMBAT_CORPSE species=Sokkuri generator=346005\n");std::fflush(stdout);}}
  if(!armorCorpse){armorCorpse=corpseOf(armor);if(armorCorpse){std::printf("P2_COMBAT_CORPSE species=Armor generator=346001\n");std::fflush(stdout);}}
  if(observed%60==0){std::printf("P2_COMBAT_SCAN frame=%d squad=%d sok[health=%.1f dead=%d corpse=%d] arm[health=%.1f dead=%d corpse=%d]\n",observed,liveSquad(),sokkuri->mHealth,int(sokDead),int(sokkuriCorpse!=nullptr),armor->mHealth,int(armDead),int(armorCorpse!=nullptr));std::fflush(stdout);}
  if(sokDead&&armDead&&sokkuriCorpse&&armorCorpse){stage=3;return result;}
  if(observed>2500&&!sokDamage&&!armDamage&&!sokDead&&!armDead){std::puts("FAIL P2_GROUND_COMBAT no_natural_damage");std::fflush(stdout);std::_Exit(1);}
  if(observed>6000){std::puts("FAIL P2_GROUND_COMBAT corpse_timeout");std::fflush(stdout);std::_Exit(1);}
  return result;
 }
 if(stage==3){
  pc_p2_sokkuri_forget(sokkuri);pc_p2_armor_forget(armor);
  require(pc_p2_sokkuri_count()==0&&pc_p2_armor_count()==0,"registries not cleared by forget");
  require(corpseOf(sokkuri)&&corpseOf(armor),"corpse handoff lost on forget");
  std::printf("P2_COMBAT_FORGET species=Sokkuri count=0 registered=0\n");
  std::printf("P2_COMBAT_FORGET species=Armor count=0 registered=0\n");
  std::fflush(stdout);stage=4;return result;
 }
 if(stage==4){
  sokkuriGen->mGenType->init(sokkuriGen);armorGen->mGenType->init(armorGen);
  freshSokkuri=static_cast<Teki*>(sokkuriGen->mLatestSpawnCreature);
  freshArmor=static_cast<Teki*>(armorGen->mLatestSpawnCreature);
  require(freshSokkuri&&freshArmor,"native generator rebirth failed");
  require(freshSokkuri!=sokkuri&&freshArmor!=armor,"allocator reused the same address; stale proof inconclusive");
  pc_p2_sokkuri_setup();pc_p2_armor_setup();
  require(pc_p2_sokkuri_registered(freshSokkuri)&&pc_p2_armor_registered(freshArmor),"fresh actor not bound");
  require(!pc_p2_sokkuri_registered(sokkuri)&&!pc_p2_armor_registered(armor),"old pointer still registered");
  require(pc_p2_sokkuri_count()==1&&pc_p2_armor_count()==1,"registry count after re-entry");
  require(!corpseOf(freshSokkuri)&&!corpseOf(freshArmor),"fresh actor inherited a corpse");
  require(pc_p2_preview_pokos()==-1&&pc_p2_preview_goal()==nullptr,"cargo-free arena Pod ledger changed");
  std::printf("P2_COMBAT_REENTRY species=Sokkuri old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)sokkuri,(void*)freshSokkuri,pc_p2_sokkuri_count());
  std::printf("P2_COMBAT_REENTRY species=Armor old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)armor,(void*)freshArmor,pc_p2_armor_count());
  std::fflush(stdout);stage=5;return result;
 }
 if(stage==5){
  std::puts("PASS P2_GROUND_COMBAT natural_death=2 corpse=2 cleanup=2 reentry=2 injected=0");
  std::fflush(stdout);std::_Exit(0);
 }
 std::fflush(stdout);return result;
}};
'''


def prepare(assets, imported, output):
    cfg = dict(CFG)
    positions = list(DEFAULT_POSITIONS)
    positions[SOKKURI_INDEX] = SOKKURI_POSITION
    positions[ARMOR_INDEX] = ARMOR_POSITION
    cfg['arena_positions'] = tuple(positions)
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    override = dict(
        species=['Sokkuri', 'Armor'],
        generators={'Sokkuri': SOKKURI_ID, 'Armor': ARMOR_ID},
        arena_default=[list(DEFAULT_POSITIONS[SOKKURI_INDEX]),
                       list(DEFAULT_POSITIONS[ARMOR_INDEX])],
        behavior_fixture=[list(SOKKURI_POSITION), list(ARMOR_POSITION)],
        midpoint=list(MIDPOINT), squad_radius=SQUAD_RADIUS,
        natural_combat='the live squad is redeployed in FreeMode around both actors; '
                       'the fixture never writes health, state or events',
        reason='place both actors inside their source sight radii (Sokkuri fp12=150, '
               'Armor fp12=200) of the starting squad so Pikmin attack them naturally',
        production_placement=False,
        pose_name_normalization=normalize_pose_names(run))
    (run / 'ground-combat-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def instrument(source, app=APP):
    if 'P2_GROUND_COMBAT' in source:
        raise ValueError('Room fixture already carries the ground combat app')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstring>\n#include <cmath>\n#include "Generator.h"\n'
                '#include "pc_p2_sokkuri.h"\n#include "pc_p2_armor.h"\n'
                '#include "pc_p2_preview.h"\n')
    return includes + source[:start] + app + source[end:]


def build(native, build_dir, output, head, resume=False, app=None):
    """Build the private instrumented replacement-main fixture (never a run)."""
    from scripts import build_pikmin2_fixture as builder
    from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
    native = native.resolve()
    build_dir = build_dir.resolve()
    output = output.resolve()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text(), app or APP)
    if resume:
        if (output / 'instrumentation.json').exists() or room.read_text() != source:
            raise ValueError('Cannot resume completed or changed fixture')
        record = json.loads((output / 'baseline/provenance.json').read_text())
        if record.get('status') != 'built' or record.get('expected_native_head') != head \
                or builder.git_state(native) != record['observed_source']:
            raise ValueError('Baseline no longer matches source')
        for key in ('inputs', 'fixture_inputs', 'configuration_inputs'):
            builder.check_snapshot(record[key])
    else:
        output.mkdir(parents=True, exist_ok=False)
        room.write_text(source)
        record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    compile_cmd = list(record['commands'][-2])
    compile_cmd[builder.option_index(compile_cmd, '-o')] = str(output / 'room.obj')
    compile_cmd[builder.option_index(compile_cmd, '-MF')] = str(output / 'room.d')
    link = list(record['commands'][-1])
    targets = [i for i, a in enumerate(link) if a.endswith('\\fixture.obj') or a.endswith('/fixture.obj')]
    if len(targets) != 1:
        raise ValueError('Expected one private room object')
    link[targets[0]] = str(output / 'room.obj')
    link[builder.option_index(link, '-o')] = str(output / 'fixture.exe')
    link = [('-Wl,--out-implib,' + str(output / 'fixture.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
    tutorial = native / 'src/plugPikiColin/newPikiGame.cpp'
    tutorial_private = output / 'tutorial.cpp'
    tutorial_private.write_text(instrument_tutorial(tutorial.read_text()))
    tutorial_compile = [str(tutorial_private) if a == str(room) else a for a in compile_cmd]
    tutorial_compile[builder.option_index(tutorial_compile, '-o')] = str(output / 'tutorial.obj')
    tutorial_compile[builder.option_index(tutorial_compile, '-MF')] = str(output / 'tutorial.d')
    targets = [i for i, a in enumerate(link) if a.endswith('libpikmin_legacy.a')]
    if len(targets) != 1:
        raise ValueError('Expected one private legacy archive')
    link.insert(targets[0], str(output / 'tutorial.obj'))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    audit = dict(original_fixture=builder.snapshot([native / 'tools/preview_p2_room.cpp', tutorial]),
                 instrumented=builder.snapshot([room, tutorial_private]),
                 commands=[compile_cmd, tutorial_compile, link], freshness_checks=[])
    for name, command in [('room-compile', compile_cmd), ('tutorial-compile', tutorial_compile),
                          ('room-link', link)]:
        code, text = builder.run(command, build_dir, env)
        (output / (name + '.log')).write_text(text)
        if code:
            raise RuntimeError(name + ' failed')
    builder.require_fresh(Path(record['toolchain']['ninja']['path']), build_dir, audit['freshness_checks'])
    builder.check_snapshot(record['inputs'])
    builder.check_snapshot(record['fixture_inputs'])
    builder.check_snapshot(record['configuration_inputs'])
    if builder.git_state(native) != record['observed_source']:
        raise RuntimeError('Native changed during private replacement')
    audit['artifacts'] = builder.snapshot([output / 'fixture.exe', output / 'room.obj'])
    audit['status'] = 'built'
    (output / 'instrumentation.json').write_text(json.dumps(audit, indent=2) + '\n')


def validate(text, code=0):
    """Check the native log for natural ground-invertebrate combat/lifecycle gates.

    Confined to the fixture's ``P2_COMBAT_*`` markers plus the two module
    ``P2_*_DEAD`` markers and the batch-2 corpse draw. A run that writes health or
    otherwise injects a death fails ``no_injection``.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    ready = re.search(r'P2_COMBAT_READY squad=(\d+) sokkuri_health=[\d.]+ armor_health=[\d.]+', text)
    squad = int(ready.group(1)) if ready else 0
    deploy = re.search(r'P2_COMBAT_DEPLOY squad=(\d+)', text)
    damage = bool(re.search(r'P2_COMBAT_DAMAGE species=(?:Sokkuri|Armor) ', text))
    sokkuri_death = DEATH_MARKERS['Sokkuri'] in text
    armor_death = DEATH_MARKERS['Armor'] in text
    corpse = CORPSE_MARKERS['Sokkuri'] in text and CORPSE_MARKERS['Armor'] in text
    module_death = (bool(re.search(r'P2_SOKKURI_DEAD generator=346005 source_id=79', text))
                    and bool(re.search(r'P2_ARMOR_DEAD generator=346001 source_id=15', text)))
    cleanup = ('P2_COMBAT_FORGET species=Sokkuri count=0 registered=0' in text
               and 'P2_COMBAT_FORGET species=Armor count=0 registered=0' in text)
    reentry = (bool(re.search(r'P2_COMBAT_REENTRY species=Sokkuri old=\S+ new=\S+ stale=0 fresh=1 count=1', text))
               and bool(re.search(r'P2_COMBAT_REENTRY species=Armor old=\S+ new=\S+ stale=0 fresh=1 count=1', text)))
    injected = ('not_natural_combat=1' in text or 'P2_LIFECYCLE_INJECT' in text
                or bool(re.search(r'P2_COMBAT_INJECT', text)))
    checks = dict(
        identity=bool(re.search(r'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0', text))
                 and bool(re.search(r'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=Sokkuri .*generator=346005 .*behavior=native '
                             r'.*source_FSM=implemented', text))
              and bool(re.search(r'P2_ENEMY_READY species=Armor .*generator=346001 .*behavior=native '
                                 r'.*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        live_squad=squad >= 1,
        deployed=bool(deploy) and int(deploy.group(1)) >= 1,
        natural_damage=(damage or (sokkuri_death and armor_death)) and not injected,
        natural_death=(sokkuri_death and armor_death and module_death) and not injected,
        corpse=corpse and 'P2_BATCH2_DRAW corpse=1' in text,
        cleanup=cleanup,
        reentry=reentry,
        no_injection=not injected,
        completion='PASS P2_GROUND_COMBAT' in text,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    gates = dict(
        combat='pass' if checks['natural_damage'] else 'fail',
        death='pass' if checks['natural_death'] else 'fail',
        corpse='pass' if checks['corpse'] else 'fail',
        delivery_reward='untested',
        cleanup='pass' if cleanup else 'fail',
        reentry='pass' if reentry else 'fail',
    )
    required = ('identity', 'ready', 'window', 'live_squad', 'deployed', 'natural_damage',
                'natural_death', 'corpse', 'cleanup', 'reentry', 'no_injection', 'completion',
                'no_extinction')
    return dict(passed=code == 0 and all(checks[name] for name in required),
                checks=checks, gates=gates, squad=squad, exit_code=code,
                delivery_reward_reason='The ground arena is a cargo-free private arena with no Pod '
                                       '(p2-cargo-free.txt, no p2-pod.txt): there is no P2 reward '
                                       'registry to exercise. Deferred to the lifecycle/reward lane '
                                       '(#397).',
                unmeasured=['P2 corpse transport and Pod reward (#397)',
                            'water (MoveWater) branch', 'full action animation bank'],
                limitations=['Redeploys the live squad in FreeMode and repositions the captain; this '
                             'is not player input.',
                             'Fixture rebirth uses the native generator path (mGenType->init) and '
                             'pc_p2_*_setup; it is not a full scene/heap teardown.'])


def run(assets, imported, output, exe, seconds=180):
    """Run the private fixture exe. Do NOT invoke while another lane owns the GL slot."""
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'ground-combat-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=180)
    build_cmd = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        build_cmd.add_argument('--' + flag, type=Path, required=True)
    build_cmd.add_argument('--head', required=True)
    build_cmd.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
