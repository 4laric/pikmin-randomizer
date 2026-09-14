"""Lane 11 two-process cave-checkpoint restart gate (#131/#112).

Process 1 (phase `write`) boots an Emergence floor with a schema-3 entry squad
containing a Bulbmin, then drives the real `pc_p2_cave_checkpoint(false)` at the
Research Pod; the engine writes `p2-cave-transfer.txt` and exits 42. The
campaign supervisor parser (`experimental.pikmin2_campaign.transition`) validates
that transfer and re-serializes an entry for process 2. Process 2 (phase `read`)
boots from that entry and the engine restores the squad; the fixture requires a
live Bulbmin (`P2_CAVE_RESTORE species=5`).

The fixture only schedules the checkpoint call; every wire byte and restore is
produced by the engine. The F6 confirmation dialog is skipped by passing
`confirm=false`; this is the same guarded handoff minus the human prompt.
"""
import argparse
import json
import os
import re
import uuid
from pathlib import Path

import experimental.pikmin2_elecbug_immunity_behavior as immunity
from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_campaign import entry_text, initial, ledger_text, transition
from experimental.pikmin2_campaign import validate as validate_state
from scripts.preview_pikmin2_emergence import prepare

_ORIGINAL_INSTRUMENT = immunity.instrument

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0;bool wrote=false;
 static bool is(const char* s,const char* w){return s&&std::strcmp(s,w)==0;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<120000,"lane11 restart startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!naviMgr||!pikiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 Suckable* pod=pc_p2_preview_goal();if(!pod)return result;
 ++observed;
 if(observed==1){
  int reds=0,yellow=0,purple=0,bulb=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;
   const int s=pc_p2_species(v);if(s==1)++reds;else if(s==2)++yellow;else if(s==3)++purple;else if(s==5)++bulb;}
  std::printf("P2_LANE11_SQUAD red=%d yellow=%d purple=%d bulbmin=%d\n",reds,yellow,purple,bulb);
  std::fflush(stdout);
 }
 const char* phase=std::getenv("P2_LANE11_PHASE");
 if(phase&&is(phase,"read")){
  if(observed>=60){
   int bulb=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive()&&pc_p2_species(v)==5)++bulb;}
   std::printf("P2_LANE11_READ bulbmin=%d observed=%d\n",bulb,observed);std::fflush(stdout);
   if(bulb>0){std::puts("PASS P2_LANE11_RESTORE");std::fflush(stdout);std::_Exit(0);}
   if(observed>6000){std::puts("FAIL P2_LANE11_RESTORE");std::fflush(stdout);std::_Exit(1);}
  }
  return result;
 }
 if(phase&&is(phase,"write")&&!wrote&&observed>=30&&n->getCurrState()
        &&n->getCurrState()->getID()==NAVISTATE_Walk){
  wrote=true;const Vector3f t=pod->mSRT.t;n->mSRT.t=Vector3f(t.x,30.0f,t.z);
  const bool ok=pc_p2_cave_checkpoint(false);
  std::printf("P2_LANE11_WRITE ok=%d\n",int(ok));std::fflush(stdout);
  if(ok){std::fflush(nullptr);std::_Exit(42);}
  std::puts("FAIL P2_LANE11_WRITE checkpoint rejected");std::fflush(stdout);std::_Exit(1);
 }
 if(observed>8000){std::puts("FAIL P2_LANE11_WRITE timeout");std::fflush(stdout);std::_Exit(1);}
 std::fflush(stdout);return result;
}};
'''


def instrument(source, app=APP):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    return ('#include <cstring>\n#include <cstdlib>\n#include <cstdio>\n'
            '#include "Piki.h"\n#include "PikiMgr.h"\n#include "PikiState.h"\n'
            '#include "Navi.h"\n#include "NaviMgr.h"\n#include "NaviState.h"\n'
            '#include "gameflow.h"\n#include "Suckable.h"\n'
            '#include "pc_p2_preview.h"\n#include "pc_p2_cave.h"\n#include "pc_p2_species.h"\n'
            + source[:start] + app + source[end:])


def build(native, build_dir, output, head, resume=False, app=None):
    immunity.instrument = lambda source, _app=None: instrument(source, app or APP)
    try:
        return immunity.build(native, build_dir, output, head, resume)
    finally:
        immunity.instrument = _ORIGINAL_INSTRUMENT


SQUAD = ([('red', 0)] * 16 + [('yellow', 1), ('purple', 2), ('bulbmin', 0)])


def _staged_squad():
    return [dict(species=s, maturity=m) for s, m in SQUAD]


def run(assets, imported, treasure, pod, purple, exe, output, seconds=75):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    state = validate_state(dict(initial('0' * 64), floor=2, revision=1, health=0.625,
                                squad=_staged_squad()))
    token = uuid.uuid4().hex

    # Phase 1: write the transfer from a live squad that already contains Bulbmin.
    run1 = prepare(Path(assets), Path(imported), Path(treasure), output / 'write',
                   floor=2, pod=Path(pod), purple=Path(purple), violet=True, squad=state['squad'])
    (run1 / 'p2-cave-entry.txt').write_text(entry_text(state, token))
    (run1 / 'p2-economy.txt').write_text(ledger_text({}))
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    os.environ['P2_LANE11_PHASE'] = 'write'
    meta1 = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                            run1, run1 / 'capture', seconds)
    text1 = (run1 / 'capture' / 'native.log').read_text(errors='replace')
    transfer_path = run1 / 'p2-cave-transfer.txt'
    if not transfer_path.is_file():
        raise RuntimeError('process 1 did not write p2-cave-transfer.txt')

    # Supervisor validation + re-serialize the entry for process 2.
    next_state = transition(state, token, transfer_path.read_text(), {}, {})
    run2 = prepare(Path(assets), Path(imported), Path(treasure), output / 'read',
                   floor=2, pod=Path(pod), purple=Path(purple), violet=True, squad=next_state['squad'])
    (run2 / 'p2-cave-entry.txt').write_text(entry_text(next_state, token))
    (run2 / 'p2-economy.txt').write_text(ledger_text({}))
    os.environ['P2_LANE11_PHASE'] = 'read'
    meta2 = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                            run2, run2 / 'capture', seconds)
    text2 = (run2 / 'capture' / 'native.log').read_text(errors='replace')

    result = validate(text1, text2, transfer_path.read_text())
    result['write'] = {'run': str(run1), 'capture': {k: meta1[k] for k in
                       ('executable_sha256', 'elapsed_seconds', 'exit_code', 'timed_out')}}
    result['read'] = {'run': str(run2), 'capture': {k: meta2[k] for k in
                      ('executable_sha256', 'elapsed_seconds', 'exit_code', 'timed_out')}}
    (output / 'cave-restart-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return output, {"write": meta1, "read": meta2}, result


def validate(text1, text2, transfer_text):
    if not isinstance(text1, str) or not isinstance(text2, str):
        raise ValueError('Expected native log strings')
    write_squad = re.search(r'P2_LANE11_SQUAD red=(\d+) yellow=(\d+) purple=(\d+) bulbmin=(\d+)', text1)
    checks = dict(
        write_window=(bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text1))
                      and bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text2))),
        write_squad=bool(write_squad) and int(write_squad.group(4)) >= 1,
        write_ok=bool(re.search(r'P2_LANE11_WRITE ok=1', text1)),
        transfer_header=transfer_text.startswith('P2_CAVE_TRANSFER_3\n'),
        transfer_floor=bool(re.search(r'\n2 0.625 19\n', transfer_text)),
        read_restore=bool(re.search(r'P2_CAVE_RESTORE species=5 maturity=0', text2)),
        read_bulbmin=bool(re.search(r'P2_LANE11_READ bulbmin=1', text2)),
        read_pass='PASS P2_LANE11_RESTORE' in text2,
        no_abort=('Invalid P2 cave entry' not in text1 and 'Invalid P2 cave entry' not in text2),
        no_extinction=(not re.search(r'Extinction', text1, re.IGNORECASE)
                       and not re.search(r'Extinction', text2, re.IGNORECASE)),
    )
    return dict(passed=all(checks.values()), checks=checks,
                transfer=transfer_text.splitlines()[:3],
                limitations=['Engineered Emergence floor 2; not production placement.',
                             'Checkpoint confirmation dialog skipped via confirm=false; '
                             'the F6 prompt itself is not exercised.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    b = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        b.add_argument('--' + flag, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    r = commands.add_parser('run')
    for flag in ('assets', 'imported', 'treasure', 'pod', 'purple', 'exe', 'output'):
        r.add_argument('--' + flag, type=Path, required=True)
    r.add_argument('--seconds', type=int, default=75)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        out, _, result = run(args.assets, args.imported, args.treasure, args.pod, args.purple,
                             args.exe, args.output, args.seconds)
        print(out)
        print(json.dumps(result, indent=2))
