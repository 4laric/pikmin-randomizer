"""Sokkuri (79) natural lethal-death runtime — no injected health (#165/#407).

The slice-1 lifecycle fixture proved death/corpse/cleanup/re-entry with an
injected `mHealth=0`. This module closes the same chain **without** injecting
health: a Sokkuri-only ground arena stages the Skitter Leaf on its own Chappy
placement vehicle, the live 20-red squad is deployed in FreeMode around it, and
the real `InteractAttack` receiver drains 120 HP until the native FSM logs
`P2_SOKKURI_DEAD` with a small `prior_health` (a combat-culminated death, not a
single-step jump). The corpse/forget/re-entry chain then runs exactly as in the
slice-1 fixture.

No enemy stat is changed and extinction is not disabled. If the squad cannot
drain the enemy, the fixture records the health floor it reached and fails with
a named blocking mechanism.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_ground_lifecycle_behavior import build as _build, instrument as _instrument
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

try:
    from experimental.pikmin2_batch2_families import FAMILIES
    CFG = dict(FAMILIES['ground'])
except Exception:  # pragma: no cover - import stub used by unit tests
    CFG = {}

SOKKURI_GEN = 346005
CONTROL_GEN = 346007
SOKKURI_POSITION = (-100.0, 30.0, 1850.0)
CONTROL_POSITION = (240.0, 30.0, 1500.0)
LIFE = 120.0
# "small prior_health": more than half the life bank has been drained by combat
# before the lethal frame, so a single injected jump (prior_health ~ full) fails.
PRIOR_HEALTH_MAX = LIFE * 0.5
NATURAL_TICKS = 5400


def sokkuri_only_cfg():
    cfg = dict(CFG)
    cfg['arena_species'] = ('Sokkuri', 'P1 Chappy')
    cfg['arena_ids'] = (SOKKURI_GEN, CONTROL_GEN)
    cfg['arena_positions'] = (SOKKURI_POSITION, CONTROL_POSITION)
    return cfg


APP = r'''class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0,deadTick=0;
    float minHealth=9999.0f;
    Teki* sokkuri=nullptr;Generator* sokkuriGen=nullptr;
    Pellet* corpse=nullptr;Teki* freshSokkuri=nullptr;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id)return a;}return nullptr;}
    Pellet* corpseOf(Teki* actor){if(!actor)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->mPelletView==static_cast<PelletView*>(actor))return p;}return nullptr;}
    int aliveReds(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
    bool deadClip(){const char* nm=nullptr;float ph=0;return pc_p2_sokkuri_clip(sokkuri,nm,ph)&&nm&&std::strcmp(nm,"dead1")==0;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<60000,"sokkuri natural startup timeout");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    ++observed;
    if(stage==0){
        sokkuri=byGenerator(346005);
        require(sokkuri&&pc_p2_sokkuri_registered(sokkuri)&&pc_p2_sokkuri_count()==1,"sokkuri registered exactly once");
        require(aliveReds()>=1,"live red starting squad");
        sokkuriGen=sokkuri->mGenerator;
        require(sokkuriGen&&sokkuriGen->mGenType&&sokkuriGen->mGenObject,"sokkuri generator present");
        std::printf("P2_SOKKURI_NATURAL_READY squad=%d sokkuri_gen=%u reg=1\n",aliveReds(),sokkuriGen->_70);
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        // FreeMode deploy around the Sokkuri; real InteractAttack drains health.
        // No health is written; no AI action beyond FreeMode is assigned.
        Iterator it(pikiMgr);int count=0;CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||p->mColor!=Red)continue;float angle=float(count)*6.2831853f/20.f;Vector3f point=sokkuri->getPosition()+Vector3f(16.f*std::sin(angle),0.f,16.f*std::cos(angle));point.y=mapMgr->getMinY(point.x,point.z,true);p->resetPosition(point);p->changeMode(PikiMode::FreeMode,n);++count;}
        require(count==20,"deployed all 20 red Pikmin");
        Vector3f cap=sokkuri->getPosition()+Vector3f(40.f,0.f,0.f);cap.y=mapMgr->getMinY(cap.x,cap.z,true);n->resetPosition(cap);
        std::printf("P2_SOKKURI_NATURAL_DEPLOY free_squad=%d x=%.2f z=%.2f\n",count,sokkuri->getPosition().x,sokkuri->getPosition().z);
        std::fflush(stdout);stage=2;return result;
    }
    if(stage==2){
        if(sokkuri->mHealth>0.0f && sokkuri->mHealth<minHealth)minHealth=sokkuri->mHealth;
        if(deadClip()){deadTick=observed;std::printf("P2_SOKKURI_NATURAL_DIED tick=%d health=%.2f\n",observed,sokkuri->mHealth);std::fflush(stdout);stage=3;return result;}
        if(observed%60==0){std::printf("P2_SOKKURI_NATURAL_OBSERVE tick=%d health=%.2f state=%d squad=%d\n",observed,sokkuri->mHealth,sokkuri->mStateID,aliveReds());std::fflush(stdout);}
        require(observed<5400,"natural death timeout (health stalled)");
        return result;
    }
    if(stage==3){
        if(!corpse)corpse=corpseOf(sokkuri);
        if(corpse){std::printf("P2_SOKKURI_NATURAL_CORPSE pellet=1 tick=%d\n",observed);std::fflush(stdout);stage=4;return result;}
        require(observed<5760,"corpse handoff timeout");
        return result;
    }
    if(stage==4){
        pc_p2_sokkuri_forget(sokkuri);
        require(pc_p2_sokkuri_count()==0,"sokkuri registry not cleared by forget");
        std::printf("P2_SOKKURI_NATURAL_FORGET count=0\n");std::fflush(stdout);
        sokkuriGen->mGenType->init(sokkuriGen);
        freshSokkuri=static_cast<Teki*>(sokkuriGen->mLatestSpawnCreature);
        require(freshSokkuri&&freshSokkuri!=sokkuri,"native generator rebirth failed / reused address");
        pc_p2_sokkuri_setup();
        require(pc_p2_sokkuri_registered(freshSokkuri)&&!pc_p2_sokkuri_registered(sokkuri),"fresh bind / old unbound");
        require(pc_p2_sokkuri_count()==1,"registry count after re-entry");
        require(!corpseOf(freshSokkuri),"fresh actor inherited corpse");
        std::printf("P2_SOKKURI_NATURAL_REENTRY old=%p new=%p stale=0 fresh=1 count=%lu\n",(void*)sokkuri,(void*)freshSokkuri,pc_p2_sokkuri_count());
        capture("sokkuri-natural-final.ppm");
        std::fflush(stdout);stage=5;return result;
    }
    if(stage==5){
        std::puts("PASS P2_SOKKURI_NATURAL_RUNTIME death=natural corpse=1 cleanup=1 reentry=1 injected=0");
        std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);return result;
}};
'''


def prepare(assets, imported, output):
    cfg = sokkuri_only_cfg()
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    # #128: the converted Sokkuri `appear1` bank names its first pose `_01`; the
    # native loader reconstructs `_00`. Copy the contiguous names (private run only).
    normalize_pose_names(run)
    return run


def instrument(source):
    return _instrument(source, APP)


def build(native, build_dir, output, head, resume=False):
    return _build(native, build_dir, output, head, resume=resume, app=APP)


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    damage = re.findall(r'P2_SOKKURI_DAMAGE generator=346005 source_id=79 health=([\d.]+)', text)
    dead = re.search(r'P2_SOKKURI_DEAD generator=346005 source_id=79 health=0 prior_health=([\d.]+)', text)
    prior = float(dead.group(1)) if dead else None
    injected = bool(re.search(r'P2_LIFECYCLE_INJECT|not_natural_combat=1|injected_health', text))
    ready = re.search(r'P2_SOKKURI_NATURAL_READY squad=(\d+) sokkuri_gen=346005', text)
    checks = dict(
        identity=bool(re.search(r'P2_SOKKURI_BIND generator=346005 source_id=79 visual_only=0', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text)),
        live_squad=int(ready.group(1)) >= 1 if ready else False,
        deploy=bool(re.search(r'P2_SOKKURI_NATURAL_DEPLOY free_squad=20', text)),
        natural_damage=bool(damage),
        natural_death=dead is not None,
        small_prior_health=prior is not None and prior < PRIOR_HEALTH_MAX,
        no_inject=not injected,
        corpse=bool(re.search(r'P2_SOKKURI_NATURAL_CORPSE pellet=1', text)),
        cleanup=bool(re.search(r'P2_SOKKURI_NATURAL_FORGET count=0', text)),
        reentry=bool(re.search(r'P2_SOKKURI_NATURAL_REENTRY old=\S+ new=\S+ stale=0 fresh=1 count=1', text)),
        completion='PASS P2_SOKKURI_NATURAL_RUNTIME' in text,
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    required = ('identity', 'window', 'live_squad', 'deploy', 'natural_damage',
                'natural_death', 'small_prior_health', 'no_inject', 'corpse',
                'cleanup', 'reentry', 'completion', 'no_extinction')
    blocked = re.search(r'FAIL p2 room: natural death timeout \(health stalled\)', text)
    floors = [float(v) for v in re.findall(r'P2_SOKKURI_NATURAL_OBSERVE tick=\d+ health=([\d.]+)', text)]
    blocking_reason = None
    if blocked:
        min_health = min(floors) if floors else None
        damage_hits = len(damage)
        blocking_reason = (f'squad failed to drain Sokkuri: min_health={min_health} '
                           f'(life={LIFE}), P2_SOKKURI_DAMAGE hits={damage_hits}')
    return dict(passed=code == 0 and (not blocked) and all(checks[name] for name in required)
                and 'PASS P2_SOKKURI_NATURAL_RUNTIME' in text,
                checks=checks, exit_code=code, prior_health=prior,
                damage_hits=len(damage), damage=[float(v) for v in damage],
                blocking_reason=blocking_reason)


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
    (run_dir / 'sokkuri-natural-validation.json').write_text(json.dumps(result, indent=2) + '\n')
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
