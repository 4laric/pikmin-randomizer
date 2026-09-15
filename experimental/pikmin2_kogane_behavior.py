"""Batch-4 beetle behavior acceptance: native flip/drop, gas and escape (#219).

Stages the batch-2 arena (three beetles + P1 control + 20-red starting squad),
writes the P2_KOGANE_NATIVE_1 sidecar from the validated batch-1 bank, then
runs a private instrumented RoomApp that stimulates the audited source cycle
on the real registered actors:

  - wander: every beetle must leave its birth point (source StateWait/StateMove
    cycle driven by pc_p2_kogane_update),
  - flip/drop: three stimulated presses each on Kogane (219001) and Wealthy
    (219002), one on Fart (219003), with exact source-table drops asserted in
    the native log (P1-host resolution: nectar + number pellets),
  - forced escape: Kogane and Wealthy burrow away after the third flip with no
    corpse pellet (pellet census stays at exactly the four dropped pellets),
  - Fart gas: one squad Pikmin is pinned at the active gas anchor via the
    pc_p2_kogane_gas_state introspection hook and must die of sustained
    exposure; the other 19 survive (beetles are harmless; control is distant).

The first-flip treasure override is now an opt-in labelled P1 number-pellet
stand-in (`native_sidecar(..., treasures=...)`), but this fixture configures no
treasure; cave relocation remains disabled in the P1 host and neither is asserted
here (recorded gaps on #219).
"""
import argparse
import json
import re
from pathlib import Path

from experimental.pikmin2_kogane_runtime import build as build_fixture_base
from experimental.pikmin2_kogane_runtime import run as run_fixture_base
from experimental.pikmin2_kogane_native import treasure_lines

IDS = (219001, 219002, 219003)
SPECIES_ID = {219001: 9, 219002: 10, 219003: 11}
KARADA_INDEX = 0  # audited karada material slot; matches root's fixed binding bundle

APP = r'''class RoomApp : public PlugPikiApp {
 int observed=0,frames=0;
 Teki* beetles[3]={nullptr,nullptr,nullptr};
 Vector3f start[3];
 bool moved[3]={false,false,false};
 Piki* pinned=nullptr;
 std::map<Piki*,Vector3f> home; // deterministic home-pin cells matching the arena squad placement
 void press(Teki* actor,Navi* n){if(!actor)return;InteractPress p(n,0.0f);actor->stimulate(p);}
 int alivePikis(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Creature* p=*it;if(p&&p->isAlive())++c;}return c;}
 bool aliveTeki(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* a=static_cast<Teki*>(*it);if(a&&a->mGenerator&&a->mGenerator->_70==id&&a->isAlive())return true;}return false;}
 bool alivePiki(Piki* q){if(!q)return false;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p==q)return p->isAlive();}return false;}
public:int idle() override {
 int result=PlugPikiApp::idle();require(++frames<20000,"beetle behavior timeout");
 if(frames%120==0){std::printf("P2_KOGANE_GATE frame=%d pause=%d ui=%d movie=%d ready=%d all=%d form=%d free=%d work=%d me=%d cont=%d dead=%d max=%d\n",frames,int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive),int(pc_p2_preview_cargo_free_ready()),int(GameStat::allPikis),int(GameStat::formationPikis),int(GameStat::freePikis),int(GameStat::workPikis),int(GameStat::mePikis),int(GameStat::containerPikis),int(GameStat::deadPikis),GameStat::maxPikis);std::fflush(stdout);}
 if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
 if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!tekiMgr||!pikiMgr)return result;
 Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
 ++observed;
 if(observed==1){
  for(int i=0;i<DEMOFLAG_COUNT;++i)playerState->mDemoFlags.setFlagOnly(i); // suppress one-shot discovery cutscenes
  std::ifstream input("kogane-positions.txt");unsigned id;float x,y,z;int count=0;
  while(input>>id>>x>>y>>z){
   Teki* actor=nullptr;int matches=0;Iterator iter(tekiMgr);CI_LOOP(iter){Teki* a=static_cast<Teki*>(*iter);if(a->mGenerator&&a->mGenerator->_70==id){actor=a;++matches;}}
   require(matches==1,"beetle roster identity");
   Vector3f birth=actor->mPersonality->mPosition;
   require(std::fabs(birth.x-x)<.02&&std::fabs(birth.y-y)<.02&&std::fabs(birth.z-z)<.02,"beetle birth XYZ");
   std::printf("P2_KOGANE_BIRTH id=%u type=%d x=%.3f y=%.3f z=%.3f\n",id,actor->mTekiType,birth.x,birth.y,birth.z);
   if(id>=219001&&id<=219003){beetles[id-219001]=actor;start[id-219001]=actor->getPosition();}
   ++count;}
  require(count==4,"beetle roster missing");}
  if(observed==60){require(alivePikis()==20,"starting squad size");}
  if(observed==50){
   int want[3]={9,10,11},before=0;
   for(int i=0;i<3;++i)if(beetles[i]&&pc_p2_kogane_source_id(static_cast<PelletView*>(beetles[i]))==want[i])++before;
   require(before==3,"pre-cleanup registration");
   pc_p2_kogane_reset();
   int cleared=0;
   for(int i=0;i<3;++i)if(beetles[i]&&pc_p2_kogane_source_id(static_cast<PelletView*>(beetles[i]))<0)++cleared;
   require(cleared==3,"stale registration rejected after reset");
   pc_p2_kogane_setup();
   int reentry=0;
   for(int i=0;i<3;++i)if(beetles[i]&&pc_p2_kogane_source_id(static_cast<PelletView*>(beetles[i]))==want[i])++reentry;
   require(reentry==3,"re-entry registration rebuilt");
   std::printf("P2_KOGANE_CLEANUP registered_before=%d cleared=%d reentry=%d\n",before,cleared,reentry);std::fflush(stdout);}
 for(int i=0;i<3;++i)if(beetles[i]&&!aliveTeki(219001+i))beetles[i]=nullptr;
 for(int i=0;i<3;++i)if(beetles[i]&&!moved[i]&&start[i].distance(beetles[i]->getPosition())>30.0f)moved[i]=true;
 {Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;
  if(p==pinned)continue; // gas probe follows the cloud anchor instead
  if(home.find(p)==home.end()){int idx=home.size();home[p]=Vector3f(-140.0f+8.0f*(idx%10),30.0f,1820.0f-8.0f*(idx/10));}
  p->mSRT.t.set(home[p]);p->mVelocity.set(0,0,0);p->mTargetVelocity.set(0,0,0);}}
 if(observed==60&&!pinned){Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive()){pinned=p;break;}}}
 if(pinned&&!alivePiki(pinned))pinned=nullptr;
 if(pinned&&beetles[2]){
  float gx,gz,gt;
  if(pc_p2_kogane_gas_state(beetles[2],&gx,&gz,&gt)){pinned->mSRT.t.set(gx,beetles[2]->getPosition().y,gz);pinned->mVelocity.set(0,0,0);pinned->mTargetVelocity.set(0,0,0);}}
 if(observed==100||observed==200||observed==300)press(beetles[0],n);
 if(observed==400||observed==500||observed==600)press(beetles[1],n);
 if(observed==700)press(beetles[2],n);
 if(observed>=1400){
  require(moved[0]&&moved[1]&&moved[2],"beetle wander");
  require(!aliveTeki(219001)&&!aliveTeki(219002),"escaped beetles still present");
  require(aliveTeki(219003),"fart beetle missing");
  require(alivePikis()==19,"gas kill count");
  int pellets=0,nectar=0;
  Iterator ip(pelletMgr);CI_LOOP(ip){Creature* p=*ip;if(p&&p->isAlive())++pellets;}
  if(itemMgr){Iterator iw(itemMgr);CI_LOOP(iw){Creature* w=*iw;if(w&&w->mObjType==OBJTYPE_Water&&w->isAlive())++nectar;}}
  std::printf("P2_KOGANE_CENSUS pellets=%d nectar=%d pikis=%d\n",pellets,nectar,alivePikis());std::fflush(stdout);
  require(pellets==4,"number pellet count (incl. corpse suppression)");
  require(nectar==14,"nectar count"); // squad is home-pinned outside the drop zones; every drop must persist
  std::puts("PASS P2_KOGANE_BEHAVIOR flips7 wander3 escapes2 gas1");std::fflush(stdout);std::_Exit(0);}
 std::fflush(stdout);return result;
}};
'''

INCLUDES = ('#include <map>\n#include "Demo.h"\n#include "GameStat.h"\n#include "Interactions.h"\n#include "ItemMgr.h"\n#include "ObjType.h"\n'
            '#include "Pellet.h"\n#include "PelletView.h"\n#include "Piki.h"\n#include "PikiMgr.h"\n#include "PlayerState.h"\n'
            '#include "pc_p2_kogane.h"\n')

# Exact source drop tables in P1-host resolution (batch-1 audit):
#   kogane  flip1: 1x 1-pellet; flip2: 2 nectar; flip3: 3 nectar (spray fallback)
#   wealthy flip1: 3x 5-pellet; flip2/3: 3 nectar (spray fallback)
#   fart    flip1: 3 nectar
EXPECTED_DROPS = {(219001, 1): (1, 1, 0), (219001, 2): (0, 0, 2), (219001, 3): (0, 0, 3),
                  (219002, 1): (5, 3, 0), (219002, 2): (0, 0, 3), (219002, 3): (0, 0, 3),
                  (219003, 1): (0, 0, 3)}
EXPECTED_HEALTH = {219001: '1000.0', 219002: '1200.0', 219003: '1500.0'}


def native_sidecar(bank, mapping=None, treasures=None):
    """Build the P2_KOGANE_NATIVE_1 sidecar from the validated batch-1 bank.

    Mirrors every constraint of the C++ parser (p2kogane::read) so a generated
    sidecar can never be rejected at load: karada slot, unique generator/species
    rows, and move/wait/damage clips with ascending frames spanning [0, duration).
    ``treasures`` optionally maps a generator to a P1 stand-in number-pellet value
    (1 or 5) for that beetle's first flip; the host has no P2 treasure item.
    """
    mapping = mapping or SPECIES_ID
    if set(mapping) != set(IDS) or any(mapping[g] != SPECIES_ID[g] for g in IDS):
        raise ValueError('Sidecar mapping must cover exactly the three beetle actors')
    manifest = json.loads((Path(bank) / 'beetles.json').read_text())
    clips = {c['file']: c for c in manifest['shared']['clips']}
    if set(clips) != {'move.bca', 'wait.bca', 'damage.bca'}:
        raise ValueError('Bank clip set mismatch')
    rows = ['P2_KOGANE_NATIVE_1', f'karada {KARADA_INDEX}', f'actors {len(IDS)}']
    rows += [f'{g} {mapping[g]}' for g in IDS]
    rows += treasure_lines((treasures or {}).items(), IDS)
    for name in ('move', 'wait', 'damage'):
        clip = clips[name + '.bca']
        frames = [int(p['frame']) for p in clip['poses']]
        duration = int(clip['source_frames'])
        if (len(frames) < 2 or len(frames) > 24 or not 1 <= duration <= 10000
                or frames[0] != 0 or frames[-1] != duration - 1
                or any(b <= a for a, b in zip(frames, frames[1:]))):
            raise ValueError('Clip frames outside the native parser contract: ' + name)
        rows.append(f"{name} {len(frames)} {duration} " + ' '.join(map(str, frames)))
    return '\n'.join(rows) + '\n'


def validate_behavior(text, code):
    """Validate a batch-4 behavior run log against the audited source contract."""
    births = [int(b) for b in re.findall(r'P2_KOGANE_BIRTH id=(\d+)', text)]
    flips = [(int(g), int(f)) for g, f in
             re.findall(r'P2_KOGANE_FLIP generator=(\d+) source_id=\d+ flip=(\d)', text)]
    drops = {(int(g), int(f)): (int(pv), int(pc), int(nc)) for g, f, pv, pc, nc in
             re.findall(r'P2_KOGANE_DROP generator=(\d+) source_id=\d+ flip=(\d) '
                        r'pellet(\d+)=(\d+) nectar=(\d+)', text)}
    health = {int(g): h for g, h in
              re.findall(r'P2_ENEMY_READY .*generator=(\d+) .* max_health=([\d.]+) behavior=native', text)}
    checks = dict(
        completion=code == 0 and 'PASS P2_KOGANE_BEHAVIOR flips7 wander3 escapes2 gas1' in text,
        births=births == [219001, 219002, 219003, 219004],
        binding={(int(g), int(s)) for g, s in re.findall(
            r'P2_KOGANE_BIND generator=(\d+) source_id=(\d+) karada_k0=\d+ visual_only=0', text)}
            == {(g, SPECIES_ID[g]) for g in IDS},
        source_health=health == EXPECTED_HEALTH,
        flip_sequence=sorted(flips) == sorted([(g, f) for g in IDS for f in
                                               ((1, 2, 3) if g != 219003 else (1,))]),
        drop_tables=drops == EXPECTED_DROPS,
        escapes=sorted(int(g) for g in re.findall(r'P2_KOGANE_ESCAPE generator=(\d+)', text)) == [219001, 219002],
        gas_cycle=('P2_KOGANE_GAS start generator=219003 duration=2.500 radius=20.0' in text
                   and 'P2_KOGANE_GAS end generator=219003' in text
                   and 'P2_KOGANE_GAS_KILL generator=219003' in text),
        draw='P2_KOGANE_DRAW corpse=0' in text,
        cleanup_reentry='P2_KOGANE_CLEANUP registered_before=3 cleared=3 reentry=3' in text)
    m = re.search(r'P2_KOGANE_CENSUS pellets=(\d+) nectar=(\d+) pikis=(\d+)', text)
    census = dict(pellets=int(m[1]), nectar=int(m[2]), pikis=int(m[3])) if m else None
    checks['census'] = bool(census) and census['pellets'] == 4 and census['nectar'] == 14 \
        and census['pikis'] == 19
    return dict(passed=all(checks.values()), checks=checks, census=census, flips=[list(f) for f in flips],
                drops={f'{g}:{f}': list(v) for (g, f), v in sorted(drops.items())},
                unmeasured=['material/texture fidelity', 'treasure override (disabled: no P2 treasure in P1 host)',
                            'cave relocation (disabled: no Cave::randMapMgr in P1 host)',
                            'full scene/day reload (manager reset/re-entry covered by cleanup_reentry)'])


def build(native, build_dir, output, head, resume=False):
    # The runtime instrumenter splices the app after its own standard includes.
    return build_fixture_base(native, build_dir, output, head, resume, app=INCLUDES + APP)


def run(assets, bank, output, exe):
    return run_fixture_base(assets, bank, output, exe,
                            sidecar=native_sidecar(bank), validator=validate_behavior)


def instrument(source):
    from experimental.pikmin2_kogane_runtime import instrument as base
    return base(source, INCLUDES + APP)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    r = sub.add_parser('run')
    for n in ('native', 'build-dir', 'output'):
        b.add_argument('--' + n, type=Path, required=True)
    b.add_argument('--head', required=True)
    b.add_argument('--resume', action='store_true')
    for n in ('assets', 'bank', 'output', 'exe'):
        r.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    if a.command == 'build':
        build(a.native, a.build_dir, a.output, a.head, a.resume)
    else:
        run(a.assets, a.bank, a.output, a.exe)
