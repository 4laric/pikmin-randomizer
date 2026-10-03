#pragma once
#include "pc_p2_original_shijimi_group.h"

namespace p2original { namespace shijimi {
// Reachable plant-origin retail states. Rest belongs to enemy-origin groups
// and is deliberately outside the original Sentinel source contract.
enum class Phase : unsigned { Wait=0, Fly=1, Fall=2, Dead=3, Leave=4 };
struct ActorState {
 Identity identity;
 Phase phase=Phase::Wait;
 bool leader=false,stuckToPiki=false,verticalFall=false,running=true;
 unsigned waitTimer=0,flyTimer=0,flyTime=0,fallTimer=0;
 int groupCount=0;
};
// These callbacks are real native actor/animation services. In particular END
// is an authored mechanical animation key, floor is an actual triangle/map
// query, and stuckPiki is the native attachment list. No health proxy exists.
class StateEngine {
public:
 virtual ~StateEngine()=default;
 virtual bool leaderInit(ActorState&,std::string&)=0;
 virtual bool nearestPikmin(const ActorState&)=0;
 virtual bool leaderWaiting(const ActorState&)=0;
 virtual bool nextGoal(ActorState&,std::string&)=0;
 virtual bool fly(ActorState&,std::string&)=0;
 virtual bool fade(ActorState&,std::string&)=0;
 virtual bool fallInit(ActorState&,std::string&)=0;
 virtual bool fall(ActorState&,std::string&)=0;
 virtual bool fallEnd(const ActorState&)=0;
 virtual bool deadInit(ActorState&,std::string&)=0;
 virtual bool deadEndKey(const ActorState&)=0;
 virtual bool drop(ActorState&,std::string&)=0;
 virtual bool leaveInit(ActorState&,std::string&)=0;
 virtual bool leave(ActorState&,std::string&)=0;
 virtual bool stuckPiki(const ActorState&)=0;
 virtual bool latchEffectAndShrink(ActorState&,std::string&)=0;
 virtual bool leaderLeaving(const ActorState&)=0;
 virtual bool outsideTerritory(const ActorState&)=0;
 virtual bool kill(ActorState&,std::string&)=0;
};
// Keep the source doUpdate, doSimulation and animation/culling phases distinct.
// Native callers must not replace attachment/floor/key services with controls.
bool update(ActorState&,StateEngine&,std::string&);
bool simulate(ActorState&,StateEngine&,std::string&);
bool culled(ActorState&,StateEngine&,std::string&);
bool cluster(ActorState&,StateEngine&,std::string&);
} }
