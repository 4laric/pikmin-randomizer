#pragma once
class Navi;
class NaviState;

// P2 NaviSaraiExit equivalent: end mouth-stick, Fall animation, atari off,
// and Walk on first floor/bounce.  It intentionally has no FallMeck impulse.
NaviState* pc_demon_escape_state_create();
bool pc_demon_escape_begin(Navi*);
bool pc_demon_escape_active(Navi*);
void pc_demon_escape_reset(Navi*);
void pc_demon_escape_scene_exit();
