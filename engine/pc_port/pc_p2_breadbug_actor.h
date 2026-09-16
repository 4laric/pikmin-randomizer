#pragma once
class BTeki;
class Graphics;
struct Matrix4f;
void pc_p2_breadbug_actor_setup();
void pc_p2_breadbug_actor_reset();
void pc_p2_breadbug_actor_forget(BTeki*);
void pc_p2_breadbug_actor_tick();
bool pc_p2_breadbug_actor_draw(BTeki*,Graphics&,const Matrix4f&);
// Test/debug probes (labelled injected runtime input, not production paths):
// override the observed carrier count for the contest (-1 = natural Stickers).
void pc_p2_breadbug_actor_probe_carriers(int count);
// Revisit: re-arm every active contest (onRevisit + handle release). The durable
// receipt ledger is untouched, so a later steal re-grant is refused (duplicate).
void pc_p2_breadbug_actor_probe_revisit();
