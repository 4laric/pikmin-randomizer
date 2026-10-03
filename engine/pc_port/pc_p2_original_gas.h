#pragma once
#include "pc_p2_original_group.h"
#include <array>
#include <map>
#include <memory>
#include <set>

namespace p2original { namespace gas {
enum class State { Dead, Wait, Attack };
enum class Event { None, End, Other };
// Every value comes from the source GasHiba parameter resource. No fallback.
struct Parameters {
 float waitTime=0,activeTime=0,attackStartTime=0,stopTime=0;
 float lodNear=0,lodMiddle=0,maxHealth=0,attackDamage=0;
 float attackRadius=0,maxAttackRange=0,maxAttackAngle=0;
};
struct Resources {
 Parameters parameters;
 bool parametersLoaded=false,model=false,collider=false,effects=false; // effects is presentation evidence, not mechanic admission
 std::array<bool,2> clips{};
};
struct Flags {
 bool platformCollision=false,leaveCarcass=false,deathEffect=false;
 bool hardConstraint=true,bitterImmune=true,shadow=false;
 bool untargetable=false,lifeGauge=true,invulnerable=false,damageAnimation=true;
 bool living=false;
};
struct Host {
 Creature* creature=nullptr;Generator* generator=nullptr;
 CatalogRow row;unsigned ordinal=0,token=0;Position position;
 Parameters parameters;State state=State::Wait;Flags flags;
 float timer=0,health=0;
 bool checkLinks=true,deathReported=false,effectActive=false;
 // Transient real item pointers; never serialize them as source identity.
 void* bridge=nullptr;void* gate=nullptr;
};
bool decode(const CatalogRow&,std::string&);
bool nearbyLink(Position pipe,Position item);
bool gasContains(Position pipe,Position target,const Parameters&);
bool damageHeight(Position pipe,Position attacker,const Parameters&);
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool resources(Resources&,std::string&)=0;
 virtual bool commonResources(const CatalogRow&,std::string&)=0;
 virtual bool reserve(unsigned,std::string&)=0;
 // Real manager-owned GasHiba creature; family update/render/interaction hooks.
 // Success with null creature is a retail manager null birth, not an error.
 virtual bool allocate(Host&,const Position&,float facing,std::string&)=0;
 // Source randWeightFloat draws once at init, even when waitTime is zero.
 virtual bool unitDraw(float&,std::string&)=0;
 virtual bool flags(Host&,const Flags&,std::string&)=0;
 virtual bool motion(Host&,unsigned,std::string&)=0;
 virtual bool finishMotion(Host&,std::string&)=0;
 virtual bool gasEffect(Host&,bool active,std::string&)=0;
 virtual bool updateEffectLod(Host&,std::string&)=0;
 // First matching bridge, then gate only if no bridge, within nearbyLink.
 // Only story surface gets item links. Otherwise return both null.
 virtual bool findLivingLinks(Host&,void*& bridge,void*& gate,std::string&)=0;
 virtual bool bridgeStage(void*,int&,std::string&)=0;
 virtual bool gateAlive(void*,bool&,std::string&)=0;
 // Enumerate actual live Piki/Navi candidates; gasContains strict boundaries;
 // stimulate InteractGas with this actor as owner, no captain HP fallback.
 // This runs even when flags.living is false: retail does not gate emission.
 virtual bool gasScan(Host&,std::string&)=0;
 virtual bool attackSound(Host&,std::string&)=0;
 // Inform actual generator once, detach native mGenerator; retain dead pipe.
 // Stop/fatal-hit sound and retail bomb effect (not EnemyBase carcass death).
 virtual bool death(Host&,std::string&)=0;
 virtual bool cleanup(Host&,std::string&)=0;
};
class Provider : public GroupProvider {
public:
 explicit Provider(Engine& e):mEngine(e){}
 bool preflight(const std::vector<CatalogRow>&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,std::string&) override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&) override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&) override;
 bool release(Creature*,unsigned,std::string&) override;
 // Actual manager forget after doKill: no cleanup/kill recursion.
 void retiredNative(Creature*);
 Host* lookup(Creature*);
 bool tick(Creature*,float,Event,std::string&);
 // Return source callback acceptance; invulnerable valid hits return true but
 // do not alter HP. Native adapter must suppress its own stored-damage path.
 // Press/hipdrop/bomb wrappers
 // return true in retail even if this callback rejects null/Navi/height.
 bool damage(Creature*,Creature* attacker,bool isNavi,Position,float,std::string&);
 std::size_t size()const{return mHosts.size();}
private:
 Engine& mEngine;Resources mResources;
 std::map<Creature*,std::unique_ptr<Host>> mHosts;
 std::map<unsigned,CatalogRow> mAdmitted;
 std::map<unsigned,unsigned> mRemaining;
 std::set<std::pair<unsigned,unsigned>> mUsed;
 bool mPrepared=false,mReserved=false;
 bool enter(Host&,State,std::string&);
 bool living(Host&,bool initialize,std::string&);
};
} }
