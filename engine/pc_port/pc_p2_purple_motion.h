#pragma once

class Graphics;
class Piki;

enum class PcP2PurpleMotionClip { RollJump, Fall };

void pc_p2_purple_motion_setup();
bool pc_p2_purple_motion_enabled();
bool pc_p2_draw_purple_motion(Piki*, Graphics&, PcP2PurpleMotionClip, float motionElapsed);
