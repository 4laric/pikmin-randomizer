#pragma once
// TEST-ONLY debug camera for skewered-Pikmin photo evidence (#1020). Env-gated: PIKMIN_P2_SKEWER_CAM=1.
// Never set in the owner package; with the env var unset every call here is a single disabled branch.
//
// While a species keeps a Pikmin held in its mouth it calls pc_p2_skewer_cam_follow(); the game camera is
// then placed beside the held Pikmin, looking at it, and a series of full-resolution probe screenshots
// (PIKMIN_P2_PROXY_SHOT=<dir>) is taken across the hold: <prefix>_h0, h1, ...
class BTeki;

bool pc_p2_skewer_cam_enabled();
// Call every tick for an actor. `yaw` is the actor heading; the camera sits on its right-hand side.
void pc_p2_skewer_cam_follow(BTeki* actor, float yaw, const char* prefix);
// Per-frame pose query from the camera update. Returns true (and fills eye/look) while a followed Pikmin is
// being framed. `focusDist` gets the depth-of-field focus distance.
bool pc_p2_skewer_cam_pose(float eye[3], float look[3], float* focusDist);
