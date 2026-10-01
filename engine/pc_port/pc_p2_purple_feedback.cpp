#include "pc_p2_purple_feedback.h"
#include "pc_p2_purple.h"
#include "pc_window.h"
#include "Piki.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "EffectMgr.h"
#include "Pcam/CameraManager.h"
#include "SoundMgr.h"
#include "gameflow.h"
#include "zen/particle.h"
#include <cmath>
#include <cstdio>
#include <map>

namespace {
struct Feedback {
    float trailTimer = 0.0f;
    bool landed = false;
};
std::map<const Piki*, Feedback> active;
PcP2PurpleFeedbackStats stats;
Uint32 lastPulse = 0;
bool hasPulse = false;

// Native PCR adaptation of P2 BlackDown/BlackDrop. Particles contain copied
// positions and this static callback only: no emitter can retain a dead Piki.
struct PurpleTint : zen::CallBack2<zen::particleGenerator*, zen::particleMdl*> {
    bool invoke(zen::particleGenerator*, zen::particleMdl* particle) override {
        particle->mPrimaryColor.r = 110;
        particle->mPrimaryColor.g = 45;
        particle->mPrimaryColor.b = 160;
        return true;
    }
} purpleTint;

void trail(Piki* piki)
{
    if (!effectMgr) return;
    auto* generator = effectMgr->create(EffectMgr::EFF_SD_Sparkle, piki->mSRT.t, nullptr, &purpleTint);
    if (!generator) return;
    generator->setScaleSize(0.65f);
    // Allow one emission update before ending this detached burst. stopGen()
    // here would suppress its first particles altogether.
    generator->configureOneShotBurst(2.0f, 6);
    ++stats.trailBursts;
}
}

void pc_p2_purple_feedback_entry(Piki* piki)
{
    if (!pc_p2_is_purple(piki) || !piki->isAlive() || !active.emplace(piki, Feedback{}).second) return;
    ++stats.entries;
    trail(piki);
    std::printf("P2_PURPLE_FEEDBACK entry=black_down native_pcr_adapter=1 source=%p\n", static_cast<void*>(piki));
}

void pc_p2_purple_feedback_update(Piki* piki, float deltaTime)
{
    auto found = active.find(piki);
    if (found == active.end() || found->second.landed) return;
    if (!piki->isAlive()) { active.erase(found); return; }
    if (!std::isfinite(deltaTime) || deltaTime <= 0.0f) return;
    found->second.trailTimer += deltaTime;
    if (found->second.trailTimer >= 0.1f) {
        found->second.trailTimer = std::fmod(found->second.trailTimer, 0.1f);
        trail(piki);
    }
}

void pc_p2_purple_feedback_land(Piki* piki, bool enemy)
{
    auto found = active.find(piki);
    if (found == active.end() || found->second.landed || !piki->isAlive()) return;
    found->second.landed = true;
    ++stats.impacts;
    const Vector3f position = piki->mSRT.t;
    unsigned created = 0;
    if (effectMgr) {
        auto* ring = effectMgr->create(EffectMgr::EFF_BigDustRing, position, nullptr, &purpleTint);
        if (ring) { ring->setScaleSize(0.35f); ++created; }
        if (effectMgr->create(EffectMgr::EFF_SD_DirtCloud, position, nullptr, nullptr)) ++created;
        auto* flash = effectMgr->create(EffectMgr::EFF_Piki_HitA, position, nullptr, &purpleTint);
        if (flash) { flash->setScaleSize(0.8f); ++created; }
    }
    // P2 DOSUN/DOSUN_HIT IDs belong to a different sound bank. Use spatial
    // native thud/hit sounds; never send P2 IDs into P1 JAudio and claim parity.
    const int sound = enemy ? SE_CHAPPY_FOOTDAMAGE : SE_FLOG_LAND;
    // playSoundDirect itself rejects requests when the sound system is closed.
    if (seSystem) {
        seSystem->playSoundDirect(JACEVENT_Battle, sound, position);
        ++stats.soundRequests;
    }
    Navi* navi = naviMgr ? naviMgr->getNavi() : nullptr;
    const float dx = navi ? position.x - navi->mSRT.t.x : 10000.0f;
    const float dz = navi ? position.z - navi->mSRT.t.z : 10000.0f;
    const Uint32 now = SDL_GetTicks();
    int rumbleResult = -2;
    if (dx * dx + dz * dz <= 250.0f * 250.0f && (!hasPulse || now - lastPulse >= 150)) {
        lastPulse = now;
        hasPulse = true;
        if (cameraMgr) {
            cameraMgr->startVibrationEvent(PCAMVIB_PurpleImpact, position);
            ++stats.cameraRequests;
        }
        SDL_GameController* controller = pc_window_get_controller();
        if (controller && gameflow.mGamePrefs.getVibeMode()) {
            rumbleResult = SDL_GameControllerRumble(controller, 0x4000, 0x2000, 80);
            if (rumbleResult == 0) ++stats.rumbleRequests;
        }
    }
    std::printf("P2_PURPLE_FEEDBACK impact=%s effects=%u sound=%d camera_requests=%u rumble_result=%d adapter=p1_pcr_audio_short_camera_sdl\n",
        enemy ? "enemy" : "ground", created, sound, stats.cameraRequests, rumbleResult);
}

void pc_p2_purple_feedback_cancel(Piki* piki)
{
    // Existing detached particles fade within their bounded lifetimes. There
    // are no actor pointers in the particle/audio/camera systems to tear down.
    active.erase(piki);
}

void pc_p2_purple_feedback_reset()
{
    active.clear();
    stats = {};
    hasPulse = false;
}

PcP2PurpleFeedbackStats pc_p2_purple_feedback_stats() { return stats; }
