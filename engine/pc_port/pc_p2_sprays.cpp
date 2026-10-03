#include "pc_p2_sprays.h"
#include "pc_p2_original_resource_state.h"
#include "PikiState.h"
#include "Piki.h"
#include "Navi.h"
#include "NaviState.h"
#include "CPlate.h"
#include "Controller.h"
#include "Kontroller.h"
#include "Interface.h"
#include "MoviePlayer.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "sysNew.h"
#include "timing/pc_render_phase.h"
#include <cstdio>
#include <cstdlib>
#include <string>
namespace {
p2originalresource::ResourceState* inventory = nullptr;
p2originalresource::honey::ReceiverClip growup;
bool gameplay() {
    return gsys && playerState && !playerState->mInDayEnd
        && gameflow.mMoviePlayer && !gameflow.mMoviePlayer->mIsActive
        && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive;
}
class DopeState final : public PikiState {
    float delay = 0;
    bool started = false;
    p2originalresource::honey::ReceiverClock clock;
    p2originalresource::honey::ReceiverClip clip;
public:
    DopeState() : PikiState(PIKISTATE_P2Dope, "P2_SPICY") {}
    void init(Piki* p) override {
        delay = 0.3f * gsys->getRand(1.0f); started = false;
        clock.reset();
        clip = growup;
        p->mTargetVelocity.set(0,0,0);
    }
    void exec(Piki* p) override {
        p->mTargetVelocity.set(0,0,0); p->mVelocity.x = p->mVelocity.z = 0;
        if (!started) {
            delay -= gsys->getFrameTime();
            if (delay <= 0) {
                // Source draws twice even though both choices are GROWUP1.
                (void)gsys->getRand(1.0f);
                started = true;
                p->startMotion(PaniMotionInfo(PIKIANIM_GrowUp1,p),PaniMotionInfo(PIKIANIM_GrowUp1));
            }
        }
    }
    // P1 character keys are presentation only. SourceBank-authenticated P2
    // GROWUP1 drives gameplay using strict source key.frame < int(timer).
    void animate(Piki* p, float dt) {
        if (!started) return;
        bool finishing = true; // GROWUP1 is non-looping.
        bool ok = clock.advance(clip, 30.0f * dt * p->mP2Spicy.animationRate(), finishing, [&](int key) {
            if (key == 2) {
                p->mP2Spicy.begin();
                std::printf("P2_SPICY_BEGIN piki=%p duration=40 maturity=%d source_frame=%.3f\n",static_cast<void*>(p),p->mHappa,clock.frame);
            } else if (key == 1000) {
                transit(p, PIKISTATE_Normal); return false;
            }
            return true;
        });
        if (!ok) { std::fputs("P2_SPICY source receiver clock invalid\n",stderr); std::abort(); }
    }
};
}
PikiState* pc_p2_spicy_state() { return new DopeState; }
bool pc_p2_sprays_bind(p2originalresource::ResourceState* state,
    const p2originalresource::honey::ReceiverClip* source, std::string& error) {
    if (!state && !source) { inventory = nullptr; growup = {}; error.clear(); return true; }
    if (!state || !state->ready() || !source || !source->valid() || source->loopStart >= 0) {
        error = "spicy inventory or verified non-looping GROWUP1 absent"; return false;
    }
    int actions = 0; for (const auto& key : source->keys) if (key.type == 2) ++actions;
    if (actions != 1) { error = "source GROWUP1 must have one actual action key"; return false; }
    growup = *source; inventory = state; error.clear(); return true;
}
bool pc_p2_spicy_active(const Piki* p) { return p && p->mP2Spicy.active(); }
void pc_p2_spicy_tick(Piki* p) {
    if (!pc_render_is_authoritative()) return;
    if (!p->isAlive()) { p->mP2Spicy.clear(); return; }
    if (gameplay() && p->getState() == PIKISTATE_P2Dope)
        static_cast<DopeState*>(p->getCurrState())->animate(p,gsys->getFrameTime());
    if (p->mP2Spicy.tick(gsys->getFrameTime(),gameplay()))
        std::printf("P2_SPICY_END piki=%p maturity=%d\n",static_cast<void*>(p),p->mHappa);
}
bool pc_p2_spicy_accept(Piki* p) {
    if (!p || !p->isAlive()) return false;
    if (p->mP2Spicy.active()) { p->mP2Spicy.begin(); return false; }
    // Source only PikiWalkState::dopable; host Normal is its counterpart.
    if (p->getState() != PIKISTATE_Normal) return false;
    p->mFSM->transit(p,PIKISTATE_P2Dope); return true;
}
bool pc_p2_spicy_use(Navi* n) {
    if (!inventory || !inventory->ready() || !gameplay() || !n || !n->isAlive()
        || !n->getCurrState() || n->getCurrState()->getID() != NAVISTATE_Walk || !n->mPlateMgr) return false;
    std::string error;
    if (!inventory->useSpray(p2originalresource::HoneyKind::Spicy,error)) return false;
    int accepted = 0;
    Iterator squad(n->mPlateMgr);
    CI_LOOP(squad) {
        Creature* c = *squad;
        if (c && c->isPiki() && pc_p2_spicy_accept(static_cast<Piki*>(c))) ++accepted;
    }
    std::printf("P2_SPICY_USE captain=%d stock=%d accepted=%d\n",n->getNaviIndex(),inventory->sprayCount(p2originalresource::HoneyKind::Spicy),accepted);
    return true;
}
bool pc_p2_sprays_input(Navi* n) {
    return n && n->mKontroller && n->mKontroller->keyClick(KBBTN_DPAD_UP) && pc_p2_spicy_use(n);
}
