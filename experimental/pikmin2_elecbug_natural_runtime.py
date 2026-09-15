"""ElecBug (28) staged-press-flip -> natural lethal-death runtime — no injected health.

Sibling of :mod:`experimental.pikmin2_sokkuri_natural_runtime.py`; closes the
Anode Beetle's chain (#408/#165/#407) with **no** injected health:

* a paired 2-ElecBug isolated roster lets the pair discharge naturally (Yellow
  parked in the sweep proves ``P2_ELECBUG_IMMUNE ... pikmin=yellow species=2``);
* a Purple is teleported onto the beetle with a forced downward velocity
  (P1-derived **staged** landing; not a thrown Pikmin) on one beetle; the
  family-local ``pc_p2_elecbug_check_landing_press`` probe (source
  ``pressCallBack`` adaptation) flips it into Reverse (``P2_ELECBUG_FLIP`` +
  ``state=reverse`` + ``P2_ELECBUG_NATURAL_PRESS``, labelled ``flip=staged-press``
  — the press is not itself natural combat);
* while reversed the beetle is vulnerable and the free-mode squad drains its 500
  HP through the real receiver (``P2_ELECBUG_HIT`` steps) to
  ``P2_ELECBUG_DEAD ... health=0`` — **death is natural**;
* corpse -> ``pc_p2_elecbug_forget`` -> generator re-bind follow.

No enemy health/stat is changed and extinction is not disabled. The Purple
species is deployed at runtime via the lane-11 ``pc_p2_set_species`` storage
(P1-derived: the P1 host has no Purple hipdrop state, so the press is a
documented family-local landing probe).
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

try:
    from experimental.pikmin2_batch2_families import FAMILIES
    CFG = dict(FAMILIES['ground'])
except Exception:  # pragma: no cover - import stub used by unit tests
    CFG = {}

ELECBUG_GEN = 346002
ELECBUG_SECOND_GEN = 346010
CONTROL_GEN = 346007
ELECBUG_SOURCE_ID = 28

ELECBUG_A_POSITION = (-100.0, 30.0, 1850.0)
ELECBUG_B_POSITION = (-160.0, 30.0, 1850.0)
CONTROL_POSITION = (240.0, 30.0, 1500.0)

REQUIRED_CHECKS = ('identity', 'window', 'live_squad', 'deploy', 'natural_flip',
                   'staged_press', 'vulnerability_damage', 'natural_death',
                   'yellow_immunity', 'no_inject', 'corpse', 'cleanup', 'reentry',
                   'completion', 'no_extinction')

GOOD_LOG = '\n'.join([
    'P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0',
    'P2_ELECBUG_BIND generator=346010 source_id=28 visual_only=0',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_ELECBUG_NATURAL_READY squad=20 elecbug_gen=346002 pair_gen=346010 reg=2',
    'P2_ELECBUG_NATURAL_DEPLOY free_squad=20 purple=1 yellow=1',
    'P2_ELECBUG_NATURAL_PRESS generator=346002 purple=1 source_id=28 state=charge',
    'P2_ELECBUG_FLIP generator=346002 source_id=28',
    'P2_ELECBUG_STATE generator=346002 state=reverse',
    'P2_ELECBUG_HIT generator=346002 source_id=28 health=380.0',
    'P2_ELECBUG_HIT generator=346002 source_id=28 health=210.0',
    'P2_ELECBUG_HIT generator=346002 source_id=28 health=95.0',
    'P2_ELECBUG_HIT generator=346002 source_id=28 health=24.0',
    'P2_ELECBUG_IMMUNE generator=346010 source_id=28 pikmin=yellow species=2',
    'P2_ELECBUG_DEAD generator=346002 source_id=28 health=0',
    'P2_ELECBUG_NATURAL_CORPSE pellet=1',
    'P2_ELECBUG_NATURAL_FORGET count=1',
    'P2_ELECBUG_NATURAL_REENTRY old=0x1 new=0x2 stale=0 fresh=1 count=2',
    'PASS P2_ELECBUG_NATURAL_RUNTIME flip=staged-press death=natural immunity=yellow '
    'corpse=1 cleanup=1 reentry=1 injected=0',
])


def validate(text, code=0):
    """Validate a synthetic/real native log for the natural ElecBug chain.

    Returns ``dict(passed, checks, gates, exit_code, hit_values)``. ``passed``
    is True only when the exit code is 0 and every required check holds.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')

    bind = re.search(r'P2_ELECBUG_BIND generator=346002 source_id=28 visual_only=0', text)
    window = re.search(r'Experimental preview window set to 960x540 windowed and centered', text)
    ready = re.search(r'P2_ELECBUG_NATURAL_READY squad=(\d+) elecbug_gen=346002', text)
    deploy = re.search(r'P2_ELECBUG_NATURAL_DEPLOY free_squad=(\d+)', text)
    flip = re.search(r'P2_ELECBUG_FLIP generator=346002 source_id=28', text)
    reverse = re.search(r'P2_ELECBUG_STATE generator=346002 state=reverse', text)
    natural_press = re.search(r'P2_ELECBUG_NATURAL_PRESS generator=346002 purple=1', text)
    hits = re.findall(r'P2_ELECBUG_HIT generator=346002 source_id=28 health=([\d.]+)', text)
    dead = re.search(r'P2_ELECBUG_DEAD generator=346002 source_id=28 health=0', text)
    immune_yellow = re.search(
        r'P2_ELECBUG_IMMUNE generator=\d+ source_id=28 pikmin=yellow species=2', text)
    inject = re.search(r'P2_LIFECYCLE_INJECT|not_natural_combat=1|injected_health|mHealth=', text)
    corpse = re.search(r'P2_ELECBUG_NATURAL_CORPSE pellet=1', text)
    cleanup = re.search(r'P2_ELECBUG_NATURAL_FORGET count=1', text)
    reentry = re.search(
        r'P2_ELECBUG_NATURAL_REENTRY old=\S+ new=\S+ stale=0 fresh=1 count=2', text)
    pass_line = re.search(r'PASS P2_ELECBUG_NATURAL_RUNTIME[^\n]*', text)
    extinction = re.search(r'Extinction', text, re.IGNORECASE)
    staged_press = 'flip=staged-press' in text and 'flip=natural' not in text
    blocked = re.search(r'natural death timeout \(health stalled\)', text)
    blocked_marker = re.search(r'P2_ELECBUG_NATURAL_BLOCKED health=([\d.]+) squad=(\d+)', text)

    checks = dict(
        identity=bool(bind),
        window=bool(window),
        live_squad=int(ready.group(1)) >= 1 if ready else False,
        deploy=int(deploy.group(1)) >= 1 if deploy else False,
        natural_flip=bool(flip) and bool(reverse) and bool(natural_press),
        staged_press=staged_press,
        vulnerability_damage=bool(hits),
        natural_death=bool(dead),
        yellow_immunity=bool(immune_yellow),
        no_inject=inject is None,
        corpse=bool(corpse),
        cleanup=bool(cleanup),
        reentry=bool(reentry),
        completion=bool(pass_line),
        no_extinction=extinction is None,
    )
    passed = code == 0 and all(checks[name] for name in REQUIRED_CHECKS)
    blocking_reason = None
    if blocked or blocked_marker:
        floors = [float(v) for v in re.findall(r'P2_ELECBUG_NATURAL_OBSERVE tick=\d+ health=([\d.]+)', text)]
        blocking_reason = (
            f'beetle not drained: health_floor={min(floors) if floors else None} '
            f'(life=500), P2_ELECBUG_HIT hits={len(hits)}')
    return dict(passed=passed, checks=checks, exit_code=code,
                hit_values=[float(v) for v in hits], blocking_reason=blocking_reason)


APP = r'''class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0,dischargeWait=0,flipTick=0;
    bool dischargeSeen=false,flipped=false;
    float minHealth=9999.0f;
    Teki* a=nullptr;Teki* b=nullptr;Generator* aGen=nullptr;
    Pellet* corpse=nullptr;Teki* freshA=nullptr;
    Piki* purple=nullptr;Piki* yellow=nullptr;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator&&t->mGenerator->_70==id)return t;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
    const char* stateOf(Teki* t){return pc_p2_elecbug_state_name(t);}
    bool isReverse(const char* s){return s&&std::strcmp(s,"reverse")==0;}
    bool isDischarging(const char* s){return s&&(std::strcmp(s,"discharge")==0||std::strcmp(s,"childdischarge")==0);}
    bool isDead(const char* s){return s&&std::strcmp(s,"dead")==0;}
    int aliveTotal(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++c;}return c;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<60000,"elecbug natural startup timeout");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    ++observed;
    if(stage==0){
        a=byGenerator(346002);b=byGenerator(346010);
        require(a&&b,"two ElecBug actors present");
        require(pc_p2_elecbug_registered(a)&&pc_p2_elecbug_registered(b)&&pc_p2_elecbug_count()==2,"elecbug registered exactly twice");
        require(aliveTotal()>=1,"live starting squad");
        aGen=a->mGenerator;require(aGen&&aGen->mGenType&&aGen->mGenObject,"elecbug A generator present");
        std::printf("P2_ELECBUG_NATURAL_READY squad=%d elecbug_gen=346002 pair_gen=346010 reg=2\n",aliveTotal());
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;if(idx==0){pc_p2_set_species(p,P2SpeciesPurple);purple=p;}else if(idx==1){pc_p2_set_species(p,P2SpeciesYellow);yellow=p;}++idx;}
        require(purple&&yellow,"purple and yellow designated");
        // Yellow parked at the pair midpoint (inside both 70-unit discharge sweeps,
        // electric-immune so it survives); purple + reds parked safely far away so
        // the natural pair can charge/discharge undisturbed before the flip phase.
        Vector3f mid=Vector3f((a->getPosition().x+b->getPosition().x)*0.5f,0,a->getPosition().z);
        mid.y=mapMgr->getMinY(mid.x,mid.z,true);yellow->resetPosition(mid);
        int park=0;Iterator p2(pikiMgr);CI_LOOP(p2){Piki* p=static_cast<Piki*>(*p2);if(!p||!p->isAlive()||p==yellow)continue;Vector3f pt=Vector3f(-400.0f,0,1850.0f+float(park)*2.0f);pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++park;}
        yellow->changeMode(PikiMode::FreeMode,n);
        Vector3f npos=Vector3f(a->getPosition().x+60.0f,0,a->getPosition().z-60.0f);npos.y=mapMgr->getMinY(npos.x,npos.z,true);n->resetPosition(npos);
        std::printf("P2_ELECBUG_NATURAL_DEPLOY free_squad=%d purple=1 yellow=1\n",aliveTotal());
        std::fflush(stdout);stage=2;return result;
    }
    if(stage==2){
        const char* sa=stateOf(a);const char* sb=stateOf(b);
        if(!dischargeSeen&&(isDischarging(sa)||isDischarging(sb))){dischargeSeen=true;std::printf("P2_ELECBUG_NATURAL_DISCHARGE tick=%d\n",observed);std::fflush(stdout);}
        // Wait for the discharge to fully end before the first staged landing so
        // the Purple is not pressed and shocked while A is still discharging.
        if(dischargeSeen&&!isDischarging(sa)&&!isDischarging(sb)){stage=3;}
        require(observed<3600,"pair never discharged");
        return result;
    }
    if(stage==3){
        // Stage a natural Purple landing overhead: place the Purple on the target
        // with a descending velocity so the family-local landing probe flips the
        // beetle through the source press receiver (P1-derived; the host has no
        // Purple hipdrop state). Mirrors preview_p2_purple_direct's staged arc.
        Vector3f onto=a->getPosition();onto.y=mapMgr->getMinY(onto.x,onto.z,true);
        purple->resetPosition(onto);
        purple->mVelocity=Vector3f(0.0f,-100.0f,0.0f);
        purple->changeMode(PikiMode::FreeMode,n);
        std::printf("P2_ELECBUG_NATURAL_THROW tick=%d purple=1\n",observed);
        std::fflush(stdout);stage=4;return result;
    }
    if(stage==4){
        const char* sa=stateOf(a);
        if(a->mHealth>0.0f&&a->mHealth<minHealth)minHealth=a->mHealth;
        if(!flipped&&isReverse(sa)){
            flipped=true;
            std::printf("P2_ELECBUG_NATURAL_FLIPPED tick=%d\n",observed);std::fflush(stdout);
            int k=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||p==purple||p==yellow)continue;float ang=float(k)*6.2831853f/18.f;Vector3f pt=a->getPosition()+Vector3f(14.f*std::sin(ang),0.f,14.f*std::cos(ang));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++k;}
        }
        // Re-designate a live Purple if the current one was shocked to death, so the
        // barrage can keep the beetle flipped through recovery without injecting.
        if(purple&&!purple->isAlive()){
            Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&pc_p2_species(p)==P2SpeciesRed){pc_p2_set_species(p,P2SpeciesPurple);purple=p;std::printf("P2_ELECBUG_NATURAL_REDESIGNATE tick=%d purple=1\n",observed);std::fflush(stdout);break;}}
        }
        // Barrage: re-stage the Purple landing (only while A is not discharging, so
        // the Purple is never pressed into a live discharge).
        if(a->mHealth>0.0f&&!isDead(sa)&&!isDischarging(sa)&&purple&&purple->isAlive()&&observed%25==0){
            Vector3f onto=a->getPosition();onto.y=mapMgr->getMinY(onto.x,onto.z,true);
            purple->resetPosition(onto);
            purple->mVelocity=Vector3f(0.0f,-100.0f,0.0f);
            purple->changeMode(PikiMode::FreeMode,n);
        }
        if(a->mHealth<=0.0f||isDead(sa)){
            std::printf("P2_ELECBUG_NATURAL_DIED tick=%d health=%.2f\n",observed,a->mHealth);std::fflush(stdout);stage=5;return result;
        }
        if(observed%60==0){std::printf("P2_ELECBUG_NATURAL_OBSERVE tick=%d health=%.2f state=%s squad=%d\n",observed,a->mHealth,sa?sa:"null",aliveTotal());std::fflush(stdout);}
        if(observed>=7080){std::printf("P2_ELECBUG_NATURAL_BLOCKED health=%.2f squad=%d\n",minHealth,aliveTotal());std::fflush(stdout);}
        require(observed<7200,"natural death timeout (health stalled)");
        return result;
    }
    if(stage==5){
        if(!corpse)corpse=corpseOf(a);
        if(corpse){std::printf("P2_ELECBUG_NATURAL_CORPSE pellet=1\n");std::fflush(stdout);stage=6;}
        require(observed<7560,"corpse handoff timeout");
        return result;
    }
    if(stage==6){
        pc_p2_elecbug_forget(a);
        require(pc_p2_elecbug_count()==1,"elecbug registry not cleared for A (B remains)");
        std::printf("P2_ELECBUG_NATURAL_FORGET count=%lu\n",pc_p2_elecbug_count());std::fflush(stdout);
        aGen->mGenType->init(aGen);
        freshA=static_cast<Teki*>(aGen->mLatestSpawnCreature);
        require(freshA&&freshA!=a,"native generator rebirth failed / reused address");
        pc_p2_elecbug_setup();
        require(pc_p2_elecbug_registered(freshA)&&!pc_p2_elecbug_registered(a),"fresh bind / old unbound");
        require(pc_p2_elecbug_count()==2,"registry count after re-entry");
        std::printf("P2_ELECBUG_NATURAL_REENTRY old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)a,(void*)freshA,pc_p2_elecbug_count());
        capture("elecbug-natural-final.ppm");
        std::fflush(stdout);stage=7;return result;
    }
    if(stage==7){
        std::puts("PASS P2_ELECBUG_NATURAL_RUNTIME flip=staged-press death=natural immunity=yellow corpse=1 cleanup=1 reentry=1 injected=0");
        std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);return result;
}};
'''


def elecbug_pair_cfg():
    cfg = dict(CFG)
    cfg['arena_species'] = ('ElecBug', 'ElecBug', 'P1 Chappy')
    cfg['arena_ids'] = (ELECBUG_GEN, ELECBUG_SECOND_GEN, CONTROL_GEN)
    cfg['arena_positions'] = (ELECBUG_A_POSITION, ELECBUG_B_POSITION, CONTROL_POSITION)
    return cfg


def prepare(assets, imported, output):
    cfg = elecbug_pair_cfg()
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    normalize_pose_names(run)
    return run


def instrument(source):
    if 'P2_ELECBUG_NATURAL_REENTRY' in source:
        raise ValueError('Room fixture already carries the ElecBug natural app')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstring>\n#include "Generator.h"\n#include "pc_p2_elecbug.h"\n'
                '#include "pc_p2_species.h"\n#include "pc_p2_purple.h"\n'
                '#include "pc_p2_preview.h"\n')
    return includes + source[:start] + APP + source[end:]


def build(native, build_dir, output, head, resume=False):
    """Build the private instrumented replacement-main fixture (never a run)."""
    from scripts import build_pikmin2_fixture as builder
    from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
    native = native.resolve()
    build_dir = build_dir.resolve()
    output = output.resolve()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text())
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
    (run_dir / 'elecbug-natural-validation.json').write_text(json.dumps(result, indent=2) + '\n')
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
