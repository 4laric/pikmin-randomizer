#pragma once
class BTeki;

 // Native source FSM for Miulin (Mamuta, EnemyID 54), own44 (#871). In
// bridge-mode campaign sessions the audited defaults drive the FSM without
// requiring `p2-mamuta-fsm.txt` (an explicit file still overrides); outside
// bridge (room preview) the file stays required so the default proxy preview
// path is unchanged. The module owns only actors already registered by
// pc_p2_mamuta; every hook is a no-op otherwise. Visuals reuse
// pc_p2_mamuta_draw (the FSM selects the host motion index per source state).
void pc_p2_mamuta_fsm_setup();
void pc_p2_mamuta_fsm_reset();
void pc_p2_mamuta_fsm_forget(BTeki*);
void pc_p2_mamuta_fsm_update(BTeki*);
bool pc_p2_mamuta_fsm_suppress_ai(const BTeki*);
bool pc_p2_mamuta_fsm_enabled();
