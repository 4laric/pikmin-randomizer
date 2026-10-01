#include "pc_p2_attack_fx_host.h"

#include "EffectMgr.h"
#include "zen/particle.h"

namespace p2attackfx {

static_assert(int(EffectMgr::EFF_P_Bubbles) == EFF_P_Bubbles, "EFF_P_Bubbles id");
static_assert(int(EffectMgr::EFF_Frog_Water1) == EFF_Frog_Water1, "EFF_Frog_Water1 id");
static_assert(int(EffectMgr::EFF_Frog_Water2) == EFF_Frog_Water2, "EFF_Frog_Water2 id");
static_assert(int(EffectMgr::EFF_Tank_Fire) == EFF_Tank_Fire, "EFF_Tank_Fire id");
static_assert(int(EffectMgr::EFF_Kinoko_AttackCloud) == EFF_Kinoko_AttackCloud, "EFF_Kinoko_AttackCloud id");
static_assert(int(EffectMgr::EFF_Kinoko_PostAttackCloud) == EFF_Kinoko_PostAttackCloud, "EFF_Kinoko_PostAttackCloud id");
static_assert(int(EffectMgr::EFF_Kinoko_AttackSpores) == EFF_Kinoko_AttackSpores, "EFF_Kinoko_AttackSpores id");
static_assert(int(EffectMgr::EFF_Spider_DeadBombSparks) == EFF_Spider_DeadBombSparks, "EFF_Spider_DeadBombSparks id");
static_assert(int(EffectMgr::EFF_Rocket_Biri) == EFF_Rocket_Biri, "EFF_Rocket_Biri id");
static_assert(int(EffectMgr::EFF_RippleWhite) == EFF_RippleWhite, "EFF_RippleWhite id");
static_assert(int(EffectMgr::EFF_Piki_Bubble) == EFF_Piki_Bubble, "EFF_Piki_Bubble id");
static_assert(int(EffectMgr::EFF_Piki_BubbleRecover) == EFF_Piki_BubbleRecover, "EFF_Piki_BubbleRecover id");
static_assert(int(EffectMgr::EFF_King_SalivaDroplet) == EFF_King_SalivaDroplet, "EFF_King_SalivaDroplet id");
static_assert(int(EffectMgr::EFF_RippleWhite2) == EFF_RippleWhite2, "EFF_RippleWhite2 id");
static_assert(int(EffectMgr::EFF_Frog_BubbleRingL) == EFF_Frog_BubbleRingL, "EFF_Frog_BubbleRingL id");
static_assert(int(EffectMgr::EFF_Frog_Bubble2) == EFF_Frog_Bubble2, "EFF_Frog_Bubble2 id");
static_assert(int(EffectMgr::EFF_Frog_BubbleRingS) == EFF_Frog_BubbleRingS, "EFF_Frog_BubbleRingS id");
static_assert(int(EffectMgr::EFF_Mizu_IdleBubbles) == EFF_Mizu_IdleBubbles, "EFF_Mizu_IdleBubbles id");
static_assert(int(EffectMgr::EFF_Mizu_JetPuff) == EFF_Mizu_JetPuff, "EFF_Mizu_JetPuff id");
static_assert(int(EffectMgr::EFF_Mizu_JetMist) == EFF_Mizu_JetMist, "EFF_Mizu_JetMist id");
static_assert(int(EffectMgr::EFF_Onyon_BubblesSmall) == EFF_Onyon_BubblesSmall, "EFF_Onyon_BubblesSmall id");
static_assert(int(EffectMgr::EFF_Onyon_Bubbles) == EFF_Onyon_Bubbles, "EFF_Onyon_Bubbles id");
static_assert(int(EffectMgr::EFF_Onyon_Ripples1) == EFF_Onyon_Ripples1, "EFF_Onyon_Ripples1 id");

namespace {
// Owner callback (BurnEffect pattern): invoke() lets the generator proceed.
struct Owner : public zen::CallBack1<zen::particleGenerator*> {
    bool invoke(zen::particleGenerator*) override { return true; }
};
} // namespace

Emitter::Emitter() : owner_(new Owner()) {}

Emitter::~Emitter() {
    stopAll();
    delete static_cast<Owner*>(owner_);
}

unsigned Emitter::emit(Element e, const Point* pts, int n, unsigned tick) {
    if (!effectMgr || !pts || n <= 0) return 0;
    unsigned made = 0;
    for (int i = 0; i < n; ++i) {
        // Skip the rest of the tick rather than flood the generator pool.
        if (effectMgr->getLiveGeneratorCount() > unsigned(MAX_LIVE_GENERATORS)) break;
        const Point& q = pts[i];
        const Look l = look(e, q.kind);
        if (l.scale <= 0.0f) continue;
        if (!l.burst && (tick % (l.every ? l.every : 1u)) != 0) continue;
        zen::particleGenerator* g = effectMgr->create(static_cast<EffectMgr::effTypeTable>(l.effect),
                                                      Vector3f(q.x, q.y, q.z), static_cast<Owner*>(owner_), nullptr);
        if (!g) continue;
        g->setEmitDir(Vector3f(q.dx, 0.0f, q.dz));
        g->setScaleSize(q.scale * l.scale);
        if (l.rgb) g->setTint(Colour(u8((l.rgb >> 16) & 255), u8((l.rgb >> 8) & 255), u8(l.rgb & 255), 255));
        if (l.burst) g->configureOneShotBurst(1.0f, l.life);
        ++made;
    }
    made_ += made;
    return made;
}

unsigned Emitter::emitLook(const Look& l, const Point* pts, int n) {
    if (!effectMgr || !pts || n <= 0) return 0;
    unsigned made = 0;
    for (int i = 0; i < n; ++i) {
        if (effectMgr->getLiveGeneratorCount() > unsigned(MAX_LIVE_CLOUD_GENERATORS)) break;
        const Point& q = pts[i];
        zen::particleGenerator* g = effectMgr->create(static_cast<EffectMgr::effTypeTable>(l.effect),
                                                      Vector3f(q.x, q.y, q.z), static_cast<Owner*>(owner_), nullptr);
        if (!g) continue;
        g->setEmitDir(Vector3f(q.dx, 0.0f, q.dz));
        g->setScaleSize(q.scale * l.scale);
        if (l.rgb) g->setTint(Colour(u8((l.rgb >> 16) & 255), u8((l.rgb >> 8) & 255), u8(l.rgb & 255), 255));
        if (l.burst) g->configureOneShotBurst(1.0f, l.life);
        ++made;
    }
    made_ += made;
    return made;
}

unsigned Emitter::stopAll() {
    const unsigned made = made_;
    if (effectMgr && made_ > 0) effectMgr->kill(static_cast<Owner*>(owner_), nullptr, true);
    made_ = 0;
    return made;
}

} // namespace p2attackfx
