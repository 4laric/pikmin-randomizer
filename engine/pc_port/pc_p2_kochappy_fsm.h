#pragma once
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
