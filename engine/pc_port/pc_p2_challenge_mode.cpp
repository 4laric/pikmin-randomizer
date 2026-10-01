// P2 Challenge host-mode consumer translation unit (#651).
//
// Real module surface: stage select by ui_index over the decoded stage table,
// squad/spray application, mTimeLimit countdown with per-floor extension, and
// the retry/reset boundary. Every entry emits a marker for the guarded fixture
// and for Python observers.
#include "pc_p2_challenge_mode.h"

namespace p2challenge {

int selectByUiIndex(const StageEntry* stages, int count, int uiIndex)
{
    if (!stages || uiIndex < 0) return -1;
    for (int i = 0; i < count; ++i)
        if (stages[i].uiIndex == uiIndex) return i;
    return -1;
}

void applySquadAndSprays(HostState& s, int bitter, int spicy)
{
    s.bitterSprays = bitter;
    s.spicySprays = spicy;
    emit("SQUAD_APPLIED", s);
}

HostState retry(const HostState& previous)
{
    HostState fresh = start(*previous.stage);
    emit("RETRY_RESET", fresh);
    return fresh;
}

} // namespace p2challenge

#include "pc_p2_challenge_mode.h"

#include <cmath>
#include <cstdio>

namespace p2challenge {
namespace wiring {

bool syncTick(HostState& s, const LiveFacts& facts)
{
    if (s.ended) {
        return false;
    }
    if (facts.squad_alive < 0 || facts.squad_reds < 0
        || facts.squad_reds > facts.squad_alive) {
        return false;
    }
    if (!(facts.seconds >= 0.0f) || !std::isfinite(facts.seconds)) {
        return false;
    }
    bindPopulation(s, facts.squad_alive);
    if (facts.captain_down) {
        end(s, "captain_down");
    } else if (facts.squad_alive == 0) {
        end(s, "extinction");
    } else {
        tick(s, facts.seconds);
    }
    std::printf("P2CHALLENGE_WIRING_TICK squad_alive=%d squad_reds=%d "
                "time_left=%.3f floor=%d end=%s\n",
                facts.squad_alive, facts.squad_reds, s.timeLeft,
                s.floorIndex, s.endState ? s.endState : "none");
    std::fflush(stdout);
    return !s.ended;
}

int bindPopulation(HostState& s, int squad_alive)
{
    if (squad_alive < 0) {
        return -1;
    }
    s.population = squad_alive;
    return s.population;
}

}  // namespace wiring
}  // namespace p2challenge
