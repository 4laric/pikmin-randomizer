#pragma once
// Empress Bulblax (Queen, enemy ID 30) sampled actor (#256, parent #172).
// Actor-local receivers only: P1 gameplay for ordinary actors stays
// authoritative and untouched. Missing/invalid config fails closed (no actor).
class Graphics;
void pc_p2_queen_setup();
void pc_p2_queen_reset();
void pc_p2_queen_update();
void pc_p2_queen_draw(Graphics&);

class Piki;
void pc_p2_queen_forget_piki(Piki*); // Before manager recycling.

// Fixture-only read-only observation getter: true once a Queen has entered Dead
// and released its live larvae, so a host fixture can gate scenario sequencing
// deterministically.
bool pc_p2_queen_death_released();
