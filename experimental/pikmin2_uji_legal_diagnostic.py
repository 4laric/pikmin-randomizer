"""Private legal-interaction Uji death diagnostic; no production modifications."""
import argparse,json
from pathlib import Path
from unittest.mock import patch
from experimental import pikmin2_uji_fixture as base
HOOK=r'''
#include "pc_p2_sheargrub.h"
static bool ujiLegalFixture(Navi* n){
 static int ticks=0;static Teki* targets[2]={};static bool hit[2]={},corpse[2]={};
 require(++ticks<3000,"legal Uji diagnostic timeout");
 if(ticks==1){
  Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);unsigned id;int value;if(pc_p2_sheargrub_receipt(t,id,value)){if(id==61000)targets[0]=t;if(id==61004)targets[1]=t;}}
  require(targets[0]&&targets[1],"diagnostic targets missing");
  for(int i=0;i<2;++i){auto* t=targets[i];float health=t->mHealth;require(t->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE),"expected buried invincible target");bool accepted=t->stimulate(InteractAttack(n,nullptr,10000,false));require(!accepted&&t->mHealth==health&&t->mStoredDamage==0,"buried attack should reject");std::printf("P2_UJI_LEGAL buried_rejected species=%s state=%d\n",pc_p2_sheargrub_name(t),t->mStateID);}
  walkGoals.clear();for(float x:{200.f,425.f,595.f,820.f,1020.f})walkGoals.push_back(Vector3f(x,0,0));walkGoals.push_back(Vector3f(1055,0,-170));walkPoint=0;phase=1;n->mKontroller=new FixtureController();
 }
 for(int i=0;i<2;++i){auto* t=targets[i];if(!hit[i]&&!t->getTekiOption(BTeki::TEKI_OPTION_INVINCIBLE)){
  require(t->stimulate(InteractAttack(n,nullptr,10000,false)),"vulnerable attack rejected");hit[i]=true;std::printf("P2_UJI_LEGAL accepted species=%s state=%d health=%.2f stored=%.2f\n",pc_p2_sheargrub_name(t),t->mStateID,t->mHealth,t->mStoredDamage);
 }}
 Iterator p(pelletMgr);CI_LOOP(p){Pellet* body=static_cast<Pellet*>(*p);for(int i=0;i<2;++i)if(body->isAlive()&&body->mPelletView==static_cast<PelletView*>(targets[i]))corpse[i]=true;}
 if(ticks%300==0)std::printf("P2_UJI_LEGAL_PROGRESS navi=%.1f,%.1f hit=%d,%d corpse=%d,%d states=%d,%d\n",n->mSRT.t.x,n->mSRT.t.z,int(hit[0]),int(hit[1]),int(corpse[0]),int(corpse[1]),targets[0]->mStateID,targets[1]->mStateID);
 if(hit[0]&&hit[1]&&corpse[0]&&corpse[1]){capture("uji-legal-corpses.ppm");std::puts("PASS Uji legal: buried attacks rejected, normal emergence, accepted lethal interactions, native corpses2; no health/state/position writes");std::fflush(stdout);std::_Exit(0);}
 std::fflush(stdout);return true;
}
'''
def instrument(source):
 anchor='class RoomApp : public PlugPikiApp {';call='        if(cargoCarryFixture(n))return result;'
 if source.count(anchor)!=1 or source.count(call)!=1:raise ValueError('Fixture framing changed')
 return source.replace(anchor,HOOK+'\n'+anchor).replace(call,'        if(ujiLegalFixture(n))return result;\n'+call)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();recipe=json.loads(a.recipe.read_text());a.output.parent.mkdir(parents=True,exist_ok=True)
 recipe['link']=[('-Wl,--out-implib,'+str((a.output/'libuji.dll.a').resolve())) if x.startswith('-Wl,--out-implib,') else x for x in recipe['link']]
 path=a.output.parent/(a.output.name+'-recipe.json')
 if path.exists():raise ValueError('Existing recipe')
 path.write_text(json.dumps(recipe,indent=2))
 with patch.object(base,'instrument',instrument):print(base.build(a.native.resolve(),path,a.output))
