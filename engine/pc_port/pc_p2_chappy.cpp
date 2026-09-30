#include "pc_p2_chappy.h"
#include "pc_p2_chappy_policy.h"
#include "pc_p2_chappy_fsm.h"
#include "pc_p2_chappy_mouth.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_enemy.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_p2_sheargrub.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_setup_failsafe.h"
#include "pc_p2_white.h"
#include "pc_randomizer.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "gameflow.h"
#include "Graphics.h"
#include "Camera.h"
#include "PaniAnimator.h"
#include "Interactions.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "pc_p2_navi_select.h"
#include "Stickers.h"
#include "system.h"
#include <algorithm>
#include <fstream>
#include <map>
#include <set>
#include <string>
#include <vector>
#include <cmath>
#include <cstdio>
#include <cstdlib>

namespace {
struct ClipDef {
    int frames = 0;
    int poses = 0;
};
struct SpeciesBank {
    unsigned source = 0;
    std::string species;
    std::map<std::string, ClipDef> clips;
};
std::map<std::string, SpeciesBank> banks; // enum -> bank (from p2-chappy-bank.txt)
std::map<std::string, std::vector<Shape*>> shapes; // "Enum|clip" -> poses
std::map<PelletView*, const p2chappy::SpeciesParams*> actors; // view -> species
std::map<PelletView*, std::string> lastClip;
std::map<PelletView*, unsigned> corpseGenerators; // delivered-corpse lookup (preview path)
p2chappy::Health health;
bool bankLoaded = false;
std::set<PelletView*> drawnLive, drawnCorpse;
size_t bankBytes = 0;

// Own-identity runtime FSM (inst2-chappy, #871). The P2 FSM decides every
// tick: movement/targeting/attacks are driven here via inputDrive/mVelocity/
// setDirection plus source animation-key attacks (bite/eat/swallow, flick,
// fire aura, warcry, burrow, rebirth, parent-follow). The P1 host AI is
// suppressed (doAI early-return + host param blinding) so this is exclusive.
constexpr float PI_F = 3.14159265f;
constexpr float TURN_RATE = 2.5f; // port adaptation (host drive rate)
constexpr float TERRITORY = 300.0f; // port adaptation (source mTerritoryRadius)
constexpr float HOME_RADIUS = 50.0f; // port adaptation (source mHomeRadius)
constexpr int FLICK_STUCK_MIN = 3; // source shake-off graduation first tier
constexpr float LOST_REBIRTH_S = 10.0f; // Kuma proper fp12 respawn (adaptation)
constexpr float KING_TURN_MAX_S = 4.0f; // King Turn safety cap (source turns until fp07; adaptation)
constexpr float KING_GATE_LOG_S = 1.0f; // P2_CHAPPY_KING_GATE rate limit
constexpr float KING_HIDEWAIT_S = 200.0f / 30.0f; // King ip02 appearance (adaptation)
constexpr float TURN_DURATION_S = 25.0f / 30.0f; // waitact1 (adaptation)
constexpr float FLICK_DURATION_S = 80.0f / 30.0f; // flick (adaptation)

struct ChappyFsm {
    const p2chappy::SpeciesParams* spec = nullptr;
    p2chappyfsm::Family family = p2chappyfsm::FAMILY_ADULT;
    int state = 7;
    float stateTime = 0.0f;
    float heading = 0.0f;
    Vector3f home;
    Vector3f wander;
    bool wanderValid = false;
    unsigned rng = 1;
    bool deadLogged = false;
    bool escaped = false;
    bool attackFired = false;
    bool swallowFired = false;
    bool flickFired = false;
    bool auraLogged = false;
    bool birthLogged = false;
    bool healthAsserted = false;
    bool pressed = false; // kumako Press latch
    std::string clip = "wait1";
    float phase = 0.0f;
    float logTimer = 0.0f;
    float auraTimer = 0.0f;
    float lastHealth = 0.0f;
    // #884 source mouth slots (pc_p2_chappy_mouth.h): the Pikmin this actor
    // stuck into each P2 slot. Only compared against the live mouth-sticker
    // set to derive occupancy; never dereferenced.
    Creature* mouth[p2chappymouth::MaxSlots] = {};
    bool mouthLogged = false;
    int lastEatFrame = -1;   // King eat window: last evaluated attack frame
    int eatenThisAttack = 0; // accepted captures in the current attack
    // King eat-window aggregates for the per-window P2_CHAPPY_BITE line.
    int winEligible = 0;
    int winFreeBefore = -1;
    int winRefusedNoHost = 0;
    int winNaviHits = 0;
    bool winNearestBehind = false;
    bool winLegacyBehind = false;
    // #884 runtime diagnosis: per-bite / per-window geometry aggregates and the
    // target that started the attack (logged on P2_CHAPPY_BITE / EAT_NONE).
    p2chappymouth::WindowDiag winDiag;
    float winHeadingDeg = 0.0f;
    float winDrawYawDeg = 0.0f;
    char tickTargetKind = '-'; // this tick: n navi, p Pikmin, s Pikmin stuck to self, - none
    float tickTargetDist = -1.0f;
    float tickTargetAngDeg = 0.0f;
    float tickTargetDist3d = -1.0f; // 3D, the separation the fp20 range gate tests
    char atkTargetKind = '-'; // latched when the attack state is entered
    float atkTargetDist = -1.0f;
    float atkTargetAngDeg = 0.0f;
    float atkTargetDist3d = -1.0f;
    // #884 round 2: King source pursuit (pc_p2_chappy_mouth.h king::Walker)
    // and the rate-limited gate-refusal diagnostic.
    p2chappymouth::king::Walker walker;
    p2chappymouth::king::Census kingCensus;
    bool kingSearched = false; // searchTarget ran this tick (not delayed / out of territory)
    float kingGateLogS = 0.0f;
    // #884 round 3: source EnemyBase::mFlickTimer for the King (checkFlick
    // captain proximity + damageCallBack flickSpeed), with diagnostics.
    float kingFlickTimer = 0.0f;
    int kingFlickHits = 0; // hits the source damageCallBack accepts since bind (each +1.0)
    int kingNaviNear = 0;  // captains inside fp06 at the last checkFlick
    // #884 round 4: source damageCallBack acceptance (king::damageAccept).
    int kingHitsStuck = 0;   // collision-part hits from stuck attackers (x1.0)
    int kingHitsLow = 0;     // partless hits low within 40 XZ (x0.2)
    int kingHitsRefused = 0; // refused: no damage, no flick
};
std::map<PelletView*, ChappyFsm> fsms;

bool claimedElsewhere(BTeki* actor)
{
    PelletView* view = static_cast<PelletView*>(actor);
    return pc_p2_enemy_name(view) || pc_p2_kochappy_name(view) || pc_p2_dwarf_orange_name(view)
           || pc_p2_sheargrub_name(view) || pc_p2_sokkuri_registered(actor);
}

float wrapPi(float a)
{
    while (a > PI_F) a -= 2.0f * PI_F;
    while (a < -PI_F) a += 2.0f * PI_F;
    return a;
}

float distXZ(const Vector3f& a, const Vector3f& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}

unsigned nextRand(ChappyFsm& s)
{
    s.rng = s.rng * 1664525u + 1013904223u;
    return s.rng >> 8;
}

float rand01(ChappyFsm& s) { return float(nextRand(s) & 0xffff) / 65535.0f; }

void stop(BTeki* a)
{
    a->inputDrive(Vector3f(0.0f, 0.0f, 0.0f));
    a->mVelocity.x = 0.0f;
    a->mVelocity.z = 0.0f;
}

bool turnTo(BTeki* a, ChappyFsm& s, const Vector3f& target, float dt, float tolerance)
{
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    return std::fabs(wrapPi(desired - s.heading)) <= tolerance;
}

void walkTo(BTeki* a, ChappyFsm& s, const Vector3f& target, float dt, float speed)
{
    const Vector3f pos = a->getPosition();
    const float desired = std::atan2(target.x - pos.x, target.z - pos.z);
    const float maxTurn = TURN_RATE * dt;
    float diff = wrapPi(desired - s.heading);
    if (diff > maxTurn) diff = maxTurn;
    if (diff < -maxTurn) diff = -maxTurn;
    s.heading = wrapPi(s.heading + diff);
    a->setDirection(s.heading);
    const Vector3f drive(std::sin(s.heading) * speed, 0.0f, std::cos(s.heading) * speed);
    a->inputDrive(drive);
    a->mVelocity.set(drive);
}

Creature* nearestTarget(const Vector3f& pos, float sight)
{
    Creature* best = nullptr;
    float bestSq = sight * sight;
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (!n->isAlive()) continue;
            const Vector3f p = n->getPosition();
            const float dx = p.x - pos.x, dz = p.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = n; }
        }
    }
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it)
        {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            const Vector3f q = p->getPosition();
            const float dx = q.x - pos.x, dz = q.z - pos.z;
            const float d = dx * dx + dz * dz;
            if (d < bestSq) { bestSq = d; best = p; }
        }
    }
    return best;
}

p2chappymouth::Vec3 mouthVec(const Vector3f& v)
{
    return p2chappymouth::Vec3{v.x, v.y, v.z};
}

// Source KingChappy::Obj::searchTarget (kingChappy.cpp:1131-1178) through
// p2chappymouth::king::selectTarget: the captain in the fp14/fp15 search cone,
// else a nearer searchable Pikmin (Piki::isSearchable: alive, not in a mouth;
// port adds drawn and not a buried sprout) in the +-50 band and outside the
// fp06 invisible range.
Creature* kingSearchTarget(BTeki* actor, ChappyFsm& s)
{
    const p2chappymouth::Vec3 apos = mouthVec(actor->getPosition());
    // Source EnemyFunc::getNearestNavi (kingChappy.cpp:1143-1144): the nearest
    // alive captain inside the search cone/distance, then Pikmin compared
    // against its distance. Probe each captain alone through selectTarget
    // (-2 = accepted captain) and keep the XZ-nearest in index order.
    Navi* navi = nullptr;
    p2chappymouth::Vec3 naviPos{};
    float naviSq = 0.0f;
    for (Navi* n : pc_p2_navis()) {
        if (!n->isAlive()) continue;
        const p2chappymouth::Vec3 np = mouthVec(n->getPosition());
        if (p2chappymouth::king::selectTarget(apos, s.heading, &np, nullptr, 0) != -2) continue;
        const float d = p2chappymouth::king::sqrXZ(np, apos);
        if (!navi || d < naviSq) { navi = n; naviPos = np; naviSq = d; }
    }
    std::vector<Piki*> pikis;
    std::vector<p2chappymouth::king::Candidate> cands;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it)
        {
            Piki* p = static_cast<Piki*>(*it);
            if (!p) continue;
            pikis.push_back(p);
            p2chappymouth::king::Candidate c{
                mouthVec(p->getPosition()),
                p->isAlive() && p->isVisible() && !p->isBuried() && !p->isStickToMouth()};
            c.latched = p->getStickObject() == actor && !p->isStickToMouth();
            cands.push_back(c);
        }
    }
    const int pick = p2chappymouth::king::selectTarget(apos, s.heading, navi ? &naviPos : nullptr, cands.data(),
                                                       (int)cands.size());
    s.kingCensus = p2chappymouth::king::census(apos, s.heading, cands.data(), (int)cands.size(),
                                               p2chappymouth::profileForSource(s.spec->source));
    if (pick == -2) return navi;
    if (pick >= 0) return pikis[pick];
    return nullptr;
}

int stuckPikminCount(Creature* c)
{
    int n = 0;
    for (Creature* s = c->mStickListHead; s; s = s->mNextSticker) {
        if (!s || !s->isPiki() || !s->isAlive()) continue;
        ++n;
    }
    return n;
}

bool attackable(const ChappyFsm& s, const Vector3f& pos, const Creature* target)
{
    if (!target) return false;
    const Vector3f tp = target->getPosition();
    if (distXZ(tp, pos) >= s.spec->attackRange) return false;
    const float ang = std::fabs(wrapPi(std::atan2(tp.x - pos.x, tp.z - pos.z) - s.heading));
    return ang <= s.spec->attackAngle * PI_F / 180.0f;
}

// KumaKo parent-follow: nearest live Kuma-family (35/67) FSM actor.
bool parentNear(const BTeki* self, const Vector3f& pos, Vector3f& parentPos)
{
    float bestSq = -1.0f;
    bool found = false;
    for (const auto& kv : fsms) {
        if (kv.second.family != p2chappyfsm::FAMILY_KUMA) continue;
        const BTeki* other = static_cast<const BTeki*>(static_cast<const void*>(kv.first));
        if (other == self) continue;
        const Vector3f q = kv.second.home;
        (void)q;
    }
    // Scan live actors for the nearest Kuma-family home within sight.
    for (const auto& kv : fsms) {
        if (kv.second.family != p2chappyfsm::FAMILY_KUMA) continue;
        if (kv.first == static_cast<PelletView*>(const_cast<BTeki*>(self))) continue;
        // Use the parent's current home as the follow anchor (stable).
        const float dx = kv.second.home.x - pos.x, dz = kv.second.home.z - pos.z;
        const float d = dx * dx + dz * dz;
        if (!found || d < bestSq) { bestSq = d; parentPos = kv.second.home; found = true; }
    }
    if (!found) return false;
    const float sight = 500.0f;
    return bestSq <= sight * sight;
}

int clipFrames(const std::string& species, const std::string& clip)
{
    auto b = banks.find(species);
    if (b == banks.end()) return 30;
    auto c = b->second.clips.find(clip);
    if (c == b->second.clips.end()) return 30;
    return c->second.frames > 0 ? c->second.frames : 30;
}

float clipDuration(const std::string& species, const std::string& clip)
{
    return float(clipFrames(species, clip)) / 30.0f;
}

// Resolve an FSM state's preferred bank clip, falling back through the
// family's actual staged stems so a missing stem never aborts the draw.
const char* clipForState(const SpeciesBank& bank, p2chappyfsm::Family family, int state)
{
    const char* prefs[6] = {nullptr, nullptr, nullptr, nullptr, nullptr, nullptr};
    int n = 0;
    auto push = [&](const char* c) { if (n < 6) prefs[n++] = c; };
    if (family == p2chappyfsm::FAMILY_ADULT) {
        switch (state) {
        case p2chappy::ADULT_DEAD: push("dead"); push("dead1"); push("pdead1"); break;
        case p2chappy::ADULT_ATTACK: push("attack"); push("attack1"); push("attack2"); break;
        case p2chappy::ADULT_FLICK: push("flick"); break;
        case p2chappy::ADULT_WALK: case p2chappy::ADULT_GO_HOME:
            push("move1"); push("move"); push("walk"); push("run1"); break;
        case p2chappy::ADULT_TURN: case p2chappy::ADULT_TURN_TO_HOME:
            push("waitact1"); push("wait1"); break;
        case p2chappy::ADULT_SLEEP: push("wait2"); push("sleep"); push("wait1"); break;
        default: push("wait1"); push("wait2"); break;
        }
    } else if (family == p2chappyfsm::FAMILY_KUMA) {
        switch (state) {
        case 0: push("dead"); push("dead1"); break;
        case 3: push("attack"); push("attack1"); break;
        case 4: push("flick"); break;
        case 7: case 8: push("move1"); push("move"); break;
        case 5: case 6: push("waitact1"); push("wait1"); break;
        case 2: push("wait2"); push("wait1"); break;
        case 1: push("waitact2"); push("wait2"); push("wait1"); break;
        default: push("wait1"); break;
        }
    } else if (family == p2chappyfsm::FAMILY_KUMAKO) {
        switch (state) {
        case 0: push("dead"); push("dead1"); break;
        case 1: push("press"); push("waitact2"); push("wait1"); break;
        case 3: push("attack"); push("attack1"); break;
        case 4: push("flick"); break;
        case 5: case 6: push("move1"); push("move"); break;
        case 2: default: push("wait1"); push("wait2"); break;
        }
    } else { // KING
        switch (state) {
        case 2: push("dead"); break;
        case 1: push("attack"); break;
        case 3: push("flick"); break;
        case 0: push("move1"); push("move"); break;
        case 6: push("waitact1"); push("wait1"); break;
        case 4: push("cry"); push("waitact2"); push("wait1"); break; // KINGANIM_WarCry = 'cry'
        case 5: push("waitact1"); push("wait1"); break;
        case 8: case 9: push("wait2"); push("wait1"); break;
        case 10: push("waitact1"); push("wait1"); break;
        case 11: push("waitact2"); push("wait1"); break;
        case 7: push("attack"); push("waitact2"); break;
        case 12: push("type1"); push("attack"); push("waitact2"); break; // KINGANIM_Swallow
        default: push("wait1"); break;
        }
    }
    for (int i = 0; i < n; ++i) {
        if (prefs[i] && bank.clips.count(prefs[i])) return bank.clips.find(prefs[i])->first.c_str();
    }
    // Final fallback: any staged wait/dead stem, else the first clip.
    static const char* const fallbacks[] = {"wait1", "wait", "wait2", "dead", nullptr};
    for (const char* const* f = fallbacks; *f; ++f) {
        if (bank.clips.count(*f)) return bank.clips.find(*f)->first.c_str();
    }
    return bank.clips.empty() ? nullptr : bank.clips.begin()->first.c_str();
}

const char* fsmStateName(p2chappyfsm::Family family, int state)
{
    if (family == p2chappyfsm::FAMILY_ADULT) {
        switch (state) {
        case p2chappy::ADULT_TURN: return "turn";
        case p2chappy::ADULT_DEAD: return "dead";
        case p2chappy::ADULT_FLICK: return "flick";
        case p2chappy::ADULT_WALK: return "walk";
        case p2chappy::ADULT_ATTACK: return "attack";
        case p2chappy::ADULT_TURN_TO_HOME: return "turntohome";
        case p2chappy::ADULT_GO_HOME: return "gohome";
        case p2chappy::ADULT_SLEEP: return "sleep";
        default: return "null";
        }
    }
    if (family == p2chappyfsm::FAMILY_KUMA) {
        switch (state) {
        case 0: return "dead"; case 1: return "rebirth"; case 2: return "lost";
        case 3: return "attack"; case 4: return "flick"; case 5: return "turn";
        case 6: return "turnpath"; case 7: return "walk"; case 8: return "walkpath";
        default: return "null";
        }
    }
    if (family == p2chappyfsm::FAMILY_KUMAKO) {
        switch (state) {
        case 0: return "dead"; case 1: return "press"; case 2: return "wait";
        case 3: return "attack"; case 4: return "flick"; case 5: return "walk";
        case 6: return "walkpath"; default: return "null";
        }
    }
    switch (state) {
    case 0: return "walk"; case 1: return "attack"; case 2: return "dead";
    case 3: return "flick"; case 4: return "warcry"; case 5: return "damage";
    case 6: return "turn"; case 7: return "eat"; case 8: return "hide";
    case 9: return "hidewait"; case 10: return "appear"; case 11: return "caution";
    case 12: return "swallow"; default: return "null";
    }
}

bool isAttackState(p2chappyfsm::Family family, int state)
{
    if (family == p2chappyfsm::FAMILY_ADULT) return state == p2chappy::ADULT_ATTACK;
    if (family == p2chappyfsm::FAMILY_KING) return state == 1;
    return state == 3; // Kuma / KumaKo
}

void transition(BTeki* actor, ChappyFsm& s, int next, unsigned gen)
{
    s.state = next;
    s.stateTime = 0.0f;
    s.attackFired = false;
    s.swallowFired = false;
    s.flickFired = false;
    s.lastEatFrame = -1;
    s.eatenThisAttack = 0;
    s.winEligible = 0;
    s.winFreeBefore = -1;
    s.winRefusedNoHost = 0;
    s.winNaviHits = 0;
    s.winNearestBehind = false;
    s.winLegacyBehind = false;
    s.winDiag = p2chappymouth::WindowDiag{};
    if (s.family == p2chappyfsm::FAMILY_KING && next == 0) {
        p2chappymouth::king::enterWalk(s.walker, s.tickTargetKind != '-'); // StateWalk::init
    }
    if (isAttackState(s.family, next)) {
        s.atkTargetKind = s.tickTargetKind;
        s.atkTargetDist = s.tickTargetDist;
        s.atkTargetAngDeg = s.tickTargetAngDeg;
        s.atkTargetDist3d = s.tickTargetDist3d;
    }
    auto b = banks.find(s.spec->enumName);
    if (b != banks.end()) {
        if (const char* c = clipForState(b->second, s.family, next)) s.clip = c;
    }
    std::printf("P2_CHAPPY_STATE generator=%u source_id=%u state=%s clip=%s\n", gen,
                s.spec->source, fsmStateName(s.family, next), s.clip.c_str());
    std::fflush(stdout);
}

void setPhase(ChappyFsm& s)
{
    const float dur = clipDuration(s.spec->enumName, s.clip);
    float ph = dur > 0.0f ? s.stateTime / dur : 1.0f;
    if (ph > 1.0f) ph = 1.0f;
    s.phase = ph;
}

int initialState(p2chappyfsm::Family family)
{
    if (family == p2chappyfsm::FAMILY_KUMA) return 6; // TurnPath
    if (family == p2chappyfsm::FAMILY_KUMAKO) return 2; // Wait
    if (family == p2chappyfsm::FAMILY_KING) return 0; // Walk
    return p2chappy::ADULT_SLEEP;
}

void initFsm(PelletView* view, BTeki* actor, const p2chappy::SpeciesParams* spec, unsigned token)
{
    ChappyFsm& s = fsms[view];
    s.spec = spec;
    s.family = p2chappyfsm::familyForSource(spec->source);
    s.state = initialState(s.family);
    s.stateTime = 0.0f;
    s.home = actor->getPosition();
    s.heading = actor->getDirection();
    // #884: the eat geometry (pc_p2_chappy_mouth.h) is at P2 model scale 1 and
    // the pose mesh is drawn with mSRT.s (tekibteki.cpp drawTekiShape). Pin it
    // so a recycled BTeki can never carry a stale P1 TPF_Scale into the draw.
    actor->mSRT.s.set(1.0f, 1.0f, 1.0f);
    p2chappymouth::king::initWalker(s.walker, p2chappymouth::Vec3{s.home.x, s.home.y, s.home.z});
    s.kingGateLogS = 0.0f;
    s.wander = s.home;
    s.wanderValid = true;
    s.rng = (token * 2654435761u) | 1u;
    s.lastHealth = actor->mHealth;
    s.deadLogged = false;
    s.escaped = false;
    s.healthAsserted = true;
    auto b = banks.find(spec->enumName);
    if (b != banks.end()) {
        if (const char* c = clipForState(b->second, s.family, s.state)) s.clip = c;
    }
    s.phase = 0.0f;
    s.logTimer = 0.0f;
    s.auraTimer = 0.0f;
}

// Source ChappyBase::StateAttack KEYEVENT_2: attackNavi + eatAttackPikmin;
// KEYEVENT_3: swallowPikmin with white poison. Ported onto the P1 host with
// the banked adult/dwarf keyframes (policy AttackBiteFrame etc.).
struct EatStats {
    int eligible = 0;
    int captured = 0;
    int freeBefore = 0;
    int refusedNoHost = 0;
    bool nearestBehind = false; // nearest eligible Pikmin within fp22 of the feet is behind
    bool legacyBehind = false;  // the pre-#884 selection would have eaten behind
};

// Source EnemyFunc::eatPikmin (enemyAction.cpp:1107-1142) through
// pc_p2_chappy_mouth.h: every eligible Pikmin within the radius of an EMPTY
// source mouth slot (kamuN joint at the eat frame) is swallowed into it, up to
// the source slot count. P2 slot i sticks to P1 host 'slot' child
// (i % host children). A host without a 'slot' part refuses the capture:
// InteractSwallow is never sent with a null part (the P1 receiver would kill
// outright, interactBattle.cpp:525-529, bypassing capacity, the swallow key
// frame and White poison). BTeki::getFreeSlot (unguarded getSphere) is not used.
EatStats doEat(BTeki* actor, ChappyFsm& s, unsigned gen, int frame)
{
    EatStats st;
    const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(s.spec->source);
    if (!prof || !pikiMgr) return st;
    CollPart* mouthPart = actor->mCollInfo ? actor->mCollInfo->getSphere('slot') : nullptr;
    const int hostCount = mouthPart ? mouthPart->getChildCount() : 0;
    if (!s.mouthLogged) {
        s.mouthLogged = true;
        std::printf("P2_CHAPPY_MOUTH generator=%u source_id=%u p2_slots=%d radius=%.1f host_slots=%d shared=%d\n",
                    gen, s.spec->source, prof->slots, p2chappymouth::effectiveRadius(*prof), hostCount,
                    (hostCount > 0 && hostCount < prof->slots) ? 1 : 0);
        std::fflush(stdout);
    }
    // Occupancy: a slot is taken while the Pikmin this actor stuck there is
    // still one of its mouth stickers (swallow, escape and death free it).
    std::vector<Creature*> inMouth;
    {
        Stickers stickers(actor);
        Iterator it(&stickers);
        CI_LOOP(it)
        {
            Creature* stuck = *it;
            if (stuck && stuck->isPiki() && stuck->isStickToMouth()) inMouth.push_back(stuck);
        }
    }
    bool occupied[p2chappymouth::MaxSlots] = {};
    for (int i = 0; i < prof->slots; ++i) {
        if (s.mouth[i] && std::find(inMouth.begin(), inMouth.end(), s.mouth[i]) != inMouth.end()) {
            occupied[i] = true;
        } else {
            s.mouth[i] = nullptr;
            ++st.freeBefore;
        }
    }
    // Snapshot the prey before any stimulate (receivers change stick state).
    std::vector<Piki*> pikis;
    std::vector<p2chappymouth::Prey> prey;
    {
        Iterator it(pikiMgr);
        CI_LOOP(it)
        {
            Piki* p = static_cast<Piki*>(*it);
            if (!p) continue;
            p2chappymouth::Prey q{};
            q.pos = mouthVec(p->getPosition());
            q.alive = p->isAlive();
            q.visible = p->isVisible();
            q.buried = p->isBuried();
            q.stuckToAnyMouth = p->isStickToMouth() != 0;
            q.stuckToSelf = p->getStickObject() == actor && !q.stuckToAnyMouth;
            q.stuckToAny = p->isStickTo();
            pikis.push_back(p);
            prey.push_back(q);
        }
    }
    const p2chappymouth::Vec3 apos = mouthVec(actor->getPosition());
    const int count = (int)prey.size();
    for (const auto& q : prey) st.eligible += p2chappymouth::eligible(q) ? 1 : 0;
    const int nearest = p2chappymouth::nearestIndex(prey.data(), count, apos, s.spec->attackHitRange,
                                                    [](const p2chappymouth::Prey& q) { return p2chappymouth::eligible(q); });
    st.nearestBehind = nearest >= 0 && p2chappymouth::toLocal(apos, s.heading, prey[nearest].pos).z <= 0.0f;
    const int legacy = p2chappymouth::nearestIndex(prey.data(), count, apos, s.spec->attackHitRange,
                                                   [](const p2chappymouth::Prey& q) { return p2chappymouth::legacyEdible(q); });
    st.legacyBehind = legacy >= 0 && p2chappymouth::toLocal(apos, s.heading, prey[legacy].pos).z <= 0.0f;
    const float radius = p2chappymouth::effectiveRadius(*prof);
    if (s.winDiag.frames == 0) {
        s.winHeadingDeg = wrapPi(s.heading) * 180.0f / PI_F;
        s.winDrawYawDeg = wrapPi(actor->getDirection()) * 180.0f / PI_F;
    }
    p2chappymouth::observe(s.winDiag, *prof, frame, apos, s.heading, prey.data(), count, occupied);
    st.captured = p2chappymouth::eat(*prof, frame, apos, s.heading, prey.data(), count, occupied, [&](int n, int slot) {
        const int idx = p2chappymouth::hostPartIndex(slot, hostCount);
        CollPart* part = idx >= 0 ? mouthPart->getChildAt(idx) : nullptr;
        if (!part) {
            ++st.refusedNoHost;
            return false;
        }
        Piki* piki = pikis[n];
        const bool white = pc_p2_is_white(piki);
        if (!piki->stimulate(InteractSwallow(actor, part, 0))) return false;
        s.mouth[slot] = piki;
        const p2chappymouth::Vec3 local = p2chappymouth::toLocal(apos, s.heading, prey[n].pos);
        const float dist = p2chappymouth::distance(p2chappymouth::slotWorld(*prof, frame, slot, apos, s.heading), prey[n].pos);
        std::printf("P2_CHAPPY_EAT generator=%u source_id=%u frame=%d slot=%d prey_angle_deg=%.1f prey_dist=%.1f "
                    "slot_radius=%.1f local_x=%.1f local_y=%.1f local_z=%.1f white=%d\n",
                    gen, s.spec->source, frame, slot, std::atan2(local.x, local.z) * 180.0f / PI_F, dist, radius,
                    local.x, local.y, local.z, white ? 1 : 0);
        std::fflush(stdout);
        return true;
    });
    s.eatenThisAttack += st.captured;
    return st;
}

// #884 geometry fields appended to P2_CHAPPY_BITE and P2_CHAPPY_EAT_NONE:
// closest = min 3D distance from any eligible Pikmin to any FREE slot over the
// evaluated frames (-1: none), closest_local = that Pikmin in the actor frame
// at closest_frame, front = max eligible Pikmin ahead within `reach` (slot
// reach + radius), stuck_self = max Pikmin latched to this body, eligible_min
// = min eligible per frame, heading_deg / draw_yaw_deg = FSM heading vs the
// mFaceDirection the draw rotates by (first eat frame), scale = mSRT.s.x,
// target_* = what started the attack (n navi, p Pikmin, s latched, - none).
void printDiag(BTeki* actor, const ChappyFsm& s, const p2chappymouth::Profile* prof)
{
    const p2chappymouth::WindowDiag& d = s.winDiag;
    std::printf(" closest=%.1f closest_local=%.1f,%.1f,%.1f closest_frame=%d closest_slot=%d slot_radius=%.1f "
                "reach=%.1f front=%d stuck_self=%d eligible_min=%d heading_deg=%.1f draw_yaw_deg=%.1f scale=%.2f "
                "target_kind=%c target_dist=%.1f target_ang_deg=%.1f target_dist_3d=%.1f",
                d.closest, d.closestLocal.x, d.closestLocal.y, d.closestLocal.z, d.closestFrame, d.closestSlot,
                prof ? p2chappymouth::effectiveRadius(*prof) : 0.0f, prof ? p2chappymouth::maxReach(*prof) : 0.0f,
                d.front, d.stuckSelf, d.eligibleMin, s.winHeadingDeg, s.winDrawYawDeg, actor->mSRT.s.x,
                s.atkTargetKind, s.atkTargetDist, s.atkTargetAngDeg, s.atkTargetDist3d);
}

void logBite(BTeki* actor, const ChappyFsm& s, unsigned gen, int frame, int first, int last, const EatStats& st,
             int slots)
{
    const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(s.spec->source);
    std::printf("P2_CHAPPY_BITE generator=%u source_id=%u frame=%d window=%d-%d eligible=%d captured=%d "
                "free_before=%d slots=%d refused_no_host=%d nearest_behind=%d legacy_would_eat_behind=%d",
                gen, s.spec->source, frame, first, last, st.eligible, st.captured, st.freeBefore, slots,
                st.refusedNoHost, st.nearestBehind ? 1 : 0, st.legacyBehind ? 1 : 0);
    printDiag(actor, s, prof);
    std::printf("\n");
    if (st.captured == 0) {
        std::printf("P2_CHAPPY_EAT_NONE generator=%u source_id=%u frame=%d eligible=%d nearest_behind=%d "
                    "all_occupied=%d refused_no_host=%d",
                    gen, s.spec->source, frame, st.eligible, st.nearestBehind ? 1 : 0, st.freeBefore == 0 ? 1 : 0,
                    st.refusedNoHost);
        printDiag(actor, s, prof);
        std::printf("\n");
    }
    std::fflush(stdout);
}

// Source KingChappy StateAttack (kingChappyState.cpp:188-205): every frame, a
// captain touching any mouth-slot sphere takes InteractAttack(fp24). The P1
// navi receiver refuses while isDamaged (navi.cpp:3310-3318), so per-frame
// contact cannot stack damage.
int kingNaviContact(BTeki* actor, const ChappyFsm& s, const p2chappymouth::Profile& prof, int frame)
{
    if (!naviMgr) return 0;
    const p2chappymouth::Vec3 apos = mouthVec(actor->getPosition());
    int hits = 0;
    for (Navi* n : pc_p2_navis()) {
        if (!n->isAlive()) continue;
        const p2chappymouth::Vec3 np = mouthVec(n->getPosition());
        for (int i = 0; i < prof.slots; ++i) {
            const p2chappymouth::Vec3 slot = p2chappymouth::slotWorld(prof, frame, i, apos, s.heading);
            if (p2chappymouth::distance(slot, np) < p2chappymouth::effectiveRadius(prof)) {
                if (n->stimulate(InteractAttack(actor, nullptr, s.spec->attackDamage, false))) ++hits;
            }
        }
    }
    return hits;
}

int doSwallow(BTeki* actor, const ChappyFsm& s, unsigned gen, int& whitePoisoned)
{
    whitePoisoned = 0;
    int count = 0;
    Stickers stickers(actor);
    Iterator it(&stickers);
    CI_LOOP(it)
    {
        Creature* stuck = *it;
        if (!stuck || !stuck->isPiki() || !stuck->isStickToMouth()) continue;
        Piki* piki = static_cast<Piki*>(stuck);
        const bool white = pc_p2_is_white(piki);
        if (piki->stimulate(InteractKill(actor, 0))) {
            ++count;
            if (white) {
                actor->mStoredDamage += s.spec->poisonDamage;
                whitePoisoned = 1;
            }
        }
    }
    if (count > 0 || whitePoisoned) {
        std::printf("P2_CHAPPY_SWALLOW generator=%u source_id=%u swallowed=%d white=%d\n", gen,
                    s.spec->source, count, whitePoisoned);
        std::fflush(stdout);
    }
    return count;
}

void doBite(BTeki* actor, ChappyFsm& s, unsigned gen, int frame)
{
    const Vector3f pos = actor->getPosition();
    int hitNavi = 0, hitPiki = 0;
    if (naviMgr) {
        for (Navi* n : pc_p2_navis()) {
            if (!n->isAlive()) continue;
            const Vector3f np = n->getPosition();
            if (distXZ(np, pos) < s.spec->attackHitRange) {
                const float ang = std::fabs(wrapPi(std::atan2(np.x - pos.x, np.z - pos.z) - s.heading));
                if (ang <= s.spec->attackAngle * PI_F / 180.0f) {
                    if (n->stimulate(InteractAttack(actor, nullptr, s.spec->attackDamage, false))) hitNavi = 1;
                }
            }
        }
    }
    // Source bites damage captains only (EnemyFunc::attackNavi iterates
    // naviMgr, enemyAction.cpp:1181-1204); Pikmin are only eaten, by the
    // mouth slots at the same key frame.
    const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(s.spec->source);
    const int eatFrame = prof ? prof->firstFrame : frame;
    const EatStats st = doEat(actor, s, gen, eatFrame);
    logBite(actor, s, gen, eatFrame, eatFrame, eatFrame, st, prof ? prof->slots : 0);
    std::printf("P2_CHAPPY_ATTACK generator=%u source_id=%u frame=%d navi=%d piki=%d eaten=%d eaten_count=%d\n",
                gen, s.spec->source, frame, hitNavi, hitPiki, st.captured > 0 ? 1 : 0, st.captured);
    std::fflush(stdout);
}

void doFlick(BTeki* actor, const ChappyFsm& s, unsigned gen, int frame)
{
    const Vector3f pos = actor->getPosition();
    int hit = 0;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it)
        {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            if (distXZ(p->getPosition(), pos) < s.spec->attackHitRange) {
                if (p->stimulate(InteractFlick(actor, 300.0f, 0.0f, FLICK_BACKWARDS_ANGLE))) ++hit;
            }
        }
    }
    for (Navi* n : pc_p2_navis()) {
        if (n->isAlive() && distXZ(n->getPosition(), pos) < s.spec->attackHitRange) {
            if (n->stimulate(InteractFlick(actor, 300.0f, 0.0f, FLICK_BACKWARDS_ANGLE))) ++hit;
        }
    }
    std::printf("P2_CHAPPY_FLICK generator=%u source_id=%u frame=%d hit=%d\n", gen, s.spec->source,
                frame, hit);
    std::fflush(stdout);
}

// FireChappy signature (FireChappy.h mOnFire/TYakiBody/Flick): burning touch.
// Port adaptation: periodic InteractFire to creatures inside the hit radius
// while alive; the P2 material animation has no host equivalent.
void doFireAura(BTeki* actor, ChappyFsm& s, unsigned gen)
{
    const Vector3f pos = actor->getPosition();
    int hit = 0;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it)
        {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive()) continue;
            if (distXZ(p->getPosition(), pos) < s.spec->attackHitRange) {
                if (p->stimulate(InteractFire(actor, s.spec->attackDamage))) ++hit;
            }
        }
    }
    for (Navi* n : pc_p2_navis()) {
        if (n->isAlive() && distXZ(n->getPosition(), pos) < s.spec->attackHitRange) {
            if (n->stimulate(InteractFire(actor, s.spec->attackDamage))) ++hit;
        }
    }
    if (hit > 0 || !s.auraLogged) {
        s.auraLogged = true;
        std::printf("P2_CHAPPY_AURA generator=%u source_id=33 hit=%d\n", gen, hit);
        std::fflush(stdout);
    }
}

void setWanderTarget(ChappyFsm& s)
{
    const float radius = 0.5f * (TERRITORY - HOME_RADIUS) * rand01(s) + HOME_RADIUS * 0.5f;
    const float angle = 2.0f * PI_F * rand01(s);
    s.wander.x = s.home.x + radius * std::sin(angle);
    s.wander.y = s.home.y;
    s.wander.z = s.home.z + radius * std::cos(angle);
    s.wanderValid = true;
}

// Bind with an explicit seed source (generated-placement path).
bool bindActorAs(BTeki* actor, unsigned generator, unsigned sourceId)
{
    if (!actor || !generator) return false;
    const p2chappy::SpeciesParams* spec = p2chappy::speciesForSource(sourceId);
    if (!spec) return false;
    PelletView* view = static_cast<PelletView*>(actor);
    if (actors.count(view)) return true;
    if (actor->mTekiType != spec->host) return false;
    if (claimedElsewhere(actor)) return false;
    if (!health.bind(view, spec->health)) return false;
    actors[view] = spec;
    actor->mHealth = spec->health;
    initFsm(view, actor, spec, generator);
    pc_randomizer_p2_bind_source(view, sourceId, generator);
    std::printf("P2_CHAPPY_DELIVERY_BIND generator=%u source_id=%u key=chappy|%s\n", generator,
                sourceId, spec->enumName);
    const auto& pos = actor->getPosition();
    std::printf("P2_ENEMY_READY species=%s source_id=%u native_family=Chappy generator=%u "
                "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native host=%d "
                "source_FSM=implemented\n",
                spec->enumName, sourceId, generator, pos.x, pos.y, pos.z, actor->mHealth,
                spec->health, spec->host);
    std::printf("P2_CHAPPY_BIND generator=%u source_id=%u species=%s visual_only=0\n", generator,
                sourceId, spec->enumName);
    std::fflush(stdout);
    return true;
}
} // namespace

void pc_p2_chappy_reset()
{
    banks.clear();
    shapes.clear();
    actors.clear();
    lastClip.clear();
    corpseGenerators.clear();
    fsms.clear();
    health.reset();
    bankLoaded = false;
    drawnLive.clear();
    drawnCorpse.clear();
    bankBytes = 0;
}

void pc_p2_chappy_forget(BTeki* actor)
{
    PelletView* view = static_cast<PelletView*>(actor);
    if (actors.erase(view)) {
        std::printf("P2_CHAPPY_FORGET registered=1\n");
        std::fflush(stdout);
    }
    lastClip.erase(view);
    corpseGenerators.erase(view);
    fsms.erase(view);
    drawnLive.erase(view);
    drawnCorpse.erase(view);
    health.forget(view);
}

float pc_p2_chappy_max_health(const BTeki* actor, float fallback)
{
    return health.life(static_cast<const PelletView*>(actor), fallback);
}

float pc_p2_chappy_param_f(const BTeki* actor, int idx, float fallback)
{
    if (!bankLoaded || !actors.count(const_cast<BTeki*>(actor))) return fallback;
    if (idx == TPF_Life) return health.life(static_cast<const PelletView*>(actor), fallback);
    // Host blinding (catfish pattern): the suppressed P1 strategy must not
    // see/decide on stale P1 radii even if a future path calls it.
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
    case TPF_LifeRecoverRate:
        return 0.0f;
    default:
        return fallback;
    }
}

bool pc_p2_chappy_suppress_ai(const BTeki* actor)
{
    return bankLoaded && actors.count(const_cast<BTeki*>(actor)) != 0;
}

bool pc_p2_chappy_probe(const BTeki* actor, const char** state, const char** clip, float* phase)
{
    auto* view = static_cast<PelletView*>(const_cast<BTeki*>(actor));
    if (!actors.count(view)) return false;
    auto ft = fsms.find(view);
    if (ft == fsms.end()) return false;
    if (state) *state = fsmStateName(ft->second.family, ft->second.state);
    if (clip) *clip = ft->second.clip.c_str();
    if (phase) *phase = ft->second.phase;
    return true;
}

void pc_p2_chappy_press(BTeki* actor)
{
    if (!actor) return;
    auto* view = static_cast<PelletView*>(actor);
    auto ft = fsms.find(view);
    if (ft == fsms.end() || ft->second.family != p2chappyfsm::FAMILY_KUMAKO) return;
    ft->second.pressed = true;
    actor->mHealth = 0.0f;
    const unsigned gen = actor->mGenerator ? pc_p2_campaign_token(actor) : 0;
    transition(actor, ft->second, 1, gen);
}

const char* pc_p2_chappy_name(PelletView* actor)
{
    auto it = actors.find(actor);
    return it == actors.end() ? nullptr : it->second->english;
}

bool pc_p2_chappy_registered(const BTeki* actor)
{
    return actors.count(const_cast<BTeki*>(actor)) != 0;
}

unsigned long pc_p2_chappy_count()
{
    return (unsigned long)actors.size();
}

bool pc_p2_chappy_receipt(PelletView* view, unsigned& generator)
{
    auto it = corpseGenerators.find(view);
    if (it == corpseGenerators.end()) return false;
    generator = it->second;
    return true;
}

void pc_p2_chappy_setup()
{
    pc_p2_chappy_reset();
    std::ifstream bank("p2-chappy-bank.txt"), bindings("p2-chappy-actors.txt");
    if (!bank && !bindings) return;
    if (!bank || !bindings || !tekiMgr) std::abort();
    // Bank: P2_CHAPPY_BANK_1, species rows, clip rows.
    std::string token;
    if (!(bank >> token) || token != "P2_CHAPPY_BANK_1") std::abort();
    std::string word;
    while (bank >> word) {
        if (word == "species") {
            std::string species;
            unsigned long long id = 0;
            if (!(bank >> species >> id)) std::abort();
            const p2chappy::SpeciesParams* spec = p2chappy::speciesForEnum(species);
            if (!spec || spec->source != (unsigned)id) std::abort();
            SpeciesBank& entry = banks[species];
            entry.source = (unsigned)id;
            entry.species = species;
        } else if (word == "clip") {
            std::string species, name, events, posesWord, status;
            long long frames = 0;
            int poses = 0;
            if (!(bank >> species >> name >> frames >> events >> posesWord >> poses >> status)) std::abort();
            if (posesWord != "poses" || status != "converted") std::abort();
            if (!banks.count(species)) std::abort();
            if (frames < 1 || frames > 10000 || poses < 1 || poses > 64) std::abort();
            if (!banks[species].clips.emplace(name, ClipDef{(int)frames, poses}).second) std::abort();
        } else {
            std::abort();
        }
    }
    if (banks.empty()) std::abort();
    // Actors: P2_CHAPPY_ACTORS_1 <count> + <generator> <Species> rows.
    if (!(bindings >> word)) std::abort();
    int count = 0;
    if (word != "P2_CHAPPY_ACTORS_1" || !(bindings >> count) || count < 1 || count > 100) std::abort();
    std::map<unsigned, std::string> wanted;
    for (int i = 0; i < count; ++i) {
        unsigned long long generator = 0;
        std::string species;
        if (!(bindings >> generator >> species)) std::abort();
        if (!generator || generator > 0xffffffffULL) std::abort();
        if (!p2chappy::speciesForEnum(species) || !wanted.emplace((unsigned)generator, species).second) std::abort();
    }
    if (bindings >> word) std::abort();
    if (pc_randomizer_p2_bridge()) {
        // Campaign identity comes from the seed, not the filed placeholders.
        // This bridge arm runs in campaign sessions via pc_p2_preview_setup.
        wanted.clear();
        for (const auto& entry : banks) {
            for (unsigned id : pc_p2_campaign_ids(entry.second.source)) wanted[id] = entry.second.species;
        }
    }
    if (wanted.empty()) return;
    // Load the staged pose bank before touching actors (fail-closed).
    for (const auto& entry : banks) {
        for (const auto& clip : entry.second.clips) {
            for (int i = 0; i < clip.second.poses; ++i) {
                char rel[192];
                std::snprintf(rel, sizeof(rel),
                              "assets/dataDir/courses/pikmin2room/ch_%s_%s_%02d.mod",
                              entry.second.species.c_str(), clip.first.c_str(), i);
                std::ifstream probe(rel, std::ios::binary | std::ios::ate);
                if (!probe) std::abort();
                const auto size = probe.tellg();
                if (size <= 0 || size_t(size) > 512 * 1024 || bankBytes + size_t(size) > 48 * 1024 * 1024) std::abort();
                bankBytes += size_t(size);
            }
        }
    }
    for (const auto& entry : banks) {
        for (const auto& clip : entry.second.clips) {
            std::vector<Shape*>& out = shapes[entry.second.species + "|" + clip.first];
            for (int i = 0; i < clip.second.poses; ++i) {
                char load[192];
                std::snprintf(load, sizeof(load), "courses/pikmin2room/ch_%s_%s_%02d.mod",
                              entry.second.species.c_str(), clip.first.c_str(), i);
                Shape* shape = gameflow.loadShape(load, true);
                if (!shape) std::abort();
                out.push_back(shape);
            }
        }
    }
    bankLoaded = true;
    // Bind the actors.
    std::set<unsigned> found;
    Iterator it(tekiMgr);
    CI_LOOP(it)
    {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->mGenerator) continue;
        const unsigned token = pc_randomizer_p2_bridge() ? pc_p2_campaign_token(actor)
                                                         : (unsigned)actor->mGenerator->_70;
        auto match = wanted.find(token);
        if (match == wanted.end()) continue;
        const p2chappy::SpeciesParams* spec = p2chappy::speciesForEnum(match->second);
        if (!spec) std::abort();
        if (actor->mTekiType != spec->host || claimedElsewhere(actor)) {
            if (pc_p2_setup_skip(pc_randomizer_p2_bridge(), spec->enumName, "actor_identity_mismatch")) return;
        }
        // Pack generators share one campaign token across members: bind
        // every member, count the token once (proxy Finding 5 pattern).
        found.insert(token);
        PelletView* view = static_cast<PelletView*>(actor);
        if (!health.bind(view, spec->health)) std::abort();
        actors[view] = spec;
        actor->mHealth = spec->health;
        initFsm(view, actor, spec, token);
        if (pc_randomizer_p2_bridge()) {
            pc_randomizer_p2_bind_source(view, spec->source, token);
            std::printf("P2_CHAPPY_DELIVERY_BIND generator=%u source_id=%u key=chappy|%s\n", token,
                        spec->source, spec->enumName);
        }
        const auto& pos = actor->getPosition();
        std::printf("P2_ENEMY_READY species=%s source_id=%u native_family=Chappy generator=%u "
                    "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native host=%d "
                    "source_FSM=implemented\n",
                    spec->enumName, spec->source, token, pos.x, pos.y, pos.z, actor->mHealth,
                    spec->health, spec->host);
        std::printf("P2_CHAPPY_BIND generator=%u source_id=%u species=%s visual_only=0\n", token,
                    spec->source, spec->enumName);
        std::printf("P2_CHAPPY_STATE generator=%u source_id=%u state=%s clip=%s\n", token,
                    spec->source, fsmStateName(fsms[view].family, fsms[view].state),
                    fsms[view].clip.c_str());
    }
    if (found.size() != wanted.size()) {
        std::printf("P2_CHAPPY_MISSING found=%zu wanted=%zu\n", found.size(), wanted.size());
        if (pc_p2_setup_skip(true, "Chappy", "actor_roster_incomplete")) return;
    }
    std::printf("P2_CHAPPY_BANK species=%zu mod_bytes=%zu\n", banks.size(), bankBytes);
    std::fflush(stdout);
}

bool pc_p2_chappy_bind_dynamic(BTeki* actor, unsigned generatorId, unsigned sourceId)
{
    const p2chappy::SpeciesParams* spec = p2chappy::speciesForSource(sourceId);
    if (!spec || !actor || !generatorId) return false;
    PelletView* view = static_cast<PelletView*>(actor);
    if (actors.count(view)) return true;
    // Only staged species bind: the pose bank arrives with the stage setup,
    // so an unstaged family member refuses here and keeps its P1/proxy path.
    if (!bankLoaded || !banks.count(spec->enumName)) return false;
    if (actor->mTekiType != spec->host) return false;
    if (claimedElsewhere(actor)) return false;
    // The pose bank arrives with the stage setup; the identity binds now so
    // damage/death/delivery track from spawn even before the first draw.
    if (!health.bind(view, spec->health)) return false;
    actors[view] = spec;
    actor->mHealth = spec->health;
    initFsm(view, actor, spec, generatorId);
    pc_randomizer_p2_bind_source(view, sourceId, generatorId);
    std::printf("P2_CHAPPY_DELIVERY_BIND generator=%u source_id=%u key=chappy|%s\n", generatorId,
                sourceId, spec->enumName);
    const auto& pos = actor->getPosition();
    std::printf("P2_ENEMY_READY species=%s source_id=%u native_family=Chappy generator=%u "
                "x=%.7f y=%.7f z=%.7f health=%.1f max_health=%.1f behavior=native host=%d "
                "source_FSM=implemented\n",
                spec->enumName, sourceId, generatorId, pos.x, pos.y, pos.z, actor->mHealth,
                spec->health, spec->host);
    std::printf("P2_CHAPPY_BIND generator=%u source_id=%u species=%s visual_only=0\n", generatorId,
                sourceId, spec->enumName);
    std::printf("P2_CHAPPY_STATE generator=%u source_id=%u state=%s clip=%s\n", generatorId,
                sourceId, fsmStateName(fsms[view].family, fsms[view].state),
                fsms[view].clip.c_str());
    std::fflush(stdout);
    return true;
}

namespace {
// #884 round 3: source KingChappy::Obj::checkFlick (kingChappy.cpp:2429-2470)
// through pc_p2_chappy_mouth.h king::checkFlick. Called only where the source
// calls it (Walk after a non-Turn walkFunc tick, Turn). Each live captain
// within 3D fp06 (80) adds 0.1 per source frame; accepted hits add 1.0 via
// pc_p2_chappy_attacked; the start threshold is the retail shake-off tier of
// the stuck-Pikmin count. Replaces the port's "3 stuck Pikmin" rule, which
// had no captain term and no hit term (the i1-53 standoff never flicked).
bool kingCheckFlick(BTeki* actor, ChappyFsm& s, float frames)
{
    const p2chappymouth::Vec3 apos = mouthVec(actor->getPosition());
    int near = 0;
    if (naviMgr) {
        Iterator it(naviMgr);
        CI_LOOP(it)
        {
            Navi* n = static_cast<Navi*>(*it);
            if (n && n->isAlive() && p2chappymouth::king::naviInInvisibleRange(apos, mouthVec(n->getPosition()))) ++near;
        }
    }
    s.kingNaviNear = near;
    return p2chappymouth::king::checkFlick(s.kingFlickTimer, near, stuckPikminCount(actor), frames);
}

// checkFlick tail: below half life (general fp00) proper fp13 of the starts
// become WarCry. The roll is drawn only when a flick starts (source order).
bool kingShout(BTeki* actor, ChappyFsm& s)
{
    return actor->mHealth < 0.5f * s.spec->health && rand01(s) < p2chappymouth::king::FlickShoutRate;
}

void logKingFlickStart(BTeki* actor, const ChappyFsm& s, unsigned generator, const char* from, bool shout)
{
    const int stuck = stuckPikminCount(actor);
    std::printf("P2_CHAPPY_KING_FLICK_START generator=%u source_id=%u from=%s next=%s flick_timer=%.2f "
                "flick_need=%d stuck_self=%d navi_near=%d hits=%d health=%.1f hits_stuck=%d hits_low=%d "
                "hits_refused=%d\n",
                generator, s.spec->source, from, shout ? "warcry" : "flick", s.kingFlickTimer,
                p2chappymouth::king::flickThreshold(stuck), stuck, s.kingNaviNear, s.kingFlickHits, actor->mHealth,
                s.kingHitsStuck, s.kingHitsLow, s.kingHitsRefused);
    std::fflush(stdout);
}

// Source StateFlick KEYEVENT_3 (trample = true; kingChappyState.cpp:867-918)
// and StateWarCry KEYEVENT_4 (trample = false; :1620-1659) with the retail
// fp24/fp08 trample and fp16-fp19 shake (pc_p2_chappy_mouth.h king::).
// Order: trample (InteractPress), flickNearbyPikmin, flickStickPikmin,
// flickNearbyNavi unless a captain was trampled; then mFlickTimer = 0.
// Adaptations (P1 receivers): a Pikmin held in any mouth is skipped (source
// ConditionPikminNearby / flickCreature exclude this King's mouth; the P1
// InteractFlick::actCommon would release it); a Pikmin stuck to anything is
// not pressed (the P1 press does not end the stick; stuck-to-self ones are
// flicked by flickStickPikmin instead); a Pikmin pressed by this event is not
// flicked (the P1 flick would lift it out of PIKISTATE_Pressed). The WarCry
// InteractAstonish roar (fp03/fp04) has no P1 equivalent here and is not
// ported. Stuck Pikmin are snapshotted before any stimulate (source Stickers).
void doKingShake(BTeki* actor, ChappyFsm& s, unsigned gen, int frame, bool trample)
{
    namespace K = p2chappymouth::king;
    const p2chappymouth::Vec3 apos = mouthVec(actor->getPosition());
    const p2chappymouth::Vec3 foot = K::footPosition(apos, s.heading);
    const float timerBefore = s.kingFlickTimer;
    int pressedPiki = 0, pressedNavi = 0, nearPiki = 0, stuckPiki = 0, flickedNavi = 0;
    bool naviCheck = true;
    std::vector<Piki*> nearby, stuck;
    if (pikiMgr) {
        Iterator it(pikiMgr);
        CI_LOOP(it)
        {
            Piki* p = static_cast<Piki*>(*it);
            if (!p || !p->isAlive() || p->isStickToMouth()) continue;
            const p2chappymouth::Vec3 q = mouthVec(p->getPosition());
            if (trample && !p->isStickTo() && K::tramples(foot, q)) {
                if (p->stimulate(InteractPress(actor, K::TrampleDamage))) ++pressedPiki;
                continue;
            }
            if (p->getStickObject() == actor) stuck.push_back(p);
            else if (K::inShakeRange(apos, q)) nearby.push_back(p);
        }
    }
    if (trample && naviMgr) {
        Iterator it(naviMgr);
        CI_LOOP(it)
        {
            Navi* n = static_cast<Navi*>(*it);
            if (!n || !n->isAlive() || !K::tramples(foot, mouthVec(n->getPosition()))) continue;
            if (n->stimulate(InteractPress(actor, K::TrampleDamage))) ++pressedNavi;
            naviCheck = false; // source clears it for any captain in the disc
        }
    }
    for (Piki* p : nearby) {
        if (p->isAlive() && p->stimulate(InteractFlick(actor, K::ShakeKnockback, K::ShakeDamage, FLICK_BACKWARDS_ANGLE)))
            ++nearPiki;
    }
    const float stuckAngle = K::flickStuckAngle(s.heading);
    for (Piki* p : stuck) {
        if (!p->isAlive() || p->getStickObject() != actor || p->isStickToMouth()) continue;
        if (K::ShakeChance < 1.0f && !(K::ShakeChance > rand01(s))) continue; // retail fp16 = 1: always
        if (p->stimulate(InteractFlick(actor, K::ShakeKnockback, K::ShakeDamage, stuckAngle))) ++stuckPiki;
    }
    float naviDist = -1.0f;
    if (naviMgr) {
        Iterator it(naviMgr);
        CI_LOOP(it)
        {
            Navi* n = static_cast<Navi*>(*it);
            if (!n || !n->isAlive()) continue;
            const p2chappymouth::Vec3 np = mouthVec(n->getPosition());
            const float d = p2chappymouth::distance(np, apos);
            if (naviDist < 0.0f || d < naviDist) naviDist = d;
            if (naviCheck && K::inShakeRange(apos, np)
                && n->stimulate(InteractFlick(actor, K::ShakeKnockback, K::ShakeDamage, FLICK_BACKWARDS_ANGLE)))
                ++flickedNavi;
        }
    }
    s.kingFlickTimer = 0.0f;
    std::printf("P2_CHAPPY_KING_SHAKE generator=%u source_id=%u event=%s frame=%d trample=%d pressed_piki=%d "
                "pressed_navi=%d flicked_near=%d flicked_stuck=%d flicked_navi=%d stuck_seen=%d navi_dist_3d=%.1f "
                "flick_timer_before=%.2f\n",
                gen, s.spec->source, trample ? "flick" : "warcry", frame, trample ? 1 : 0, pressedPiki, pressedNavi,
                nearPiki, stuckPiki, flickedNavi, (int)stuck.size(), naviDist, timerBefore);
    std::fflush(stdout);
}

// Maps a Walk/Turn decision to the port King state ids and logs flick starts.
void kingApply(BTeki* actor, ChappyFsm& s, unsigned generator, p2chappymouth::king::WalkNext next, const char* from)
{
    namespace K = p2chappymouth::king;
    switch (next) {
    case K::NextFlick:
    case K::NextWarCry:
        stop(actor);
        logKingFlickStart(actor, s, generator, from, next == K::NextWarCry);
        transition(actor, s, next == K::NextWarCry ? 4 : 3, generator);
        break;
    case K::NextAttack: transition(actor, s, 1, generator); break;
    case K::NextTurn: stop(actor); transition(actor, s, 6, generator); break;
    case K::NextHide: stop(actor); transition(actor, s, 8, generator); break;
    case K::NextWalk:
        if (s.state != 0) transition(actor, s, 0, generator);
        break;
    }
}
} // namespace

// Source KingChappy::Obj::damageCallBack (kingChappy.cpp:824-848) through
// pc_p2_chappy_mouth.h king::damageAccept, evaluated on the InteractAttack
// fields (mOwner, mCollPart) before the P1 host sees the hit. A refused hit
// takes no damage and adds no flickSpeed; a partless hit low within 40 XZ is
// scaled by 0.2. P1 Pikmin that latch onto the King always carry their stick
// part (aiAttack.cpp:495-518, pikiState.cpp startStick/startStickObject), so
// the latched-attacker kill path is kept. P1 ground attacks
// (aiAttack.cpp:672/691, collPart nullptr) count only low within 40 XZ, as
// source partless hits. A captain punch is mapped to the source part branch
// (king::sourceHasCollPart: the source punch always carries a part,
// R naviState.cpp:1614-1627; the P1 punch at W naviState.cpp:3237 has none),
// so it is refused from any position, as in the source.
// Bittered is never set (no P1 spray path). Returns < 0 for every actor that
// is not a live registered King (host path unchanged).
float pc_p2_chappy_king_damage_rate(BTeki* actor, Creature* owner, CollPart* part)
{
    if (!actor) return -1.0f;
    auto ft = fsms.find(static_cast<PelletView*>(actor));
    if (ft == fsms.end() || ft->second.family != p2chappyfsm::FAMILY_KING) return -1.0f;
    ChappyFsm& s = ft->second;
    if (s.state == 2) return -1.0f; // Dead: host corpse path
    namespace K = p2chappymouth::king;
    K::DamageAttacker a;
    a.present = owner != nullptr;
    a.hasCollPart = K::sourceHasCollPart(part != nullptr, owner && owner->mObjType == OBJTYPE_Navi);
    if (owner) {
        a.alive = owner->isAlive();
        a.stuck = owner->isStickTo();
        a.pos = mouthVec(owner->getPosition());
    }
    const p2chappymouth::Vec3 kp = mouthVec(actor->getPosition());
    const K::DamageAccept d = K::damageAccept(kp, a, false);
    if (d == K::DamageStuck) ++s.kingHitsStuck;
    else if (d == K::DamageLowPartless) ++s.kingHitsLow;
    else if (d == K::DamageRefused) ++s.kingHitsRefused;
    // Rate-limited: the first of each kind, then every 100th refusal.
    const bool first = (d == K::DamageStuck && s.kingHitsStuck == 1) || (d == K::DamageLowPartless && s.kingHitsLow == 1)
                       || (d == K::DamageRefused && s.kingHitsRefused == 1);
    if (first || (d == K::DamageRefused && s.kingHitsRefused % 100 == 0)) {
        const float dx = a.pos.x - kp.x, dz = a.pos.z - kp.z;
        std::printf("P2_CHAPPY_KING_DAMAGE source_id=%u verdict=%s owner=%s part=%d alive=%d stuck=%d dxz=%.1f dy=%.1f "
                    "hits_stuck=%d hits_low=%d hits_refused=%d health=%.1f\n",
                    s.spec->source, d == K::DamageStuck ? "stuck" : d == K::DamageLowPartless ? "low" : "refused",
                    !owner ? "none" : owner->isPiki() ? "piki" : owner->mObjType == OBJTYPE_Navi ? "navi" : "other",
                    a.hasCollPart ? 1 : 0, a.alive ? 1 : 0, a.stuck ? 1 : 0, std::sqrt(dx * dx + dz * dz), a.pos.y - kp.y,
                    s.kingHitsStuck, s.kingHitsLow, s.kingHitsRefused, actor->mHealth);
        std::fflush(stdout);
    }
    return K::damageRate(d);
}

// Source EnemyBase::addDamage flickSpeed (enemyBase.cpp:2762-2773) for the
// King: every hit that damageCallBack accepts adds 1.0 to the flick timer, in
// every state. InteractAttack::actTeki calls this only after
// pc_p2_chappy_king_damage_rate passed the hit, so a refused hit never gets
// here. No-op for every other actor and family.
void pc_p2_chappy_attacked(BTeki* actor, bool accepted)
{
    if (!actor || !accepted) return;
    auto ft = fsms.find(static_cast<PelletView*>(actor));
    if (ft == fsms.end() || ft->second.family != p2chappyfsm::FAMILY_KING) return;
    ChappyFsm& s = ft->second;
    if (s.state == 2) return; // Dead
    s.kingFlickTimer += p2chappymouth::king::FlickPerHit;
    ++s.kingFlickHits;
}

void pc_p2_chappy_update(BTeki* actor)
{
    if (!actor || !bankLoaded) return;
    PelletView* view = static_cast<PelletView*>(actor);
    auto it = actors.find(view);
    if (it == actors.end()) return;
    auto ft = fsms.find(view);
    if (ft == fsms.end()) return;
    ChappyFsm& s = ft->second;
    const float dt = gsys->getFrameTime();
    if (dt <= 0.0f || dt > 0.5f) return;
    const unsigned generator = actor->mGenerator ? pc_p2_campaign_token(actor) : 0;

    // The suppressed P1 strategy normally applies stored damage through its
    // damage reaction; apply it here so real Pikmin hits reach mHealth.
    if (actor->mStoredDamage > 0.0f) actor->makeDamaged();

    // Natural-combat observability: incremental still-positive decrease is
    // real attack damage. Death marker records prior health.
    const float previousHealth = s.lastHealth;
    if (actor->mHealth < s.lastHealth && actor->mHealth > 0.0f) {
        std::printf("P2_CHAPPY_DAMAGE generator=%u source_id=%u health=%.1f\n", generator,
                    s.spec->source, actor->mHealth);
        std::fflush(stdout);
    }
    s.lastHealth = actor->mHealth;
    (void)previousHealth;

    // Death takes precedence in every family (source checkDead). The host
    // dieSoon() only runs inside the suppressed doAI, so finalize with
    // pcEscapeNow() once the P2 dead clip completes (frog pattern). The
    // host death funnel may still birth the pellet; the corpse is the real
    // P2-drawn pellet via pc_p2_chappy_draw(corpse=true).
    const bool deadNow = (actor->mHealth <= 0.0f || actor->mDeadState != 0);
    const int deadState = (s.family == p2chappyfsm::FAMILY_ADULT) ? p2chappy::ADULT_DEAD
        : (s.family == p2chappyfsm::FAMILY_KING)                 ? 2
                                                                : 0;
    if (deadNow && s.state != deadState && !(s.family == p2chappyfsm::FAMILY_KUMAKO && s.state == 1)) {
        if (s.family == p2chappyfsm::FAMILY_KUMAKO && s.pressed) {
            transition(actor, s, 1, generator);
        } else {
            transition(actor, s, deadState, generator);
        }
    }
    if (s.state == deadState || (s.family == p2chappyfsm::FAMILY_KUMAKO && s.state == 1)) {
        stop(actor);
        if (!s.deadLogged) {
            s.deadLogged = true;
            std::printf("P2_CHAPPY_DEAD generator=%u source_id=%u\n", generator, s.spec->source);
            std::printf("P2_CHAPPY_CORPSE_READY generator=%u source_id=%u\n", generator, s.spec->source);
            if (generator) corpseGenerators[view] = generator;
            if (!health.markDead(view)) { /* already marked */ }
            std::fflush(stdout);
        }
        s.stateTime += dt;
        setPhase(s);
        const float deadDur = clipDuration(s.spec->enumName, s.clip);
        const float wait = (s.family == p2chappyfsm::FAMILY_KUMAKO && s.state == 1)
            ? clipDuration(s.spec->enumName, s.clip)
            : deadDur;
        if (s.family == p2chappyfsm::FAMILY_KUMAKO && s.state == 1) {
            if (s.stateTime >= wait) transition(actor, s, 0, generator);
        } else if (!s.escaped && s.stateTime >= wait) {
            s.escaped = true;
            actor->pcEscapeNow();
        }
        return;
    }

    // Fire signature runs while alive (all states).
    if (s.spec->source == 33) {
        s.auraTimer += dt;
        if (s.auraTimer >= 0.5f) {
            s.auraTimer = 0.0f;
            doFireAura(actor, s, generator);
        }
    }

    const Vector3f pos = actor->getPosition();
    // KingChappy uses the source searchTarget / checkAttack gate (#884): no
    // tongue attack on a target inside the invisible range, where no kamu slot
    // of the 40..94 window reaches ground prey.
    const bool king = s.family == p2chappyfsm::FAMILY_KING;
    // King: doSimulation ticks the search delay every frame in every state;
    // searchTarget early-outs on the delay / home-goal-out-of-territory
    // (kingChappy.cpp:797-802, 1135-1145).
    if (king) p2chappymouth::king::tickDelay(s.walker, dt * 30.0f);
    s.kingSearched = king && p2chappymouth::king::canSearch(s.walker, mouthVec(pos));
    if (king && !s.kingSearched) s.kingCensus = p2chappymouth::king::Census{};
    Creature* target = king ? (s.kingSearched ? kingSearchTarget(actor, s) : nullptr)
                            : nearestTarget(pos, s.spec->sight);
    if (target) actor->setCreaturePointer(0, target);
    else actor->clearCreaturePointer(0);
    const bool sees = target != nullptr;
    const bool inRange = king ? (target && p2chappymouth::king::attackGate(mouthVec(pos), s.heading,
                                                                           mouthVec(target->getPosition())))
                              : attackable(s, pos, target);
    s.tickTargetKind = '-';
    s.tickTargetDist = -1.0f;
    s.tickTargetAngDeg = 0.0f;
    s.tickTargetDist3d = -1.0f;
    if (target) {
        const Vector3f tp = target->getPosition();
        s.tickTargetKind = !target->isPiki() ? 'n' : (target->getStickObject() == actor ? 's' : 'p');
        s.tickTargetDist = distXZ(tp, pos);
        s.tickTargetDist3d = p2chappymouth::distance(mouthVec(tp), mouthVec(pos));
        s.tickTargetAngDeg = wrapPi(std::atan2(tp.x - pos.x, tp.z - pos.z) - s.heading) * 180.0f / PI_F;
    }
    // Source EnemyFunc::isStartFlick keys on Pikmin stuck to the body, not
    // mere proximity: a nearby-swarm latch flicks every few seconds and the
    // bot can never accumulate attackers (round-2 FireChappy stalemate).
    // The King does not use this: it runs the source checkFlick timer
    // (kingCheckFlick, #884 round 3) in Walk and Turn.
    const bool flickWanted = !inRange && stuckPikminCount(actor) >= FLICK_STUCK_MIN;
    const bool farHome = distXZ(pos, s.home) > TERRITORY;
    const bool nearHome = distXZ(pos, s.home) < HOME_RADIUS;

    s.stateTime += dt;

    if (s.family == p2chappyfsm::FAMILY_ADULT) {
        switch (s.state) {
        case p2chappy::ADULT_SLEEP: {
            stop(actor);
            if (flickWanted) { transition(actor, s, p2chappy::ADULT_FLICK, generator); break; }
            if (sees || actor->mHealth < s.spec->health) {
                transition(actor, s, p2chappy::ADULT_TURN, generator);
            }
            break;
        }
        case p2chappy::ADULT_TURN: {
            stop(actor);
            if (flickWanted) { transition(actor, s, p2chappy::ADULT_FLICK, generator); break; }
            if (!sees) { transition(actor, s, p2chappy::ADULT_TURN_TO_HOME, generator); break; }
            if (inRange) { transition(actor, s, p2chappy::ADULT_ATTACK, generator); break; }
            if (target && turnTo(actor, s, target->getPosition(), dt,
                                 s.spec->attackAngle * PI_F / 180.0f)) {
                transition(actor, s, p2chappy::ADULT_WALK, generator);
            } else if (s.stateTime >= TURN_DURATION_S) {
                transition(actor, s, p2chappy::ADULT_WALK, generator);
            }
            break;
        }
        case p2chappy::ADULT_WALK: {
            if (inRange) { transition(actor, s, p2chappy::ADULT_ATTACK, generator); break; }
            if (!sees) { transition(actor, s, p2chappy::ADULT_TURN_TO_HOME, generator); break; }
            if (flickWanted) { transition(actor, s, p2chappy::ADULT_FLICK, generator); break; }
            if (farHome) {
                stop(actor);
                transition(actor, s, p2chappy::ADULT_TURN_TO_HOME, generator);
                break;
            }
            if (target) {
                const Vector3f tp = target->getPosition();
                const float ang = std::fabs(wrapPi(std::atan2(tp.x - pos.x, tp.z - pos.z) - s.heading));
                if (ang <= 25.0f * PI_F / 180.0f) walkTo(actor, s, tp, dt, s.spec->moveSpeed);
                else {
                    stop(actor);
                    transition(actor, s, p2chappy::ADULT_TURN, generator);
                }
            } else {
                stop(actor);
                transition(actor, s, p2chappy::ADULT_TURN_TO_HOME, generator);
            }
            break;
        }
        case p2chappy::ADULT_ATTACK: {
            stop(actor);
            const float frames = s.stateTime * 30.0f;
            if (!s.attackFired && frames >= float(p2chappy::AttackBiteFrame)) {
                s.attackFired = true;
                doBite(actor, s, generator, p2chappy::AttackBiteFrame);
            }
            if (!s.swallowFired && frames >= float(p2chappy::AttackSwallowFrame)) {
                s.swallowFired = true;
                int white = 0;
                doSwallow(actor, s, generator, white);
            }
            if (frames >= float(p2chappy::AttackEndFrame)) {
                if (inRange) transition(actor, s, p2chappy::ADULT_ATTACK, generator);
                else if (sees) transition(actor, s, p2chappy::ADULT_TURN, generator);
                else transition(actor, s, p2chappy::ADULT_TURN_TO_HOME, generator);
            }
            break;
        }
        case p2chappy::ADULT_FLICK: {
            stop(actor);
            if (!s.flickFired && s.stateTime * 30.0f >= 31.0f) {
                s.flickFired = true;
                doFlick(actor, s, generator, 31);
            }
            if (s.stateTime >= FLICK_DURATION_S) {
                if (inRange) transition(actor, s, p2chappy::ADULT_ATTACK, generator);
                else if (sees) transition(actor, s, p2chappy::ADULT_WALK, generator);
                else transition(actor, s, p2chappy::ADULT_TURN_TO_HOME, generator);
            }
            break;
        }
        case p2chappy::ADULT_TURN_TO_HOME: {
            stop(actor);
            if (inRange) { transition(actor, s, p2chappy::ADULT_ATTACK, generator); break; }
            if (nearHome) { transition(actor, s, p2chappy::ADULT_SLEEP, generator); break; }
            if (turnTo(actor, s, s.home, dt, 0.1f) || s.stateTime >= TURN_DURATION_S) {
                transition(actor, s, p2chappy::ADULT_GO_HOME, generator);
            }
            break;
        }
        case p2chappy::ADULT_GO_HOME: {
            if (nearHome) {
                stop(actor);
                transition(actor, s, p2chappy::ADULT_SLEEP, generator);
                break;
            }
            if (inRange) { transition(actor, s, p2chappy::ADULT_ATTACK, generator); break; }
            if (sees) { transition(actor, s, p2chappy::ADULT_WALK, generator); break; }
            walkTo(actor, s, s.home, dt, s.spec->moveSpeed);
            break;
        }
        default:
            stop(actor);
            transition(actor, s, p2chappy::ADULT_SLEEP, generator);
            break;
        }
    } else if (s.family == p2chappyfsm::FAMILY_KUMA) {
        // Leaf (67) rides the Kuma FSM with its own smaller parms; its
        // birthChildren Bulbmin spawn has no host equivalent and is logged.
        if (s.spec->source == 67 && !s.birthLogged && sees) {
            s.birthLogged = true;
            std::printf("P2_CHAPPY_BIRTH generator=%u source_id=67 children=0 note=no_host_equivalent\n",
                        generator);
            std::fflush(stdout);
        }
        switch (s.state) {
        case 6: { // TurnPath
            stop(actor);
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (flickWanted) { transition(actor, s, 4, generator); break; }
            if (sees) { transition(actor, s, 7, generator); break; }
            if (s.stateTime >= TURN_DURATION_S) transition(actor, s, 8, generator);
            break;
        }
        case 8: { // WalkPath (patrol wander)
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (flickWanted) { transition(actor, s, 4, generator); break; }
            if (sees) { transition(actor, s, 7, generator); break; }
            if (!s.wanderValid || distXZ(s.wander, pos) < 20.0f) setWanderTarget(s);
            walkTo(actor, s, s.wander, dt, s.spec->moveSpeed);
            if (farHome) { transition(actor, s, 2, generator); break; }
            break;
        }
        case 7: { // Walk (chase)
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (!sees) { transition(actor, s, 2, generator); break; }
            if (flickWanted) { transition(actor, s, 4, generator); break; }
            if (target) walkTo(actor, s, target->getPosition(), dt, s.spec->moveSpeed);
            if (farHome && !sees) { transition(actor, s, 2, generator); break; }
            break;
        }
        case 3: { // Attack
            stop(actor);
            const float frames = s.stateTime * 30.0f;
            if (!s.attackFired && frames >= float(p2chappy::AttackBiteFrame)) {
                s.attackFired = true;
                doBite(actor, s, generator, p2chappy::AttackBiteFrame);
            }
            if (!s.swallowFired && frames >= float(p2chappy::AttackSwallowFrame)) {
                s.swallowFired = true;
                int white = 0;
                doSwallow(actor, s, generator, white);
            }
            if (frames >= float(p2chappy::AttackEndFrame)) {
                if (inRange) transition(actor, s, 3, generator);
                else if (sees) transition(actor, s, 7, generator);
                else transition(actor, s, 2, generator);
            }
            break;
        }
        case 4: { // Flick
            stop(actor);
            if (!s.flickFired && s.stateTime * 30.0f >= 31.0f) {
                s.flickFired = true;
                doFlick(actor, s, generator, 31);
            }
            if (s.stateTime >= FLICK_DURATION_S) {
                transition(actor, s, sees ? 7 : 6, generator);
            }
            break;
        }
        case 2: { // Lost
            stop(actor);
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (sees) { transition(actor, s, 7, generator); break; }
            // Rebirth timer (KumaChappy proper fp12 adaptation): the carcass
            // revive has no host equivalent while alive, so Lost graduates
            // back to patrol via Rebirth.
            if (s.stateTime >= LOST_REBIRTH_S) {
                transition(actor, s, 1, generator);
                std::printf("P2_CHAPPY_REBIRTH generator=%u source_id=%u\n", generator, s.spec->source);
                std::fflush(stdout);
            }
            break;
        }
        case 1: { // Rebirth
            stop(actor);
            if (s.stateTime >= clipDuration(s.spec->enumName, s.clip)) {
                transition(actor, s, 6, generator);
            }
            break;
        }
        case 5: { // Turn
            stop(actor);
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (s.stateTime >= TURN_DURATION_S) transition(actor, s, 7, generator);
            break;
        }
        default:
            stop(actor);
            transition(actor, s, 6, generator);
            break;
        }
    } else if (s.family == p2chappyfsm::FAMILY_KUMAKO) {
        Vector3f parentPos = s.home;
        const bool hasParent = parentNear(actor, pos, parentPos);
        switch (s.state) {
        case 2: { // Wait
            stop(actor);
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (flickWanted) { transition(actor, s, 4, generator); break; }
            if (hasParent || sees) transition(actor, s, 6, generator);
            break;
        }
        case 6: { // WalkPath (parent-follow / chase)
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (flickWanted) { transition(actor, s, 4, generator); break; }
            if (target && sees) walkTo(actor, s, target->getPosition(), dt, s.spec->moveSpeed);
            else if (hasParent) walkTo(actor, s, parentPos, dt, s.spec->moveSpeed);
            else transition(actor, s, 2, generator);
            break;
        }
        case 5: { // Walk
            if (inRange) { transition(actor, s, 3, generator); break; }
            if (!sees && !hasParent) { transition(actor, s, 2, generator); break; }
            if (target && sees) walkTo(actor, s, target->getPosition(), dt, s.spec->moveSpeed);
            else if (hasParent) walkTo(actor, s, parentPos, dt, s.spec->moveSpeed);
            break;
        }
        case 3: { // Attack
            stop(actor);
            const float frames = s.stateTime * 30.0f;
            if (!s.attackFired && frames >= float(p2chappy::DwarfAttackEatFrame)) {
                s.attackFired = true;
                doBite(actor, s, generator, p2chappy::DwarfAttackEatFrame);
            }
            if (!s.swallowFired && frames >= float(p2chappy::DwarfAttackSwallowFrame)) {
                s.swallowFired = true;
                int white = 0;
                doSwallow(actor, s, generator, white);
            }
            if (frames >= float(p2chappy::DwarfAttackSwallowFrame) + 2.0f) {
                if (inRange) transition(actor, s, 3, generator);
                else transition(actor, s, 5, generator);
            }
            break;
        }
        case 4: { // Flick
            stop(actor);
            if (!s.flickFired && s.stateTime * 30.0f >= 31.0f) {
                s.flickFired = true;
                doFlick(actor, s, generator, 31);
            }
            if (s.stateTime >= FLICK_DURATION_S) transition(actor, s, 5, generator);
            break;
        }
        default:
            stop(actor);
            transition(actor, s, 2, generator);
            break;
        }
    } else { // KING
        // #884 round 2: one rate-limited line while Walk/Turn refuses the
        // attack, so a zero-attack run still shows why (no target, target
        // under the chin, outside +-30 deg, beyond 3D 130) and where the
        // Pikmin are relative to the tongue.
        s.kingGateLogS += dt;
        if ((s.state == 0 || s.state == 6) && !inRange && s.kingGateLogS >= KING_GATE_LOG_S) {
            s.kingGateLogS = 0.0f;
            const p2chappymouth::Vec3 apos = mouthVec(pos);
            p2chappymouth::Vec3 tpos{0.0f, 0.0f, 0.0f};
            if (target) tpos = mouthVec(target->getPosition());
            const p2chappymouth::king::Gate gate =
                p2chappymouth::king::gateReason(apos, s.heading, target ? &tpos : nullptr);
            const float dy = target ? tpos.y - apos.y : 0.0f;
            const float goalDist = std::sqrt(p2chappymouth::king::sqrXZ(s.walker.goal, apos));
            const float goalAng = p2chappymouth::king::angDist(apos, s.heading, s.walker.goal) * 180.0f / PI_F;
            // Round 3: under_chin/band/front count FREE Pikmin only (front =
            // reachable by a tongue slot), latched = Pikmin latched to the
            // body; stuck_self = the flick tier count; flick_timer/flick_need
            // = source mFlickTimer vs the isStartFlick threshold.
            const int stuckSelf = stuckPikminCount(actor);
            std::printf("P2_CHAPPY_KING_GATE generator=%u source_id=%u state=%s reason=%s searched=%d "
                        "search_delay=%.0f target_kind=%c dist_xz=%.1f dist_3d=%.1f ang_deg=%.1f under_chin=%d "
                        "band=%d front=%d goal_dist=%.1f goal_ang_deg=%.1f goal_home=%d no_target_frames=%.0f "
                        "heading_deg=%.1f draw_yaw_deg=%.1f latched=%d stuck_self=%d flick_timer=%.2f flick_need=%d "
                        "navi_near=%d hits=%d\n",
                        generator, s.spec->source, fsmStateName(s.family, s.state),
                        s.kingSearched ? p2chappymouth::king::gateName(gate) : "no_search", s.kingSearched ? 1 : 0,
                        s.walker.searchDelay, s.tickTargetKind, s.tickTargetDist,
                        target ? std::sqrt(s.tickTargetDist * s.tickTargetDist + dy * dy) : -1.0f, s.tickTargetAngDeg,
                        s.kingCensus.underChin, s.kingCensus.band, s.kingCensus.front, goalDist, goalAng,
                        p2chappymouth::king::goalIsHome(s.walker) ? 1 : 0, s.walker.noTargetFrames,
                        wrapPi(s.heading) * 180.0f / PI_F, wrapPi(actor->getDirection()) * 180.0f / PI_F,
                        s.kingCensus.latched, stuckSelf, s.kingFlickTimer,
                        p2chappymouth::king::flickThreshold(stuckSelf), s.kingNaviNear, s.kingFlickHits);
            std::fflush(stdout);
        }
        switch (s.state) {
        case 0: { // Walk: source StateWalk::exec (kingChappyState.cpp:69-107)
            // walkFunc first: pursue mGoalPosition (the target while one is
            // held) with the source turn law, stall check, checkTurn,
            // incubation and setNextGoal (king::walkTick). Then checkFlick
            // (skipped on a Turn tick: the turn transit's blend makes it
            // return early) and checkAttack on the post-walkFunc heading (a
            // stall drops the target). king::walkStateStep orders the
            // transits: Turn > Flick/WarCry > Attack > Hide > walk. The
            // pre-round-2 port went Walk -> WarCry on every sighting; round 2
            // let Attack win over Flick and flicked on 3 stuck Pikmin only.
            namespace K = p2chappymouth::king;
            const p2chappymouth::Vec3 apos = mouthVec(pos);
            p2chappymouth::Vec3 tpos{0.0f, 0.0f, 0.0f};
            if (target) tpos = mouthVec(target->getPosition());
            const float frames = dt * 30.0f;
            const float r0 = rand01(s), r1 = rand01(s);
            K::WalkInputs in;
            in.walker = K::walkTick(s.walker, apos, s.heading, target ? &tpos : nullptr, frames, r0, r1);
            actor->setDirection(s.heading);
            in.hasTarget = target != nullptr;
            in.flickStart = in.walker != K::WalkTurn && kingCheckFlick(actor, s, frames);
            in.shout = in.flickStart && kingShout(actor, s);
            in.inRange = target && !s.walker.targetDropped && K::attackGate(apos, s.heading, tpos);
            const K::WalkNext next = K::walkStateStep(in);
            if (next != K::NextWalk) { kingApply(actor, s, generator, next, "walk"); break; }
            const Vector3f drive(std::sin(s.heading) * s.spec->moveSpeed, 0.0f, std::cos(s.heading) * s.spec->moveSpeed);
            actor->inputDrive(drive);
            actor->mVelocity.set(drive);
            break;
        }
        case 4: { // WarCry: source StateWarCry (kingChappyState.cpp:1588-1680),
                  // cry.bca; KEYEVENT_4 (frame 65) shakes off stuck and nearby
                  // Pikmin and nearby captains and resets the flick timer.
            stop(actor);
            const float frames = s.stateTime * 30.0f;
            if (!s.flickFired && frames >= float(p2chappymouth::king::CryShakeFrame)) {
                s.flickFired = true;
                doKingShake(actor, s, generator, p2chappymouth::king::CryShakeFrame, false);
            }
            const int endFrame = std::max(clipFrames(s.spec->enumName, "cry"), p2chappymouth::king::CryShakeFrame + 1);
            if (frames >= float(endFrame)) {
                std::printf("P2_CHAPPY_WARCRY generator=%u source_id=53\n", generator);
                std::fflush(stdout);
                transition(actor, s, 0, generator);
            }
            break;
        }
        case 6: { // Turn: source StateTurn::exec (kingChappyState.cpp:1800-1823):
                  // turnFunc toward the target, else the goal, until under
                  // fp07 (target) / 0.5 rad; then checkDead + checkFlick,
                  // whose transit wins (king::turnStateStep).
            namespace K = p2chappymouth::king;
            stop(actor);
            const float frames = dt * 30.0f;
            const p2chappymouth::Vec3 aim = target ? mouthVec(target->getPosition()) : s.walker.goal;
            const bool done = K::turnTick(s.heading, mouthVec(pos), aim, target != nullptr, frames);
            actor->setDirection(s.heading);
            const bool flickStart = kingCheckFlick(actor, s, frames);
            const bool shout = flickStart && kingShout(actor, s);
            const K::WalkNext next = K::turnStateStep(done || s.stateTime >= KING_TURN_MAX_S, flickStart, shout);
            if (next != K::NextTurn) kingApply(actor, s, generator, next, "turn");
            break;
        }
        case 1: { // Attack
            // Source StateAttack (kingChappyState.cpp:148-250): from KEYEVENT_3
            // (frame 40) eatPikmin runs every frame with the tongue's kamu1..9
            // slots, captains touching a slot are attacked, and KEYEVENT_END
            // goes to Swallow when Pikmin were eaten, else Walk. Every integer
            // frame of the window is evaluated (a long tick catches up).
            // Adaptation: no tongue terrain trace (:162-185); on flat ground the
            // tongue sphere never reaches the floor, so the window runs to END.
            stop(actor);
            const float frames = s.stateTime * 30.0f;
            const p2chappymouth::Profile* prof = p2chappymouth::profileForSource(s.spec->source);
            const int endFrame = std::max(clipFrames(s.spec->enumName, "attack"), prof ? prof->lastFrame + 1 : 0);
            if (prof) {
                const int upto = std::min(int(frames), prof->lastFrame);
                for (int f = std::max(prof->firstFrame, s.lastEatFrame + 1); f <= upto; ++f) {
                    const EatStats st = doEat(actor, s, generator, f);
                    if (s.winFreeBefore < 0) s.winFreeBefore = st.freeBefore;
                    s.winEligible = std::max(s.winEligible, st.eligible);
                    s.winRefusedNoHost += st.refusedNoHost;
                    s.winNearestBehind = s.winNearestBehind || st.nearestBehind;
                    s.winLegacyBehind = s.winLegacyBehind || st.legacyBehind;
                    s.winNaviHits += kingNaviContact(actor, s, *prof, f);
                    s.lastEatFrame = f;
                }
            }
            if (frames >= float(endFrame)) {
                EatStats win;
                win.eligible = s.winEligible;
                win.captured = s.eatenThisAttack;
                win.freeBefore = s.winFreeBefore < 0 ? 0 : s.winFreeBefore;
                win.refusedNoHost = s.winRefusedNoHost;
                win.nearestBehind = s.winNearestBehind;
                win.legacyBehind = s.winLegacyBehind;
                logBite(actor, s, generator, endFrame, prof ? prof->firstFrame : 0, s.lastEatFrame, win,
                        prof ? prof->slots : 0);
                std::printf("P2_CHAPPY_ATTACK generator=%u source_id=%u frame=%d navi=%d piki=0 eaten=%d "
                            "eaten_count=%d\n",
                            generator, s.spec->source, endFrame, s.winNaviHits > 0 ? 1 : 0,
                            s.eatenThisAttack > 0 ? 1 : 0, s.eatenThisAttack);
                std::fflush(stdout);
                transition(actor, s, s.eatenThisAttack > 0 ? 12 : 0, generator);
            }
            break;
        }
        case 3: { // Flick: source StateFlick (kingChappyState.cpp:823-918),
                  // flick.bca; KEYEVENT_3 (frame 35) tramples, shakes off and
                  // resets the flick timer; KEYEVENT_END -> Walk.
            stop(actor);
            const float frames = s.stateTime * 30.0f;
            if (!s.flickFired && frames >= float(p2chappymouth::king::FlickEventFrame)) {
                s.flickFired = true;
                doKingShake(actor, s, generator, p2chappymouth::king::FlickEventFrame, true);
            }
            const int endFrame =
                std::max(clipFrames(s.spec->enumName, "flick"), p2chappymouth::king::FlickEventFrame + 1);
            if (frames >= float(endFrame)) transition(actor, s, 0, generator);
            break;
        }
        case 5: { // Damage (bomb stun; bombs have no host equivalent)
            stop(actor);
            if (s.stateTime >= clipDuration(s.spec->enumName, s.clip)) transition(actor, s, 0, generator);
            break;
        }
        case 8: { // Hide
            stop(actor);
            if (s.stateTime >= 1.0f) transition(actor, s, 9, generator);
            break;
        }
        case 9: { // HideWait (burrowed; ip02 adaptation)
            stop(actor);
            if (s.stateTime >= KING_HIDEWAIT_S) transition(actor, s, 10, generator);
            break;
        }
        case 10: { // Appear
            stop(actor);
            if (s.stateTime >= clipDuration(s.spec->enumName, s.clip)) {
                std::printf("P2_CHAPPY_APPEAR generator=%u source_id=53\n", generator);
                std::fflush(stdout);
                transition(actor, s, 11, generator);
            }
            break;
        }
        case 11: { // Caution
            stop(actor);
            if (s.stateTime >= clipDuration(s.spec->enumName, s.clip)) transition(actor, s, 0, generator);
            break;
        }
        case 7: { // Eat -> Swallow (bomb path has no host equivalent)
            stop(actor);
            transition(actor, s, 12, generator);
            break;
        }
        case 12: { // Swallow (source StateSwallow: type1, swallowPikmin at
                   // KEYEVENT_END, kingChappyState.cpp:2168-2178)
            stop(actor);
            if (s.stateTime >= clipDuration(s.spec->enumName, s.clip)) {
                if (!s.swallowFired) {
                    s.swallowFired = true;
                    int white = 0;
                    doSwallow(actor, s, generator, white);
                }
                transition(actor, s, 0, generator);
            }
            break;
        }
        default:
            stop(actor);
            transition(actor, s, 0, generator);
            break;
        }
    }

    setPhase(s);
    s.logTimer += dt;
    if (s.logTimer >= 1.0f) {
        s.logTimer = 0.0f;
        const Vector3f now = actor->getPosition();
        std::printf("P2_CHAPPY_FSM_POS generator=%u source_id=%u state=%s x=%.2f y=%.2f z=%.2f health=%.1f\n",
                    generator, s.spec->source, fsmStateName(s.family, s.state), now.x, now.y, now.z,
                    actor->mHealth);
        std::fflush(stdout);
    }
}

bool pc_p2_chappy_draw(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse)
{
    if (!actor || !bankLoaded) return false;
    PelletView* view = static_cast<PelletView*>(actor);
    auto it = actors.find(view);
    if (it == actors.end()) return false;
    const p2chappy::SpeciesParams* spec = it->second;
    auto bank = banks.find(spec->enumName);
    if (bank == banks.end() || bank->second.clips.empty()) return false;
    // The P2 FSM decides the clip/phase every tick; the host animator motion
    // is never consulted (it reflects the suppressed P1 AI).
    std::string clip = "wait1";
    float phase = 0.0f;
    bool dead = corpse;
    auto ft = fsms.find(view);
    if (ft != fsms.end()) {
        clip = ft->second.clip;
        phase = ft->second.phase;
        if (actor->mHealth <= 0.0f || actor->mDeadState != 0) dead = true;
    } else {
        dead = corpse || actor->mHealth <= 0.0f || actor->mDeadState != 0;
    }
    if (dead) {
        const char* prefs[] = {"dead", "dead1", "pdead1", nullptr};
        for (const char** p = prefs; *p; ++p) {
            if (bank->second.clips.count(*p)) { clip = *p; break; }
        }
        phase = 1.0f;
    } else if (!bank->second.clips.count(clip)) {
        if (const char* c = clipForState(bank->second,
                                         ft != fsms.end() ? ft->second.family
                                                          : p2chappyfsm::familyForSource(spec->source),
                                         ft != fsms.end() ? ft->second.state : 7)) {
            clip = c;
        } else {
            return false;
        }
    }
    auto shapesIt = shapes.find(std::string(spec->enumName) + "|" + clip);
    if (shapesIt == shapes.end() || shapesIt->second.empty()) return false;
    size_t index = 0;
    if (!dead && shapesIt->second.size() > 1) {
        float ph = phase;
        if (!(ph >= 0.0f && ph <= 1.0f)) ph = 0.0f;
        index = size_t(ph * float(shapesIt->second.size() - 1) + 0.5f);
        if (index >= shapesIt->second.size()) index = shapesIt->second.size() - 1;
    } else {
        index = shapesIt->second.size() - 1;
    }
    Shape* shape = shapesIt->second[index];
    // Per-actor first-draw markers (frog pattern): every bound actor logs
    // its own live draw and its own corpse draw with its campaign token, so
    // a bystander drawn first can never consume another actor's evidence.
    if (!corpse) {
        if (drawnLive.insert(view).second) {
            const unsigned generator = actor->mGenerator ? pc_p2_campaign_token(actor) : 0;
            std::printf("P2_CHAPPY_DRAW corpse=0 species=%s generator=%u clip=%s\n", spec->enumName,
                        generator, clip.c_str());
            std::fflush(stdout);
        }
    } else if (drawnCorpse.insert(view).second) {
        const unsigned generator = actor->mGenerator ? pc_p2_campaign_token(actor) : 0;
        unsigned logged = generator;
        if (!logged) {
            auto cg = corpseGenerators.find(view);
            if (cg != corpseGenerators.end()) logged = cg->second;
        }
        std::printf("P2_CHAPPY_DRAW corpse=1 species=%s generator=%u clip=%s\n", spec->enumName,
                    logged, clip.c_str());
        std::fflush(stdout);
    }
    {
        auto known = lastClip.find(view);
        if (known == lastClip.end() || known->second != clip) {
            lastClip[view] = clip;
            const unsigned generator = actor->mGenerator ? pc_p2_campaign_token(actor) : 0;
            std::printf("P2_CHAPPY_STATE generator=%u source_id=%u clip=%s\n", generator,
                        spec->source, clip.c_str());
            std::fflush(stdout);
        }
    }
    shape->updateAnim(gfx, matrix, nullptr, actor);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    return true;
}
