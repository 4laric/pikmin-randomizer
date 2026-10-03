#include "pc_p2_original_wisp.h"
#include <cmath>
#include <sstream>
#include <algorithm>
#include <tuple>

namespace p2original { namespace wisp { namespace {
constexpr float pi=3.14159265358979323846f,tau=2*pi;
bool fail(std::string& e,const char* s){e=s;return false;}
bool number(const std::string& s,float& value){std::istringstream in(s);std::string rest;return bool(in>>value)&&std::isfinite(value)&&!(in>>rest);}
bool same(const CatalogRow& a,const CatalogRow& b){
 const auto& x=a.enemy;const auto& y=b.enemy;
 return std::tie(a.course,a.member,a.sourceKey,a.index,x.source,x.uid,x.birthType,x.count,x.deathCount,x.spawnType,
 x.position.x,x.position.y,x.position.z,x.offset.x,x.offset.y,x.offset.z,x.directionDegrees,x.appearRadius,x.enemySize,
 x.treasureCode,x.pelletColor,x.pelletSize,x.pelletMinimum,x.pelletMaximum,x.pelletProbability,x.generatorVersion,x.generatorTail)
 ==std::tie(b.course,b.member,b.sourceKey,b.index,y.source,y.uid,y.birthType,y.count,y.deathCount,y.spawnType,
 y.position.x,y.position.y,y.position.z,y.offset.x,y.offset.y,y.offset.z,y.directionDegrees,y.appearRadius,y.enemySize,
 y.treasureCode,y.pelletColor,y.pelletSize,y.pelletMinimum,y.pelletMaximum,y.pelletProbability,y.generatorVersion,y.generatorTail);
}
bool finite(const Parameters& p){
 for(float v:{p.flightHeight,p.pitchRate,p.pitchAmplitude,p.deathRate,p.deathTime,p.moveSpeed,p.viewAngle,p.sightRadius,p.health})if(!std::isfinite(v)||v<0)return false;
 return p.health>0;
}
}
bool decode(const CatalogRow& row,Initial& out,std::string& e){
 if(row.enemy.source!=16||row.enemy.generatorVersion!="0000"||row.enemy.generatorTail.size()!=2)return fail(e,"Honeywisp requires literal source16 version0000 fly/slide tail");
 Initial next;
 if(!number(row.enemy.generatorTail[0],next.fly)||!number(row.enemy.generatorTail[1],next.slide))return fail(e,"Honeywisp nonfinite generator fly/slide");
 out=next;e.clear();return true;
}
bool Provider::preflight(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mHosts.empty()||rows.empty())return fail(e,"Honeywisp preparation while actors are owned or empty catalog");
 mPrepared=mReserved=false;mAdmitted.clear();mRemaining.clear();mUsed.clear();
 std::map<unsigned,CatalogRow> next;
 for(const auto& row:rows){if(row.enemy.source!=16)continue;Initial initial;if(!validateOriginalRecord(row.enemy,e)||!decode(row,initial,e))return false;
  if(!next.emplace(row.enemy.uid,row).second)return fail(e,"Honeywisp duplicate original UID");
 }
 Resources resources;
 if(!mEngine.resources(resources,e))return false;
 if(!finite(resources.parameters)||!resources.model||!resources.collider||!resources.waterJoint||!resources.glowJoint||!resources.egg
  ||std::find(resources.motions.begin(),resources.motions.end(),false)!=resources.motions.end())return fail(e,"Honeywisp authored model/collision/capture/motion/Egg resources incomplete");
 mResources=resources;mAdmitted.swap(next);mPrepared=true;e.clear();return true;
}
bool Provider::reserve(const std::vector<CatalogRow>& rows,std::string& e){
 if(!mPrepared||mReserved)return fail(e,"Honeywisp reservation outside exact prepared batch");
 unsigned count=0;std::map<unsigned,unsigned> next;
 for(const auto& row:rows){if(row.enemy.source!=16)continue;auto i=mAdmitted.find(row.enemy.uid);if(i==mAdmitted.end()||!same(i->second,row)||next.count(row.enemy.uid))return fail(e,"Honeywisp reservation changed original rows");
  next[row.enemy.uid]=row.enemy.count;count+=row.enemy.count;
 }
 if(next.size()!=mAdmitted.size())return fail(e,"Honeywisp reservation omitted source rows");
 if(!mEngine.reserve(count,count,e))return false;
 mRemaining.swap(next);mReserved=true;e.clear();return true;
}
bool Provider::birth(const CatalogRow& row,Generator* generator,unsigned ordinal,const Position& p,float facing,Creature*& out,std::string& e){
 out=nullptr;auto i=mRemaining.find(row.enemy.uid);
 if(!mReserved||!generator||i==mRemaining.end()||!i->second||!same(mAdmitted.at(row.enemy.uid),row)||ordinal>=row.enemy.count||!std::isfinite(facing)
  ||!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z))return fail(e,"Honeywisp birth outside reserved original group");
 if(mUsed.count({row.enemy.uid,ordinal}))return fail(e,"Honeywisp duplicate original ordinal");
 auto h=std::make_unique<Host>();h->row=mAdmitted.at(row.enemy.uid);h->generator=generator;h->ordinal=ordinal;h->parameters=mResources.parameters;h->facing=facing;
 if(!decode(h->row,h->initial,e))return false;
 --i->second;mUsed.insert({row.enemy.uid,ordinal});
 bool born=mEngine.allocate(*h,p,facing,e);out=h->creature;
 if(!out)return born; // Source null root birth consumes placement only.
 if(mHosts.count(out))return fail(e,"Honeywisp root pool address still owned");
 Host* host=h.get();mHosts.emplace(out,std::move(h));if(!born)return false;
 // Retail birth attaches an actual Egg before generator initial settings.
 if(!mEngine.attachEgg(*host,host->egg,e))return false;
 host->spawn[0]={p.x,p.y+host->parameters.flightHeight,p.z};
 float flyX=host->initial.fly*std::sin(facing),flyZ=host->initial.fly*std::cos(facing);
 float slideX=host->initial.slide*std::sin(facing-pi/2),slideZ=host->initial.slide*std::cos(facing-pi/2);
 host->spawn[1]={slideX+(host->spawn[0].x+flyX),host->spawn[0].y,slideZ+(host->spawn[0].z+flyZ)};
 return enter(*host,State::Stay,e);
}
bool Provider::bind(const CatalogRow& row,Creature* actor,unsigned token,std::string& e){
 auto* h=lookup(actor);if(!h||h->token||!token||!same(row,h->row))return fail(e,"Honeywisp original token binding mismatch");
 for(const auto& entry:mHosts)if(entry.second->token==token)return fail(e,"Honeywisp original token already live");
 h->token=token;e.clear();return true;
}
Host* Provider::lookup(Creature* actor){auto i=mHosts.find(actor);return i==mHosts.end()?nullptr:i->second.get();}
void Provider::retiredNative(Creature* actor){mHosts.erase(actor);}
bool Provider::release(Creature* actor,unsigned token,std::string& e){
 auto i=mHosts.find(actor);if(i==mHosts.end())return fail(e,"Honeywisp release outside owned source");
 if(i->second->token!=token)return fail(e,"Honeywisp release token mismatch");
 if(!mEngine.cleanup(*i->second,e))return false;
 mHosts.erase(i);e.clear();return true;
}
bool Provider::enter(Host& h,State next,std::string& e){
 h.state=next;
 switch(next){
 case State::Stay:h.timer=0;h.scale=0;return mEngine.facing(h,h.facing,e)&&mEngine.setPosition(h,h.spawn[h.spawnIndex],e)&&mEngine.flags(h,false,true,true,true,e)&&mEngine.velocity(h,{0,0,0},e)&&mEngine.motion(h,3,true,e);
 case State::Appear:return mEngine.flags(h,false,false,true,true,e)&&mEngine.velocity(h,{0,0,0},e)&&mEngine.motion(h,3,false,e)&&mEngine.effect(h,"appear",e)&&mEngine.effect(h,"glow-start",e);
 case State::Disappear:return mEngine.flags(h,false,false,true,true,e)&&mEngine.velocity(h,{0,0,0},e)&&mEngine.motion(h,4,false,e)&&mEngine.effect(h,"disappear",e);
 case State::Move:return mEngine.velocity(h,{0,0,0},e)&&mEngine.motion(h,0,false,e);
 case State::Drop:return mEngine.flags(h,true,false,false,true,e)&&mEngine.effect(h,"hit",e)&&mEngine.velocity(h,{0,0,0},e)&&mEngine.motion(h,1,false,e);
 case State::Dead:h.timer=0;h.dead=true;return mEngine.flags(h,true,false,false,false,e)&&mEngine.velocity(h,{0,h.parameters.deathRate,0},e)&&mEngine.motion(h,2,false,e);
 }
 return false;
}
bool Provider::flyingCollision(Creature* actor,bool pikmin,std::string& e){auto* h=lookup(actor);if(!h)return fail(e,"Honeywisp collision outside owned source");if(pikmin&&h->state==State::Move)return enter(*h,State::Drop,e);e.clear();return true;}
bool Provider::tick(Creature* actor,float dt,Event event,std::string& e){
 auto* h=lookup(actor);if(!h||!h->token||!std::isfinite(dt)||dt<0)return fail(e,"Honeywisp invalid owned tick");
 switch(h->state){
 case State::Stay:{h->timer+=dt;bool appear=false;if(h->timer>1&&(!mEngine.appear(*h,appear,e)|| (appear&&!enter(*h,State::Appear,e))))return false;break;}
 case State::Appear:h->scale=std::min(1.0f,float(double(h->scale)+0.05));if(!mEngine.effect(*h,"glow-scale",e))return false;
  if(event==Event::End){h->scale=1;if(!mEngine.flags(*h,true,false,true,true,e)||!mEngine.effect(*h,"glow-scale",e)||!enter(*h,State::Move,e))return false;}break;
 case State::Disappear:h->scale=std::max(0.0f,float(double(h->scale)-0.05));if(!mEngine.effect(*h,"glow-scale",e))return false;
  if(event==Event::End){h->facing+=pi;if(h->facing>=tau)h->facing-=tau;h->spawnIndex^=1;if(!mEngine.flags(*h,true,false,true,true,e)||!mEngine.effect(*h,"glow-finish",e)||!enter(*h,State::Stay,e))return false;}break;
 case State::Move:{Position p;float floor=0;if(!mEngine.position(*h,p,e)||!mEngine.floor(p,floor,e))return false;
  h->pitch+=h->parameters.pitchRate*dt;if(h->pitch>tau)h->pitch-=tau;
  Position v{std::sin(h->facing)*h->parameters.moveSpeed,2.5f*((floor+(h->parameters.pitchAmplitude*std::sin(h->pitch)+h->parameters.flightHeight))-p.y),std::cos(h->facing)*h->parameters.moveSpeed};
  if(!mEngine.velocity(*h,v,e))return false;
  const auto& spawn=h->spawn[h->spawnIndex];float dx=spawn.x-p.x,dz=spawn.z-p.z;
  if(dx*dx+dz*dz>h->initial.fly*h->initial.fly&&!enter(*h,State::Disappear,e))return false;
  break;}
 case State::Drop:if(event==Event::ReleaseEgg&&!h->released){if(h->egg&&!mEngine.releaseEgg(*h,h->egg,e))return false;h->egg=nullptr;h->released=true;}
  if(event==Event::End&&!enter(*h,State::Dead,e))return false;
  break;
 case State::Dead:{h->timer+=dt;bool visible=false;if(!mEngine.visible(*h,visible,e))return false;
  if(!visible||h->timer>h->parameters.deathTime){if(!mEngine.effect(*h,"glow-finish",e)||!mEngine.kill(*h,e))return false;return true;}break;}
 }
 e.clear();return true;
}
} }
