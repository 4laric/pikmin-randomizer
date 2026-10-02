#pragma once
#include <cstdint>
// Inert fixture observation. A failed history stays failed until explicit begin.
struct PcOnionStartBody { uintptr_t actor=0; unsigned exits=0, formations=0; };
inline bool pc_onion_start_enabled=false, pc_onion_start_failed=false;
inline unsigned pc_onion_start_count=0, pc_onion_start_events=0;
inline uintptr_t pc_onion_start_bad_actor=0;
inline int pc_onion_start_bad_action=-1;
inline PcOnionStartBody pc_onion_start_bodies[20];
inline void pc_onion_start_begin(){
    pc_onion_start_count=pc_onion_start_events=0;pc_onion_start_failed=false;
    pc_onion_start_bad_actor=0;pc_onion_start_bad_action=-1;
    for(auto& body:pc_onion_start_bodies)body={};pc_onion_start_enabled=true;
}
inline void pc_onion_start_fail(uintptr_t actor,int action){
    if(!pc_onion_start_failed){pc_onion_start_bad_actor=actor;pc_onion_start_bad_action=action;}
    pc_onion_start_failed=true;
}
inline void pc_onion_start_note(uintptr_t actor,int action,bool entry){
    if(!pc_onion_start_enabled)return;
    ++pc_onion_start_events;
    PcOnionStartBody* body=nullptr;
    for(unsigned i=0;i<pc_onion_start_count;++i)if(pc_onion_start_bodies[i].actor==actor)body=&pc_onion_start_bodies[i];
    if(!body){
        if(!actor || !entry || action!=18 || pc_onion_start_count==20){pc_onion_start_fail(actor,action);return;}
        body=&pc_onion_start_bodies[pc_onion_start_count++];body->actor=actor;
    }
    // Native GoalItem::exitPiki enters Exit18; natural return enters Crowd14.
    // No work/free/unknown entry or even temporary return to Exit is accepted.
    if(action==18 && !body->formations){if(entry && ++body->exits!=1)pc_onion_start_fail(actor,action);}
    else if(action==14 && body->exits==1){if(entry)++body->formations;else if(!body->formations)pc_onion_start_fail(actor,action);}
    else pc_onion_start_fail(actor,action);
}
inline bool pc_onion_start_complete(){
    if(!pc_onion_start_enabled || pc_onion_start_failed || pc_onion_start_count!=20)return false;
    for(const auto& body:pc_onion_start_bodies)if(!body.actor || body.exits!=1 || !body.formations)return false;
    return true;
}
inline void pc_onion_start_end(){pc_onion_start_enabled=false;}
