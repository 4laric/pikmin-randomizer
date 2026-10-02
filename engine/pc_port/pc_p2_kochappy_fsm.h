#pragma once
#include <cmath>
class BTeki;
class PelletView;
class Graphics;
struct Matrix4f;

// Native source FSM for the Dwarf Orange Bulborb (BlueKochappy,
// EnemyID 44), lane 13 gate B + own44 (#871). In bridge-mode campaign sessions
// the audited retail defaults drive the FSM without requiring
// `p2-dwarf-orange-fsm.txt` (an explicit file still overrides); outside bridge
// (room preview) the file stays required so the default-OFF preview path is
// unchanged. The module owns only actors already registered by
// pc_p2_dwarf_orange; every hook is a no-op otherwise. Visuals reuse
// pc_p2_dwarf_orange_draw (the FSM selects the host motion index per source
// state).
void pc_p2_kochappy_fsm_setup();
void pc_p2_kochappy_fsm_reset();
void pc_p2_kochappy_fsm_forget(BTeki*);
void pc_p2_kochappy_fsm_update(BTeki*);
bool pc_p2_kochappy_fsm_suppress_ai(const BTeki*);
bool pc_p2_kochappy_fsm_enabled();
void pc_p2_kochappy_fsm_press(BTeki*);
// Earthquake is a source lifecycle overlay: pause/resume this FSM, never
// transit its actor through an unconsumed P1 strategy state.
bool pc_p2_kochappy_fsm_stun_eligible(const BTeki*);
void pc_p2_kochappy_fsm_begin_stun(BTeki*);
// Values only. Caller must establish current manager ownership before querying;
// no snapshot retains an actor address or mutates the registered FSM.
struct PcKochappyFsmSnapshot {
 bool available=false,attackFired=false,swallowFired=false,flickFired=false,stunPaused=false,terminal=false;
 int state=-1;float stateTime=0;
};
PcKochappyFsmSnapshot pc_p2_kochappy_fsm_observe(const BTeki*);
inline bool pc_kochappy_overlay_preserved(const PcKochappyFsmSnapshot& before,const PcKochappyFsmSnapshot& now) {
 return before.available&&now.available&&before.stunPaused&&now.stunPaused&&!before.terminal&&!now.terminal
  &&std::isfinite(before.stateTime)&&std::isfinite(now.stateTime)&&before.state==now.state&&before.stateTime==now.stateTime
  &&before.attackFired==now.attackFired&&before.swallowFired==now.swallowFired&&before.flickFired==now.flickFired;
}
inline bool pc_kochappy_clock_resumed(const PcKochappyFsmSnapshot& before,const PcKochappyFsmSnapshot& now) {
 return before.available&&now.available&&!now.stunPaused&&!now.terminal
  &&std::isfinite(before.stateTime)&&std::isfinite(now.stateTime)
  &&(before.state!=now.state||now.stateTime>before.stateTime);
}
