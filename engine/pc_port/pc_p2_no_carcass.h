#pragma once
// P2 species that leave no carcass (#1088): corpse suppression and the
// kill-based randomizer receipt. See pc_p2_no_carcass_policy.h.
class BTeki;

// TPI_CorpseType hook: NoCorpse for a bound no-carcass source, else `value`.
int pc_p2_no_carcass_corpse_type(BTeki* actor, int value);
// Actor-lifetime seam (first thing in pc_p2_forget_teki, before the source
// binding is released): a killed no-carcass actor earns its check here.
void pc_p2_no_carcass_forget(BTeki* actor);
