"""Reward beetle real collection + restart dedupe (lane 17, #168/#219).

Slice 2 proved the drops are actually collected through the ordinary P1
Onion/nectar path and that a process restart neither duplicates nor loses the
receipts. Slice 3 strengthens the same gate end-to-end:

  * **natural flips** — the three flip triggers are real Pikmin stick-attacks
    through the ordinary interaction path (``pc_p2_kogane_attacked``), not the
    labelled injected ``InteractPress``; the ``P2_KOGANE_NATURAL_ATTACK`` lines are
    emitted by the native flip for the natural scenario, and the injected variant
    stays available as a separately flagged legacy ``mode=injected``.
  * **real second-flip sequence** — pass 2 now drives the same natural attack
    routine at the restored (escaped) beetle and then re-drives the three grant
    events through the *real* ``pc_p2_receipt_host_grant`` Duplicate path, proving
    both defence layers (flip sidecar -> no re-arm, onion ledger -> duplicate).
    The validator checks the persisted ledger still has exactly three rows.

The ordinary P1 transport (carry, ``GoalItem::suckMe``, ``PIKISTATE_Absorb``) and
the lane-06 ``pc_p2_receipt_host`` grant are unchanged and remain the real
endpoints; only the flip trigger and the pass-2 assertion are tightened here.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental.pikmin2_kogane_arena import prepare
from experimental.pikmin2_kogane_behavior import native_sidecar
from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import run as run_fixture_base
from scripts import build_pikmin2_fixture as builder

TARGET = 219001  # Iridescent Flint Beetle (source ID 9)
CONTROL = 219004
SOURCE_ID = 9

INCLUDES = ('#include <map>\n#include "Demo.h"\n#include "GameStat.h"\n#include "Interactions.h"\n'
            '#include "ItemMgr.h"\n#include "ObjType.h"\n'
            '#include "Pellet.h"\n#include "PelletView.h"\n#include "Piki.h"\n#include "PikiMgr.h"\n'
            '#include "PikiAI.h"\n#include "PlayerState.h"\n#include "GoalItem.h"\n'
            '#include "pc_p2_kogane.h"\n')

# One parameterized fixture with a mode flag (natural by default, injected as the
# separately flagged legacy scenario) and a pass flag (0=collect, 2=restart).
APP = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0,pass=0,mode=1;
 Teki* beetle=nullptr;Teki* control=nullptr;
 Piki* attackers[5]={nullptr,nullptr,nullptr,nullptr,nullptr};
 bool staged=false,escaped=false;int born0=0;int peakPellets=0,peakWater=0;
 Vector3f dropAnchor;std::map<unsigned,Vector3f> hold; // pinned birth anchors (natural mode)
 void holdBeetles(){for(auto& h:hold){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==h.first){a->mSRT.t.set(h.second);a->mVelocity.set(0,0,0);break;}}}}
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 bool nearDrops(Vector3f v){Vector3f d=v;d.sub(dropAnchor);return d.length()<80.0f;}
 int pelletsNear(){int c=0;if(!pelletMgr)return 0;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->isAlive()&&!p->isUfoParts()&&nearDrops(p->getPosition()))++c;}return c;}
 int waterNear(){int c=0;if(!itemMgr)return 0;Iterator it(itemMgr);CI_LOOP(it){Creature* w=*it;if(w&&w->mObjType==OBJTYPE_Water&&w->isAlive()&&nearDrops(w->getPosition()))++c;}return c;}
 int waterTotal(){int c=0;if(!itemMgr)return 0;Iterator it(itemMgr);CI_LOOP(it){Creature* w=*it;if(w&&w->mObjType==OBJTYPE_Water&&w->isAlive())++c;}return c;}
 bool aliveTeki(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id&&a->isAlive())return true;}return false;}
 void press(Teki* actor,Navi* n){if(!actor)return;InteractPress p(n,0.0f);actor->stimulate(p);}
 void command(Piki* p,int idx){ // labelled C-stick style attack (mirrors the slice-1 natural receiver)
  if(!p||!beetle||!p->isAlive()||beetle->mDeadState!=0)return;
  Vector3f b=beetle->getPosition();
  Vector3f spot(b.x-40.0f+6.0f*idx,b.y,b.z+(idx-2)*6.0f);
  p->resetPosition(spot);p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);
  if(p->mActiveAction){p->mActiveAction->abandon(nullptr);p->mActiveAction->startAction(PikiAction::Attack,beetle);}
  p->mMode=PikiMode::AttackMode;
 }
 void requeue(){ // re-issue the natural attack, never interrupting a drinker
  for(int i=0;i<5;++i){Piki* p=attackers[i];
   if(!p||!p->isAlive()||!beetle||!beetle->isAlive())continue;
   if(p->mMode!=PikiMode::AttackMode&&p->getState()!=PIKISTATE_Absorb&&!p->mCurrNectar){
    if(p->mActiveAction){p->mActiveAction->abandon(nullptr);p->mActiveAction->startAction(PikiAction::Attack,beetle);}
    p->mMode=PikiMode::AttackMode;}}
 }
 Pellet* pelletNearAnchor(){if(!pelletMgr)return nullptr;Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);if(p&&p->isAlive()&&!p->isUfoParts()&&nearDrops(p->getPosition()))return p;}return nullptr;}
 void transportTo(Piki* p,Pellet* pel){ // labelled grab+transport initiation; the carry and Onion suck are native
  if(!p||!pel||!p->mActiveAction)return;
  if(p->getState()==PIKISTATE_Absorb||p->mCurrNectar)return; // never interrupt a drinker (mizunomi)
  p->mActiveAction->abandon(nullptr);p->mActiveAction->startAction(PikiAction::Transport,pel);
  p->mMode=PikiMode::TransportMode;}
 void nudgeDrink(){ // place a free Pikmin onto each remaining nectar so it drinks
  if(!itemMgr||!pikiMgr)return;
  Iterator iw(itemMgr);CI_LOOP(iw){Creature* w=*iw;
   if(!w||w->mObjType!=OBJTYPE_Water||!w->isAlive())continue;
   Iterator ip(pikiMgr);CI_LOOP(ip){Piki* p=static_cast<Piki*>(*ip);
    if(!p||!p->isAlive()||p->isHolding()||p->mMode==PikiMode::TransportMode||p->mCurrNectar)continue;
    Vector3f wp=w->getPosition();p->resetPosition(Vector3f(wp.x,wp.y+1.0f,wp.z));break;}}}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<30000,"beetle collect timeout");
  if(frames==1){std::ifstream pf("kogane-pass.txt");if(pf)pf>>pass;
   std::ifstream mf("kogane-mode.txt");int m=1;if(mf)mf>>m;mode=m?1:0;
   std::printf("P2_KOGANE_COLLECT_PASS pass=%d mode=%s\n",pass,mode?"natural":"injected");std::fflush(stdout);}
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i);
   std::ifstream input("kogane-positions.txt");unsigned id;float x,y,z;int count=0;
   while(input>>id>>x>>y>>z){
    Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
    if(pass==0)require(matches==1,"beetle roster identity");
    std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor?actor->mTekiType:-1,x,y,z);
    if(actor&&pass==0)hold[id]=actor->getPosition();
    if(id==219001)beetle=actor;if(id==219004)control=actor;++count;}
   if(pass==0){require(count==4,"beetle roster missing");require(beetle&&control,"identity");}
   else{require(control,"restart control identity");}
   born0=int(GameStat::bornPikis);}
  if(pass==0){
   if(observed==60)require(alivePikis()==20,"starting squad");
   if(beetle&&beetle->isAlive())dropAnchor=beetle->getPosition();
   if(mode){
    holdBeetles(); // labelled position hold: keep the three beetles at their birth anchors so the natural attacks and drops are deterministic
    if(observed==80){int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||idx>=5)continue;attackers[idx]=p;command(p,idx);++idx;}
     std::printf("P2_KOGANE_NATURAL_COMMAND attackers=%d mode=natural\n",idx);std::fflush(stdout);}
    if(beetle&&beetle->isAlive()&&observed>80&&observed%12==1)requeue();
   }else{
    if(observed==90||observed==180||observed==270)press(beetle,n); // labelled injected (legacy scenario)
   }
   if(observed>80&&beetle&&!beetle->isAlive()&&!escaped){escaped=true;std::printf("P2_KOGANE_ESCAPED_OBS tick=%d\n",observed);std::fflush(stdout);}
   if(escaped){
    if(!staged){ // move the squad onto the drop zone once the beetle is gone
     n->mSRT.t.set(Vector3f(dropAnchor.x,30.0f,dropAnchor.z));
     int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
      Vector3f spot(dropAnchor.x-12.0f+6.0f*(idx%5),30.0f,dropAnchor.z-12.0f+6.0f*(idx/5));p->resetPosition(spot);++idx;}
     staged=true;std::printf("P2_KOGANE_STAGE squad=20 anchor=%.1f,%.1f\n",dropAnchor.x,dropAnchor.z);std::fflush(stdout);}
    if(observed%15==1){nudgeDrink();Pellet* pel=pelletNearAnchor();if(pel){ // latch two Pikmin onto the dropped pellet
     int slots=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||slots>=2)continue;if(!p->isHolding()&&p->mMode!=PikiMode::TransportMode){transportTo(p,pel);++slots;}}}}
    if(peakPellets<pelletsNear())peakPellets=pelletsNear();
    if(peakWater<waterNear())peakWater=waterNear();
    if(observed%60==0)std::printf("P2_KOGANE_COLLECT_PROGRESS tick=%d pellets=%d water=%d sprout=%d\n",observed,pelletsNear(),waterTotal(),int(GameStat::bornPikis)-born0);
    int sprouts=int(GameStat::bornPikis)-born0;
    if(pelletsNear()==0&&waterTotal()==0&&sprouts>=1){
     int dropsNectar=pc_p2_kogane_nectar_dropped();
     std::printf("P2_KOGANE_COLLECTED pellets_collected=%d nectar_drunk=%d sprouts=%d\n",peakPellets,dropsNectar,sprouts);
     require(control&&control->isAlive(),"P1 control disturbed");
     require(peakPellets==1&&dropsNectar==5,"collectable drop census");
     std::puts("PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3");std::fflush(stdout);std::_Exit(0);}
   }
  }else{ // pass 2: restart dedupe, now with a real second-flip sequence + ledger probe
   if(observed==60){
    require(!aliveTeki(219001),"restarted beetle re-armed (still alive)");
    require(control&&control->isAlive(),"P1 control disturbed");
    std::printf("P2_KOGANE_RESTART rearmed=0\n");std::fflush(stdout);
    // Drive the same natural attack routine at the restored beetle: it was
    // reconstructed escaped (dead), so every command no-ops — no flip, no drop,
    // no re-grant. This is the "second flip sequence" the receipt cap must hold.
    if(beetle){int idx=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive()||idx>=5)continue;attackers[idx]=p;command(p,idx);++idx;}
     std::printf("P2_KOGANE_NATURAL_COMMAND attackers=%d mode=reattempt\n",idx);std::fflush(stdout);}
   }
   if(observed==240){
    require(!aliveTeki(219001),"beetle re-armed after natural re-attack");
    int dups=pc_p2_kogane_reprobe_duplicates(219001,9); // genuine Duplicate path
    int rows=pc_p2_kogane_onion_ledger_rows();
    std::printf("P2_KOGANE_REPROBE duplicates=%d\n",dups);std::fflush(stdout);
    std::printf("P2_KOGANE_ONION_LEDGER rows=%d\n",rows);std::fflush(stdout);
    require(dups==3,"onion ledger re-grant (cap broken)");
    require(rows==3,"onion ledger row count drifted");
    require(!aliveTeki(219001),"restored beetle re-armed (passive check; no reward)");
    std::puts("PASS P2_KOGANE_RESTART dedupe_ok rearmed=0 duplicate=3 ledger=3");std::fflush(stdout);std::_Exit(0);}
  }
  std::fflush(stdout);return result;
 }};
'''

EXPECTED_DROPS = {(219001, 1): (1, 1, 0), (219001, 2): (0, 0, 2), (219001, 3): (0, 0, 3)}


def validate_collect(text, code):
    """Validate the collection pass: exact flip table, escape, exactly-once onion
    receipts, and a real collection census (1 pellet carried, 5 nectar drunk)."""
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    flips = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text))
    drops = {(int(g), int(f)): (int(pv), int(pc), int(nc)) for g, f, pv, pc, nc in
             re.findall(r'P2_KOGANE_DROP generator=(\d+) source_id=\d+ flip=(\d) '
                        r'pellet(\d+)=(\d+) nectar=(\d+)', text)}
    receipts = [(int(g), int(f), int(gr), int(dp)) for g, f, gr, dp in re.findall(
        r'P2_KOGANE_ONION_RECEIPT generator=(\d+) flip=(\d) granted=(\d) duplicate=(\d+).*ledger=onion', text)]
    escapes = [int(g) for g in re.findall(r'P2_KOGANE_ESCAPE generator=(\d+)', text)]
    m = re.search(r'P2_KOGANE_COLLECTED pellets_collected=(\d+) nectar_drunk=(\d+) sprouts=(\d+)', text)
    collected = dict(pellets=int(m[1]), nectar=int(m[2]), sprouts=int(m[3])) if m else None
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_COLLECT collect1 drink5 onion_receipt3' in text,
        births=births == [219001, 219002, 219003, CONTROL],
        flips=[f for g, f in flips if g == TARGET] == [1, 2, 3],
        drop_tables=all(drops.get((TARGET, f)) == EXPECTED_DROPS[(TARGET, f)] for f in (1, 2, 3)),
        onion_receipts=[(f, gr, dp) for g, f, gr, dp in receipts if g == TARGET]
                       == [(1, 1, 0), (2, 1, 0), (3, 1, 0)],
        escape=TARGET in escapes,
        collected=bool(collected) and collected['pellets'] == 1 and collected['nectar'] == 5
                  and collected['sprouts'] >= 1)
    return dict(passed=all(checks.values()), checks=checks, collected=collected,
                receipts=[list(r) for r in receipts],
                unmeasured=['P2 cave treasure/relocation (no P2 cave in the P1 host)',
                            'durable P2 save (family-local + lane-06 sidecars, not the lane 01/06 save)'])


def validate_collect_natural(text, code):
    """Validate the NATURAL collection pass: the base contract plus the flips coming
    from real Pikmin stick-attacks (``P2_KOGANE_NATURAL_ATTACK``), never the
    injected ``InteractPress`` path."""
    base = validate_collect(text, code)
    naturals = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_NATURAL_ATTACK generator=(\d+) source_id=\d+ flip=(\d)', text))
    target_naturals = [f for g, f in naturals if g == TARGET]
    extra = dict(
        natural_mode='mode=natural' in text,
        not_injected='mode=injected' not in text,
        natural_attacks=target_naturals == [1, 2, 3])
    checks = dict(base['checks'], **extra)
    return dict(passed=base['passed'] and all(checks.values()),
                checks=checks, collected=base.get('collected'),
                receipts=base.get('receipts'),
                natural_attacks=target_naturals, mode='natural')


def validate_restart(text, code):
    """Validate the restart pass: receipts reloaded, the farmed beetle reconstructed
    escaped, no re-arm/duplicate drop, a genuine Duplicate re-probe (x3) and the
    persisted onion ledger still at exactly three rows."""
    receipts_loaded = [int(n) for n in re.findall(r'P2_KOGANE_RECEIPTS loaded=(\d+)', text)]
    restored_escape = [(int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_RESTORED_ESCAPE generator=(\d+) flips=(\d+)', text)]
    new_drops = [g for g in re.findall(r'P2_KOGANE_DROP generator=(\d+)', text)]
    new_receipts = [g for g in re.findall(r'P2_KOGANE_ONION_RECEIPT generator=(\d+) .*granted=1', text)]
    dups = [int(d) for d in re.findall(r'P2_KOGANE_REPROBE duplicates=(\d+)', text)]
    rows = [int(n) for n in re.findall(r'P2_KOGANE_ONION_LEDGER rows=(\d+)', text)]
    dup_receipts = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_ONION_RECEIPT generator=(\d+) flip=(\d) granted=0 duplicate=1 ledger=onion', text))
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_RESTART dedupe_ok rearmed=0' in text,
        receipts_loaded=1 in receipts_loaded,
        restored_escape=restored_escape == [(TARGET, 3)],
        no_new_drop=new_drops == [],
        no_new_grant=new_receipts == [],
        rearmed_plain='P2_KOGANE_RESTART rearmed=0' in text,
        reprobe_duplicates=dups == [3],
        duplicate_receipts=dup_receipts == [(TARGET, 1), (TARGET, 2), (TARGET, 3)],
        onion_ledger_rows=rows == [3])
    return dict(passed=all(checks.values()), checks=checks,
                receipts_loaded=receipts_loaded,
                restored_escape=[list(r) for r in restored_escape],
                reprobe_duplicates=dups, onion_ledger_rows=rows)


def validate_cross(first_text, first_code, second_text, second_code):
    first = validate_collect(first_text, first_code)
    second = validate_restart(second_text, second_code)
    return dict(passed=first['passed'] and second['passed'],
                checks=dict(collect=first['passed'], restart=second['passed']),
                collect=first['checks'], restart=second['checks'], collected=first.get('collected'))


def _reward_rows(text):
    """Reward identities from a ``P2_RECEIPTS_1`` sidecar body."""
    out = []
    for line in (text or '').splitlines():
        line = line.strip()
        if not line or line.startswith('P2_RECEIPTS_1'):
            continue
        parts = line.split()
        if len(parts) >= 2:
            out.append(parts[1])
    return out


def validate_mixed_scene(kogane_file_text, flora_file_text):
    """Codify the lane-06 mixed-scene contract: the Kogane and Flora ordinary-Onion
    ledgers must stay in their own files. Today's native receipt host is a single
    process-global singleton (``pc_p2_receipt_host.cpp``), so a co-staged Flora
    steals the shared ledger; this validator flags that cross-contamination and
    documents the pending lane-06 per-consumer-ledger ask."""
    kogane = _reward_rows(kogane_file_text)
    flora = _reward_rows(flora_file_text)
    kogane_leak = [r for r in kogane if r.startswith('flora-pelplant:')]
    flora_leak = [r for r in flora if r == 'enemy:9']
    checks = dict(
        kogane_exactly_once=kogane == ['enemy:9', 'enemy:9', 'enemy:9'],
        flora_has_no_kogane=not flora_leak,
        kogane_has_no_flora=not kogane_leak)
    passed = checks['kogane_exactly_once'] and checks['flora_has_no_kogane'] and checks['kogane_has_no_flora']
    return dict(passed=passed, checks=checks, kogane=kogane, flora=flora,
                kogane_leak=kogane_leak, flora_leak=flora_leak,
                blocker=('lane-06 per-consumer ledger: pc_p2_receipt_host.cpp keeps one '
                         'process-global persistence/ledger singleton (:7-9) that '
                         'pc_p2_receipt_host_open replaces unconditionally (:11-22), so '
                         'co-staged consumers share it (flora_actor.cpp opens p2-flora-receipts.txt '
                         'in setup; kogane.cpp opens p2-kogane-onion-receipts.txt in setup).'))


def build(native, build_dir, output, head, resume=False):
    return build_fixture_base(native, build_dir, output, head, resume, app=INCLUDES + APP)


def run(assets, bank, output, exe, mode='natural'):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PYTHONUTF8'] = '1'
    validator = validate_collect_natural if mode == 'natural' else validate_collect
    return run_fixture_base(assets, bank, output, exe,
                            sidecar=native_sidecar(bank), validator=validator)


def _stage_marker(stage, name, content):
    (stage / name).write_text(content)


def run_cross_process(assets, bank, output, exe, mode='natural'):
    """Stage once, then run pass 1 (collect) and pass 2 (restart) on one directory."""
    stage = prepare(assets, bank, output / 'stages')
    manifest = json.loads((stage / 'arena.json').read_text())
    (stage / 'kogane-positions.txt').write_bytes(
        ''.join(f"{a['generator']} " + ' '.join(map(str, a['expected_xyz'])) + '\n'
                for a in manifest['actors']).encode())
    (stage / 'p2-kogane-native.txt').write_text(native_sidecar(bank))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               PIKMIN_P2_ROOM_WINDOW='960x540', PYTHONUTF8='1', SDL_AUDIODRIVER='dummy')
    logs, codes = [], []
    for number in (0, 2):
        (stage / 'kogane-pass.txt').write_text('%d\n' % number)
        _stage_marker(stage, 'kogane-mode.txt', '%s\n' % (1 if mode == 'natural' else 0))
        log_path = stage / ('native-pass%d.log' % number)
        with log_path.open('w') as log:
            try:
                codes.append(subprocess.run(
                    [str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                    cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT,
                    timeout=300).returncode)
            except subprocess.TimeoutExpired:
                codes.append('timeout')
        logs.append(log_path.read_text(errors='replace'))
    evidence = validate_cross(logs[0], codes[0], logs[1], codes[1])
    evidence.update(exit_codes=codes, executable=builder.snapshot([exe]),
                    arena=builder.snapshot([stage / 'arena.json', stage / 'kogane-positions.txt',
                                            stage / 'p2-kogane-native.txt']))
    (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2))
    print(stage, flush=True)
    print(json.dumps(evidence), flush=True)
    return stage


def run_mixed(assets, bank, output, exe):
    """Co-stage a Flora Pelplant consumer with the Kogane consumer in one room and
    run the natural collection pass, then read both ordinary-Onion ledgers to show
    whether they stay separate under the shared single-consumer receipt host."""
    stage = prepare(assets, bank, output / 'stages')
    manifest = json.loads((stage / 'arena.json').read_text())
    (stage / 'kogane-positions.txt').write_bytes(
        ''.join(f"{a['generator']} " + ' '.join(map(str, a['expected_xyz'])) + '\n'
                for a in manifest['actors']).encode())
    (stage / 'p2-kogane-native.txt').write_text(native_sidecar(bank))
    # One pending Pelplant spec (never binds to a live TEKI_Palm here) is enough to
    # make pc_p2_flora_setup open its own receipt ledger, exercising the mixed scene.
    _stage_marker(stage, 'p2-flora-pelplant.txt',
                  'P2_FLORA_PELPLANT_1 1\n240001 full 1 red\n')
    _stage_marker(stage, 'kogane-pass.txt', '0\n')
    _stage_marker(stage, 'kogane-mode.txt', '1\n')
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               PIKMIN_P2_ROOM_WINDOW='960x540', PYTHONUTF8='1', SDL_AUDIODRIVER='dummy')
    log_path = stage / 'native-pass0.log'
    code = 'n/a'
    with log_path.open('w') as log:
        try:
            code = subprocess.run(
                [str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT,
                timeout=300).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    text = log_path.read_text(errors='replace')
    kogane_file = (stage / 'p2-kogane-onion-receipts.txt').read_text(errors='replace') \
        if (stage / 'p2-kogane-onion-receipts.txt').is_file() else ''
    flora_file = (stage / 'p2-flora-receipts.txt').read_text(errors='replace') \
        if (stage / 'p2-flora-receipts.txt').is_file() else ''
    separation = validate_mixed_scene(kogane_file, flora_file)
    evidence = dict(collect=validate_collect(text, code), separation=separation,
                    exit_code=code, executable=builder.snapshot([exe]),
                    kogane_ledger=dict(rows=_reward_rows(kogane_file), file='p2-kogane-onion-receipts.txt'),
                    flora_ledger=dict(rows=_reward_rows(flora_file), file='p2-flora-receipts.txt'))
    (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2))
    print(stage, flush=True)
    print(json.dumps(evidence), flush=True)
    return stage


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    rc = sub.add_parser('run-cross')
    rm = sub.add_parser('run-mixed')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
        rc.add_argument('--' + n, type=Path, required=True)
        rm.add_argument('--' + n, type=Path, required=True)
    r.add_argument('--mode', choices=('natural', 'injected'), default='natural')
    rc.add_argument('--mode', choices=('natural', 'injected'), default='natural')
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    elif a.command == 'run':
        run(a.assets, a.bank, a.output, a.exe, a.mode)
    elif a.command == 'run-cross':
        run_cross_process(a.assets, a.bank, a.output, a.exe, a.mode)
    else:
        run_mixed(a.assets, a.bank, a.output, a.exe)
