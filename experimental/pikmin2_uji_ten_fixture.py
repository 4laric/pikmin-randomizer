"""Ten source-count Uji proxy hauling regression, private native sources only."""
import argparse,json,re
from pathlib import Path
from unittest.mock import patch
from experimental import pikmin2_uji_fixture as base

HOOK=r'''
#include "pc_p2_sheargrub.h"
#include "YaiStrategy.h"
#include "TAI/Action.h"
struct UjiDeathProbe:BTeki { static void finish(BTeki* actor){auto call=&UjiDeathProbe::dieSoon;(actor->*call)();} };
static bool ujiTenFixture(Navi* n){
 static int ticks=0,step=0,repairs=0;static Teki* bugs[10]={};static Pellet* bodies[10]={};static bool crossed[10]={};
 require(++ticks<8000,"ten-Uji timeout");
 if(step==0){
  Iterator it(tekiMgr);int count=0;CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);unsigned id;int value;if(!pc_p2_sheargrub_receipt(t,id,value))continue;require(id>=61000&&id<61010,"unexpected Uji generator");int index=id-61000;require(!bugs[index]&&value==(index<4?2:1),"source Uji mapping");bugs[index]=t;++count;}
  require(count==10,"expected ten Uji actors");repairs=playerState->getCurrParts();require(pc_p2_preview_pokos()==0,"dirty ledger");
  std::puts("P2_UJI_TEN registered=10 female=6 male=4 positions_unchanged=1 proxy=P1");step=1;ticks=0;
 }else if(step==1&&ticks>=60){
  capture("uji-ten-live-scene.ppm");for(auto* bug:bugs){bug->mHealth=0;UjiDeathProbe::finish(bug);}
  n->mKontroller=new FixtureController();phase=1;walkPoint=0;step=2;ticks=0;
 }else if(step==2){
  Iterator it(pelletMgr);CI_LOOP(it){Pellet* p=static_cast<Pellet*>(*it);for(int i=0;i<10;++i)if(p->isAlive()&&p->mPelletView==static_cast<PelletView*>(bugs[i]))bodies[i]=p;}
  bool all=true;int found=0;for(auto* body:bodies){all=all&&body;if(body)++found;}if(ticks%300==0)std::printf("P2_TEN_WAIT bodies=%d captain_x=%.1f state=%d\n",found,n->mSRT.t.x,n->getCurrState()->getID());
  if(all&&n->mSRT.t.x>995){phase=2;capture("uji-ten-corpses.ppm");int index=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(!v->isAlive())continue;v->mActiveAction->abandon(nullptr);v->mActiveAction->mCurrActionIdx=PikiAction::Transport;v->mActiveAction->mChildActions[PikiAction::Transport].initialise(bodies[index++%10]);v->mMode=PikiMode::TransportMode;}require(index>=20,"twenty carriers required");std::puts("P2_UJI_TEN_TRANSPORT real_ai=1 corpse_relocation=0");step=3;ticks=0;}
 }else if(step==3){
  for(int i=0;i<10;++i)if(!crossed[i]&&bodies[i]->mSRT.t.x<425){crossed[i]=true;std::printf("P2_UJI_TEN_CROSS generator=%d\n",61000+i);}
  if(pc_p2_preview_pokos()==14||pc_p2_preview_pokos()==114){for(bool b:crossed)require(b,"corpse missed connector");require(playerState->getCurrParts()==repairs,"repairs changed");require(pc_p2_preview_pokos()==(pc_p2_preview_treasure()->isAlive()?14:114),"source treasure accounting");capture("uji-ten-delivered.ppm");std::puts("PASS Uji ten: receipts14 duplicates0 repairs_unchanged cargo100_separate connector_crossings10");std::fflush(stdout);std::_Exit(0);}
 }
 std::fflush(stdout);return true;
}
'''

def instrument(source):
 anchor='class RoomApp : public PlugPikiApp {';call='        if(cargoCarryFixture(n))return result;'
 if source.count(anchor)!=1 or source.count(call)!=1:raise ValueError('Fixture framing changed')
 return source.replace(anchor,HOOK+'\n'+anchor).replace(call,'        if(ujiTenFixture(n))return result;\n'+call)


def validate(log):
 if 'PASS Uji ten: receipts14 duplicates0 repairs_unchanged cargo100_separate connector_crossings10' not in log:raise ValueError('Incomplete acceptance')
 expected={str(i):2 if i<61004 else 1 for i in range(61000,61010)}
 rows=re.findall(r'P2_POD_RECEIPT id=corpse:[^ ]*uji:(\d+) value=([12]) new=1 pokos=\d+ seeds=0',log)
 if len(rows)!=10 or {i:int(v) for i,v in rows}!=expected:raise ValueError('Wrong corpse identities/count/value')
 if set(re.findall(r'P2_UJI_TEN_CROSS generator=(\d+)',log))!=set(expected):raise ValueError('Missing connector observation')
 if set(re.findall(r'P2_UJI_DUPLICATE id=corpse:[^ ]*uji:(\d+) value=[12] duplicate_credit=0',log))!=set(expected):raise ValueError('Missing duplicate checks')
 return dict(corpse_pokos=14,registrations=10,connector_crossings=10,cargo_value=100,proxy_ai='P1')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 recipe=json.loads(a.recipe.read_text());a.output.parent.mkdir(parents=True,exist_ok=True)
 recipe['link']=[('-Wl,--out-implib,'+str((a.output/'libuji.dll.a').resolve())) if x.startswith('-Wl,--out-implib,') else x for x in recipe['link']]
 private_recipe=a.output.parent/(a.output.name+'-recipe.json')
 if private_recipe.exists():raise ValueError('Existing private recipe')
 private_recipe.write_text(json.dumps(recipe,indent=2))
 with patch.object(base,'instrument',instrument):print(base.build(a.native.resolve(),private_recipe,a.output))
