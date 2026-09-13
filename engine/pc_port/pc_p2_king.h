#pragma once
// Emperor Bulblax (KingChappy, enemy ID 53) sampled actor (#289, parent #172).
// Actor-local receivers only: P1 gameplay for ordinary actors stays
// authoritative and untouched. Missing/invalid config fails closed (no actor).
class Graphics;
void pc_p2_king_setup();
void pc_p2_king_reset();
void pc_p2_king_update();
void pc_p2_king_draw(Graphics&);
