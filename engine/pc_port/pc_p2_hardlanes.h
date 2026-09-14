#pragma once
class Graphics;

// Hard-lane shared registration seam (#244 BombSarai, #245 Fuefuki, #246
// BigTreasure). Opt-in: only active inside the Pikipelago private room preview
// with a lane profile present; otherwise every entry point is a no-op and
// ordinary P1 play is untouched.
void pc_p2_hardlanes_setup();
void pc_p2_hardlanes_update();
void pc_p2_hardlanes_draw(Graphics&);
void pc_p2_hardlanes_reset();
