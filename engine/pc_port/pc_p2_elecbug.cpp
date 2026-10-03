// Family-owned ground-invertebrate source behavior for the batch-2 Chappy
// placement vehicle: Anode Beetle (ElecBug, EnemyID 28). Implements the source
// ElecBugState.cpp cycle (Wait/Turn/Move wander -> Charge -> Discharge -> Return)
// plus the source two-beetle Charge/ChildCharge partner link and the Reverse flip
// from ElecBug.cpp::pressCallBack / StateReverse. Source revision
// 632af93787b9c95b63f0c13be32b161375ce3a96; retail parms from
// experimental/pikmin2_ground_inverts_assets.py (GPVE01 rev 0).
//
// Source contract implemented:
//   * StateCharge::exec searches once, 2.0s into Charge, for a live unlinked
//     beetle in Wait/Turn/Move within 300 units and links reciprocally via
//     startChargeState/startChildChargeState (generator Charge, child ChildCharge).
//   * Charge lasts 3.0s then Discharge; ChildCharge lasts 1.0s then ChildDischarge.
//     On discharge the generator sweeps the electrical receiver across the pair.
//   * Partner links break on partner death, press/Reverse (finishPartnerAndEffect),
//     discharge completion and partner loss.
//
// Port adaptations (recorded, not retail-faithful):
//   * Partner selection is nearest-first (the source picks uniformly at random
//     among candidates within 300 units).
//   * Between-beetle Denki geometry is resolved as a single nearest shockable
//     Pikmin within the discharge radius of either linked beetle, shocked once
//     per discharge. The emitter now delivers the real lane-10 `InteractDenki`
//     receiver (not InteractKill), so the source Yellow/Bulbmin exclusion is
//     enforced by the lane-11 species capability matrix exactly as the receiver
//     does; a non-immune target transits PIKISTATE_DenkiDying.
//   * Charge and ChildCharge durations are port values (source hard-codes
//     mStateTimer > 3.0 / > 1.0; Return ends on animation end).
//   * View angle is a full hemisphere.
// No other lane's module is modified; every hook is a no-op for unregistered actors.
#include "pc_p2_elecbug.h"
#include "pc_p2_elecbug_fsm.h"
#include "pc_p2_elecbug_fx.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_randomizer.h"
#include "pc_p2_species.h"
#include "pc_p2_hazard_emitter.h"
#include "teki.h"
#include "pc_p2_attack_fx_host.h"
#include <memory>
#include "pc_p2_navi_select.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "GlobalGameOptions.h"
#include "Generator.h"
#include "gameflow.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace {
enum State {
    ELEC_INVALID = -1,
    ELEC_DEAD = 0,
    ELEC_WAIT = 1,
    ELEC_TURN = 2,
    ELEC_MOVE = 3,
    ELEC_CHARGE = 4,
    ELEC_DISCHARGE = 5,
    ELEC_CHILDCHARGE = 6,
    ELEC_CHILDISCHARGE = 7,
    ELEC_REVERSE = 8,
    ELEC_RETURN = 9,
};

const char* stateName(State s) {
    switch (s) {
    case ELEC_DEAD: return "dead";
    case ELEC_WAIT: return "wait";
    case ELEC_TURN: return "turn";
    case ELEC_MOVE: return "move";
    case ELEC_CHARGE: return "charge";
    case ELEC_DISCHARGE: return "discharge";
    case ELEC_CHILDCHARGE: return "childcharge";
    case ELEC_CHILDISCHARGE: return "childdischarge";
    case ELEC_REVERSE: return "reverse";
    case ELEC_RETURN: return "return";
    default: return "null";
    }
}

// Source enemyparm.txt values (ground_inverts manifest general/proper).
constexpr float LIFE = 500.0f;
constexpr float MOVE_SPEED = 30.0f;
constexpr float TERRITORY = 200.0f;
constexpr float HOME_RADIUS = 100.0f;
constexpr float FLIP_TIME = 5.0f;         // fp01
constexpr float WAIT_TIME = 1.5f;         // fp02
constexpr float DISCHARGE_TIME = 3.0f;    // fp11
constexpr float CHARGE_TIME = 3.0f;       // source StateCharge mStateTimer > 3.0
constexpr float CHILD_CHARGE_TIME = 1.0f; // source StateChildCharge mStateTimer > 1.0
constexpr float CHARGE_SEARCH_DELAY = 2.0f; // source mStateTimer > 2.0
constexpr float PAIR_RADIUS = 300.0f;     // source bugPos.distance(otherPos) < 300
constexpr float TURN_TIME = 0.5f;         // port value (source turns until facing the target)
constexpr float WANDER_TIME = 1.5f;       // port value
constexpr float ELEC_RADIUS = 70.0f;      // source sweep radius fp20/22 = 70
constexpr float TURN_RATE = 2.0f;

struct Clip {
    std::string name;
    float duration = 1.0f;
    bool loop = false;
    int frames = 0;
    p2elecbug::ClipKeys keys;
};

struct ElecBug {
    State state = ELEC_WAIT;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    BTeki* self = nullptr;
    BTeki* partner = nullptr;
    bool hasSearched = false;
    bool shockedThisDischarge = false;
    bool arcLogged = false;
    bool arcFxLogged = false;
    std::unique_ptr<p2attackfx::Emitter> fx; // P1 electric spark arc (shared attack fx)
    unsigned fxTick = 0;
    std::set<const Creature*> arcHit;
    bool immuneLogged = false;
    bool flipped = false;
    bool deadLogged = false;
    bool escaped = false;
    float lastHealth = LIFE;
    float testClock = 0.0f;
    float testChargeClock = 0.0f;
    bool testPressed = false;
    float inactiveTimer = 0.0f; // source mInactiveTimer (Charge only when > 15)
    std::string clip = "wait";
    float phase = 0.0f;
    float logTimer = 0.0f;
};

std::map<PelletView*, ElecBug> actors;
std::map<std::string, Clip> clips;
bool ready = false;

float wrapPi(float a) {
    while (a > 3.14159265f) a -= 6.28318531f;
    while (a < -3.14159265f) a += 6.28318531f;
    return a;
}
float distXZ(const Vector3f& a, const Vector3f& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}
float clipDuration(const std::string& name) {
    auto it = clips.find(name);
    return it == clips.end() ? 1.0f : it->second.duration;
}
bool clipLoops(const std::string& name) {
    auto it = clips.find(name);
    return it != clips.end() && it->second.loop;
}
unsigned genOf(const BTeki* actor) {
    // Bridge pack members may carry a placeholder _70; the seed token is the
    // stable own-token for evidence (setup binds by it). Fall back to _70
    // off-bridge. Fixes the generator=0 HIT/DEAD/PRESS attribution.
    if (!actor) return 0u;
    const unsigned token = pc_p2_campaign_token(const_cast<BTeki*>(actor));
    if (token) return token;
    return actor->mGenerator ? actor->mGenerator->_70 : 0u;
}
ElecBug* lookup(BTeki* actor) {
    auto it = actors.find(static_cast<PelletView*>(actor));
    return it == actors.end() ? nullptr : &it->second;
}
// A Pikmin is shockable exactly when the lane-10 electric receiver would accept
// it: the lane-11 capability matrix rejects electric-immune species (Yellow,
// Bulbmin) and everything else transits PIKISTATE_DenkiDying. Deriving the
// emitter's target from the receiver's own decision keeps the two in lockstep.
bool elecShockable(const Piki* p) {
    if (!p || !p->isAlive()) return false;
    return p2_emitter_accepts(pc_p2_species(p), P2HazardElectric, p->gasInvicible());
}
Piki* nearestShockable(const Vector3f& pos, float radius) {
    Piki* best = nullptr;
    float bestSq = radius * radius;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!elecShockable(p)) continue;
            const float d = distXZ(p->getPosition(), pos);
            if (d < radius && d * d < bestSq) { bestSq = d * d; best = p; }
        }
    }
    return best;
}
// The source StateDischarge::checkInteract sweeps the Denki line between the two
// linked beetles. The emitter resolves the nearest shockable Pikmin to either
// end of the pair and delivers the real lane-10 InteractDenki receiver.
Piki* nearestShockablePair(const Vector3f& pos, const BTeki* partner, float radius) {
    Piki* best = nearestShockable(pos, radius);
    if (!best && partner) best = nearestShockable(partner->getPosition(), radius);
    return best;
}
const char* colorName(unsigned color) {
    switch (color) {
    case Blue: return "blue";
    case Red: return "red";
    case Yellow: return "yellow";
    default: return "other";
    }
}
// Source InteractDenki::actPiki excludes Yellow/Bulbmin from the discharge. The
// receiver and the emitter both consult the lane-11 matrix, so this probe
// reports every immune species inside the sweep that was deliberately rejected,
// emitting one immunity marker per species. Returns true when any was in range.
bool logElecImmuneInRange(unsigned generator, const Vector3f& pos, float radius) {
    if (!pikiMgr) return false;
    bool sawYellow = false, sawBulbmin = false;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        const int species = pc_p2_species(p);
        if (!p2_species_immune(species, P2HazardElectric)) continue;
        if (distXZ(p->getPosition(), pos) >= radius) continue;
        if (species == P2SpeciesBulbmin) sawBulbmin = true;
        else if (species == P2SpeciesYellow) sawYellow = true;
    }
    if (sawYellow) {
        std::printf("P2_ELECBUG_IMMUNE generator=%u source_id=28 pikmin=yellow species=2\n",
                    generator);
    }
    if (sawBulbmin) {
        std::printf("P2_ELECBUG_IMMUNE generator=%u source_id=28 pikmin=bulbmin species=5\n",
                    generator);
    }
    std::fflush(stdout);
    return sawYellow || sawBulbmin;
}
// Source Obj::checkInteract (ElecBug.cpp:411): the Denki band between the two
// beetles. Pikmin and Navis inside it take InteractDenki every frame.
void sweepArc(BTeki* actor, ElecBug& s, unsigned generator) {
    if (!s.partner) return;
    const Vector3f a = actor->getPosition();
    const Vector3f b = s.partner->getPosition();
    const p2elecbug::V3 pa{a.x, a.y, a.z}, pb{b.x, b.y, b.z};
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it) {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f c = p->getPosition();
            if (!p2elecbug::inArcBand(pa, pb, p2elecbug::V3{c.x, c.y, c.z})) continue;
            const int species = pc_p2_species(p);
            if (p2_species_immune(species, P2HazardElectric)) {
                if (s.arcHit.insert(p).second) {
                    std::printf("P2_ELECBUG_ARC_IMMUNE generator=%u species=%d\n", generator, species);
                }
                continue;
            }
            if (p->getState() == PIKISTATE_DenkiDying) continue;
            Vector3f dir(b.x - a.x, 0.0f, b.z - a.z);
            const bool accepted = p->stimulate(InteractDenki(actor, 1.0f, &dir));
            if (s.arcHit.insert(p).second) {
                std::printf("P2_ELECBUG_DENKI generator=%u source_id=28 emitter=arc target=%d accepted=%d "
                            "target_state=%d(%s)\n", generator, species, int(accepted), p->getState(),
                            p->getState() == PIKISTATE_DenkiDying ? "DenkiDying" : "other");
                std::printf("P2_ELECBUG_SHOCK generator=%u pikmin=1 color=%s\n", generator,
                            colorName(p->mColor));
            }
        }
    }
    for (Navi* n : pc_p2_navis()) {
        if (!n || !n->isAlive()) continue;
        const Vector3f c = n->getPosition();
        if (!p2elecbug::inArcBand(pa, pb, p2elecbug::V3{c.x, c.y, c.z})) continue;
        Vector3f dir(b.x - a.x, 0.0f, b.z - a.z);
        n->stimulate(InteractDenki(actor, 1.0f, &dir));
        if (s.arcHit.insert(n).second) {
            std::printf("P2_ELECBUG_DENKI generator=%u source_id=28 emitter=arc target=navi\n", generator);
        }
    }
    std::fflush(stdout);
}
// Source randWeightFloat(10.0f): the inactivity timer restarts in [0,10).
float inactiveReset() { return 10.0f * float(std::rand() % 1000) / 1000.0f; }
int recoverFrames() {
    auto it = clips.find("recover");
    return it == clips.end() ? 30 : it->second.frames;
}
// Stand-ins for efx::TDnkmsEffect (see pc_p2_elecbug_fx.h): HoudenB charge sparks on
// the beetle from the charge start, HoudenA glow on both beetles plus the
// ThunderA/B zap between them from the discharge event, all gone on fade().
void fxUpdate(BTeki* actor, ElecBug& s, unsigned generator) {
    const int st = int(s.state);
    if (!p2elecbugfx::effectsLive(st)) return;
    if (!s.fx) s.fx.reset(new p2attackfx::Emitter());
    const unsigned tick = s.fxTick++;
    const Vector3f a = actor->getPosition();
    unsigned made = 0;
    if (tick % p2elecbugfx::kHaloEvery == 0) {
        // HoudenB: charge sparks chasing the beetle (Electric Dweevil charge plan: 268 + 189/190 at 2.5x).
        p2attackfx::Point ring[4];
        for (int k = 0; k < 4; ++k) {
            const float ang = float(k) * 1.5707963f + float(tick) * 0.35f;
            ring[k] = {p2attackfx::Kind::Node, a.x + std::cos(ang) * 12.0f, a.y + 10.0f, a.z + std::sin(ang) * 12.0f,
                       p2elecbugfx::kHaloScale, std::cos(ang), std::sin(ang)};
        }
        made += s.fx->emit(p2attackfx::Element::Elec, ring, 4, tick);
        p2attackfx::Point core{p2attackfx::Kind::Arc, a.x, a.y + 10.0f, a.z, p2elecbugfx::kHaloScale, 0.0f, 1.0f};
        made += s.fx->emit(p2attackfx::Element::Elec, &core, 1, tick);
    }
    if (p2elecbugfx::arcLive(st, s.partner != nullptr, s.stateTime)) {
        const Vector3f b = s.partner->getPosition();
        const float dx = b.x - a.x, dz = b.z - a.z;
        const float len = std::sqrt(dx * dx + dz * dz);
        const int pieces = p2elecbugfx::arcPieces(len);
        // HoudenA glow at both beetles.
        p2attackfx::Point ends[2] = {
            {p2attackfx::Kind::Arc, a.x, a.y + 10.0f, a.z, p2elecbugfx::kArcScale, 0.0f, 1.0f},
            {p2attackfx::Kind::Arc, b.x, b.y + 10.0f, b.z, p2elecbugfx::kArcScale, 0.0f, 1.0f}};
        made += s.fx->emit(p2attackfx::Element::Elec, ends, 2, tick);
        // ThunderA / ThunderB: two jagged strands end to end, each split in pieces so
        // long links keep a dense, continuous bolt.
        for (unsigned strand = 0; strand < 2; ++strand) {
            for (int piece = 0; piece < pieces; ++piece) {
                const float t0 = float(piece) / float(pieces), t1 = float(piece + 1) / float(pieces);
                p2attackfx::Point pts[p2attackfx::MAX_ARC_POINTS];
                const int n = p2attackfx::layoutArc(a.x + dx * t0, a.y + 10.0f + (b.y - a.y) * t0, a.z + dz * t0,
                                                    a.x + dx * t1, a.y + 10.0f + (b.y - a.y) * t1, a.z + dz * t1,
                                                    tick, generator + strand * 101u + unsigned(piece) * 13u,
                                                    p2elecbugfx::kArcJitter, pts);
                // Bolt body in pale lightning yellow (tinted EFF_Rocket_Biri); the two end nodes keep
                // the authored EFF_Spider_DeadBombSparks so the contact points flash.
                p2attackfx::Point body[p2attackfx::MAX_ARC_POINTS];
                int nb = 0;
                for (int k = 0; k < n; ++k) {
                    pts[k].scale = p2elecbugfx::kArcScale;
                    if (pts[k].kind == p2attackfx::Kind::Arc) body[nb++] = pts[k];
                }
                made += s.fx->emitLook({p2attackfx::EFF_Rocket_Biri, 5, true, p2elecbugfx::kBoltRgb}, body, nb);
                made += s.fx->emit(p2attackfx::Element::Elec, pts, n, tick);
            }
        }
        if (!s.arcFxLogged) {
            s.arcFxLogged = true;
            std::printf("P2_ELECBUG_ARC_FX generator=%u pieces=%d length=%.1f generators_first_tick=%u\n",
                        generator, pieces, len, made);
            std::fflush(stdout);
        }
    }
}
void enter(ElecBug& s, State state, const char* clip) {
    std::printf("P2_ELECBUG_CLIP generator=%u state=%s clip=%s\n", s.self ? genOf(s.self) : 0u,
                stateName(state), clip ? clip : s.clip.c_str());
    s.state = state;
    s.stateTime = 0.0f;
    s.arcLogged = false;
    s.arcHit.clear();
    if (s.fx && !p2elecbugfx::effectsLive(int(state))) {
        s.fxTick = 0;
        s.arcFxLogged = false;
        const unsigned n = s.fx->stopAll();
        if (n) std::printf("P2_ELECBUG_ARC_STOP generator=%u generators=%u\n", s.self ? genOf(s.self) : 0u, n);
    }
    if (clip) s.clip = clip;
}
void wander(BTeki* a, ElecBug& s) {
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * MOVE_SPEED, 0.0f, std::cos(s.heading) * MOVE_SPEED);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}
void stop(BTeki* a) {
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}
void setPhase(ElecBug& s) {
    if (s.state == ELEC_REVERSE && s.clip == "turn") {
        auto it = clips.find("turn");
        if (it != clips.end() && it->second.frames > 0) {
            const p2elecbug::ReverseClip rc =
                p2elecbug::reverseClip(it->second.keys, s.stateTime, FLIP_TIME);
            s.phase = rc.frame / float(it->second.frames);
            if (s.phase > 1.0f) s.phase = 1.0f;
            return;
        }
    }
    const float duration = clipDuration(s.clip);
    const float len = duration > 0.0f ? duration : 1.0f;
    if (clipLoops(s.clip)) {
        s.phase = s.stateTime / len;
        s.phase -= std::floor(s.phase);
    } else {
        s.phase = s.stateTime / len;
        if (s.phase > 1.0f) s.phase = 1.0f;
    }
}
// Source Obj::resetPartnerPtr / finishPartnerAndEffect null both sides. Log the
// unlink for each beetle that actually carried the pointer.
void breakLink(BTeki* actor, ElecBug& s) {
    BTeki* partner = s.partner;
    if (!partner) return;
    ElecBug* other = lookup(partner);
    s.partner = nullptr;
    if (other) other->partner = nullptr;
    std::printf("P2_ELECBUG_UNLINK generator=%u\n", genOf(actor));
    if (other) std::printf("P2_ELECBUG_UNLINK generator=%u\n", genOf(partner));
    std::fflush(stdout);
}
// Source StateCharge::exec picks among other beetles within 300 units that are in
// a pre-charge state. A beetle already in Charge but still unlinked is also a
// valid candidate here so two beetles that acquire sight on the same frame still
// form a pair (the source staggers via its random inactive timer).
BTeki* nearestPartner(BTeki* actor, float radius) {
    const Vector3f pos = actor->getPosition();
    BTeki* best = nullptr;
    float bestSq = radius * radius;
    for (auto& entry : actors) {
        ElecBug& other = entry.second;
        if (!other.self || other.self == actor) continue;
        if (other.partner || other.state == ELEC_DEAD) continue;
        if (other.self->mHealth <= 0.0f) continue;
        if (other.state != ELEC_WAIT && other.state != ELEC_TURN
                && other.state != ELEC_MOVE && other.state != ELEC_CHARGE) continue;
        const float d = distXZ(pos, other.self->getPosition());
        if (d < radius && d * d < bestSq) { bestSq = d * d; best = other.self; }
    }
    return best;
}
// Source startChargeState/startChildChargeState reciprocal assignment.
void linkPair(BTeki* actor, ElecBug& s, BTeki* partner, ElecBug& child) {
    s.partner = partner;
    child.partner = actor;
    s.hasSearched = true;
    child.hasSearched = true;
    child.shockedThisDischarge = false;
    child.immuneLogged = false;
    child.flipped = false;
    enter(child, ELEC_CHILDCHARGE, "charge");
    std::printf("P2_ELECBUG_LINK generator=%u partner=%u\n", genOf(actor), genOf(partner));
    std::printf("P2_ELECBUG_STATE generator=%u state=childcharge\n", genOf(partner));
    std::fflush(stdout);
}
// Source StateCharge::exec faces the pair outward: target = bugPos + (bugPos - partnerPos).
void turnTowardsPair(BTeki* a, ElecBug& s) {
    if (!s.partner) return;
    const Vector3f bugPos = a->getPosition();
    const Vector3f partnerPos = s.partner->getPosition();
    const float dx = bugPos.x - partnerPos.x;
    const float dz = bugPos.z - partnerPos.z;
    if (dx * dx + dz * dz < 1e-6f) return;
    s.heading = std::atan2(dx, dz);
    a->setDirection(s.heading);
}
}

void pc_p2_elecbug_reset() {
    actors.clear();
    clips.clear();
    ready = false;
}
// Fixture observability (mirrors pc_p2_sokkuri/armor): read-only registration
// count/membership so the lifecycle fixture can prove forget clears stale state.
unsigned long pc_p2_elecbug_count() { return (unsigned long)actors.size(); }
bool pc_p2_elecbug_registered(BTeki* actor) { return actors.count(static_cast<PelletView*>(actor)) != 0; }
bool pc_p2_elecbug_suppress_ai(const BTeki* actor) {
    return ready && actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor))) != 0;
}
void pc_p2_elecbug_forget(BTeki* actor) {
    // Lane 06 single-use binding: drop the ordinary-delivery source so a
    // recycled actor address can never inherit source 28. The central
    // pc_p2_forget_teki seam also clears it; this is idempotent.
    pc_randomizer_p2_forget_source(static_cast<PelletView*>(actor));
    ElecBug* s = lookup(actor);
    if (s && s->partner) breakLink(actor, *s);
    actors.erase(static_cast<PelletView*>(actor));
}

float pc_p2_elecbug_param_f(const BTeki* actor, int idx, float fallback) {
    if (!ready || !actors.count(static_cast<PelletView*>(const_cast<BTeki*>(actor)))) return fallback;
    if (idx == TPF_Life) return LIFE;
    if (idx == TPF_LifeRecoverRate) return 0.0f;
    switch (idx) {
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
        return 0.0f;
    default:
        return fallback;
    }
}

bool pc_p2_elecbug_attacked(Teki* teki) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(teki));
    if (it == actors.end()) return false;
    if (it->second.state == ELEC_DEAD) return false;
    if (!it->second.flipped) {
        // Source ElecBug::init enables invulnerability; any attack is swallowed.
        std::printf("P2_ELECBUG_ATTACK_BLOCKED generator=%u source_id=28 invulnerable=1\n",
                    genOf(teki));
        std::fflush(stdout);
        return true;
    }
    // Source StateReverse::init disables invulnerability: the attack lands.
    std::printf("P2_ELECBUG_ATTACK_ACCEPTED generator=%u source_id=28 state=reverse health=%.1f\n",
                genOf(teki), teki->mHealth);
    std::fflush(stdout);
    return false;
}

bool pc_p2_elecbug_pressed(BTeki* teki, Creature* presser) {
    if (!ready) return false;
    ElecBug* s = lookup(teki);
    if (!s) return false;
    if (s->state == ELEC_DEAD || s->state == ELEC_REVERSE) return true;
    // Source ElecBug::pressCallBack: an actively discharging beetle sends Denki
    // to the pressing Pikmin (InteractDenki still excludes Yellow/Bulbmin).
    if (s->state == ELEC_DISCHARGE || s->state == ELEC_CHILDISCHARGE) {
        Piki* piki = (presser && presser->isPiki()) ? static_cast<Piki*>(presser) : nullptr;
        if (piki && piki->isAlive()) {
            const int species = pc_p2_species(piki);
            const int stateBefore = piki->getState();
            // Source pressCallBack dispatches even immune Pikmin. The actual
            // InteractDenki receiver owns Yellow/Bulbmin rejection.
            Vector3f dir(piki->getPosition().x - teki->getPosition().x, 0.0f,
                         piki->getPosition().z - teki->getPosition().z);
            const bool accepted = piki->stimulate(InteractDenki(teki, 1.0f, &dir));
            if (p2_species_immune(species, P2HazardElectric)) {
                std::printf("P2_ELECBUG_PRESS_IMMUNE generator=%u source_id=28 pikmin=%s species=%d "
                            "piki=%p accepted=%d state_before=%d target_state=%d alive=%d\n",
                            genOf(teki), species == P2SpeciesBulbmin ? "bulbmin" : "yellow", species,
                            static_cast<void*>(piki), int(accepted), stateBefore, piki->getState(), int(piki->isAlive()));
            } else {
                std::printf("P2_ELECBUG_PRESS_DENKI generator=%u source_id=28 pikmin=1 piki=%p target=%d accepted=%d "
                            "target_state=%d(%s)\n",
                            genOf(teki), static_cast<void*>(piki), species, int(accepted), piki->getState(),
                            piki->getState() == PIKISTATE_DenkiDying ? "DenkiDying" : "other");
                std::printf("P2_ELECBUG_PRESS_SHOCK generator=%u source_id=28 pikmin=1 color=%s\n",
                            genOf(teki), colorName(piki->mColor));
            }
            std::fflush(stdout);
        }
    }
    if (s->partner) breakLink(teki, *s); // source StateReverse::init finishPartnerAndEffect
    s->flipped = true;
    enter(*s, ELEC_REVERSE, "turn"); // source StateReverse::init startMotion(ELECBUGANIM_Turn)
    std::printf("P2_ELECBUG_FLIP generator=%u source_id=28\n", genOf(teki));
    std::printf("P2_ELECBUG_STATE generator=%u state=reverse\n", genOf(teki));
    std::fflush(stdout);
    return true;
}

static bool flyingPress(BTeki* actor, Piki* piki, const char* callback) {
    if (!ready || !actor || !piki || !piki->isAlive() || piki->getState() != PIKISTATE_Flying
        || !std::isfinite(piki->mVelocity.y) || piki->mVelocity.y >= -0.01f) return false;
    ElecBug* s = lookup(actor);
    if (!s || s->state < ELEC_WAIT || s->state > ELEC_CHILDISCHARGE) return false;
    const char* before = stateName(s->state);
    const int species = pc_p2_species(piki);
    const float velocityY = piki->mVelocity.y;
    if (!actor->stimulate(InteractPress(piki, 0))) return false;
    // This dispatch originates in the real collision event, not proximity.
    std::printf("P2_ELECBUG_CONTACT_DISPATCH generator=%u piki=%p species=%d vy=%.6f "
                "contact=1 enemy_before=%s enemy_after=%s callback=%s\n",
                genOf(actor), static_cast<void*>(piki), species, velocityY, before, stateName(s->state), callback);
    std::fflush(stdout);
    return true;
}

bool pc_p2_elecbug_flying_press(BTeki* actor, Piki* piki) {
    return flyingPress(actor, piki, "flying");
}

bool pc_p2_elecbug_ground_press(Piki* piki) {
    if (!ready || !piki || !piki->isAlive() || piki->getState() != PIKISTATE_Flying
        || !std::isfinite(piki->mVelocity.y) || piki->mVelocity.y >= -0.01f) return false;
    // The P1 movement phase sends ground bounce before creature collisions.
    // Resolve an actual simultaneous beetle intersection before losing Flying;
    // terrain contact alone cannot press an enemy.
    for (auto& entry : actors) {
        BTeki* actor = entry.second.self;
        if (!actor || !actor->isAlive() || entry.second.state < ELEC_WAIT
            || entry.second.state > ELEC_CHILDISCHARGE || !actor->mCollInfo
            || !actor->mCollInfo->hasInfo()) continue;
        Vector3f ignored;
        if (actor->mCollInfo->checkCollision(piki, ignored)
            && flyingPress(actor, piki, "ground_bounce")) return true;
    }
    return false;
}

bool pc_p2_elecbug_clip(const BTeki* actor, const char*& name, float& phase) {
    if (!ready) return false;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return false;
    name = it->second.clip.c_str();
    phase = it->second.phase;
    return true;
}

// Read-only state probe for the private runtime fixture. It lets an injected
// main schedule the press/discharge gates at the exact source state; it never
// mutates behavior and returns nullptr for unregistered actors.
const char* pc_p2_elecbug_state_name(const BTeki* actor) {
    if (!ready) return nullptr;
    auto it = actors.find(static_cast<PelletView*>(const_cast<BTeki*>(actor)));
    if (it == actors.end()) return nullptr;
    return stateName(it->second.state);
}

// Natural press adaptation (#165, inst-bugs #871): the source
// ElecBug::pressCallBack fires when a thrown Pikmin lands on the beetle
// (PikiFlyingState/PikiHipDropState collision, velocity.y<0), for ANY Pikmin
// color. Flying collision/ground-bounce hooks now dispatch before grounding;
// this inherited fallback detects a descending Pikmin colliding with a registered
// ElecBug once per flip (REVERSE/DEAD short-circuit) and delegates to
// pc_p2_elecbug_pressed. Purple hipdrops satisfy the same probe; the color is
// logged for evidence. Use the engine collision-part query, not an XZ radius:
// proximity alone let a descending Pikmin far above/below the beetle flip it
// before contact (#1159). The query supplies geometry only; it does not apply
// its returned push vector or change ordinary collision response.
void pc_p2_elecbug_check_landing_press(BTeki* actor) {
    if (!ready || !pikiMgr) return;
    ElecBug* s = lookup(actor);
    // Source pressCallBack only reacts in Wait..ChildDischarge: not Reverse, not
    // Return (recover), not Dead. A Pikmin idling on the recovering beetle must
    // not re-flip it the moment it stands up.
    if (!s || s->state == ELEC_DEAD || s->state == ELEC_REVERSE || s->state == ELEC_RETURN) return;

    if (!actor->mCollInfo || !actor->mCollInfo->hasInfo()) return;
    Iterator it(pikiMgr);
    CI_LOOP(it) {
        Piki* p = static_cast<Piki*>(*it);
        if (!p || !p->isAlive()) continue;
        if (p->mVelocity.y >= -0.01f) continue;  // ascending / grounded
        Vector3f pushVector;
        if (!actor->mCollInfo->checkCollision(p, pushVector)) continue;
        std::printf("P2_ELECBUG_NATURAL_PRESS generator=%u species=%d source_id=28 state=%s\n",
                    genOf(actor), pc_p2_species(p), stateName(s->state));
        std::fflush(stdout);
        // Read-only dispatch evidence for the ordinary-throw fixture (#1164).
        // Snapshot before the receiver, which may electrocute the presser.
        const char* enemyBefore = stateName(s->state);
        const int presserSpecies = pc_p2_species(p);
        const float presserVelocityY = p->mVelocity.y;
        pc_p2_elecbug_pressed(actor, p);
        std::printf("P2_ELECBUG_CONTACT_DISPATCH generator=%u piki=%p species=%d vy=%.6f "
                    "contact=1 enemy_before=%s enemy_after=%s\n",
                    genOf(actor), static_cast<void*>(p), presserSpecies, presserVelocityY,
                    enemyBefore, stateName(s->state));
        std::fflush(stdout);
        break;
    }
}

void pc_p2_elecbug_setup() {
    pc_p2_elecbug_reset();
    if (!tekiMgr) return;

    std::ifstream bank("p2-ground-bank.txt");
    if (bank) {
        std::string token;
        if (bank >> token && token == "P2_GROUND_BANK_1") {
            while (bank >> token) {
                if (token == "species") {
                    std::string species, id;
                    bank >> species >> id;
                } else if (token == "clip") {
                    std::string species, name, events, marker, status;
                    long long frames = 0;
                    int poses = 0;
                    bank >> species >> name >> frames >> events >> marker >> poses >> status;
                    if (species == "ElecBug") {
                        Clip clip;
                        clip.name = name;
                        clip.duration = frames > 0 ? float(frames) / 30.0f : 1.0f;
                        clip.loop = (name == "move" || name == "wait");
                        clip.frames = int(frames);
                        clip.keys = p2elecbug::parseKeys(int(frames), events);
                        clips[name] = clip;
                    }
                } else if (token == "frames") {
                    // P2_BANK_FRAMES_1 trailer (#895): per-pose source frames,
                    // consumed by the batch draw paths; skip its list token here.
                    std::string framesList;
                    bank >> framesList;
                } else {
                    break;
                }
            }
        }
    }

    std::ifstream in("p2-ground-actors.txt");
    if (!in) return;
    std::string header;
    int count = 0;
    if (!(in >> header >> count) || header != "P2_GROUND_ACTORS_1" || count < 1) return;
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(in >> generator >> species)) return;
        if (species == "ElecBug") wanted[unsigned(generator)] = species;
    }
    // inst-bugs lane (#871): in bridge campaigns the seed owns the binding,
    // so the filed ids are placeholders replaced from pc_p2_campaign_ids(28)
    // (mirrors pc_p2_sokkuri_setup). Actors match by campaign token: scene
    // members may carry no mGenerator, exactly like the batch-2 bind.
    const bool bridge = pc_randomizer_p2_bridge();
    if (bridge) {
        wanted.clear();
        for (unsigned id : pc_p2_campaign_ids(28)) wanted[id] = "ElecBug";
    }
    if (wanted.empty()) return;

    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor) continue;
        const unsigned token = pc_p2_campaign_token(actor);
        const unsigned key =
            bridge ? token : (actor->mGenerator ? actor->mGenerator->_70 : 0u);
        if (!bridge && key == 0u) continue;
        auto match = wanted.find(key);
        if (match == wanted.end()) continue;
        if (actor->mTekiType != TEKI_Chappy) {
            std::printf("P2_ELECBUG_ERROR native_type generator=%u\n", key);
            if (pc_p2_setup_skip(bridge, "ElecBug", "actor_type_mismatch")) return;
            std::abort();
        }
        ElecBug& s = actors[static_cast<PelletView*>(actor)];
        s.self = actor;
        s.home = actor->getPosition();
        s.heading = actor->getDirection();
        actor->mHealth = LIFE;
        s.inactiveTimer = inactiveReset(); // source onInit randWeightFloat(10)
        enter(s, ELEC_TURN, "move");       // source onInit: mFsm->start(ELECBUG_Turn)
        // Ordinary-delivery bridge (lane 06 contract, #585): bind source 28 to
        // this live actor so GoalItem::suckMe can grant onion:p2:28 exactly once
        // through pc_randomizer_p2_corpse_delivered. Rejected (unbindable id)
        // is logged by the callee, never fatal. Single-use: consumed on
        // delivery and cleared on forget/recycle.
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(actor), 28, key);
        std::printf("P2_ELECBUG_DELIVERY_BIND generator=%u source_id=28\n", key);
        std::printf("P2_ELECBUG_BIND generator=%u source_id=28 visual_only=0\n", key);
        const Vector3f pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=ElecBug native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native "
                    "source_FSM=implemented attack=discharge_receiver\n",
                    key, pos.x, pos.y, pos.z, actor->mHealth, LIFE);
        found.insert(key);
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_ELECBUG_ERROR missing_actor wanted=%zu found=%zu\n", wanted.size(), found.size());
        if (pc_p2_setup_skip(bridge, "ElecBug", "actor_roster_incomplete")) return;
        std::abort();
    }
    ready = true;
}

void pc_p2_elecbug_update(BTeki* actor) {
    if (!ready) return;
    auto it = actors.find(static_cast<PelletView*>(actor));
    if (it == actors.end()) return;
    ElecBug& s = it->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const Vector3f pos = actor->getPosition();
    const unsigned generator = genOf(actor);

    // The P1 TAI damage reaction lives in the suppressed host strategy, so
    // the P2 FSM drains queued Pikmin damage itself (frog pattern). The
    // pre-flip invulnerability gate (pc_p2_elecbug_attacked) still swallows
    // attack interactions; this only applies admitted damage.
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();

    // TEST-ONLY evidence hook (inert unless BOTH the autoplay gate and
    // PIKMIN_P2_ELECBUG_TEST_PRESS=<seconds> are set; never in the owner launcher):
    // flips each beetle once, N seconds after bind, from Wait/Turn/Move, so a
    // headless bot run can show Reverse -> recover -> normal behaviour.
    if (!s.testPressed) {
        const char* ap = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY");
        const char* tp = std::getenv("PIKMIN_P2_ELECBUG_TEST_PRESS");
        s.testClock += dt;
        if (ap && ap[0] && ap[0] != '0' && tp && tp[0] && s.testClock >= float(std::atof(tp)) &&
            (s.state == ELEC_WAIT || s.state == ELEC_TURN || s.state == ELEC_MOVE)) {
            s.testPressed = true;
            std::printf("P2_ELECBUG_TEST_PRESS generator=%u source_id=28 state=%s\n", generator,
                        stateName(s.state));
            std::fflush(stdout);
            pc_p2_elecbug_pressed(actor, nullptr);
        }
    }

    // TEST-ONLY (autoplay gate + PIKMIN_P2_ELECBUG_TEST_CHARGE=<seconds>): every N seconds
    // the inactivity timer is pushed past the source's 15 s charge threshold, so pairs
    // charge, link and discharge within a bot run. The FSM itself is untouched.
    {
        const char* ap = std::getenv("PIKMIN_RANDOMIZER_AUTOPLAY");
        const char* tc = std::getenv("PIKMIN_P2_ELECBUG_TEST_CHARGE");
        if (ap && ap[0] && ap[0] != '0' && tc && tc[0]) {
            s.testChargeClock += dt;
            // staggered per beetle so one of a pair is still wandering when the other charges (source partner rule)
            if (s.testChargeClock >= float(std::atof(tc)) * (1.0f + float(generator % 7) * 0.45f)) {
                s.testChargeClock = 0.0f;
                if (s.inactiveTimer < 16.0f) s.inactiveTimer = 16.0f;
            }
        }
    }

    // Natural press (Purple landing) -> source StateReverse, before the health
    // bookkeeping so a same-frame flip still reports the pre-flip health.
    pc_p2_elecbug_check_landing_press(actor);

    // Reversed beetles accept InteractAttack damage; every non-lethal drop is the
    // runtime proof that invulnerability is disabled while flipped.
    if (actor->mHealth < s.lastHealth && actor->mHealth > 0.0f) {
        std::printf("P2_ELECBUG_HIT generator=%u source_id=28 health=%.1f\n",
                    generator, actor->mHealth);
        std::fflush(stdout);
    }
    s.lastHealth = actor->mHealth;

    if (actor->mHealth <= 0.0f && s.state != ELEC_DEAD) {
        if (s.partner) breakLink(actor, s);
        if (!s.deadLogged) {
            std::printf("P2_ELECBUG_DEAD generator=%u source_id=28 health=0\n", generator);
            std::fflush(stdout);
            s.deadLogged = true;
        }
        enter(s, ELEC_DEAD, "dead");
    }

    // Partner loss (removed from the arena, dead, or health-0) breaks the link.
    if (s.state != ELEC_DEAD && s.partner) {
        ElecBug* other = lookup(s.partner);
        if (!other || !other->self || other->state == ELEC_DEAD || other->self->mHealth <= 0.0f) {
            breakLink(actor, s);
        }
    }

    s.stateTime += dt;
    s.inactiveTimer += dt; // source Obj::doUpdate: mInactiveTimer += deltaTime
    switch (s.state) {
    case ELEC_WAIT:
        stop(actor);
        if (s.stateTime > WAIT_TIME) {
            // Source StateWait: after WaitTime, StateTurn (move clip).
            std::printf("P2_ELECBUG_STATE generator=%u state=turn\n", generator);
            enter(s, ELEC_TURN, "move");
        }
        break;
    case ELEC_TURN:
        stop(actor);
        if (s.stateTime > TURN_TIME) {
            // Source StateTurn END: inactive > 15 -> Charge, else Move. Charge is
            // never entered from player sight (that port trigger caused the
            // charge -> recover -> charge loop).
            if (p2elecbug::chargeDue(s.inactiveTimer)) {
                std::printf("P2_ELECBUG_STATE generator=%u state=charge\n", generator);
                s.hasSearched = false;
                enter(s, ELEC_CHARGE, "charge");
            } else {
                std::printf("P2_ELECBUG_STATE generator=%u state=move\n", generator);
                enter(s, ELEC_MOVE, "move");
            }
        }
        break;
    case ELEC_MOVE:
        s.heading = wrapPi(s.heading + 0.4f * dt);
        wander(actor, s);
        if (s.stateTime > WANDER_TIME) {
            // Source StateMove END: inactive > 15 -> Charge, else Wait.
            if (p2elecbug::chargeDue(s.inactiveTimer)) {
                std::printf("P2_ELECBUG_STATE generator=%u state=charge\n", generator);
                s.hasSearched = false;
                enter(s, ELEC_CHARGE, "charge");
            } else {
                std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
                enter(s, ELEC_WAIT, "wait");
            }
        }
        break;
    case ELEC_CHARGE: {
        stop(actor);
        if (!s.hasSearched && s.stateTime >= CHARGE_SEARCH_DELAY) {
            s.hasSearched = true;
            BTeki* partner = nearestPartner(actor, PAIR_RADIUS);
            ElecBug* child = partner ? lookup(partner) : nullptr;
            if (child) linkPair(actor, s, partner, *child);
        }
        if (s.partner) turnTowardsPair(actor, s);
        if (s.stateTime >= CHARGE_TIME) {
            if (s.partner) {
                s.shockedThisDischarge = false;
                s.immuneLogged = false;
                std::printf("P2_ELECBUG_STATE generator=%u state=discharge\n", generator);
                std::printf("P2_ELECBUG_DISCHARGE generator=%u source_id=28 duration=%.3f state=charge\n",
                            generator, DISCHARGE_TIME);
                std::fflush(stdout);
                enter(s, ELEC_DISCHARGE, "discharge");
            } else {
                // Source StateCharge/StateChildCharge without a partner -> StateTurn.
                std::printf("P2_ELECBUG_STATE generator=%u state=turn\n", generator);
                s.inactiveTimer = inactiveReset();
                enter(s, ELEC_TURN, "move");
            }
        }
        break;
    }
    case ELEC_CHILDCHARGE: {
        stop(actor);
        if (s.partner) turnTowardsPair(actor, s);
        if (s.stateTime >= CHILD_CHARGE_TIME) {
            if (s.partner) {
                s.shockedThisDischarge = false;
                s.immuneLogged = false;
                std::printf("P2_ELECBUG_STATE generator=%u state=childdischarge\n", generator);
                std::printf("P2_ELECBUG_DISCHARGE generator=%u source_id=28 duration=%.3f state=child\n",
                            generator, DISCHARGE_TIME);
                std::fflush(stdout);
                enter(s, ELEC_CHILDISCHARGE, "discharge");
            } else {
                // Source StateCharge/StateChildCharge without a partner -> StateTurn.
                std::printf("P2_ELECBUG_STATE generator=%u state=turn\n", generator);
                s.inactiveTimer = inactiveReset();
                enter(s, ELEC_TURN, "move");
            }
        }
        break;
    }
    case ELEC_DISCHARGE: {
        stop(actor);
        if (!s.partner) {
            std::printf("P2_ELECBUG_STATE generator=%u state=turn\n", generator);
            s.inactiveTimer = inactiveReset();
            enter(s, ELEC_TURN, "move");
            break;
        }
        // Source StateDischarge: checkInteract(partner) every frame (the arc is lit
        // from the KEYEVENT_2 at frame 8). Every live Pikmin/Navi inside the band
        // between the two beetles gets InteractDenki; Yellow/Bulbmin are rejected
        // by the receiver. Each creature is logged once per discharge.
        if (s.stateTime >= p2elecbug::kArcStart) {
            if (!s.arcLogged) {
                s.arcLogged = true;
                std::printf("P2_ELECBUG_ARC generator=%u partner=%u length=%.1f\n", generator,
                            genOf(s.partner), distXZ(pos, s.partner->getPosition()));
                std::fflush(stdout);
            }
            sweepArc(actor, s, generator);
        }
        if (s.stateTime >= DISCHARGE_TIME) {
            breakLink(actor, s);
            std::printf("P2_ELECBUG_STATE generator=%u state=turn\n", generator);
            s.inactiveTimer = inactiveReset();
            enter(s, ELEC_TURN, "move");
        }
        break;
    }
    case ELEC_CHILDISCHARGE: {
        stop(actor);
        if (!s.partner) {
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            s.inactiveTimer = inactiveReset();
            enter(s, ELEC_WAIT, "wait");
            break;
        }
        if (s.stateTime >= DISCHARGE_TIME) {
            breakLink(actor, s);
            std::printf("P2_ELECBUG_STATE generator=%u state=wait\n", generator);
            s.inactiveTimer = inactiveReset();
            enter(s, ELEC_WAIT, "wait");
        }
        break;
    }
    case ELEC_RETURN:
        // Source StateReturn plays the recover clip once, then StateTurn. The
        // converted recover clip has no END key, so the exit is its length
        // (p2elecbug::recoverDone), not a fixed port timer.
        stop(actor);
        if (p2elecbug::recoverDone(s.stateTime, recoverFrames())) {
            std::printf("P2_ELECBUG_RECOVER_DONE generator=%u source_id=28 t=%.2f\n", generator, s.stateTime);
            std::printf("P2_ELECBUG_STATE generator=%u state=turn\n", generator);
            std::fflush(stdout);
            enter(s, ELEC_TURN, "move");
        }
        break;
    case ELEC_REVERSE: {
        // Source StateReverse: Turn clip (flip, then belly-up loop); after FlipTime
        // the clip finishes on its END key, then StateReturn (recover clip).
        stop(actor);
        auto turnIt = clips.find("turn");
        const bool clipDone = turnIt == clips.end()
            ? s.stateTime >= FLIP_TIME
            : p2elecbug::reverseClip(turnIt->second.keys, s.stateTime, FLIP_TIME).finished;
        if (clipDone) {
            s.flipped = false;
            std::printf("P2_ELECBUG_RECOVER generator=%u source_id=28 t=%.2f\n", generator, s.stateTime);
            std::printf("P2_ELECBUG_STATE generator=%u state=return\n", generator);
            std::fflush(stdout);
            enter(s, ELEC_RETURN, "recover");
        }
        break;
    }
    case ELEC_DEAD:
        stop(actor);
        // dieSoon() only runs inside the suppressed host doAI; finalize the
        // corpse outside doAI once the dead clip completes (frog pattern).
        if (!s.escaped && s.stateTime >= clipDuration("dead")) {
            s.escaped = true;
            actor->pcEscapeNow();
        }
        break;
    default:
        break;
    }
    fxUpdate(actor, s, generator);
    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        std::printf("P2_ELECBUG_POS generator=%u state=%s clip=%s phase=%.2f x=%.2f z=%.2f\n",
                    generator, stateName(s.state), s.clip.c_str(), s.phase, pos.x, pos.z);
        std::fflush(stdout);
    }
}

