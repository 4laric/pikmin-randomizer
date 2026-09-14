"""Sokkuri (79) + Armor (15) death/corpse/cleanup/re-entry family-owner proof (#165/#407).

Closes the batch-2 ground-invertebrate gates the behavior runners left
``UNMEASURED``: source death path, corpse creation/handoff, module-registry
teardown and reset/re-entry with no stale pointer or duplicate reward.

A private replacement-main fixture (built against a Ninja-fresh private
``pikmin_pc`` exactly like :mod:`experimental.pikmin2_elecbug_immunity_behavior`)
drives the real engine:

* it waits for the cargo-free ground arena, finds the two registered native
  actors by generator (Sokkuri 346005, Armor 346001) and probes the *read-only*
  ``pc_p2_sokkuri_count()``/``pc_p2_armor_count()`` accessors,
* at a scheduled frame it **injects lethal damage** (``mHealth=0``) on both
  actors. This is explicit fixture-injected state, never natural combat, and the
  log says so (``P2_LIFECYCLE_INJECT ... not_natural_combat=1``),
* it observes the source death markers, the forced ``dead1``/``dead`` clip, and
  the host corpse pellet whose ``mPelletView`` is the dead actor,
* it calls the production teardown ``pc_p2_*_forget`` and proves both module
  registries return to zero (no stale registration),
* it respawns each species from its own generator (``mGenType->init``) and
  re-runs ``pc_p2_*_setup``; the probe proves a fresh pointer is bound, the old
  pointer is gone, the registry holds exactly one entry, the fresh actors carry
  no corpse and the cargo-free arena's Pod ledger (``-1``/no Pod) is unchanged.

The ground arena is a cargo-free private arena with no Pod (``p2-cargo-free.txt``
and no ``p2-pod.txt``), so there is no P2 reward registry to exercise here. That
gate is reported ``untested`` and deferred to the lifecycle/reward lane (#397);
the source carry clips (Sokkuri ``type5``, Armor ``carry``) mean this is *not* a
source-backed N/A for the species. The read-only probes are additive native
changes; no reusable fixture, disc asset or player save is touched.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install

try:
    from experimental.pikmin2_batch2_families import FAMILIES
    CFG = dict(FAMILIES['ground'])
except Exception:  # pragma: no cover - import stub used by unit tests
    CFG = {}

SOKKURI_ID = 346005
ARMOR_ID = 346001
SOKKURI_SOURCE_ID = 79
ARMOR_SOURCE_ID = 15
SOKKURI_INDEX = tuple(CFG.get('arena_species', ())).index('Sokkuri') if CFG else 4
ARMOR_INDEX = tuple(CFG.get('arena_species', ())).index('Armor') if CFG else 0
DEFAULT_POSITIONS = tuple(((-(len(CFG.get('arena_species', ())) - 2) / 2 + index) * 120.0,
                          30.0, 1850.0)
                          for index in range(len(CFG.get('arena_species', ())) - 1)) \
    + ((240.0, 30.0, 1500.0),) if CFG else ()
SOKKURI_POSITION = (-100.0, 30.0, 1850.0)
ARMOR_POSITION = (-60.0, 30.0, 1850.0)
SQUAD_X = tuple(-140.0 + (index % 10) * 8.0 for index in range(20))
SQUAD_Z = tuple(1820.0 - (index // 10) * 8.0 for index in range(20))


def position_override():
    return dict(
        species=['Sokkuri', 'Armor'],
        generators={'Sokkuri': SOKKURI_ID, 'Armor': ARMOR_ID},
        arena_default=[list(DEFAULT_POSITIONS[SOKKURI_INDEX]),
                       list(DEFAULT_POSITIONS[ARMOR_INDEX])] if DEFAULT_POSITIONS else [],
        behavior_fixture=[list(SOKKURI_POSITION), list(ARMOR_POSITION)],
        reason='place both actors inside their source sight radii (Sokkuri fp12=150, '
               'Armor fp12=200) of the starting squad so death occurs from a live, '
               'active FSM state',
        production_placement=False)


APP = r'''class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0,deadSokkuri=0,deadArmor=0;
    Teki* sokkuri=nullptr;Teki* armor=nullptr;
    Generator* sokkuriGen=nullptr;Generator* armorGen=nullptr;
    Teki* freshSokkuri=nullptr;Teki* freshArmor=nullptr;
    Pellet* sokkuriCorpse=nullptr;Pellet* armorCorpse=nullptr;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<40000,"ground lifecycle startup timeout");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    ++observed;
    if(stage==0){
        sokkuri=byGenerator(346005);armor=byGenerator(346001);
        require(sokkuri&&armor,"registered Sokkuri/Armor actors present");
        require(pc_p2_sokkuri_registered(sokkuri)&&pc_p2_sokkuri_count()==1,"sokkuri registered exactly once");
        require(pc_p2_armor_registered(armor)&&pc_p2_armor_count()==1,"armor registered exactly once");
        int squad=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive())++squad;}
        require(squad>=1,"live starting squad");
        sokkuriGen=sokkuri->mGenerator;armorGen=armor->mGenerator;
        require(sokkuriGen&&sokkuriGen->mGenType&&sokkuriGen->mGenObject,"sokkuri generator present");
        require(armorGen&&armorGen->mGenType&&armorGen->mGenObject,"armor generator present");
        std::printf("P2_LIFECYCLE_READY squad=%d sokkuri_gen=%u armor_gen=%u sokkuri_reg=1 armor_reg=1\n",squad,sokkuriGen->_70,armorGen->_70);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        if(!deadSokkuri){const char* nm=nullptr;float ph=0;if(pc_p2_sokkuri_clip(sokkuri,nm,ph)&&nm&&std::strcmp(nm,"dead1")==0){deadSokkuri=1;std::printf("P2_LIFECYCLE_DEADCLIP species=Sokkuri source_id=79 clip=%s\n",nm);std::fflush(stdout);}}
        if(!deadArmor){const char* nm=nullptr;float ph=0;if(pc_p2_armor_clip(armor,nm,ph)&&nm&&std::strcmp(nm,"dead")==0){deadArmor=1;std::printf("P2_LIFECYCLE_DEADCLIP species=Armor source_id=15 clip=%s\n",nm);std::fflush(stdout);}}
        if(observed>=30){
            std::printf("P2_LIFECYCLE_INJECT species=Sokkuri,Armor injected_health=0 source=fixture not_natural_combat=1\n");
            sokkuri->mHealth=0.0f;armor->mHealth=0.0f;std::fflush(stdout);stage=2;
        }
        return result;
    }
    if(stage==2){
        if(!deadSokkuri){const char* nm=nullptr;float ph=0;if(pc_p2_sokkuri_clip(sokkuri,nm,ph)&&nm&&std::strcmp(nm,"dead1")==0){deadSokkuri=1;std::printf("P2_LIFECYCLE_DEADCLIP species=Sokkuri source_id=79 clip=%s\n",nm);std::fflush(stdout);}}
        if(!deadArmor){const char* nm=nullptr;float ph=0;if(pc_p2_armor_clip(armor,nm,ph)&&nm&&std::strcmp(nm,"dead")==0){deadArmor=1;std::printf("P2_LIFECYCLE_DEADCLIP species=Armor source_id=15 clip=%s\n",nm);std::fflush(stdout);}}
        if(!sokkuriCorpse){sokkuriCorpse=corpseOf(sokkuri);if(sokkuriCorpse){std::printf("P2_LIFECYCLE_CORPSE species=Sokkuri pellet=1 generator=%u\n",sokkuriGen->_70);std::fflush(stdout);}}
        if(!armorCorpse){armorCorpse=corpseOf(armor);if(armorCorpse){std::printf("P2_LIFECYCLE_CORPSE species=Armor pellet=1 generator=%u\n",armorGen->_70);std::fflush(stdout);}}
        if(observed%60==0){
            int pellets=0,sMatch=0,aMatch=0,inMgr=0;Iterator pi(pelletMgr);CI_LOOP(pi){Pellet* pp=static_cast<Pellet*>(*pi);++pellets;if(pp->mPelletView==static_cast<PelletView*>(sokkuri))sMatch=1;if(pp->mPelletView==static_cast<PelletView*>(armor))aMatch=1;}
            Iterator ti(tekiMgr);CI_LOOP(ti){Teki* tt=static_cast<Teki*>(*ti);if(tt==sokkuri||tt==armor)++inMgr;}
            std::printf("P2_LIFECYCLE_SCAN frame=%d pellets=%d sokkuri_pellet=%d armor_pellet=%d actors_in_mgr=%d "
                        "sok[state=%d motion=%d dead=%d alive=%d] arm[state=%d motion=%d dead=%d alive=%d]\n",
                        observed,pellets,sMatch,aMatch,inMgr,
                        sokkuri->mStateID,sokkuri->mTekiAnimator->getCurrentMotionIndex(),sokkuri->mDeadState,int(sokkuri->isAlive()),
                        armor->mStateID,armor->mTekiAnimator->getCurrentMotionIndex(),armor->mDeadState,int(armor->isAlive()));
            std::fflush(stdout);
        }
        if(sokkuriCorpse&&armorCorpse){stage=3;}
        if(observed>1200){std::puts("FAIL P2_GROUND_LIFECYCLE corpse_timeout");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    if(stage==3){
        pc_p2_sokkuri_forget(sokkuri);pc_p2_armor_forget(armor);
        require(pc_p2_sokkuri_count()==0,"sokkuri registry not cleared by forget");
        require(pc_p2_armor_count()==0,"armor registry not cleared by forget");
        const char* nm=nullptr;float ph=0;
        require(!pc_p2_sokkuri_clip(sokkuri,nm,ph)&&!pc_p2_armor_clip(armor,nm,ph),"stale clip after forget");
        require(corpseOf(sokkuri)&&corpseOf(armor),"corpse handoff lost on forget");
        std::printf("P2_LIFECYCLE_FORGET species=Sokkuri count=0 registered=0\n");
        std::printf("P2_LIFECYCLE_FORGET species=Armor count=0 registered=0\n");
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
        std::printf("P2_LIFECYCLE_REENTRY species=Sokkuri old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)sokkuri,(void*)freshSokkuri,pc_p2_sokkuri_count());
        std::printf("P2_LIFECYCLE_REENTRY species=Armor old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)armor,(void*)freshArmor,pc_p2_armor_count());
        std::printf("P2_LIFECYCLE_NOREWARD pod=0 pokos=%d fresh_corpses=0\n",pc_p2_preview_pokos());
        std::fflush(stdout);stage=5;return result;
    }
    if(stage==5){
        std::puts("PASS P2_GROUND_LIFECYCLE death=Sokkuri,Armor corpse=2 registry_empty=2 reentry=2 stale=0 duplicate_reward=0 injected=1");
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
    from experimental.pikmin2_sokkuri_behavior import normalize_pose_names
    override = position_override()
    override['pose_name_normalization'] = normalize_pose_names(run)
    (run / 'ground-lifecycle-override.json').write_text(json.dumps(override, indent=2) + '\n')
    return run


def instrument(source, app=APP):
    if 'P2_LIFECYCLE_REENTRY' in source:
        raise ValueError('Room fixture already carries the ground lifecycle app')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstring>\n#include "Generator.h"\n#include "pc_p2_sokkuri.h"\n'
                '#include "pc_p2_armor.h"\n#include "pc_p2_preview.h"\n')
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
    for name, command in [('room-compile', compile_cmd), ('tutorial-compile', tutorial_compile), ('room-link', link)]:
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


def _order(text, pattern):
    match = re.search(pattern, text)
    return match.start() if match else None


def validate(text, code=0):
    """Check the native log for the family-owner death/corpse/cleanup/re-entry gates.

    Confined to ``P2_LIFECYCLE_*``, the two module ``P2_*_DEAD`` markers and the
    batch-2 corpse draw. Injected damage is labelled by the fixture.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    ready = re.search(r'P2_LIFECYCLE_READY squad=(\d+) sokkuri_gen=346005 armor_gen=346001', text)
    squad = int(ready.group(1)) if ready else 0
    death = (bool(re.search(r'P2_SOKKURI_DEAD generator=346005 source_id=79', text))
             and bool(re.search(r'P2_ARMOR_DEAD generator=346001 source_id=15', text)))
    natural_label = bool(re.search(r'P2_SOKKURI_NATURAL_DEATH generator=346005 source_id=79 '
                                   r'natural=0', text))
    natural_damage_seen = bool(re.search(r'P2_SOKKURI_DAMAGE generator=346005 source_id=79 '
                                         r'health=\d+\.\d+', text))
    deadclips = (bool(re.search(r'P2_LIFECYCLE_DEADCLIP species=Sokkuri source_id=79 clip=dead1', text))
                 and bool(re.search(r'P2_LIFECYCLE_DEADCLIP species=Armor source_id=15 clip=dead', text)))
    corpse = (bool(re.search(r'P2_LIFECYCLE_CORPSE species=Sokkuri pellet=1 generator=346005', text))
              and bool(re.search(r'P2_LIFECYCLE_CORPSE species=Armor pellet=1 generator=346001', text))
              and 'P2_BATCH2_DRAW corpse=1' in text)
    cleanup = (bool(re.search(r'P2_LIFECYCLE_FORGET species=Sokkuri count=0 registered=0', text))
               and bool(re.search(r'P2_LIFECYCLE_FORGET species=Armor count=0 registered=0', text)))
    reentry = (bool(re.search(r'P2_LIFECYCLE_REENTRY species=Sokkuri old=\S+ new=\S+ stale=0 fresh=1 count=1', text))
               and bool(re.search(r'P2_LIFECYCLE_REENTRY species=Armor old=\S+ new=\S+ stale=0 fresh=1 count=1', text)))
    noreward = bool(re.search(r'P2_LIFECYCLE_NOREWARD pod=0 pokos=-1 fresh_corpses=0', text))
    injected = 'P2_LIFECYCLE_INJECT species=Sokkuri,Armor injected_health=0 source=fixture not_natural_combat=1' in text
    checks = dict(
        identity=bool(re.search(r'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0', text))
                 and bool(re.search(r'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        live_squad=squad >= 1,
        injected_damage=injected,
        death=death,
        natural_label=natural_label,
        natural_damage_seen=natural_damage_seen,
        dead_clip=deadclips,
        corpse=corpse,
        cleanup=cleanup,
        reentry=reentry,
        no_duplicate_reward=noreward,
        completion='PASS P2_GROUND_LIFECYCLE' in text,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    gates = dict(
        death='pass' if (death and deadclips) else 'fail',
        corpse='pass' if corpse else 'fail',
        delivery_reward='untested',
        cleanup='pass' if cleanup else 'fail',
        reentry='pass' if reentry else 'fail',
    )
    required = ('identity', 'window', 'live_squad', 'injected_damage', 'death', 'natural_label',
                'dead_clip', 'corpse', 'cleanup', 'reentry', 'no_duplicate_reward', 'completion',
                'no_extinction')
    return dict(passed=code == 0 and all(checks[name] for name in required),
                checks=checks, gates=gates, squad=squad, exit_code=code,
                delivery_reward_reason='The ground arena is a cargo-free private arena with no Pod '
                                       '(p2-cargo-free.txt, no p2-pod.txt): there is no P2 reward '
                                       'registry to exercise. Deferred to the lifecycle/reward lane '
                                       '(#397). Source carry clips exist (Sokkuri type5, Armor carry), '
                                       'so this is not a source-backed N/A for the species.',
                unmeasured=['natural combat (damage is fixture-injected)',
                            'P2 corpse transport and Pod reward (#397)',
                            'water (MoveWater) branch', 'full action animation bank'],
                limitations=['Fixture injects lethal damage (mHealth=0); this is not a receiver/combat proof.',
                             'Fixture rebirth uses the native generator path (mGenType->init) and '
                             'pc_p2_*_setup; it is not a full scene/heap teardown or campaign resume.'])


def run(assets, imported, output, exe, seconds=150):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'ground-lifecycle-validation.json').write_text(json.dumps(result, indent=2) + '\n')
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
            sub.add_argument('--seconds', type=int, default=150)
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
