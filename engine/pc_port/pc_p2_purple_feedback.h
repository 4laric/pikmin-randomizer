#pragma once

class Piki;

struct PcP2PurpleFeedbackStats {
    unsigned entries = 0;
    unsigned trailBursts = 0;
    unsigned impacts = 0;
    unsigned soundRequests = 0;
    unsigned cameraRequests = 0;
    unsigned rumbleRequests = 0;
};

void pc_p2_purple_feedback_entry(Piki*);
void pc_p2_purple_feedback_update(Piki*, float deltaTime);
void pc_p2_purple_feedback_land(Piki*, bool enemy);
void pc_p2_purple_feedback_cancel(Piki*);
void pc_p2_purple_feedback_reset();
PcP2PurpleFeedbackStats pc_p2_purple_feedback_stats();
