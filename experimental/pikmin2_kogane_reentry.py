"""Lane 17 re-entry acceptance for restored-flip dedupe (#168/#219).

Private fixture built on the parameterized
``experimental.pikmin2_kogane_runtime.build/run`` arena (the same staging path as
the accepted batch-4 behavior fixture). ``kogane-pass.txt`` selects the RoomApp
pass; the default (no marker) is the in-process pass 0. It drives two flips on
Kogane (219001), one on Wealthy (219002) and leaves Doodlebug (219003)
untouched, then calls ``pc_p2_kogane_reset()`` + ``pc_p2_kogane_setup()`` a second
time in the same process. The reset snapshots every live actor's flip count by
generator id and setup must reconstruct the spent state instead of re-spawning a
beetle that can never drop again:

  - Kogane, already at the source flip cap, is restored escaped
    (``P2_KOGANE_RESTORED_ESCAPE``) and burrows away,
  - Wealthy resumes at its restored flip count (``P2_KOGANE_FLIPS_RESTORED``),
  - the untouched Doodlebug emits no restore line.

The third Kogane press and the reset+setup happen in the same tick, before the
pending damage-clip escape finalizes, so every actor is still present at setup.

``run-cross`` extends this across processes: pass 1 spends the flips and exits;
pass 2 starts fresh on the same run directory, loads the ``p2-kogane-receipts.txt``
sidecar written by pass 1 and must report ``P2_KOGANE_RECEIPTS loaded=2`` plus the
same restored rows before resuming the survivor to the cap. This module never
runs the desktop/GL slot; ``validate``/``validate_cross_process`` check the
captured logs. See ``docs/PIKMIN2_KOGANE_REWARDS.md``.

The ``treasure=True`` option opts one beetle into the native first-flip treasure
stand-in (#168/#219). Wealthy (219002) carries a single 5-pellet stand-in instead
of its audited first-flip table row (three 5-pellets); ``validate_treasure``
requires the ``P2_KOGANE_TREASURE generator=219002 value=5`` marker plus the
single stand-in pellet, and rejects the untouched table row. The P1 host has no
P2 treasure object, so this is a labelled number pellet, not the source treasure.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from experimental.pikmin2_kogane_arena import prepare
from experimental.pikmin2_kogane_assets import MAX_FLIPS
from experimental.pikmin2_kogane_behavior import EXPECTED_DROPS, native_sidecar
from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import instrument as instrument_base
from experimental.pikmin2_kogane_runtime import run as run_fixture_base
from scripts import build_pikmin2_fixture as builder

IDS = (219001, 219002, 219003)
SPENT = 219001     # reaches the flip cap in the first pass; restored escaped
SURVIVOR = 219002  # partial flips; restored at its count
UNTOUCHED = 219003 # never flipped; must not emit a restore line
# First-flip treasure stand-in (#168/#219): Wealthy's audited table first flip is
# three 5-pellets, so one configured 5-pellet stand-in is observably distinct.
TREASURE = 219002
TREASURE_VALUE = 5

APP = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0,pass=0;
 Teki* beetles[3]={nullptr,nullptr,nullptr};
 void press(Teki* actor,Navi* n){if(!actor)return;InteractPress p(n,0.0f);actor->stimulate(p);}
 bool aliveTeki(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id&&a->isAlive())return true;}return false;}
 void reenter(){pc_p2_kogane_reset();pc_p2_kogane_setup();std::printf("P2_KOGANE_REENTRY reset_setup=2\n");std::fflush(stdout);}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<20000,"beetle reentry timeout");
  if(frames==1){std::ifstream pf("kogane-pass.txt");if(pf)pf>>pass;std::printf("P2_KOGANE_PASS pass=%d\n",pass);std::fflush(stdout);}
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
   if(pass==2){
    // A second process restores the spent beetle from the on-disk receipts, so
    // it may already be escaping at first observation; tolerate its absence.
    for(int i=0;i<3;++i){Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==219001+i){actor=a;++matches;}}
     require(matches<=1,"beetle roster identity");beetles[i]=actor;
     if(actor){Vector3f p=actor->getPosition();std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",219001+i,actor->mTekiType,p.x,p.y,p.z);}}
   }else{
    std::ifstream input("kogane-positions.txt");unsigned id;float x,y,z;int count=0;
    while(input>>id>>x>>y>>z){
     Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
     require(matches==1,"beetle roster identity");
     std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,x,y,z);
     if(id>=219001&&id<=219003)beetles[id-219001]=actor;
     ++count;}
    require(count==4,"beetle roster missing");}
  }
  if(pass==0){
   // In-process reset+setup: two flips on Kogane and one on Wealthy; the third
   // Kogane press and the reset+setup happen together, before the pending escape
   // can finalize.
   if(observed==90||observed==180)press(beetles[0],n);
   if(observed==90)press(beetles[1],n);
   if(observed==270){press(beetles[0],n);reenter();}
   if(observed==280){
    require(!aliveTeki(219001),"restored spent beetle still present");
    require(aliveTeki(219002),"restored surviving beetle missing");
    require(aliveTeki(219003),"untouched beetle missing");
    std::puts("PASS P2_KOGANE_REENTRY restored2 escaped1");std::fflush(stdout);std::_Exit(0);}
  }else if(pass==1){
   // First process: spend Kogane and leave Wealthy at one flip, then exit so the
   // sidecar receipts survive for a second process on the same run directory.
   if(observed==90||observed==180)press(beetles[0],n);
   if(observed==90)press(beetles[1],n);
   if(observed==270)press(beetles[0],n);
   if(observed==400){
    require(!aliveTeki(219001),"pass1 spent beetle still present");
    require(aliveTeki(219002)&&aliveTeki(219003),"pass1 surviving beetles missing");
    std::puts("PASS P2_KOGANE_RECEIPTS_PASS1 flips4 escaped1");std::fflush(stdout);std::_Exit(0);}
  }else{
   // Second process: the sidecar restores the spent escape and the partial
   // survivor; resume the survivor to the source cap before finishing.
   if(observed==90||observed==180)press(beetles[1],n);
   if(observed==280){
    require(!aliveTeki(219001),"cross-process spent beetle still present");
    require(!aliveTeki(219002),"cross-process survivor never escaped");
    require(aliveTeki(219003),"untouched beetle missing");
    std::puts("PASS P2_KOGANE_RECEIPTS_PASS2 restored2 escaped1");std::fflush(stdout);std::_Exit(0);}
  }
  std::fflush(stdout);return result;
 }};
'''

APP_TREASURE = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0;
 Teki* beetles[3]={nullptr,nullptr,nullptr};
 int alivePellets(){int c=0;Iterator it(pelletMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 void press(Teki* actor,Navi* n){if(!actor)return;InteractPress p(n,0.0f);actor->stimulate(p);}
 public:int idle() override {
  int result=PlugPikiApp::idle();require(++frames<20000,"beetle treasure timeout");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr)return result;
  Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  ++observed;
  if(observed==1){
   for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
   for(int i=0;i<3;++i){Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==219001+i){actor=a;++matches;}}
    require(matches==1,"beetle roster identity");beetles[i]=actor;Vector3f p=actor->getPosition();
    std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",219001+i,actor->mTekiType,p.x,p.y,p.z);}
  }
  // One press on the configured Wealthy. The audited table first flip is three
  // 5-pellets, so a single stand-in 5-pellet plus the P2_KOGANE_TREASURE marker
  // (emitted by the native override) is the observable difference. Exit as soon
  // as the stand-in pellet exists, before the squad can collect it.
  if(observed==90)press(beetles[1],n);
  if(observed>90&&alivePellets()>=1){
   int pellets=alivePellets();
   std::printf("P2_KOGANE_CENSUS pellets=%d\n",pellets);std::fflush(stdout);
   require(pellets==1,"treasure stand-in pellet count");
   std::puts("PASS P2_KOGANE_TREASURE standin1 value5");std::fflush(stdout);std::_Exit(0);}
  std::fflush(stdout);return result;
 }};
'''

INCLUDES = ('#include <map>\n#include "Demo.h"\n#include "Interactions.h"\n'
            '#include "PelletView.h"\n#include "PlayerState.h"\n'
            '#include "pc_p2_kogane.h"\n')

# The treasure app counts live number pellets, so it needs the pellet manager.
TREASURE_INCLUDES = INCLUDES + '#include "Pellet.h"\n'


def validate(text, code):
    """Validate a re-entry run log against the restored-flip contract.

    Accepts only a clean completion where exactly Kogane at the cap is reported
    escaped, Wealthy resumes at one flip and the untouched Doodlebug emits no
    restore line. The reset+setup reloads the receipts written by the third
    press, so the in-process path also reports ``P2_KOGANE_RECEIPTS loaded=2``.
    """
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    restored = sorted((int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_FLIPS_RESTORED generator=(\d+) flips=(\d+)', text))
    escaped = sorted((int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_RESTORED_ESCAPE generator=(\d+) flips=(\d+)', text))
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_REENTRY restored2 escaped1' in text,
        pass_marker='P2_KOGANE_PASS pass=0' in text,
        births=births == list(IDS) + [219004],
        reset_setup='P2_KOGANE_REENTRY reset_setup=2' in text,
        receipts_loaded='P2_KOGANE_RECEIPTS loaded=2' in text,
        restored=restored == [(SPENT, MAX_FLIPS), (SURVIVOR, 1)],
        restored_escape=escaped == [(SPENT, MAX_FLIPS)],
        untouched=UNTOUCHED not in {g for g, _ in restored})
    return dict(passed=all(checks.values()), checks=checks,
                restored={str(g): n for g, n in restored},
                restored_escape=[list(row) for row in escaped],
                unmeasured=['full scene/day reload (in-process reset/re-entry only)',
                            'native treasure override / cave relocation (disabled: P1 host)',
                            'cross-process save bridge (lane 01/06)',
                            'cross-process sidecar restart (see validate_cross_process)'])


def validate_treasure(text, code):
    """Validate the first-flip treasure override run (#168/#219).

    Requires the configured Wealthy actor's single first flip to log the
    ``P2_KOGANE_TREASURE generator=219002 value=5`` marker (emitted by the native
    stand-in) and to drop exactly one stand-in 5-pellet. The audited table row
    for that flip (three 5-pellets) is rejected, so a run that left the table in
    place cannot pass even if a marker were forged. This is a P1 number-pellet
    approximation, not the source treasure object.
    """
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    flips = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text))
    drops = {(int(g), int(f)): (int(pv), int(pc), int(nc)) for g, f, pv, pc, nc in
             re.findall(r'P2_KOGANE_DROP generator=(\d+) source_id=\d+ flip=(\d) '
                        r'pellet(\d+)=(\d+) nectar=(\d+)', text)}
    treasures = sorted((int(g), int(v)) for g, v in re.findall(
        r'P2_KOGANE_TREASURE generator=(\d+) value=(\d+)', text))
    m = re.search(r'P2_KOGANE_CENSUS pellets=(\d+)', text)
    census = int(m[1]) if m else None
    table = EXPECTED_DROPS[(TREASURE, 1)]
    standin = (TREASURE_VALUE, 1, 0)
    observed = drops.get((TREASURE, 1))
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_TREASURE standin1 value5' in text,
        births=births == list(IDS),
        flips=flips == [(TREASURE, 1)],
        marker=treasures == [(TREASURE, TREASURE_VALUE)],
        standin=observed == standin,
        override_vs_table=observed == standin and standin != table,
        census=census == 1)
    return dict(passed=all(checks.values()), checks=checks,
                treasures={str(g): v for g, v in treasures},
                drop={f'{g}:{f}': list(v) for (g, f), v in sorted(drops.items())},
                census=census,
                unmeasured=['real P2 treasure item (labelled P1 number-pellet stand-in)',
                            'cave relocation and carry-to-Onion (no P2 cave in the P1 host)',
                            'other actors/flips keep the audited table (host model only)'])


def validate_pass1(text, code):
    """Validate the first process of the cross-process restart sequence.

    A fresh run directory has no receipt sidecar, so setup reports
    ``P2_KOGANE_RECEIPTS loaded=0`` and no beetle is restored. Kogane is driven
    to the cap (with the source escape) and Wealthy is left at one flip for the
    second process.
    """
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    flips = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text))
    escaped = sorted(int(g) for g in re.findall(r'P2_KOGANE_ESCAPE generator=(\d+)', text))
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_RECEIPTS_PASS1 ' in text,
        pass_marker='P2_KOGANE_PASS pass=1' in text,
        births=births == list(IDS) + [219004],
        fresh_receipts=set(re.findall(r'P2_KOGANE_RECEIPTS loaded=(\d+)', text)) == {'0'},
        flips=flips == [(SPENT, 1), (SPENT, 2), (SPENT, 3), (SURVIVOR, 1)],
        escape=escaped == [SPENT],
        no_restore='P2_KOGANE_FLIPS_RESTORED' not in text)
    return dict(passed=all(checks.values()), checks=checks)


def validate_pass2(text, code):
    """Validate the second process, which must load the on-disk receipts.

    The sidecar restores Kogane at the cap (reconstructed escape) and Wealthy at
    one flip; the untouched Doodlebug emits no restore line. The restored
    survivor is then driven to the cap, proving the finite dedupe resumes across
    a process restart.
    """
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    restored = sorted((int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_FLIPS_RESTORED generator=(\d+) flips=(\d+)', text))
    escaped = sorted((int(g), int(n)) for g, n in re.findall(
        r'P2_KOGANE_RESTORED_ESCAPE generator=(\d+) flips=(\d+)', text))
    flips = sorted((int(g), int(f)) for g, f in re.findall(
        r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text))
    live_escape = sorted(int(g) for g in re.findall(r'P2_KOGANE_ESCAPE generator=(\d+)', text))
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_RECEIPTS_PASS2 ' in text,
        pass_marker='P2_KOGANE_PASS pass=2' in text,
        receipts_loaded=set(re.findall(r'P2_KOGANE_RECEIPTS loaded=(\d+)', text)) == {'2'},
        restored=restored == [(SPENT, MAX_FLIPS), (SURVIVOR, 1)],
        restored_escape=escaped == [(SPENT, MAX_FLIPS)],
        untouched=UNTOUCHED not in {g for g, _ in restored},
        survivor_birth=SURVIVOR in births and UNTOUCHED in births,
        resumed=flips == [(SURVIVOR, 2), (SURVIVOR, 3)],
        survivor_escape=live_escape == [SURVIVOR])
    return dict(passed=all(checks.values()), checks=checks,
                restored={str(g): n for g, n in restored},
                restored_escape=[list(row) for row in escaped],
                receipts_loaded=2 if checks['receipts_loaded'] else None)


def validate_cross_process(first_text, first_code, second_text, second_code):
    """Validate a full first-pass + second-process restart run on one run dir."""
    first = validate_pass1(first_text, first_code)
    second = validate_pass2(second_text, second_code)
    checks = dict(first_pass=first['passed'], second_pass=second['passed'])
    return dict(passed=all(checks.values()), checks=checks,
                first_pass=first['checks'], second_pass=second['checks'],
                restored=second['restored'], restored_escape=second['restored_escape'],
                receipt_rows=second['receipts_loaded'],
                unmeasured=['full scene/day reload (two process launches on one run dir only)',
                            'native treasure override / cave relocation (disabled: P1 host)',
                            'P2 save bridge (family-local sidecar, not the lane 01/06 save)'])


def treasure_sidecar(bank):
    """Sidecar for the treasure fixture: Wealthy's first flip carries one 5-pellet.

    The audited table first flip for Wealthy is three 5-pellets, so the single
    stand-in is observably distinct from the normal table.
    """
    return native_sidecar(bank, treasures={TREASURE: TREASURE_VALUE})


def build(native, build_dir, output, head, resume=False, treasure=False):
    app = TREASURE_INCLUDES + APP_TREASURE if treasure else INCLUDES + APP
    return build_fixture_base(native, build_dir, output, head, resume, app=app)


def run(assets, bank, output, exe, treasure=False):
    sidecar = treasure_sidecar(bank) if treasure else native_sidecar(bank)
    validator = validate_treasure if treasure else validate
    return run_fixture_base(assets, bank, output, exe,
                            sidecar=sidecar, validator=validator)


def run_cross_process(assets, bank, output, exe):
    """Stage once, then run two processes on the same run directory.

    The first process spends the finite flips; the second starts fresh, loads the
    ``p2-kogane-receipts.txt`` sidecar and must reconstruct the restored state.
    The ``kogane-pass.txt`` marker selects the RoomApp pass.
    """
    stage = prepare(assets, bank, output / 'stages')
    manifest = json.loads((stage / 'arena.json').read_text())
    (stage / 'kogane-positions.txt').write_bytes(
        ''.join(f"{a['generator']} " + ' '.join(map(str, a['expected_xyz'])) + '\n'
                for a in manifest['actors']).encode())
    (stage / 'p2-kogane-native.txt').write_text(native_sidecar(bank))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''),
               SDL_AUDIODRIVER='dummy')
    logs, codes = [], []
    for number in (1, 2):
        (stage / 'kogane-pass.txt').write_text('%d\n' % number)
        log_path = stage / ('native-pass%d.log' % number)
        with log_path.open('w') as log:
            try:
                codes.append(subprocess.run(
                    [str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                    cwd=stage, env=env, stdout=log, stderr=subprocess.STDOUT,
                    timeout=180).returncode)
            except subprocess.TimeoutExpired:
                codes.append('timeout')
        logs.append(log_path.read_text(errors='replace'))
    evidence = validate_cross_process(logs[0], codes[0], logs[1], codes[1])
    sidecar = stage / 'p2-kogane-receipts.txt'
    evidence.update(exit_codes=codes, executable=builder.snapshot([exe]),
                    sidecar=builder.snapshot([sidecar]) if sidecar.exists() else None,
                    arena=builder.snapshot([stage / 'arena.json', stage / 'kogane-positions.txt',
                                            stage / 'p2-kogane-native.txt']))
    (stage / 'runtime-evidence.json').write_text(json.dumps(evidence, indent=2))
    print(stage, flush=True)
    print(json.dumps(evidence), flush=True)
    return stage


def instrument(source, treasure=False):
    app = TREASURE_INCLUDES + APP_TREASURE if treasure else INCLUDES + APP
    return instrument_base(source, app)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    rc = sub.add_parser('run-cross')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    b.add_argument('--treasure', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    r.add_argument('--treasure', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        rc.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume, a.treasure)
    elif a.command == 'run':
        run(a.assets, a.bank, a.output, a.exe, a.treasure)
    else:
        run_cross_process(a.assets, a.bank, a.output, a.exe)
