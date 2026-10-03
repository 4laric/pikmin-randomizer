#include "pc_p2_original_shijimi_state.h"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace p2original::shijimi;
struct NativeInputs final:StateEngine {
 bool near=false,waiting=true,attached=false,ground=false,end=false,leaving=false,outside=false;
 unsigned flies=0,fades=0,goals=0,kills=0,drops=0,leaves=0,leaderCalls=0;
 std::vector<int> order;
 bool leaderInit(ActorState&,std::string&)override{++leaderCalls;return true;}
 bool nearestPikmin(const ActorState&)override{return near;}
 bool leaderWaiting(const ActorState&)override{return waiting;}
 bool nextGoal(ActorState&,std::string&)override{++goals;return true;}
 bool fly(ActorState&,std::string&)override{++flies;return true;}
 bool fade(ActorState&,std::string&)override{++fades;return true;}
 bool fallInit(ActorState&,std::string&)override{order.push_back(2);return true;}
 bool fall(ActorState&,std::string&)override{return true;}
 bool fallEnd(const ActorState&)override{return ground;}
 bool deadInit(ActorState&,std::string&)override{order.push_back(3);return true;}
 bool deadEndKey(const ActorState&)override{return end;}
 bool drop(ActorState&,std::string&)override{++drops;order.push_back(4);return true;}
 bool leaveInit(ActorState&,std::string&)override{return true;}
 bool leave(ActorState&,std::string&)override{++leaves;return true;}
 bool stuckPiki(const ActorState&)override{return attached;}
 bool latchEffectAndShrink(ActorState&,std::string&)override{order.push_back(1);return true;}
 bool leaderLeaving(const ActorState&)override{return leaving;}
 bool outsideTerritory(const ActorState&)override{return outside;}
 bool kill(ActorState&,std::string&)override{++kills;order.push_back(5);return true;}
};
int main(){
 std::string error;NativeInputs engine;ActorState follower;
 for(unsigned i=0;i<10;++i)assert(update(follower,engine,error)&&follower.phase==Phase::Wait);
 assert(engine.flies==10);assert(update(follower,engine,error)&&follower.phase==Phase::Fly&&engine.goals==1);
 for(unsigned i=0;i<11;++i)assert(update(follower,engine,error));
 assert(follower.flyTime==0&&engine.fades==1);
 engine.waiting=false;
 for(unsigned i=0;i<250;++i)assert(update(follower,engine,error)&&follower.phase==Phase::Fly);
 assert(update(follower,engine,error)&&follower.phase==Phase::Leave);
 for(unsigned i=0;i<1000;++i)assert(update(follower,engine,error));
 assert(follower.running&&engine.kills==0&&engine.leaves==1000);
 engine.leaving=true;assert(culled(follower,engine,error)&&!follower.running&&engine.kills==1&&engine.drops==0);

 NativeInputs contact;ActorState falling;
 assert(simulate(falling,contact,error)&&falling.phase==Phase::Wait);
 contact.attached=true;assert(simulate(falling,contact,error)&&falling.phase==Phase::Fall&&falling.stuckToPiki);
 assert(contact.order==std::vector<int>({1,2}));
 assert(simulate(falling,contact,error)&&contact.order.size()==2);
 contact.ground=true;assert(update(falling,contact,error)&&falling.phase==Phase::Dead&&contact.fades==1);
 for(unsigned i=0;i<100;++i)assert(update(falling,contact,error));
 assert(contact.drops==0&&falling.running);
 contact.end=true;assert(update(falling,contact,error)&&!falling.running);
 assert(contact.order==std::vector<int>({1,2,3,4,5}));
 assert(update(falling,contact,error)&&contact.drops==1&&contact.kills==1);

 NativeInputs timeout;ActorState stalled;stalled.phase=Phase::Fall;
 for(unsigned i=0;i<101;++i)assert(update(stalled,timeout,error)&&stalled.phase==Phase::Fall);
 assert(update(stalled,timeout,error)&&stalled.phase==Phase::Dead&&timeout.fades==0);
 NativeInputs hidden;ActorState leader;leader.leader=true;leader.groupCount=1;
 for(unsigned i=0;i<11;++i)assert(update(leader,hidden,error)&&leader.phase==Phase::Wait);
 assert(hidden.leaderCalls==10&&cluster(leader,hidden,error)&&leader.running);
 hidden.near=true;assert(update(leader,hidden,error)&&leader.phase==Phase::Fly);
 assert(cluster(leader,hidden,error)&&!leader.running&&hidden.kills==1);
 ActorState impossible;impossible.leader=true;hidden.attached=true;
 assert(!simulate(impossible,hidden,error)&&!impossible.stuckToPiki);
 std::puts("P2_ORIGINAL_SHIJIMI_STATE_TEST PASS source-counters actual-input-boundary attachment-only authored-END no-timed-Leave cull-cluster");
}
