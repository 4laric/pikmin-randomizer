#pragma once

class Piki;

enum class PcP2PurpleFlightPhase { None, Ascent, EntryPause, Descent, Recovery };

struct PcP2PurpleFlightSample {
    PcP2PurpleFlightPhase phase = PcP2PurpleFlightPhase::None;
    float phaseElapsed = 0.0f;
    float motionElapsed = 0.0f;
};

void pc_p2_purple_flight_reset();
void pc_p2_purple_flight_setup();
bool pc_p2_purple_flight_enabled();
void pc_p2_purple_flight_arm(Piki*);
bool pc_p2_purple_flight_update(Piki*, float deltaTime, float gravity);
bool pc_p2_purple_flight_land(Piki*, bool enemyContact);
void pc_p2_purple_flight_contact(Piki*, bool enemyContact);
void pc_p2_purple_flight_cancel(Piki*);
bool pc_p2_purple_flight_active(const Piki*);
PcP2PurpleFlightSample pc_p2_purple_flight_sample(const Piki*);
