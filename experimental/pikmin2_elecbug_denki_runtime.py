"""ElecBug electrical emitter -> lane-10 InteractDenki receiver -> lane-11 matrix.

Natural, non-injected runtime gate for the paired lane 10 / lane 11 / lane 14
slice (#408 / #131 / #165):

* the actual ElecBug two-beetle Discharge sweep is the emitter (``emitter=sweep``
  in ``P2_ELECBUG_DENKI``); the electrical target is chosen by the lane-11
  species capability matrix, not a colour literal;
* the receiver is the real ``InteractDenki`` from ``interactBattle.cpp``; the
  emitted marker records its return value and the target's resulting state, so
  ``accepted=1 target_state=35(DenkiDying)`` proves the receiver ran and the
  non-immune Pikmin entered ``PIKISTATE_DenkiDying``;
* Yellow and Bulbmin are rejected (``P2_ELECBUG_IMMUNE``) and never enter
  ``PIKISTATE_DenkiDying``; and
* the shocked target runs the source lethal pipeline (DenkiDying -> Dead), which
  the fixture observes directly.

Contrast with :mod:`experimental.pikmin2_receivers_runtime`, which injects
``InteractDenki`` from the fixture; here the interaction is produced by the
acting family emitter. The fixture only recolours three starting Pikmin and
parks them inside the source 70-unit sweep while a beetle is discharging.

The real-GL run is serialized against other lanes' acceptance runs.
"""
import argparse
import json
import os
import re
from pathlib import Path

import experimental.pikmin2_elecbug_immunity_behavior as immunity
from experimental.pikmin2_animation_profile import capture_command

ELECBUG_A = immunity.ELECBUG_A
ELECBUG_B = immunity.ELECBUG_B

_ORIGINAL_INSTRUMENT = immunity.instrument

DENKI_APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0,shockFrame=0;
 Teki* a=nullptr;Teki* b=nullptr;
 Piki* yellow=nullptr;Piki* bulb=nullptr;Piki* blue=nullptr;
 bool shock=false,lethal=false,violation=false;
 static bool is(const char* s,const char* want){return s&&std::strcmp(s,want)==0;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<90000,"denki runtime startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  Iterator e(tekiMgr);CI_LOOP(e){Teki* t=static_cast<Teki*>(*e);if(!t->mGenerator)continue;
   unsigned id=t->mGenerator->_70;if(id==346002)a=t;else if(id==346008)b=t;}
  require(a&&b,"two registered ElecBugs present");
  // Mark the whole squad electric-immune except one Blue, so the emitter's
  // matrix-based target selection can only resolve to Blue regardless of which
  // uncorrelated squad member is physically nearest.
  int index=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
   if(index==0){yellow=v;pc_p2_set_species(v,P2SpeciesYellow);}
   else if(index==1){bulb=v;pc_p2_set_species(v,P2SpeciesBulbmin);}
   else if(index==2){blue=v;pc_p2_set_species(v,P2SpeciesBlue);}
   else pc_p2_set_species(v,P2SpeciesBulbmin);
   ++index;}
  require(yellow&&bulb&&blue,"three starting Pikmin available");
  require(pc_p2_species(yellow)==P2SpeciesYellow,"yellow species");
  require(pc_p2_species(bulb)==P2SpeciesBulbmin,"bulbmin species");
  require(pc_p2_species(blue)==P2SpeciesBlue,"blue species");
  int alive=0,reds=0;Iterator q(pikiMgr);CI_LOOP(q){Piki* v=static_cast<Piki*>(*q);if(v->isAlive()){++alive;if(v->mColor==Red)++reds;}}
  std::printf("P2_DENKI_SQUAD alive=%d reds=%d yellow=%d bulbmin=%d blue=%d\n",alive,reds,
              pc_p2_species(yellow),pc_p2_species(bulb),pc_p2_species(blue));
 }
 // A beetle actively discharging is the emitter; park the three targets inside
 // the source 70-unit sweep. Yellow (+8) and Bulbmin (+16) are immune and are
 // skipped by the matrix; Blue (+32) is the nearest shockable.
 const char* sa=pc_p2_elecbug_state_name(a);const char* sb=pc_p2_elecbug_state_name(b);
 bool da=is(sa,"discharge")||is(sa,"childdischarge");
 bool db=is(sb,"discharge")||is(sb,"childdischarge");
 Teki* host=da?a:(db?b:nullptr);
 if(host){const Vector3f bp=host->getPosition();
  if(yellow->isAlive()&&yellow->getState()!=PIKISTATE_DenkiDying)yellow->mSRT.t=Vector3f(bp.x+8.0f,bp.y,bp.z);
  if(bulb->isAlive()&&bulb->getState()!=PIKISTATE_DenkiDying)bulb->mSRT.t=Vector3f(bp.x+16.0f,bp.y,bp.z);
  if(blue->isAlive())blue->mSRT.t=Vector3f(bp.x+32.0f,bp.y,bp.z);
 }
 // An immune species must never be driven into the electric death state.
 if(yellow->getState()==PIKISTATE_DenkiDying||bulb->getState()==PIKISTATE_DenkiDying)violation=true;
 if(!shock&&blue->getState()==PIKISTATE_DenkiDying){
  shock=true;shockFrame=observed;
  std::printf("P2_DENKI_ACCEPT target=blue yellow_state=%d bulbmin_state=%d observed=%d\n",
              yellow->getState(),bulb->getState(),observed);
  std::fflush(stdout);
 }
 if(shock&&!lethal&&(!blue->isAlive()||blue->getState()==PIKISTATE_Dead)){
  lethal=true;
  std::printf("P2_DENKI_LETHAL target=blue alive=0 yellow_alive=%d yellow_state=%d "
              "bulbmin_alive=%d bulbmin_state=%d violation=%d observed=%d\n",
              int(yellow->isAlive()),yellow->getState(),int(bulb->isAlive()),bulb->getState(),
              int(violation),observed);
  std::fflush(stdout);
  if(violation){std::puts("FAIL P2_ELECBUG_DENKI_RUNTIME immune_violation=1");std::fflush(stdout);std::_Exit(1);}
  std::puts("PASS P2_ELECBUG_DENKI_RUNTIME");std::fflush(stdout);std::_Exit(0);
 }
 if(observed>40000){std::puts("FAIL P2_ELECBUG_DENKI_RUNTIME timeout");std::fflush(stdout);std::_Exit(1);}
 std::fflush(stdout);return result;
}};
'''


def instrument(source, app=DENKI_APP):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return ('#include <cstring>\n#include <cstdlib>\n#include "Generator.h"\n'
            '#include "TekiPersonality.h"\n#include "Interactions.h"\n'
            '#include "Piki.h"\n#include "PikiState.h"\n#include "PikiMgr.h"\n'
            '#include "GlobalGameOptions.h"\n#include "pc_p2_elecbug.h"\n'
            '#include "pc_p2_species.h"\n'
            + source[:start] + app + source[end:])


def prepare(assets, imported, output):
    return immunity.prepare(assets, imported, output)


def build(native, build_dir, output, head, resume=False, app=None):
    """Instrument :mod:`experimental.pikmin2_elecbug_immunity_behavior`'s build."""
    immunity.instrument = lambda source, _app=None: instrument(source, app or DENKI_APP)
    try:
        return immunity.build(native, build_dir, output, head, resume)
    finally:
        immunity.instrument = _ORIGINAL_INSTRUMENT


def run(assets, imported, output, exe, seconds=90):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'elecbug-denki-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    # P2_ELECBUG_DENKI ... emitter=sweep target=<species> accepted=<0|1> target_state=<n>(<name>)
    shocks = [(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5))
              for m in re.finditer(
                  r'P2_ELECBUG_DENKI generator=(\d+) source_id=28 emitter=sweep target=(-?\d+) '
                  r'accepted=(\d) target_state=(-?\d+)\((\w+)\)', text)]
    # compatibility with older logs that had no accepted/state fields
    shocks_legacy = [(int(m.group(1)), int(m.group(2))) for m in
                     re.finditer(
                         r'P2_ELECBUG_DENKI generator=(\d+) source_id=28 emitter=sweep '
                         r'target=(-?\d+) shockable=1', text)]
    immune_yellow = bool(re.search(
        r'P2_ELECBUG_IMMUNE generator=\d+ source_id=28 pikmin=yellow', text))
    immune_bulbmin = bool(re.search(
        r'P2_ELECBUG_IMMUNE generator=\d+ source_id=28 pikmin=bulbmin', text))
    squad = re.search(r'P2_DENKI_SQUAD alive=(\d+) reds=(\d+)', text)
    accept = re.search(r'P2_DENKI_ACCEPT target=blue yellow_state=(\d+) '
                                     r'bulbmin_state=(\d+)', text)
    lethal = re.search(r'P2_DENKI_LETHAL target=blue alive=0 yellow_alive=(\d) '
                                     r'yellow_state=(\d+) bulbmin_alive=(\d) bulbmin_state=(\d) '
                                     r'violation=(\d)', text)
    # Blue = P2SpeciesBlue = 0; Yellow = 2; Bulbmin = 5.
    receiver_accepted = any(a == 1 and name == 'DenkiDying' for (_, _, a, _, name) in shocks)
    no_immune_target = all(target not in (2, 5) for (_, target, _, _, _) in shocks) and \
                       all(target not in (2, 5) for (_, target) in shocks_legacy)
    checks = dict(
        completion=code == 0 and 'PASS P2_ELECBUG_DENKI_RUNTIME' in text,
        window=bool(re.search(
            r'Experimental preview window set to 960x540 windowed and centered', text)),
        squad=bool(squad) and int(squad.group(1)) > 0,
        emitter_shock=receiver_accepted and any(
            target == 0 for (_, target, _, _, _) in shocks),
        receiver_denki=receiver_accepted,
        immunity_yellow=immune_yellow and no_immune_target,
        immunity_bulbmin=immune_bulbmin,
        no_immune_reaction=bool(accept) and accept.group(1) != '35' and accept.group(2) != '35',
        lethal_path=bool(lethal) and lethal.group(1) == '1' and lethal.group(3) == '1'
                    and lethal.group(5) == '0',
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
    )
    return dict(passed=all(checks.values()), checks=checks, exit_code=code,
                shocks=shocks, shocks_legacy=shocks_legacy,
                immune_yellow=immune_yellow, immune_bulbmin=immune_bulbmin,
                unmeasured=['retail uniform-random partner selection (port picks nearest)',
                            'source electric-effect particles (port has no effect emitter)'],
                limitations=['Behavior fixture overrides both ElecBug arena coordinates; not '
                             'production placement evidence.',
                             'The fixture parks three recoloured starting Pikmin inside the sweep; '
                             'the emitter target selection and receiver are native.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=90)
    b = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        b.add_argument('--' + flag, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
