#pragma once
#include <cstdint>
// Test observation only: copied values, no game pointers or mutation API escape.
struct PcTransportObservation {
    uintptr_t actor=0, target=0; bool member=false, alive=false, pellet=false;
    bool visible=false, atGoal=true;
    unsigned generator=0; int state=-1; float x=0,y=0,z=0;
    bool valid() const { return actor && target && member && alive && pellet; }
};
struct PcWorkerRecallEvent {
    unsigned episode=0; uintptr_t actor=0; int captain=-1, mode=-1, action=-1, state=-1, afterMode=-1, afterState=-1;
    PcTransportObservation target;
    bool held=false, recall=false, vs=false, alive=false, callable=false, buried=false, kinoko=false, fired=false, damaged=false, rope=false;
    bool instant=false; float heldSeconds=0,radius=0,distance=0,x=0,y=0,z=0,cursorX=0,cursorY=0,cursorZ=0;
    bool eligible() const {
        return actor && target.valid() && target.actor==actor && captain==0 && mode==9 && action==21 && state==0
            && held && recall && heldSeconds>=0.6f && radius>0 && distance>=0 && distance<radius
            && !vs && alive && callable && !buried && !kinoko && !fired && !damaged && !rope;
    }
    bool nativeResult() const { return instant ? afterMode==1 && afterState==0 : afterState==26; }
};
inline bool pc_worker_observer_enabled=false;
inline unsigned pc_worker_observer_count=0;
inline bool pc_worker_observer_overflow=false;
inline PcWorkerRecallEvent pc_worker_observer_events[64];

struct PcWorkerEpisode {
    unsigned id=0; uintptr_t actor=0, action=0; PcTransportObservation target;
    int reason=0; bool active=false;
};
struct PcWorkerTerminal {
    unsigned episode=0; uintptr_t actor=0, action=0; PcTransportObservation before, after;
    int reason=0, result=-1, captain=-1, mode=-1, state=-1;
    bool joined=false;
    bool eligible() const {
        return episode && actor && action && before.actor==actor && after.actor==actor
            && before.valid() && after.valid() && before.target==after.target
            && before.visible && after.visible && !before.atGoal && !after.atGoal
            && reason>=1 && reason<=4 && result==1 && joined && captain==0 && mode==1;
    }
};
inline PcWorkerEpisode pc_worker_episodes[64];
inline unsigned pc_worker_episode_count=0;
inline PcWorkerTerminal pc_worker_terminals[64];
inline unsigned pc_worker_terminal_count=0;
inline PcWorkerEpisode* pc_worker_current(uintptr_t actor) {
    for(unsigned i=pc_worker_episode_count;i>0;--i)if(pc_worker_episodes[i-1].actor==actor && pc_worker_episodes[i-1].active)return &pc_worker_episodes[i-1];
    return nullptr;
}
inline unsigned pc_worker_task_begin(uintptr_t action,const PcTransportObservation& target) {
    if(!pc_worker_observer_enabled)return 0;
    if(pc_worker_current(target.actor) || pc_worker_episode_count==64){pc_worker_observer_overflow=true;return 0;}
    auto& e=pc_worker_episodes[pc_worker_episode_count++];e={};e.id=pc_worker_episode_count;e.actor=target.actor;e.action=action;e.target=target;e.active=true;return e.id;
}
inline unsigned pc_worker_task_ensure(uintptr_t action,const PcTransportObservation& target) {
    if(!pc_worker_observer_enabled)return 0;
    auto* e=pc_worker_current(target.actor);
    if(!e)return pc_worker_task_begin(action,target); // Existing task when observation was enabled.
    if(e->action!=action || e->target.target!=target.target){pc_worker_observer_overflow=true;return 0;}
    return e->id;
}
inline void pc_worker_task_end(uintptr_t actor) {
    if(pc_worker_observer_enabled)if(auto* e=pc_worker_current(actor))e->active=false;
}
inline void pc_worker_slot_failure(uintptr_t actor,int reason) {
    if(pc_worker_observer_enabled){auto* e=pc_worker_current(actor);if(!e){pc_worker_observer_overflow=true;return;}e->reason=reason;}
}
inline void pc_worker_terminal_record(const PcWorkerTerminal& e) {
    if(!pc_worker_observer_enabled || !e.episode)return;
    if(pc_worker_terminal_count==64){pc_worker_observer_overflow=true;return;}
    pc_worker_terminals[pc_worker_terminal_count++]=e;
}
inline void pc_worker_observer_begin() { pc_worker_observer_count=0;pc_worker_episode_count=0;pc_worker_terminal_count=0;pc_worker_observer_overflow=false;pc_worker_observer_enabled=true; }
inline void pc_worker_observer_end() { pc_worker_observer_enabled=false; }
inline void pc_worker_observer_record(const PcWorkerRecallEvent& event) {
    if(!pc_worker_observer_enabled || !event.actor)return;
    if(pc_worker_observer_count==64){pc_worker_observer_overflow=true;return;}
    if(!event.episode || event.episode>pc_worker_episode_count){pc_worker_observer_overflow=true;return;}
    const auto& episode=pc_worker_episodes[event.episode-1];
    if(episode.actor!=event.actor || episode.target.target!=event.target.target){pc_worker_observer_overflow=true;return;}
    pc_worker_observer_events[pc_worker_observer_count++]=event;
}
