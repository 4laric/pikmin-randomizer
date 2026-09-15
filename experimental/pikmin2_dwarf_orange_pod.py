"""Dwarf Orange Pod corpse-receipt witness (gate 5, lane 13 #120) — natural carry.

Mirrors the lane-19 Mamuta natural-carry pattern: park the captain beyond the
enemy's sight range, ring-deploy the 20 reds around the source actor in
``PikiMode::FreeMode``, re-ring every 120 ticks, and NEVER write ``TransportMode``
— free Pikmin self-assign transport (``Piki::graspSituation`` -> PIKISITCH_Unk9)
once the FSM-killed corpse is dropped. The corpse is carried to the Research Pod
and ``pc_p2_preview_deliver`` is fired automatically by ``PelletGoalState::exec``,
logging ``P2_POD_RECEIPT``. No enemy state/health/animation and no transport task
is written.

Exactly-once is ``P2Economy::credit`` (generator-keyed receipt dedupe), unit-proven
by ``tools/test_p2_economy.cpp``.
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_mamuta_rules import stage_cargo, find_pod_package

APP = r'''class RoomApp : public PlugPikiApp {
  int frames=0,observed=0,deathFrame=-1;
  unsigned gen=0;
  Teki* actor=nullptr;Pellet* corpse=nullptr;
  Teki* findActor(){if(!tekiMgr)return nullptr;Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==211001)return a;}return nullptr;}
  int squadCount(){int c=0;if(!pikiMgr)return 0;Iterator sq(pikiMgr);CI_LOOP(sq){Piki* p=static_cast<Piki*>(*sq);if(p&&p->isAlive()&&p->mColor==Red)++c;}return c;}
  void ringReds(){if(!actor)return;Navi* n=naviMgr?naviMgr->getNavi():nullptr;int ring=0;int squad=squadCount();if(!squad)return;
    Iterator sq(pikiMgr);CI_LOOP(sq){Piki* p=static_cast<Piki*>(*sq);if(!p||!p->isAlive()||p->mColor!=Red)continue;
      float a=float(ring)*6.2831853f/float(squad);Vector3f pt(actor->mSRT.t.x+22.0f*std::sin(a),0,actor->mSRT.t.z+22.0f*std::cos(a));
      pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++ring;}
    std::printf("P2_DWARF_ORANGE_POD_RING ticks=%d ring=%d squad=%d\n",observed,ring,squad);std::fflush(stdout);}
public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<30000,"pod natural-carry startup timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_ready()||pc_p2_preview_pokos()<0||!naviMgr||!tekiMgr||!pikiMgr||!pelletMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
    actor=findActor();require(actor,"no Dwarf Orange actor (211001)");gen=actor->mGenerator->_70;
    Vector3f park(actor->mSRT.t.x,0,actor->mSRT.t.z+160.0f);park.y=mapMgr->getMinY(park.x,park.z,true);n->resetPosition(park);
    ringReds();
    std::printf("P2_DWARF_ORANGE_POD_READY gen=%u pokos=%d\n",gen,pc_p2_preview_pokos());std::fflush(stdout);
  }
  if(actor&&!actor->isAlive()&&!corpse){
    Iterator pel(pelletMgr);CI_LOOP(pel){Pellet* p=static_cast<Pellet*>(*pel);if(p&&p->isAlive()&&p->mPelletView==static_cast<PelletView*>(actor)){corpse=p;break;}}
    if(corpse){deathFrame=observed;std::printf("P2_DWARF_ORANGE_POD_CORPSE tick=%d\n",observed);std::fflush(stdout);}
  }
  if(actor&&actor->isAlive()&&observed>1&&observed%120==0)ringReds();
  if(corpse){
    int transport=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mMode==PikiMode::TransportMode)++transport;}
    if(observed%60==0)std::printf("P2_DWARF_ORANGE_POD_CARRY tick=%d state=%d alive=%d transport=%d pokos=%d\n",
      observed,corpse->getState(),int(corpse->isAlive()),transport,pc_p2_preview_pokos());
  }
  if(pc_p2_preview_pokos()>0||observed>=2400){
    int transport=0;Iterator pit(pikiMgr);CI_LOOP(pit){Piki* p=static_cast<Piki*>(*pit);if(p&&p->isAlive()&&p->mMode==PikiMode::TransportMode)++transport;}
    std::printf("P2_DWARF_ORANGE_POD_SUMMARY observed=%d death=%d transport=%d pokos=%d\n",observed,deathFrame,transport,pc_p2_preview_pokos());
    require(pc_p2_preview_pokos()>0,"corpse never entered transport: no Pod receipt");
    std::puts("PASS P2_DWARF_ORANGE_P1_POD");std::fflush(stdout);std::_Exit(0);
  }
  return result;
}};
'''


def instrument(source):
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    if 'P2_DWARF_ORANGE_POD_READY' in source:
        raise ValueError('Already instrumented')
    text = source[:start] + APP + source[end:]
    # The maintained fixture applies the window baseline after settings.
    if 'Experimental preview window set to' in source[end:] and 'pc_window_center()' in source[end:]:
        return text
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


def prepare(assets, bank, profile, pod_package, output):
    """Dwarf Orange arena + Research Pod (stage_cargo). Returns the run dir."""
    from experimental.pikmin2_dwarf_orange_runtime import prepare as combat_prepare
    stage = combat_prepare(Path(assets).resolve(), Path(bank).resolve(),
                           Path(profile).resolve(), Path(output).resolve())
    package = find_pod_package([Path(pod_package).resolve()])
    stage_cargo(stage, Path(assets).resolve(), package)
    return stage


def build(native, build_dir, output, head):
    from scripts import build_pikmin2_fixture as builder
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument((native / 'tools/preview_p2_room.cpp').read_text()))
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe


def evidence(log, code):
    receipts = re.findall(r'P2_POD_RECEIPT id=(\S+) value=(\d+) new=(\d) pokos=(\d+)', log)
    corpse = [r for r in receipts if r[0].startswith('corpse:')]
    rows = [dict((k, float(v)) for k, v in re.findall(r'(\w+)=([-+\d.eE]+)', line))
            for line in log.splitlines() if line.startswith('P2_DWARF_ORANGE_POD_CARRY ')]
    checks = {
        'pod_ready': 'P2_DWARF_ORANGE_POD_READY ' in log,
        'fsm_death': 'P2_KOCHAPPY_DEAD generator=211001 source_id=44' in log,
        'corpse': 'P2_DWARF_ORANGE_POD_CORPSE ' in log,
        'transport': any(r.get('transport', 0) > 0 for r in rows),
        'receipt': bool(corpse) and '211001' in corpse[0][0] and corpse[0][2] == '1',
        'completion': 'PASS P2_DWARF_ORANGE_P1_POD' in log,
    }
    return dict(passed=code == 0 and all(checks.values()), checks=checks, exit_code=code,
                receipts=receipts, rows=rows,
                scope='natural FSM kill (no injected enemy state) + FreeMode ring-deploy squad; '
                      'no TransportMode writes — Pikmin self-assign carry, corpse to Pod, receipt logged',
                unmeasured=['exactly-once revisit (P2Economy dedupe unit-proven, tools/test_p2_economy.cpp)',
                            'P2 once-credit idempotency across process restart'])


def run(stage, exe, output, timeout=300):
    from experimental.pikmin2_animation_profile import capture_command
    stage = Path(stage).resolve()
    output = Path(output).resolve()
    os.environ.setdefault('PIKMIN_P2_ROOM_WINDOW', '960x540')
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, timeout)
    report = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    report['capture'] = meta
    (output / 'evidence.json').write_text(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    p = sub.add_parser('prepare')
    for name in ('assets', 'bank', 'profile', 'pod-package', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    if args.command == 'build':
        print(build(args.native, args.build_dir, args.output, args.head))
    elif args.command == 'prepare':
        print(prepare(args.assets, args.bank, args.profile, args.pod_package, args.output))
    else:
        print(json.dumps({k: v for k, v in run(args.stage, args.exe, args.output, args.timeout).items()
                          if k != 'rows'}, indent=2))
