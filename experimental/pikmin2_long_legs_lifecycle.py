"""Houdai (66) + BigFoot (69) natural encounter, death, cleanup and re-entry (#173/#312).

Closes the batch-2 Long Legs gates the bind-pose visual slice left ``UNMEASURED``:
real natural combat damage to the registered host actors, the source foot-crush
landing attack reaching a live squad, the policy death output, corpse handoff,
module-registry teardown and reset/re-entry with no stale pointer or duplicate
reward. Regenerates the arena from the P2 disc (recovered by
:mod:`experimental.pikmin2_long_legs_assets`) instead of reusing a stale bank.

A private replacement-main fixture (built against a Ninja-fresh private
``pikmin_pc`` exactly like :mod:`experimental.pikmin2_ground_lifecycle_behavior`)
drives the real engine:

* it waits for the cargo-free Long Legs arena, finds the two registered native
  actors by generator (Houdai 312001, BigFoot 312002) and probes the *read-only*
  ``pc_p2_long_legs_count()``/``pc_p2_long_legs_registered()`` accessors,
* it assigns the live squad to attack BigFoot with the real Pikmin Attack action,
  so the host observes incremental ``P2_LONG_LEGS_DAMAGE`` (natural combat, not a
  fixture health write), and BigFoot is staged under the squad so the landing
  foot-crush reaches live Pikmin (``P2_LONG_LEGS_CRUSH ... pikmin>=1``),
* it lets the proxy die naturally; if combat does not kill it within the window
  it **injects** lethal damage (``mHealth=0``) on both actors, and the log labels
  that injection (``P2_LL_INJECT ... not_natural_combat=1``),
* it observes the policy death output (BigFoot ``P2_LONG_LEGS_BIRTH count=30``,
  Houdai no children by source) and the host corpse pellet whose ``mPelletView``
  is the dead proxy actor,
* it calls the production teardown ``pc_p2_long_legs_forget`` and proves both
  module registries return to zero (no stale registration),
* it respawns each species from its own generator (``mGenType->init``) and
  re-runs ``pc_p2_long_legs_setup``; the probe proves a fresh pointer is bound,
  the old pointer is gone, the registry holds exactly two entries, the fresh
  actors carry no corpse and the cargo-free arena's Pod ledger (``-1``/no Pod)
  is unchanged.

The Long Legs source has no carcass (the audit's "no carcass" flag): dying with
no held treasure births children (BigFoot -> 30 Mitites). The ``P2_LL_CORPSE``
pellet is the P1 Chappy placement vehicle's own corpse, a proxy artifact, not a
source Long Legs carcass; it is retained only to prove proxy death/forget
handoff. The actual Mitite children, weapons, IK foot positions and rewards stay
with lanes 14/20/08/06; the policy only emits intents.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import prepare as _prepare
from experimental.pikmin2_long_legs_arena import CFG
from experimental.pikmin2_long_legs_install import install, verify_install
from experimental.pikmin2_long_legs_visual import convert as convert_visual

HOUDAI_ID = 312001
BIGFOOT_ID = 312002
HOUDAI_SOURCE_ID = 66
BIGFOOT_SOURCE_ID = 69

# Impact Site squad overlay places 20 reds at x in [-140,-68], z in [1804,1820]
# (scripts/preview_pikmin2_room.ensure_pikmin_squad). Put BigFoot among the squad
# so the landing foot-crush and combat start immediately; Houdai stays clear so
# its gunless-no-press schedule is observed without crush interference.
DEFAULT_POSITIONS = tuple(CFG['arena_positions'])
SPECIES = tuple(CFG['arena_species'])
HOUDAI_INDEX = SPECIES.index('Houdai')
BIGFOOT_INDEX = SPECIES.index('BigFoot')
HOUDAI_POSITION = (120.0, 30.0, 1850.0)
BIGFOOT_POSITION = (-104.0, 30.0, 1816.0)


def position_override():
    positions = dict(
        species=['Houdai', 'BigFoot'],
        generators={'Houdai': HOUDAI_ID, 'BigFoot': BIGFOOT_ID},
        arena_default=[list(DEFAULT_POSITIONS[HOUDAI_INDEX]),
                       list(DEFAULT_POSITIONS[BIGFOOT_INDEX])],
        behavior_fixture=[list(HOUDAI_POSITION), list(BIGFOOT_POSITION)],
        reason='stage BigFoot under the starting squad so the source landing '
               'foot-crush and real Pikmin attacks reach it immediately',
        production_placement=False)
    return positions


APP = r'''class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0;
    Teki* houdai=nullptr;Teki* bigfoot=nullptr;
    Generator* houdaiGen=nullptr;Generator* bigfootGen=nullptr;
    Teki* freshHoudai=nullptr;Teki* freshBigfoot=nullptr;
    Pellet* houdaiCorpse=nullptr;Pellet* bigfootCorpse=nullptr;
    bool bigfootDied=false;bool houdaiDied=false;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
    int assignAttack(Teki* target){int n=0;Iterator a(pikiMgr);CI_LOOP(a){Piki* v=static_cast<Piki*>(*a);if(!v->isAlive())continue;
        v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
        v->mActiveAction->mChildActions[PikiAction::Attack].initialise(target);v->mMode=PikiMode::AttackMode;++n;}return n;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<40000,"long legs lifecycle startup timeout");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    ++observed;
    if(stage==0){
        houdai=byGenerator(312001);bigfoot=byGenerator(312002);
        require(houdai&&bigfoot,"registered Long Legs actors present");
        require(pc_p2_long_legs_registered(houdai)&&pc_p2_long_legs_registered(bigfoot),"long legs registered");
        require(pc_p2_long_legs_count()==2,"long legs registered exactly twice");
        int squad=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive())++squad;}
        require(squad>=1,"live starting squad");
        houdaiGen=houdai->mGenerator;bigfootGen=bigfoot->mGenerator;
        require(houdaiGen&&houdaiGen->mGenType&&houdaiGen->mGenObject,"houdai generator present");
        require(bigfootGen&&bigfootGen->mGenType&&bigfootGen->mGenObject,"bigfoot generator present");
        int attackers=assignAttack(bigfoot);
        require(attackers>0,"no attackers after ready");
        std::printf("P2_LL_READY squad=%d houdai_gen=%u bigfoot_gen=%u attack=%d\n",squad,houdaiGen->_70,bigfootGen->_70,attackers);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        if(!bigfoot->isAlive()&&!bigfootDied){bigfootDied=true;std::printf("P2_LL_NATURAL_DEATH bigfoot=1 health=%.2f\n",bigfoot->mHealth);std::fflush(stdout);}
        if(bigfootDied){
            int a=assignAttack(houdai);
            std::printf("P2_LL_ATTACK_HOUDAI attack=%d\n",a);std::fflush(stdout);stage=2;
        } else if(observed>=4500){
            std::printf("P2_LL_INJECT species=BigFoot injected_health=0 source=fixture not_natural_combat=1\n");
            bigfoot->mHealth=0.0f;std::fflush(stdout);
        }
        return result;
    }
    if(stage==2){
        if(!houdai->isAlive()&&!houdaiDied){houdaiDied=true;std::printf("P2_LL_NATURAL_DEATH houdai=1 health=%.2f\n",houdai->mHealth);std::fflush(stdout);}
        if(houdaiDied){stage=3;}
        else if(observed>=7000){
            std::printf("P2_LL_INJECT species=Houdai injected_health=0 source=fixture not_natural_combat=1\n");
            houdai->mHealth=0.0f;std::fflush(stdout);
        }
        return result;
    }
    if(stage==3){
        if(!bigfootCorpse){bigfootCorpse=corpseOf(bigfoot);if(bigfootCorpse){std::printf("P2_LL_CORPSE species=BigFoot pellet=1 generator=%u\n",bigfootGen->_70);std::fflush(stdout);}}
        if(!houdaiCorpse){houdaiCorpse=corpseOf(houdai);if(houdaiCorpse){std::printf("P2_LL_CORPSE species=Houdai pellet=1 generator=%u\n",houdaiGen->_70);std::fflush(stdout);}}
        if(observed%60==0){
            int pellets=0,bMatch=0,hMatch=0,inMgr=0;Iterator pi(pelletMgr);CI_LOOP(pi){Pellet* pp=static_cast<Pellet*>(*pi);++pellets;if(pp->mPelletView==static_cast<PelletView*>(bigfoot))bMatch=1;if(pp->mPelletView==static_cast<PelletView*>(houdai))hMatch=1;}
            Iterator ti(tekiMgr);CI_LOOP(ti){Teki* tt=static_cast<Teki*>(*ti);if(tt==bigfoot||tt==houdai)++inMgr;}
            std::printf("P2_LL_SCAN frame=%d pellets=%d bigfoot_pellet=%d houdai_pellet=%d actors_in_mgr=%d "
                        "bf[state=%d motion=%d dead=%d alive=%d] hd[state=%d motion=%d dead=%d alive=%d]\n",
                        observed,pellets,bMatch,hMatch,inMgr,
                        bigfoot->mStateID,bigfoot->mTekiAnimator->getCurrentMotionIndex(),bigfoot->mDeadState,int(bigfoot->isAlive()),
                        houdai->mStateID,houdai->mTekiAnimator->getCurrentMotionIndex(),houdai->mDeadState,int(houdai->isAlive()));
            std::fflush(stdout);
        }
        if(bigfootCorpse&&houdaiCorpse)stage=4;
        if(observed>9000){std::puts("FAIL P2_LONG_LEGS_LIFECYCLE corpse_timeout");std::fflush(stdout);std::_Exit(1);}
        return result;
    }
    if(stage==4){
        pc_p2_long_legs_forget(bigfoot);pc_p2_long_legs_forget(houdai);
        require(pc_p2_long_legs_count()==0,"long legs registry not cleared by forget");
        require(corpseOf(bigfoot)&&corpseOf(houdai),"corpse handoff lost on forget");
        std::printf("P2_LL_FORGET species=BigFoot count=0 registered=0\n");
        std::printf("P2_LL_FORGET species=Houdai count=0 registered=0\n");
        std::fflush(stdout);stage=5;return result;
    }
    if(stage==5){
        bigfootGen->mGenType->init(bigfootGen);houdaiGen->mGenType->init(houdaiGen);
        freshBigfoot=static_cast<Teki*>(bigfootGen->mLatestSpawnCreature);
        freshHoudai=static_cast<Teki*>(houdaiGen->mLatestSpawnCreature);
        require(freshBigfoot&&freshHoudai,"native generator rebirth failed");
        require(freshBigfoot!=bigfoot&&freshHoudai!=houdai,"allocator reused the same address; stale proof inconclusive");
        pc_p2_long_legs_setup();
        require(pc_p2_long_legs_registered(freshBigfoot)&&pc_p2_long_legs_registered(freshHoudai),"fresh actor not bound");
        require(!pc_p2_long_legs_registered(bigfoot)&&!pc_p2_long_legs_registered(houdai),"old pointer still registered");
        require(pc_p2_long_legs_count()==2,"registry count after re-entry");
        require(!corpseOf(freshBigfoot)&&!corpseOf(freshHoudai),"fresh actor inherited a corpse");
        require(pc_p2_preview_pokos()==-1&&pc_p2_preview_goal()==nullptr,"cargo-free arena Pod ledger changed");
        std::printf("P2_LL_REENTRY species=BigFoot old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)bigfoot,(void*)freshBigfoot,pc_p2_long_legs_count());
        std::printf("P2_LL_REENTRY species=Houdai old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)houdai,(void*)freshHoudai,pc_p2_long_legs_count());
        std::printf("P2_LL_NOREWARD pod=0 pokos=%d fresh_corpses=0\n",pc_p2_preview_pokos());
        std::fflush(stdout);stage=6;return result;
    }
    if(stage==6){
        std::puts("PASS P2_LONG_LEGS_LIFECYCLE death=Houdai,BigFoot corpse=2 registry_empty=2 reentry=2 stale=0 duplicate_reward=0");
        std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);return result;
}};
'''


def prepare(assets, imported, output):
    cfg = dict(CFG)
    positions = list(CFG['arena_positions'])
    positions[HOUDAI_INDEX] = HOUDAI_POSITION
    positions[BIGFOOT_INDEX] = BIGFOOT_POSITION
    cfg['arena_positions'] = tuple(positions)
    run = _prepare(cfg, assets, imported, output,
                   installer=install, verifier=verify_install)
    convert_visual(run / 'assets/dataDir/courses/pikmin2room')
    (run / 'long-legs-lifecycle-override.json').write_text(
        json.dumps(position_override(), indent=2) + '\n')
    return run


def instrument(source, app=APP):
    if 'P2_LL_REENTRY' in source:
        raise ValueError('Room fixture already carries the Long Legs lifecycle app')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstring>\n#include "Generator.h"\n#include "pc_p2_long_legs.h"\n'
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


def validate(text, code=0):
    """Check the native log for the family-owner encounter/lifecycle gates.

    Confined to the Long Legs ``P2_LONG_LEGS_*`` markers and ``P2_LL_*``
    fixture markers. Injected damage is labelled by the fixture; natural combat
    damage (``P2_LONG_LEGS_DAMAGE``) and the landing foot-crush
    (``P2_LONG_LEGS_CRUSH ... pikmin>=1``) are separately evidenced.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    ready = re.search(r'P2_LL_READY squad=(\d+) houdai_gen=312001 bigfoot_gen=312002 attack=(\d+)', text)
    squad = int(ready.group(1)) if ready else 0
    attackers = int(ready.group(2)) if ready else 0
    binds = (bool(re.search(r'P2_LONG_LEGS_BIND generator=312001 species=Houdai .* native_fsm=implemented', text))
             and bool(re.search(r'P2_LONG_LEGS_BIND generator=312002 species=BigFoot .* native_fsm=implemented', text)))
    schedules = (bool(re.search(r'P2_LONG_LEGS_STATE species=Houdai generator=312001 state=(Land|Wait|Flick|Shot)', text))
                 and bool(re.search(r'P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=(Land|Wait|Flick)', text)))
    natural_damage = bool(re.search(r'P2_LONG_LEGS_DAMAGE species=BigFoot generator=312002 '
                                    r'health=(?!0+(?:\.0+)?\s)\d+(\.\d+)? prior=\d+(\.\d+)?', text))
    crush = bool(re.search(r'P2_LONG_LEGS_CRUSH species=BigFoot generator=312002 pikmin=[1-9]\d*', text))
    injected = 'P2_LL_INJECT' in text and 'not_natural_combat=1' in text
    natural_bigfoot_death = bool(re.search(r'P2_LL_NATURAL_DEATH bigfoot=1', text))
    dead_out = (bool(re.search(r'P2_LONG_LEGS_DEAD species=BigFoot generator=312002 health=0 prior_health=[\d.]+', text))
                and bool(re.search(r'P2_LONG_LEGS_DEAD species=Houdai generator=312001 health=0 prior_health=[\d.]+', text)))
    birth = bool(re.search(r'P2_LONG_LEGS_BIRTH species=BigFoot generator=312002 count=30', text))
    corpse = (bool(re.search(r'P2_LL_CORPSE species=BigFoot pellet=1 generator=312002', text))
              and bool(re.search(r'P2_LL_CORPSE species=Houdai pellet=1 generator=312001', text)))
    cleanup = (bool(re.search(r'P2_LL_FORGET species=BigFoot count=0 registered=0', text))
               and bool(re.search(r'P2_LL_FORGET species=Houdai count=0 registered=0', text)))
    reentry = (bool(re.search(r'P2_LL_REENTRY species=BigFoot old=\S+ new=\S+ stale=0 fresh=1 count=2', text))
               and bool(re.search(r'P2_LL_REENTRY species=Houdai old=\S+ new=\S+ stale=0 fresh=1 count=2', text)))
    noreward = bool(re.search(r'P2_LL_NOREWARD pod=0 pokos=-1 fresh_corpses=0', text))
    # Slice 2: Houdai natural combat in its source damage window, shell firing
    # and natural death, with no fixture-injected Houdai lethality.
    houdai_damage_re = re.compile(
        r'P2_LONG_LEGS_DAMAGE species=Houdai generator=312001 '
        r'health=(\d+(?:\.\d+)?) prior=(\d+(?:\.\d+)?)')
    houdai_natural_damage = any(
        float(m.group(1)) > 0 and 0 < float(m.group(2)) - float(m.group(1)) <= 30
        for m in houdai_damage_re.finditer(text))
    houdai_shell_fires = bool(re.search(r'P2_LONG_LEGS_SHELL species=Houdai generator=312001', text))
    houdai_shell_hits = bool(re.search(r'P2_LONG_LEGS_SHELL_HIT species=Houdai generator=312001 pikmin=[1-9]\d*', text))
    houdai_natural_death = (bool(re.search(r'P2_LL_NATURAL_DEATH houdai=1', text))
                            and bool(re.search(r'P2_LONG_LEGS_DEAD species=Houdai generator=312001 '
                                               r'health=0 prior_health=(?!0+(?:\.0+)?\s)[\d.]+', text)))
    houdai_no_inject = not re.search(r'P2_LL_INJECT[^\n]*Houdai', text)
    checks = dict(
        identity=binds,
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        live_squad=squad >= 1,
        attackers=attackers >= 1,
        schedule=schedules,
        natural_damage=natural_damage,
        foot_crush=crush,
        injected_lethal=injected,
        natural_bigfoot_death=natural_bigfoot_death,
        death_output=dead_out,
        birth_children=birth,
        corpse=corpse,
        cleanup=cleanup,
        reentry=reentry,
        no_duplicate_reward=noreward,
        houdai_natural_damage=houdai_natural_damage,
        houdai_shell_fires=houdai_shell_fires,
        houdai_shell_hits=houdai_shell_hits,
        houdai_natural_death=houdai_natural_death,
        houdai_no_inject=houdai_no_inject,
        completion='PASS P2_LONG_LEGS_LIFECYCLE' in text,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    gates = dict(
        identity='pass' if binds else 'fail',
        schedule='pass' if schedules else 'unmeasured',
        combat_damage='pass' if natural_damage else 'unmeasured',
        foot_crush='pass' if crush else 'unmeasured',
        death_output='pass' if (dead_out and birth) else 'fail',
        corpse_handoff='pass' if corpse else 'fail',
        delivery_reward='untested',
        cleanup='pass' if cleanup else 'fail',
        reentry='pass' if reentry else 'fail',
        houdai_natural_damage='pass' if houdai_natural_damage else 'fail',
        houdai_shell_fires='pass' if houdai_shell_fires else 'fail',
        houdai_shell_hits='pass' if houdai_shell_hits else 'fail',
        houdai_natural_death='pass' if houdai_natural_death else 'fail',
        houdai_no_inject='pass' if houdai_no_inject else 'fail',
    )
    # `passed` is the full natural lifecycle contract for both species: natural
    # combat (damage + foot crush + Houdai shell firing/hits), natural death,
    # and clean forget/re-entry. A fixture-injected run still parses and is
    # flagged separately (houdai_no_inject / injected_lethal), but it does not
    # satisfy `passed`.
    required = ('identity', 'window', 'live_squad', 'attackers', 'schedule',
                'natural_damage', 'foot_crush', 'natural_bigfoot_death',
                'death_output', 'birth_children',
                'houdai_natural_damage', 'houdai_shell_fires', 'houdai_shell_hits',
                'houdai_natural_death', 'houdai_no_inject',
                'corpse', 'cleanup', 'reentry', 'no_duplicate_reward',
                'completion', 'no_extinction')
    return dict(passed=code == 0 and all(checks[name] for name in required),
                checks=checks, gates=gates, squad=squad, exit_code=code,
                natural_vs_injected=dict(
                    natural_bigfoot_death=natural_bigfoot_death,
                    natural_houdai_death=houdai_natural_death,
                    natural_combat_damage=natural_damage,
                    houdai_natural_combat_damage=houdai_natural_damage,
                    houdai_shell_fired=houdai_shell_fires,
                    houdai_shell_hits=houdai_shell_hits,
                    inject_present=injected,
                    foot_crush_hits=crush),
                delivery_reward_reason='The cargo-free arena has no Pod (p2-cargo-free.txt); the '
                                       'source no-carcass death outputs Mitite/Shijimi children owned by '
                                       'lane 14, and held-treasure drop is lane 06. Only the policy '
                                       'drop/birth intents are logged here.',
                unmeasured=['actual Mitite child birth (lane 14)', 'held-treasure drop (lane 06)',
                            'IK foot positions and stuck-Pikmin damage rule (collision/host)',
                            'Man-at-Legs shell in-flight pool ownership beyond the host approximation',
                            'full animation bank (skeletal playback)'],
                limitations=['BigFoot proxy was staged under the squad (behavior fixture position, '
                             'not production placement).',
                             'P2_LL_CORPSE pellet is the P1 Chappy placement vehicle corpse; the '
                             'source Long Legs has no carcass and instead emits P2_LONG_LEGS_BIRTH.',
                             'The Man-at-Legs shell reuses lane 20\'s rolling Stone projectile for '
                             'flight; the source THdamaShell curl/gravity is a documented approximation.',
                             'Fixture rebirth uses the native generator path (mGenType->init) and '
                             'pc_p2_long_legs_setup; it is not a full scene/heap teardown or campaign resume.'])


def run(assets, imported, output, exe, seconds=200):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'long-legs-lifecycle-validation.json').write_text(json.dumps(result, indent=2) + '\n')
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
            sub.add_argument('--seconds', type=int, default=200)
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
