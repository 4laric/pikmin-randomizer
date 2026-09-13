#include "pc_p2_purple_impact.h"
#include "pc_p2_purple_impact_policy.h"
#include "pc_p2_kochappy_stun.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_purple.h"
#include "Piki.h"
#include "teki.h"
#include "system.h"

#include <cstdio>
#include <set>

namespace {
p2purpleimpact::Sources sources;
bool enabled = false;
}

void pc_p2_purple_impact_reset() { sources.reset(); enabled = false; }
void pc_p2_purple_impact_set_enabled(bool value) { enabled = value; }
bool pc_p2_purple_impact_enabled() { return enabled; }

void pc_p2_purple_impact_arm(Piki* piki)
{
    if (!enabled || !pc_p2_is_purple(piki) || !piki->isAlive()) return;
    const auto event = sources.arm(piki);
    std::printf("P2_PURPLE_ARM source=%p lifetime=%llu token=%llu\n", static_cast<void*>(piki),
        static_cast<unsigned long long>(event.sourceLifetime), static_cast<unsigned long long>(event.attackToken));
}

void pc_p2_purple_impact_forget(Piki* piki) { sources.forget(piki); }

bool pc_p2_purple_impact_emit(Piki* piki, const char* cause)
{
    if (!enabled || !pc_p2_is_purple(piki) || !piki->isAlive()) return false;
    p2purpleimpact::Event event;
    const Vector3f& source = piki->mSRT.t;
    if (!sources.consume(piki, event, source.x, source.y, source.z)) return false;
    std::set<BTeki*> visited;
    int accepted = 0;
    if (tekiMgr) {
        Iterator iterator(tekiMgr);
        CI_LOOP(iterator) {
            BTeki* target = static_cast<BTeki*>(*iterator);
            if (!target || !visited.insert(target).second) continue;
            if (!pc_p2_kochappy_registered(target)) continue;
            const Vector3f& position = target->mSRT.t;
            if (!p2purpleimpact::inRange(event, position.x, position.z, target->mCollisionRadius)) continue;
            if (pc_p2_kochappy_stun_receive(target, event, gsys->getRand(1.0f))) ++accepted;
        }
    }
    std::printf("P2_PURPLE_IMPACT source=%p lifetime=%llu token=%llu cause=%s x=%.1f y=%.1f z=%.1f accepted=%d scan=registered_global\n",
        static_cast<void*>(piki), static_cast<unsigned long long>(event.sourceLifetime),
        static_cast<unsigned long long>(event.attackToken), cause ? cause : "unknown",
        event.x, event.y, event.z, accepted);
    return true;
}
