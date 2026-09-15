"""Lane 11 natural Mother Bulbmin recruitment + real-whistle gate 6 (#131).

Slice 3 continuation. Process 1 (floor 1) uses the *bank-free* Chappy-family
host that every room preview writes (``scripts/preview_pikmin2_room.py`` sets
``TEKI_Chappy`` on the dwarf host) as the Mother Bulbmin stand-in: the engine
resolver ``pc_p2_bulbmin_mother_host()`` auto-attaches it and births the source
ten-body wild flock. The captain's real whistle hook (``pc_p2_bulbmin_call_pikis``,
the code ``Navi::callPikis`` invokes) converts wild dependents in place; the
live ``pc_p2_cave_checkpoint`` descend then drops the remaining wild dependents
while the whistled ones persist through a schema-3 transfer. Process 2 (floor 2)
restores them and runs the exit move over any remaining tracked dependents.

The fixture schedules the whistle and the checkpoint; every wire byte, the
mother registration and the drop are produced by the engine. No Mother Bulbmin
(LeafChappy) actor or Kochappy bank is required — the dependency is the bridge's
own binding to the resolved host.
"""
import argparse
import json
import os
import re
import uuid
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_campaign import SPECIES, ledger_text
from scripts.preview_pikmin2_emergence import prepare

_ORIGINAL_INSTRUMENT = None

try:
    import experimental.pikmin2_elecbug_immunity_behavior as immunity
    _ORIGINAL_INSTRUMENT = immunity.instrument
except Exception:  # pragma: no cover - build() is only needed for the GL run
    immunity = None

MINGW = os.environ.get('PIKMIN_MINGW64_BIN') or 'C:/msys64/mingw64/bin'

APP = r'''class RoomApp : public PlugPikiApp {
 int frames=0,observed=0;bool bound=false,whistled=false,wrote=false;
 static bool is(const char* s,const char* w){return s&&std::strcmp(s,w)==0;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<120000,"lane11 natural startup timeout");
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!naviMgr||!pikiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 Suckable* pod=pc_p2_preview_goal();if(!pod)return result;
 ++observed;
 const char* phase=std::getenv("P2_BULBMIN_TX_PHASE");
 if(phase&&is(phase,"read")){
  if(observed==60){
   int bulb=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive()&&pc_p2_species(v)==5)++bulb;}
   std::printf("P2_BULBMIN_TX_READ bulbmin=%d observed=%d\n",bulb,observed);std::fflush(stdout);
   if(bulb==0){std::puts("FAIL P2_BULBMIN_NATURAL no bulbmin restored");std::fflush(stdout);std::_Exit(1);}
  }
  if(observed>=60&&n->getCurrState()&&n->getCurrState()->getID()==NAVISTATE_Walk){
   const Vector3f t=pod->mSRT.t;n->mSRT.t=Vector3f(t.x,30.0f,t.z);
   const bool ok=pc_p2_cave_checkpoint(false);
   if(ok){std::puts("PASS P2_BULBMIN_NATURAL");std::fflush(stdout);std::_Exit(0);}
  }
  if(observed>6000){std::puts("FAIL P2_BULBMIN_NATURAL exit timeout");std::fflush(stdout);std::_Exit(1);}
  return result;
 }
 if(phase&&is(phase,"write")){
  if(!bound){
   int made=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);
    if(!v->isAlive()||pc_p2_species(v)!=1)continue;
    if(pc_p2_bulbmin_birth(v)){if(++made>=2)break;}}
   std::printf("P2_BULBMIN_TX_BOUND wild=%d\n",made);std::fflush(stdout);
   bound=true;
  }
  if(bound&&!whistled){
   Piki* target=nullptr;Iterator w(pikiMgr);CI_LOOP(w){
    Piki* v=static_cast<Piki*>(*w);
    if(v->isAlive()&&pc_p2_bulbmin_phase(v)==0){target=v;break;}}
   if(target){
    n->mCursorWorldPos=target->mSRT.t;
    const int rec=pc_p2_bulbmin_call_pikis(n,1.0f);
    std::printf("P2_BULBMIN_TX_WHISTLE recruited=%d\n",rec);std::fflush(stdout);
    whistled=true;
   }
  }
  if(whistled&&!wrote&&observed>=30&&n->getCurrState()
        &&n->getCurrState()->getID()==NAVISTATE_Walk){
   wrote=true;const Vector3f t=pod->mSRT.t;n->mSRT.t=Vector3f(t.x,30.0f,t.z);
   const bool ok=pc_p2_cave_checkpoint(false);
   std::printf("P2_BULBMIN_TX_CHECKPOINT ok=%d\n",int(ok));std::fflush(stdout);
   if(ok){std::fflush(nullptr);std::_Exit(42);}
   std::puts("FAIL P2_BULBMIN_NATURAL descend-rejected");std::fflush(stdout);std::_Exit(1);
  }
  if(observed>8000){std::puts("FAIL P2_BULBMIN_NATURAL write timeout");std::fflush(stdout);std::_Exit(1);}
 }
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
            '#include "pc_p2_preview.h"\n#include "pc_p2_cave.h"\n'
            '#include "pc_p2_species.h"\n#include "pc_p2_bulbmin.h"\n'
            + source[:start] + app + source[end:])


def build(native, build_dir, output, head, resume=False):
    if immunity is None:
        raise RuntimeError('immunity.build unavailable in this checkout')
    immunity.instrument = lambda source, _app=None: instrument(source, APP)
    try:
        return immunity.build(native, build_dir, output, head, resume)
    finally:
        immunity.instrument = _ORIGINAL_INSTRUMENT


def _entry_from_transfer(token, transfer_text, floor):
    """Read-side entry: same schema/body as the transfer, next floor."""
    lines = transfer_text.splitlines()
    header = lines[0]
    schema = header.replace('P2_CAVE_TRANSFER_', '')
    _, health, count = lines[2].split()
    body = [line.split() for line in lines[3:3 + int(count)]]
    return (f'P2_CAVE_ENTRY_{schema}\n{token}\n{floor} {health} {count}\n'
            + ''.join(f'{s} {m}\n' for s, m in body) + '\n')


def run(assets, imported, treasure, pod, purple, exe, output, seconds=75):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    red = [dict(species='red', maturity=0) for _ in range(18)]
    token = uuid.uuid4().hex

    run1 = prepare(Path(assets), Path(imported), Path(treasure), output / 'write',
                   floor=1, pod=Path(pod), purple=Path(purple), violet=False, squad=red)
    (run1 / 'p2-cave-entry.txt').write_text(
        f'P2_CAVE_ENTRY_3\n{token}\n1 0.625 18\n' + '1 0\n' * 18)
    (run1 / 'p2-economy.txt').write_text(ledger_text({}))
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = MINGW + ';' + os.environ.get('PATH', '')
    os.environ['P2_BULBMIN_TX_PHASE'] = 'write'
    os.environ['PIKMIN_P2_BULBMIN'] = '1'
    meta1 = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                            run1, run1 / 'capture', seconds)
    text1 = (run1 / 'capture' / 'native.log').read_text(errors='replace')
    transfer_path = run1 / 'p2-cave-transfer.txt'
    if not transfer_path.is_file():
        raise RuntimeError('process 1 did not write p2-cave-transfer.txt')

    transfer_text = transfer_path.read_text()
    read_squad = [dict(species=SPECIES[int(s)], maturity=int(m))
                  for s, m in (line.split() for line in transfer_text.splitlines()[3:])]
    run2 = prepare(Path(assets), Path(imported), Path(treasure), output / 'read',
                   floor=2, pod=Path(pod), purple=Path(purple), violet=True, squad=read_squad)
    (run2 / 'p2-cave-entry.txt').write_text(_entry_from_transfer(token, transfer_text, 2))
    (run2 / 'p2-economy.txt').write_text(ledger_text({}))
    os.environ['P2_BULBMIN_TX_PHASE'] = 'read'
    meta2 = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                            run2, run2 / 'capture', seconds)
    text2 = (run2 / 'capture' / 'native.log').read_text(errors='replace')

    result = validate(text1, text2, transfer_text)
    result['write'] = {'run': str(run1), 'capture': {k: meta1[k] for k in
                       ('executable_sha256', 'elapsed_seconds', 'exit_code', 'timed_out')}}
    result['read'] = {'run': str(run2), 'capture': {k: meta2[k] for k in
                      ('executable_sha256', 'elapsed_seconds', 'exit_code', 'timed_out')}}
    (output / 'bulbmin-natural-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return output, {"write": meta1, "read": meta2}, result


def validate(text1, text2, transfer_text):
    if not isinstance(text1, str) or not isinstance(text2, str):
        raise ValueError('Expected native log strings')
    hdr = transfer_text.startswith('P2_CAVE_TRANSFER_3\n')
    body = transfer_text.splitlines()[3:] if hdr else []
    whistle = re.search(r'P2_BULBMIN_WHISTLE recruited=(\d+)', text1)
    descend = re.search(r'P2_CAVE_BULBMIN_TRANSITION move=descend removed=(\d+)', text1)
    checks = dict(
        write_window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered', text1)),
        mother_sidecar=bool(re.search(r'P2_BULBMIN_MOTHER_BIRTH model=\S+ generator=[1-9]\d*', text1)),
        mother_birth=bool(re.search(r'P2_BULBMIN_MOTHER_BIRTH model=\S+ generator=\d+ dependents=0', text1)),
        natural_whistle=bool(whistle) and int(whistle.group(1)) >= 1,
        whistle_via_real_path='P2_BULBMIN_TX_RECRUIT' not in text1,
        descend_drops_wild=bool(descend) and int(descend.group(1)) >= 1,
        recruited_persist=(len([l for l in body if l.split()[0] == '5']) >= 1),
        read_restore=bool(re.search(r'P2_CAVE_RESTORE species=5 maturity=0', text2)),
        exit_removes_tracked=bool(re.search(r'P2_CAVE_BULBMIN_TRANSITION move=exit', text2)),
        no_extinction=(not re.search(r'Extinction', text1, re.IGNORECASE)
                       and not re.search(r'Extinction', text2, re.IGNORECASE)),
    )
    return dict(passed=all(checks.values()), checks=checks,
                transfer=transfer_text.splitlines()[:3],
                limitations=['Engineered arena: the mother is the bank-free Chappy-family host, '
                             'not a LeafChappy actor (its birth is out of scope). The whistle is the '
                             'real Navi::callPikis hook code; the fixture only positions the captain.'])


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
