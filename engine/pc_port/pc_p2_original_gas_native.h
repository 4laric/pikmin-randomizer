#pragma once
#include "pc_p2_original_gas.h"
#include <functional>
class BTeki;
class Graphics;
struct Matrix4f;
namespace p2original { namespace gas {
// Actual source item mechanics are mandatory. Presentation may be explicitly
// deferred without changing gas/attack/death behavior; no proxy particles/audio.
class Services {
public:
 virtual ~Services()=default;
 virtual bool linksReady(std::string&)=0;
 virtual bool sourceEffectsAndSoundsReady()const{return false;}
 virtual bool gasEffect(Creature*,bool,bool,std::string&){return true;}
 virtual bool effectLod(Creature*,float,float,std::string&){return true;}
 virtual bool sourceSound(Creature*,const char*,std::string&){return true;}
 virtual bool sourceFatalEffect(Creature*,std::string&){return true;}
 virtual bool surfaceStory()const=0;
 virtual bool livingLinks(Position,void*&,void*&,std::string&)=0;
 virtual bool bridgeStage(void*,int&,std::string&)=0;
 virtual bool gateAlive(void*,bool&,std::string&)=0;
 virtual bool linkIdentity(void*,std::string&,bool&)const=0;
 virtual bool resolveLink(const std::string&,bool isBridge,void*&,std::string&)=0;
};
struct Snapshot {
 InstanceIdentity identity;
 State state=State::Wait;
 Position position;float facing=0,health=0,timer=0,sourceFrame=0;
 unsigned motion=0;bool finishMotion=false,checkLinks=true,living=false;
 bool generatorDeathCommitted=false;
 std::string bridge,gate;
};
class Native {
public:
 explicit Native(Services&);
 ~Native();
 Native(const Native&)=delete; Native& operator=(const Native&)=delete;
 Provider& provider();
 bool owns(const Creature*)const;
 bool tick(BTeki*,float,std::string&);
 bool draw(BTeki*,Graphics&,const Matrix4f&,std::string&);
 bool snapshot(BTeki*,Snapshot&,std::string&)const;
 // Applies only to an actual source-owned body bound to the EXACT saved
 // incarnation by the typed checkpoint loader. Logical dead/count state must
 // already be restored by GroupCourse; this never informs a second death.
 bool restore(BTeki*,const Snapshot&,std::string&);
 // Optional observation AFTER actual Generator::informDeath and detach.
 // Must not record a second GroupCourse death.
 void onDeath(std::function<bool(Creature*,std::string&)>);
 void forget(BTeki*);
private:
 struct Impl; std::unique_ptr<Impl> m;
};
} }
bool pc_p2_original_gas_update(BTeki*);
bool pc_p2_original_gas_refresh(BTeki*,Graphics&);
// owned is independent of accepted: suppress host fallback even on rejection.
bool pc_p2_original_gas_damage(BTeki*,Creature* attacker,float damage,bool& accepted);
void pc_p2_original_gas_forget(BTeki*);
