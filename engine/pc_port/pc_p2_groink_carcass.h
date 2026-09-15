#pragma once
#include <array>
#include <cstddef>
#include "pc_p2_groink.h"

struct P2GroinkCarcassConfig {
    float gaugeDelay = 0;
    float recoverySeconds = 1;
    float maxHealth = 1;
};
enum class P2GroinkCarcassCommand { ActivateGauge, KillPellet, RequestBirth, DeactivateGauge };
struct P2GroinkCarcassStep {
    bool valid = false;
    std::array<P2GroinkCarcassCommand,2> commands{};
    std::size_t count = 0;
};
// Host-side payload for the RequestBirth command. Mirrors the EnemyBirthArg
// fields the source populates at revival (MiniHoudai.cpp:307-311): position,
// face direction from the base-matrix Z axis, existence duration and the
// Piklopedia flag. The policy never fills this; the host owns the identity and
// constructs it from the dead object before requesting the replacement birth.
struct P2GroinkCarcassBirth {
    P2GroinkVec3 position{};
    float faceDir = 0.0f;
    float existenceLength = -1.0f;
    bool inPiklopedia = false;
};

// Process-wide RequestBirth tally for host/runtime evidence. It is deliberately
// not owned by any per-actor binding, so erasing a binding on pellet kill /
// forget cannot zero a birth that already fired. Monotonic; never reset.
void p2_groink_carcass_note_birth();
int p2_groink_carcass_total_births();
class P2GroinkCarcass {
public:
    bool become(const P2GroinkCarcassConfig& config);
    void reset();
    P2GroinkCarcassStep step(float delta, bool pelletAlive, bool gaugeManager, bool activeTick=true);
    bool ready() const { return ready_; }
    float timer() const { return timer_; }
    float health() const { return health_; }
private:
    P2GroinkCarcassConfig config_{};
    bool ready_ = false;
    float timer_ = 0, health_ = 0;
};
