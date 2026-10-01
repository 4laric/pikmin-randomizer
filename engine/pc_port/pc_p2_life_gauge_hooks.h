#pragma once
// Engine-side hooks for the shared P2 life gauge (see pc_p2_life_gauge.h).
// Header-only (inline) so no CMake source list changes are needed.
#include "pc_p2_life_gauge.h"
#include "pc_p2_campaign_actor.h"
#include "LifeGauge.h"
#include <cstdio>
#include <unordered_map>

// Audit marker (env-free, rate limited): one line per damaged campaign actor
// every 120 draw calls, reporting every condition that decides whether the P1
// wheel reaches the screen. `drawn` is what refresh2d actually did.
inline void pc_p2_life_gauge_audit(BTeki* t, bool drawn)
{
    const unsigned source = pc_p2_campaign_source(t);
    if (!source) return;
    const float max = t->getMaxLife();
    if (!(t->mHealth < max)) return;
    static std::unordered_map<const BTeki*, int> sCount;
    int& n = sCount[t];
    if (n++ % 120 != 0) return;
    std::printf("P2_LIFE_GAUGE_AUDIT source_id=%u token=%u health=%.1f max=%.1f target_ratio=%.3f display_state=%d "
                "option=%d visible=%d has_model=%d ai_culled=%d dead_state=%d drawn=%d\n",
                source, pc_p2_campaign_token(t), t->mHealth, max, t->mLifeGauge.mTargetHealthRatio,
                t->mLifeGauge.mDisplayState, int(t->getTekiOption(TEKIOPT_LifeGaugeVisible)), int(t->isVisible()),
                int(tekiMgr->hasModel(t->mTekiType)), int(t->isCreatureFlag(CF_UseAICulling)), int(t->mDeadState),
                int(drawn));
    std::fflush(stdout);
}

// Shared fix (#215 owner playtest, P2 health bars): a campaign P2 actor whose
// doAI is suppressed by a family seam never reaches BTeki::doAI's
// updateLifeGauge(), so its gauge ratio stayed 1.0 and the wheel never showed.
// BTeki::update runs for every actor, so feed the gauge there. Idempotent for
// the families that already call updateLifeGauge themselves.
inline void pc_p2_life_gauge_update(BTeki* t)
{
    if (t->mDeadState != 0 || t->mHealth <= 0.0f) return;
    const unsigned source = pc_p2_campaign_source(t);
    if (!source) return;
    if (p2lifegauge::gaugeFollowsTargetable(source)) {
        if (t->isAtari()) t->setTekiOption(TEKIOPT_LifeGaugeVisible);
        else t->clearTekiOption(TEKIOPT_LifeGaugeVisible);
    }
    t->updateLifeGauge();
}

// P2 EnemyBase::doGetLifeGaugeParam: gauge at root position + fp27 (retail
// per-species "life height"). P1 hosts report the P1 vehicle's offset from a
// collision centre, which is wrong for a different P2 body.
inline void pc_p2_life_gauge_place(BTeki* t, Vector3f& position, float& offsetY)
{
    const unsigned source = pc_p2_campaign_source(t);
    if (!source || !p2lifegauge::hasHeight(source)) return;
    position = t->getPosition();
    offsetY = p2lifegauge::lifeMeterHeight(source, offsetY);
}
