#include "pc_p2_gas_cloud.h"

#include "Piki.h"
#include "pc_p2_attack_fx_host.h"
#include "pc_p2_gas_cloud_policy.h"
#include "gl/pc_gfx.h"

#include <cstdio>
#include <map>

namespace {
struct Entry {
    p2attackfx::Emitter fx;
    p2gascloud::Cloud cloud;
};
std::map<Piki*, Entry> sClouds;
unsigned sLifetimeStarted = 0, sLifetimeStopped = 0;

unsigned saltOf(const Piki* p) { return unsigned(reinterpret_cast<unsigned long long>(p) >> 4); }

void stopEntry(Piki* piki, Entry& e, p2gascloud::Why why) {
    if (!e.cloud.end()) return;
    const unsigned ticks = e.cloud.ticks, points = e.cloud.points;
    const unsigned made = e.fx.stopAll();
    ++sLifetimeStopped;
    std::printf("P2_GAS_CLOUD_STOP piki=%p reason=%s ticks=%u points=%u generators=%u outstanding=%u live=%u\n",
                static_cast<void*>(piki), p2gascloud::whyName(why), ticks, points, made, e.cloud.outstanding(),
                sLifetimeStarted - sLifetimeStopped);
    std::fflush(stdout);
}
} // namespace

void pc_p2_gas_cloud_begin(Piki* piki) {
    if (!piki) return;
    Entry& e = sClouds[piki];
    if (e.cloud.begin()) {
        ++sLifetimeStarted;
        std::printf("P2_GAS_CLOUD_START piki=%p live=%u visual_only=1\n", static_cast<void*>(piki),
                    sLifetimeStarted - sLifetimeStopped);
        std::fflush(stdout);
    }
}

void pc_p2_gas_cloud_update(Piki* piki) {
    auto it = sClouds.find(piki);
    if (it == sClouds.end() || !it->second.cloud.active) return;
    Entry& e = it->second;
    const unsigned tick = e.cloud.ticks++;
    if (!p2gascloud::emitsOn(tick)) return;
    const Vector3f& p = piki->mSRT.t;
    p2attackfx::Point pts[p2gascloud::PUFFS];
    const int n = p2gascloud::layout(p.x, p.y, p.z, tick, saltOf(piki), pts);
    const p2attackfx::Look look{p2gascloud::EFFECT, p2gascloud::PUFF_LIFE, true, p2attackfx::PURPLE};
    const unsigned made = e.fx.emitLook(look, pts, n);
    e.cloud.points += unsigned(n);
    // Probe-only frame dump (PIKMIN_P2_PROXY_SHOT directory): the first few clouds of the run.
    static unsigned sDumps = 0;
    if ((tick == 12 || tick == 36 || tick == 60) && sDumps < 6) {
        char key[40];
        std::snprintf(key, sizeof(key), "GasCloud_%02u", sDumps++);
        pc_gfx_proxy_shot_now(key);
    }
    if (tick == 0 && made > 0) {
        std::printf("P2_GAS_CLOUD piki=%p head=%.1f,%.1f,%.1f puffs=%d generators=%u effect=EFF_Kinoko_AttackCloud\n",
                    static_cast<void*>(piki), pts[0].x, pts[0].y, pts[0].z, n, made);
        std::fflush(stdout);
    }
}

void pc_p2_gas_cloud_end(Piki* piki, bool death) {
    auto it = sClouds.find(piki);
    if (it == sClouds.end()) return;
    stopEntry(piki, it->second, death ? p2gascloud::Why::Death : p2gascloud::Why::Cured);
    sClouds.erase(it);
}

void pc_p2_gas_cloud_reset() {
    for (auto& kv : sClouds) stopEntry(kv.first, kv.second, p2gascloud::Why::Reset);
    sClouds.clear();
}
