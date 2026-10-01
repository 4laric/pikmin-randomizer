#include "pc_p2_sfx.h"
#include "SoundID.h"
#include "SoundMgr.h"
#include "jaudio/pikiinter.h"
#include "teki.h"
#include "Navi.h"
#include "NaviMgr.h"
#include <SDL2/SDL.h>
#include <cstdio>
#include <map>
#include <utility>

// The policy header mirrors SoundID.h so it can stay engine-free; a drift in
// either enum must fail the build rather than play the wrong sound.
static_assert(p2sfx::kKingWalk == SE_KING_WALK, "SE drift");
static_assert(p2sfx::kKingReady == SE_KING_READY, "SE drift");
static_assert(p2sfx::kKingBero2 == SE_KING_BERO2, "SE drift");
static_assert(p2sfx::kKingCheek == SE_KING_CHEEK, "SE drift");
static_assert(p2sfx::kKingHip == SE_KING_HIP, "SE drift");
static_assert(p2sfx::kKingDead1 == SE_KING_DEAD1, "SE drift");
static_assert(p2sfx::kChappySwing == SE_CHAPPY_SWING, "SE drift");
static_assert(p2sfx::kChappyFootDamage == SE_CHAPPY_FOOTDAMAGE, "SE drift");
static_assert(p2sfx::kFlogJump == SE_FLOG_JUMP, "SE drift");
static_assert(p2sfx::kFlogLand == SE_FLOG_LAND, "SE drift");
static_assert(p2sfx::kBomb == SE_BOMB, "SE drift");
static_assert(p2sfx::kMinicDie == SE_MINIC_DIE, "SE drift");
static_assert(p2sfx::kMinicAlert == SE_MINIC_ALERT, "SE drift");
static_assert(p2sfx::kSpiderWalk == SE_SPIDER_WALK, "SE drift");
static_assert(p2sfx::kSpiderSwing == SE_SPIDER_SWING, "SE drift");
static_assert(p2sfx::kSpiderDead == SE_SPIDER_DEAD, "SE drift");
static_assert(p2sfx::kSpiderBomb == SE_SPIDER_BOMB, "SE drift");
static_assert(p2sfx::kTankFire == SE_TANK_FIRE, "SE drift");
static_assert(p2sfx::kTankBreath == SE_TANK_BREATH, "SE drift");
static_assert(p2sfx::kTankWalk == SE_TANK_WALK, "SE drift");
static_assert(p2sfx::kTankSwing == SE_TANK_SWING, "SE drift");
static_assert(p2sfx::kTankDamage == SE_TANK_DAMAGE, "SE drift");
static_assert(p2sfx::kTankDead1 == SE_TANK_DEAD1, "SE drift");
static_assert(p2sfx::kMushSpore == SE_MUSH_SPORE, "SE drift");
static_assert(p2sfx::kKabutoShot == SE_KABUTO_SHOT, "SE drift");
static_assert(p2sfx::kKabutoFlip == SE_KABUTO_FLIP, "SE drift");
static_assert(p2sfx::kKabutoWalk == SE_KABUTO_WALK, "SE drift");
static_assert(p2sfx::kKabutoDead == SE_KABUTO_DEAD, "SE drift");
static_assert(p2sfx::kRockRoll == SE_ROCK_ROLL, "SE drift");
static_assert(p2sfx::kRockBreak == SE_ROCK_BREAK, "SE drift");
static_assert(p2sfx::kCollecPull == SE_COLLEC_PULL, "SE drift");
static_assert(p2sfx::kCollecWalk == SE_COLLEC_WALK, "SE drift");
static_assert(p2sfx::kCollecDead == SE_COLLEC_DEAD, "SE drift");
static_assert(p2sfx::kCollecDown == SE_COLLEC_DOWN, "SE drift");
static_assert(p2sfx::kCollecCry == SE_COLLEC_CRY, "SE drift");
static_assert(p2sfx::kCollecDamage == SE_COLLEC_DAMAGE, "SE drift");
static_assert(p2sfx::kKoganeWalk == SE_KOGANE_WALK, "SE drift");
static_assert(p2sfx::kKoganeDamage == SE_KOGANE_DAMAGE, "SE drift");
static_assert(p2sfx::kSaraiHover == SE_SARAI_HOVER, "SE drift");
static_assert(p2sfx::kSaraiDamage == SE_SARAI_DAMAGE, "SE drift");
static_assert(p2sfx::kSaraiAttack == SE_SARAI_ATTACK, "SE drift");
static_assert(p2sfx::kSaraiDead == SE_SARAI_DEAD, "SE drift");
static_assert(p2sfx::kMarDead1 == SE_MAR_DEAD1, "SE drift");
static_assert(p2sfx::kKurioneWater == SE_KURIONE_WATER, "SE drift");
static_assert(p2sfx::kKingWalk == SE_KING_WALK, "SE drift");
static_assert(p2sfx::kKingReady == SE_KING_READY, "SE drift");
static_assert(p2sfx::kKingBero1 == SE_KING_BERO1, "SE drift");
static_assert(p2sfx::kKingEat == SE_KING_EAT, "SE drift");
static_assert(p2sfx::kKingCheek == SE_KING_CHEEK, "SE drift");
static_assert(p2sfx::kKingHip == SE_KING_HIP, "SE drift");
static_assert(p2sfx::kKingDead1 == SE_KING_DEAD1, "SE drift");
static_assert(p2sfx::kKingAppear == SE_KING_APPEAR, "SE drift");
static_assert(p2sfx::kKingSink == SE_KING_SINK, "SE drift");

namespace {
struct Actor {
    p2sfx::ActorGate gate;
    p2sfx::Stride stride;
};
std::map<std::pair<unsigned, unsigned>, Actor> gActors;

Actor& actorFor(unsigned sourceId, unsigned token) { return gActors[std::make_pair(sourceId, token)]; }

// Wall clock in seconds. Output-only: it never feeds the sim.
float nowSeconds() { return float(SDL_GetTicks()) * 0.001f; }
} // namespace

namespace {
int play(unsigned sourceId, unsigned token, p2sfx::Event event, const Vector3f& position, BTeki* actor)
{
    if (!seSystem) return p2sfx::kNone;
    // P1 culls a far creature's AI (and so its sound keys) by distance; the
    // P2 FSMs run everywhere, so cull the request itself at the audible
    // radius (SeConstant p00, 700 units: beyond it the offset normalises to
    // volume 0 and createEvent would only churn or lose an event slot).
    // SeSystem keeps its listener protected; the nearest captain is what it
    // listens from during play (SeSystem::update caller), as in
    // pc_p2_purple_feedback.
    if (naviMgr) {
        if (Navi* navi = naviMgr->getNearestNavi(position)) {
            const float cutoff = 700.0f; // SeConstant p00 default (SoundMgr.h:44)
            const float dx = position.x - navi->mSRT.t.x;
            const float dy = position.y - navi->mSRT.t.y;
            const float dz = position.z - navi->mSRT.t.z;
            if (dx * dx + dy * dy + dz * dz > cutoff * cutoff) return p2sfx::kNone;
        }
    }
    bool logIt = false;
    const int se = actorFor(sourceId, token).gate.admit(sourceId, event, nowSeconds(), &logIt);
    if (se == p2sfx::kNone) return p2sfx::kNone;
    if (actor && actor->mSeContext) {
        // One Jac event per actor, created on first play and evicted by
        // listener distance like any P1 creature's (SeSystem::createEvent).
        actor->playSound(se);
    } else {
        // Actor-less one-shot: a system context (playSoundDirect reuses the
        // nearest same-type context within 200 units, else round-robin).
        seSystem->playSoundDirect(JACEVENT_Battle, se, position);
    }
    if (logIt) {
        char line[128];
        p2sfx::formatMarker(line, sizeof line, sourceId, token, event, se);
        std::printf("%s x=%.1f y=%.1f z=%.1f ctx=%s\n", line, position.x, position.y, position.z,
                    actor && actor->mSeContext ? "actor" : "direct");
    }
    return se;
}
} // namespace

int pc_p2_sfx(unsigned sourceId, unsigned token, p2sfx::Event event, const Vector3f& position)
{
    return play(sourceId, token, event, position, nullptr);
}

int pc_p2_sfx(unsigned sourceId, unsigned token, p2sfx::Event event, BTeki* actor)
{
    if (!actor) return p2sfx::kNone;
    return play(sourceId, token, event, actor->getPosition(), actor);
}

void pc_p2_sfx_stop(unsigned sourceId, p2sfx::Event event, BTeki* actor)
{
    const int se = p2sfx::seFor(sourceId, event);
    if (se == p2sfx::kNone || !actor || !actor->mSeContext) return;
    actor->stopSound(se);
}

void pc_p2_sfx_stride(unsigned sourceId, unsigned token, const Vector3f& position, float strideLength)
{
    Actor& a = actorFor(sourceId, token);
    if (a.stride.advance(position.x, position.z, strideLength)) pc_p2_sfx(sourceId, token, p2sfx::Event::Step, position);
}

void pc_p2_sfx_stride(unsigned sourceId, unsigned token, BTeki* actor, float strideLength)
{
    if (!actor) return;
    Actor& a = actorFor(sourceId, token);
    const Vector3f position = actor->getPosition();
    if (a.stride.advance(position.x, position.z, strideLength)) play(sourceId, token, p2sfx::Event::Step, position, actor);
}

void pc_p2_sfx_forget(unsigned sourceId, unsigned token)
{
    for (auto it = gActors.begin(); it != gActors.end();) {
        if (it->first.first == sourceId && (token == 0 || it->first.second == token)) it = gActors.erase(it);
        else ++it;
    }
}
