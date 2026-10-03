#include "pc_p2_original_pelplant.h"
#include <cmath>
#include <set>

namespace p2original { namespace pelplant {
namespace {
bool refuse(std::string& e,const char* s){e=s;return false;}
bool byte(const std::string& s,unsigned& out){
 if(s.empty()||s.size()>3)return false;
 unsigned n=0;for(char c:s){if(c<'0'||c>'9')return false;n=n*10+unsigned(c-'0');}
 if(n>255)return false;out=n;return true;
}
int amountIndex(unsigned n){switch(n){case 1:return 0;case 5:return 1;case 10:return 2;case 20:return 3;default:return -1;}}
float lod(unsigned n){const float radii[]={45,60,103,133};return radii[amountIndex(n)];}
bool wait(State s){return s==State::Small||s==State::Middle||s==State::Full;}
bool sameRow(const CatalogRow& a,const CatalogRow& b){
 const auto& x=a.enemy;const auto& y=b.enemy;
 return a.course==b.course&&a.member==b.member&&a.index==b.index&&a.sourceKey==b.sourceKey
 &&x.source==y.source&&x.uid==y.uid&&x.birthType==y.birthType&&x.count==y.count&&x.deathCount==y.deathCount&&x.spawnType==y.spawnType
 &&x.position.x==y.position.x&&x.position.y==y.position.y&&x.position.z==y.position.z
 &&x.offset.x==y.offset.x&&x.offset.y==y.offset.y&&x.offset.z==y.offset.z
 &&x.directionDegrees==y.directionDegrees&&x.appearRadius==y.appearRadius&&x.enemySize==y.enemySize
 &&x.treasureCode==y.treasureCode&&x.pelletColor==y.pelletColor&&x.pelletSize==y.pelletSize
 &&x.pelletMinimum==y.pelletMinimum&&x.pelletMaximum==y.pelletMaximum&&x.pelletProbability==y.pelletProbability
 &&x.generatorVersion==y.generatorVersion&&x.generatorTail==y.generatorTail;
}
bool valid(const Parameters& p){return std::isfinite(p.smallToMiddle)&&p.smallToMiddle>=0
 &&std::isfinite(p.middleToFull)&&p.middleToFull>=0&&std::isfinite(p.colorPeriod)&&p.colorPeriod>=0
 &&std::isfinite(p.maxHealth)&&p.maxHealth>0;}
}
bool decode(const CatalogRow& row,Initial& out,std::string& e){
 if(row.enemy.source!=0)return refuse(e,"Pelplant source must be literal zero");
 if(!validateOriginalRecord(row.enemy,e))return false;
 Initial next;const auto& tail=row.enemy.generatorTail;
 if(row.enemy.generatorVersion=="0001"){
  if(tail.size()!=3||!byte(tail[0],next.color)||!byte(tail[1],next.amount)||!byte(tail[2],next.stage))return refuse(e,"Pelplant 0001 requires exactly three bytes");
 }else if(row.enemy.generatorVersion=="0000"){
  if(tail.size()!=2||!byte(tail[0],next.color)||!byte(tail[1],next.stage))return refuse(e,"Pelplant 0000 requires color and state bytes");
 }else return refuse(e,"unsupported Pelplant generator version");
 if(next.color>3||amountIndex(next.amount)<0||next.stage>2)return refuse(e,"invalid Pelplant color, literal amount or growth stage");
 out=next;e.clear();return true;
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty())return refuse(e,"cannot replace resources with live Pelplants");
 mPrepared=false;mReserved=false;mAdmitted.clear();mRemaining.clear();
 Resources resources;if(!mEngine.resources(resources,e))return false;
 if(!resources.model||!resources.root||!resources.head||!resources.neck||!resources.collider||!valid(resources.parameters))return refuse(e,"Pelplant physical rig, collider or parameters unresolved");
 for(bool clip:resources.clips)if(!clip)return refuse(e,"Pelplant authored animation unresolved");
 std::map<unsigned,CatalogRow> admitted;
 for(const auto& row:rows){if(row.enemy.source!=0)continue;Initial init;if(!decode(row,init,e))return false;
  if(!mEngine.commonResources(row,e))return false;
  if(!admitted.emplace(row.enemy.uid,row).second)return refuse(e,"duplicate original Pelplant generator");
  for(unsigned c=0;c<3;++c)if(!resources.numberConfigs[amountIndex(init.amount)][c])return refuse(e,"configured Pelplant number/color pellet resource unresolved");
 }
 mResources=resources;mAdmitted=std::move(admitted);mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved||!mHosts.empty())return refuse(e,"Pelplant reservation requires fresh preflight");
 std::array<unsigned,4> pellets{};unsigned actors=0;std::set<unsigned> seen;std::map<unsigned,unsigned> remaining;
 for(const auto& row:rows){if(row.enemy.source!=0)continue;auto found=mAdmitted.find(row.enemy.uid);Initial init;
  if(found==mAdmitted.end()||!seen.insert(row.enemy.uid).second||!decode(row,init,e))return refuse(e,"Pelplant reservation catalog differs from preflight");
  const auto& expected=found->second;
  if(!sameRow(expected,row))return refuse(e,"Pelplant reservation row changed after preflight");
  unsigned n=row.enemy.count-row.enemy.deathCount;actors+=n;pellets[amountIndex(init.amount)]+=n;remaining[row.enemy.uid]=n;
 }
 if(seen.size()!=mAdmitted.size())return refuse(e,"Pelplant reservation omitted an admitted row");
 if(!mEngine.reserve(actors,pellets,e))return false;
 mRemaining=std::move(remaining);mReserved=true;e.clear();return true;
}
bool Provider::attach(Host& h,std::string& e){
 if(h.captured)return true;
 Pellet* pellet=nullptr;
 if(!mEngine.captureNumber(h,h.initial.amount,h.initial.color<3?int(h.initial.color):1,pellet,e))return false;
 if(!pellet)return refuse(e,"Pelplant capture returned no owned pellet");
 h.captured=pellet;h.actualColor=h.initial.color<3?int(h.initial.color):1;return true;
}
bool Provider::enter(Host& h,State next,std::string& e){
 const State previous=h.state;unsigned animation=0;bool blend=false;
 switch(next){
 case State::Small:animation=4;break;
 case State::Middle:animation=5;break;
 case State::Full:animation=6;break;
 case State::GrowSmallMiddle:animation=2;break;
 case State::GrowMiddleFull:animation=h.initial.amount>=10?7:3;if(!attach(h,e))return false;break;
 case State::Damage:animation=0;h.previous=previous;break;
 case State::Dead:animation=h.initial.amount>=10?9:1;if(!mEngine.deathProcedure(h,e))return false;break;
 case State::WitherFull:animation=6;blend=true;break;
 case State::WitherMiddle:animation=5;blend=true;break;
 case State::WitherSmall:animation=4;blend=true;break;
 }
 // Wait init changes EB_Cullable; damage/death/wither retain it. Grow init
 // enlarges the LOD sphere, while wither cleanup resets it at WaitSmall.
 bool cullable=h.cullable;float radius=h.lodRadius;
 if(wait(next))cullable=next==State::Full;
 if(next==State::Full||next==State::GrowMiddleFull)radius=lod(h.initial.amount);
 if(next==State::Small&&(previous==State::WitherFull||previous==State::WitherMiddle||previous==State::WitherSmall))radius=45;
 if(!mEngine.flags(h,next==State::Full||next==State::Damage,next==State::Full||next==State::Damage,cullable,radius,e))return false;
 h.cullable=cullable;h.lodRadius=radius;
 if(blend&&!mEngine.flick(h,e))return false;
 if(!mEngine.motion(h,animation,blend,e))return false;
 h.state=next;return true;
}
bool Provider::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;auto admitted=mAdmitted.find(row.enemy.uid);auto remaining=mRemaining.find(row.enemy.uid);Initial init;
 if(!mReserved||admitted==mAdmitted.end()||remaining==mRemaining.end()||!remaining->second||!generator||!decode(row,init,e))return refuse(e,"Pelplant birth lacks original reservation");
 if(!sameRow(admitted->second,row))return refuse(e,"Pelplant birth differs from admitted row");
 if(ordinal>=row.enemy.count||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(facing))return refuse(e,"invalid Pelplant birth position, facing or ordinal");
 for(const auto& entry:mHosts)if(entry.second->generator==generator&&entry.second->ordinal==ordinal)return refuse(e,"duplicate Pelplant birth ordinal");
 auto host=std::make_unique<Host>();host->row=row;host->generator=generator;host->ordinal=ordinal;host->initial=init;
 host->parameters=mResources.parameters;host->health=host->parameters.maxHealth;
 if(!mEngine.allocate(*host,p,facing,e)){
  if(host->creature){Creature* actor=host->creature;if(!mEngine.cleanup(*host,e)){mHosts.emplace(actor,std::move(host));out=actor;}}
  return false;
 }
 if(!host->creature)return refuse(e,"Pelplant allocation produced no canonical creature");
 Creature* actor=host->creature;
 // Keep ownership before init so any failure remains recoverable by release(0).
 if(mHosts.count(actor)){mEngine.cleanup(*host,e);return refuse(e,"Pelplant allocator reused a live creature");}
 Host& h=*host;mHosts.emplace(actor,std::move(host));
 State state=init.stage==0?State::Small:init.stage==1?State::Middle:State::Full;
 if((state==State::Full&&!attach(h,e))||!enter(h,state,e)){
  std::string cleanupError;if(release(actor,0,cleanupError))return false;
  out=actor;e+="; retained pending cleanup: "+cleanupError;return false;
 }
 --remaining->second;out=actor;e.clear();return true;
}
Host* Provider::lookup(Creature* actor){auto it=mHosts.find(actor);return it==mHosts.end()?nullptr:it->second.get();}
bool Provider::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 Host* h=lookup(actor);if(!h||h->token||!token||!sameRow(h->row,row))return refuse(e,"Pelplant original registry binding mismatch");
 for(const auto& entry:mHosts)if(entry.second->token==token)return refuse(e,"Pelplant registry token already live");
 std::string durable;
 h->token=token; // Registry already owns this token, including failed init cleanup.
 if(!mEngine.identity(*h,durable,e)||durable.empty())return refuse(e,"Pelplant original durable identity unresolved");
 h->durableIdentity=std::move(durable);h->token=token;e.clear();return true;
}
bool Provider::release(Creature* actor,unsigned token,std::string& e){
 Host* h=lookup(actor);if(!h||h->token!=token)return refuse(e,"Pelplant release token mismatch");
 if(!mEngine.cleanup(*h,e))return false;
 mHosts.erase(actor);e.clear();return true;
}
bool Provider::color(Host& h,float dt,std::string& e){
 if(!h.captured||h.initial.color!=3)return true;
 if(h.colorTime>h.parameters.colorPeriod){
  unsigned next=unsigned(h.actualColor)+1;
  // Preserve retail's hasMet(3) query before wrapping, including Purple.
  unsigned cap=next;unsigned attempts=0;
  while(!mEngine.metColor(next)){
   if(++next>2)next=0;
   if(next==cap)next=1;
   if(++attempts>8)return refuse(e,"Pelplant color cycle has no eligible met Pikmin");
  }
  if(next>2)next=0;
  const int actual=mEngine.metColor(next)?int(next):1;
  if(!mEngine.pelletColor(h.captured,actual,e))return false;
  h.actualColor=actual;h.colorTime=0;
 }else if(h.growing)h.colorTime+=dt;
 return true;
}
bool Provider::tick(Creature* actor,float dt,Event event,std::string& e){
 Host* h=lookup(actor);if(!h||!h->token||!std::isfinite(dt)||dt<0)return refuse(e,"invalid Pelplant tick or unbound original actor");
 if(h->dead)return true;
 if(wait(h->state)){
  if(h->growing)h->growthTime+=dt;
  if(event==Event::End||event==Event::LoopEnd){
   float limit=h->state==State::Small?h->parameters.smallToMiddle:h->parameters.middleToFull;
   if(h->growthTime>limit||h->farmPower>0){h->growthTime=0;
    if(h->state==State::Small)return enter(*h,State::GrowSmallMiddle,e);
    if(h->state==State::Middle)return enter(*h,State::GrowMiddleFull,e);
   }else if(h->farmPower<0){
    if(h->state==State::Middle)return enter(*h,State::WitherMiddle,e);
    if(h->state==State::Full)return enter(*h,State::WitherFull,e);
   }
  }else if(event==Event::None){
   if(!color(*h,dt,e))return false;
   if(h->damage>0&&h->state==State::Full){h->health-=h->damage;h->damage=0;return enter(*h,h->health<=0?State::Dead:State::Damage,e);}
  }
 }else if(h->state==State::GrowSmallMiddle||h->state==State::GrowMiddleFull){
  if(event==Event::End||event==Event::LoopEnd)return enter(*h,h->state==State::GrowSmallMiddle?State::Middle:State::Full,e);
 }else if(h->state==State::Damage){
  if(event==Event::End&&!enter(*h,h->previous,e))return false;
  if(!color(*h,dt,e))return false;
 }else if(h->state==State::Dead&&event==Event::End){
  if(h->captured){Pellet* pellet=h->captured;
   if(mCargo.count(pellet))return refuse(e,"Pelplant released cargo address still has an original identity");
   if(!mEngine.endCapture(*h,pellet,e))return false;
   mCargo.emplace(pellet,Cargo{h->token,false,h->durableIdentity});h->captured=nullptr;h->released=true;}
  if(!mEngine.killPlant(*h,e))return false;h->dead=true;
 }else if((h->state==State::WitherFull||h->state==State::WitherMiddle||h->state==State::WitherSmall)&&event==Event::EndBlend)return enter(*h,State::Small,e);
 e.clear();return true;
}
bool Provider::damage(Creature* actor,float amount,const char special[4],std::string& e){
 Host* h=lookup(actor);if(!h||!std::isfinite(amount)||amount<0)return refuse(e,"invalid Pelplant damage callback");
 if(h->state==State::Full||h->state==State::Damage){h->damage+=amount;if(special&&special[3]=='0')h->damage+=h->parameters.maxHealth;}
 e.clear();return true;
}
bool Provider::stick(Creature* actor,const char special[4],std::string& e){return damage(actor,0,special,e);}
bool Provider::farm(Creature* actor,int power,std::string& e){Host* h=lookup(actor);if(!h)return refuse(e,"unknown Pelplant farm callback");h->farmPower=power;h->growing=power>=0;e.clear();return true;}
bool Provider::onion(Pellet* pellet,unsigned& token,bool& duplicate,std::string* identity){auto it=mCargo.find(pellet);if(it==mCargo.end())return false;token=it->second.token;duplicate=it->second.delivered;if(identity)*identity=it->second.identity;it->second.delivered=true;return true;}
void Provider::forgetPellet(Pellet* pellet){mCargo.erase(pellet);for(auto& entry:mHosts)if(entry.second->captured==pellet)entry.second->captured=nullptr;}
} }
