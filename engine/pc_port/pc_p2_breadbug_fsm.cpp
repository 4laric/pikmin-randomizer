#include "pc_p2_breadbug_fsm.h"

#include <cmath>
#include <cstdlib>
#include <map>
#include <sstream>

namespace p2breadbugfsm {
namespace {
constexpr float kFltMax = 3.402823466e+38f;
float toRad(float degrees) { return degrees * (kPi / 180.0f); }
bool finite(float v) { return std::isfinite(v); }
bool finite(const Vec3& v) { return finite(v.x) && finite(v.y) && finite(v.z); }
float sqr2D(const Vec3& a, const Vec3& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}
float clampAbs(float v, float limit) { return v > limit ? limit : (v < -limit ? -limit : v); }
} // namespace

float roundAng(float angle) {
    if (angle < 0.0f) angle += kTau * std::ceil(-angle / kTau);
    angle = std::fmod(angle, kTau);
    return angle < 0.0f ? angle + kTau : angle;
}
float angDist(float first, float second) {
    const float distance = roundAng(first - second);
    return distance >= kPi ? distance - kTau : distance;
}

void applyVariant(Params& params, bool giant) {
    // PanModokiBase::Obj() defaults vs OoPanModoki::Obj() (panModoki.cpp:133,1709)
    // and walkFunc (panModoki.cpp:926-929).
    params.giant = giant;
    params.carrySizeDiff = giant ? kGiantCarrySizeDiff : kCarrySizeDiff;
    params.waypointSlack = giant ? kGiantWaypointSlack : kWaypointSlack;
}

const char* stateName(State state) {
    switch (state) {
    case State::Dead: return "dead";
    case State::Walk: return "walk";
    case State::Back: return "back";
    case State::Pulled: return "pulled";
    case State::Appear: return "appear";
    case State::Hide: return "hide";
    case State::Damage: return "damage";
    case State::Wait: return "wait";
    case State::Stick: return "stick";
    case State::Sucked: return "sucked";
    case State::CarryEnd: return "carryend";
    default: return "null";
    }
}

const char* animDefaultName(int anim) {
    // PanModokiBase.h:242-253 names; enemyanimmgr.txt file stems.
    static const char* names[AnimCount] = {"dead", "move1", "move2", "type1", "type2",
                                           "type3", "type4", "type5", "wait1"};
    return anim >= 0 && anim < AnimCount ? names[anim] : "";
}

// ---------------------------------------------------------------- params
bool parseEnemyParm(std::istream& in, Params& out, std::string& error) {
    std::string text, line;
    while (std::getline(in, line)) {
        const std::size_t hash = line.find('#');
        if (hash != std::string::npos) line.erase(hash);
        text += line;
        text += '\n';
    }
    std::vector<std::map<std::string, float>> blocks(1);
    std::istringstream words(text);
    std::string word;
    while (words >> word) {
        if (word == "{_eof}") { blocks.emplace_back(); continue; }
        if (word.size() == 6 && word.front() == '{' && word.back() == '}') {
            std::string kind, value;
            if (!(words >> kind >> value)) { error = "truncated parameter row"; return false; }
            char* end = nullptr;
            const float v = std::strtof(value.c_str(), &end);
            if (!end || *end != '\0' || !finite(v)) { error = "bad parameter value " + word; return false; }
            const std::string tag = word.substr(1, 4);
            auto& block = blocks.back();
            if (block.count(tag) && block[tag] != v) { error = "conflicting duplicate " + tag; return false; }
            block[tag] = v;
        }
    }
    const std::map<std::string, float>* general = nullptr;
    const std::map<std::string, float>* proper = nullptr;
    const std::map<std::string, float>* creature = nullptr;
    for (const auto& block : blocks) {
        if (block.count("fp00") && block.count("fp27")) {
            if (general) { error = "duplicate general block"; return false; }
            general = &block;
        } else if (block.count("s003")) {
            creature = &block;
        } else if (general && !proper && block.count("fp16") && block.count("ip01")) {
            proper = &block;
        }
    }
    if (!general) { error = "missing general block"; return false; }
    Params p = out;
    auto f = [](const std::map<std::string, float>& b, const char* tag, float& dst) {
        auto it = b.find(tag);
        if (it != b.end()) dst = it->second;
    };
    if (creature) f(*creature, "s003", p.accel);
    const auto& g = *general;
    f(g, "fp00", p.health); f(g, "fp06", p.moveSpeed); f(g, "fp08", p.turnSpeed);
    f(g, "fp28", p.maxTurnAngle); f(g, "fp10", p.homeRadius); f(g, "fp14", p.searchDistance);
    f(g, "fp15", p.searchAngle);
    if (proper) {
        const auto& q = *proper;
        f(q, "fp00", p.nestScale); f(q, "fp16", p.walkAnimSpeed); f(q, "fp02", p.fastTurnSpeed);
        f(q, "fp05", p.maxFastTurnAngle); f(q, "fp03", p.carrySpeed); f(q, "fp04", p.suckDamage);
        f(q, "fp06", p.pressDamage); f(q, "fp14", p.waitTime); f(q, "fp15", p.hideTime);
        auto it = q.find("ip01");
        if (it != q.end()) p.maxCarryWeight = int(it->second);
    }
    if (!(p.health > 0.0f) || !(p.accel > 0.0f) || p.moveSpeed < 0.0f || p.turnSpeed < 0.0f
        || p.maxTurnAngle < 0.0f || !(p.homeRadius > 0.0f) || p.carrySpeed < 0.0f || p.suckDamage < 0.0f
        || p.pressDamage < 0.0f || p.waitTime < 0.0f || p.hideTime < 0.0f || p.maxCarryWeight < 1
        || p.walkAnimSpeed < 0.0f || p.fastTurnSpeed < 0.0f || p.maxFastTurnAngle < 0.0f) {
        error = "nonphysical parameter value";
        return false;
    }
    p.retail = true;
    out = p;
    return true;
}

// ---------------------------------------------------------------- bank
Bank defaultBank() {
    Bank bank;
    auto make = [](int frames, std::vector<KeyEvent> events) {
        Clip c;
        c.frames = frames;
        c.events = std::move(events);
        return c;
    };
    // Retail GPVE01 panmodoki/enemyanimmgr.txt rows and PanModoki anim.szs
    // bca durations (dumped by the root extractor, experimental/
    // pikmin2_breadbug_own_assets.py). Replaced by the staged bank.
    bank.clip[AnimDead] = make(99, {});
    bank.clip[AnimWalk] = make(54, {{10, KeyLoopStart}, {39, KeyLoopEnd}});
    bank.clip[AnimBack] = make(49, {{10, KeyLoopStart}, {39, KeyLoopEnd}});
    bank.clip[AnimPulled] = make(49, {{5, KeyLoopStart}, {10, KeyLoopEnd}});
    bank.clip[AnimAppear] = make(69, {});
    bank.clip[AnimHide] = make(49, {{20, Key2}});
    bank.clip[AnimDamage] = make(54, {});
    bank.clip[AnimCarry] = make(39, {{10, KeyLoopStart}, {29, KeyLoopEnd}});
    bank.clip[AnimWait] = make(59, {{10, KeyLoopStart}, {49, KeyLoopEnd}});
    for (int a = 0; a < AnimCount; ++a) bank.clip[a].name = animDefaultName(a);
    return bank;
}

bool parseBank(std::istream& in, Bank& bank, std::string& error) {
    std::string word;
    int count = 0;
    if (!(in >> word >> count) || word != "P2_BREADBUG_BANK_1" || count < 1 || count > AnimCount) {
        error = "bad bank header";
        return false;
    }
    Bank next = bank;
    bool seen[AnimCount] = {};
    for (int n = 0; n < count; ++n) {
        int id = -1, frames = 0, events = 0, poses = 0;
        Clip clip;
        if (!(in >> word >> id >> clip.name >> frames >> events) || word != "clip" || id < 0
            || id >= AnimCount || seen[id] || frames < 2 || frames > 10000 || events < 0 || events > 64) {
            error = "bad clip row";
            return false;
        }
        seen[id] = true;
        clip.frames = frames;
        int previous = -1;
        for (int e = 0; e < events; ++e) {
            KeyEvent k;
            if (!(in >> k.frame >> k.type) || k.frame < 0 || k.frame >= frames || k.frame < previous
                || k.type < 0 || k.type > 2000) {
                error = "bad key event";
                return false;
            }
            previous = k.frame;
            clip.events.push_back(k);
        }
        if (!(in >> poses) || poses < 0 || poses > 24) { error = "bad pose count"; return false; }
        for (int p = 0; p < poses; ++p) {
            int frame;
            if (!(in >> frame) || frame < 0 || frame >= frames
                || (!clip.poses.empty() && frame <= clip.poses.back())) {
                error = "bad pose frame";
                return false;
            }
            clip.poses.push_back(frame);
        }
        clip.staged = true;
        next.clip[id] = clip;
    }
    if (!(in >> word) || word != "END") { error = "missing END"; return false; }
    bank = next;
    return true;
}

// ---------------------------------------------------------------- animator
std::size_t Animator::lowest(float minimum) const {
    std::size_t best = mClip->events.size();
    float bestFrame = kFltMax;
    for (std::size_t i = 0; i < mClip->events.size(); ++i) {
        const int frame = mClip->events[i].frame;
        if (frame >= int(minimum) && float(frame) < bestFrame) { bestFrame = float(frame); best = i; }
    }
    return best;
}

void Animator::start(const Clip* clip, int anim) {
    mClip = clip;
    mAnim = anim;
    mTimer = 0.0f;
    mKey = clip ? lowest(0.0f) : 0;
    mFinish = mCompleted = false;
    mPlaying = false;
}

void Animator::setFrame(float frame) {
    if (!mClip) return;
    mTimer = frame;
    mKey = lowest(frame);
}

int Animator::firstKeyFrame() const {
    return mClip && !mClip->events.empty() ? mClip->events.front().frame : 0;
}

void Animator::animate(float dt) {
    mPlaying = false;
    if (!mClip) return;
    mTimer += mSpeed * dt;
    bool loopEndFound = false;
    const auto& events = mClip->events;
    while (!loopEndFound && mKey < events.size() && events[mKey].frame < int(mTimer)) {
        trigger(events[mKey].type);
        if (events[mKey].type == KeyLoopEnd && !mFinish) {
            int start = -1;
            for (std::size_t j = mKey; j-- > 0;) if (events[j].type == KeyLoopStart) { start = events[j].frame; break; }
            mTimer = start >= 0 ? float(start) : 0.0f;
            loopEndFound = true;
            break;
        }
        ++mKey;
    }
    if (loopEndFound) mKey = lowest(mTimer);
    if (mTimer >= float(mClip->frames)) {
        mTimer = float(mClip->frames) - 1.0f;
        if (!mCompleted) { mCompleted = true; trigger(KeyEnd); }
    }
}

// ---------------------------------------------------------------- PelletCarry
bool PelletCarry::pull(int who, const Vec3& vel, float amount) {
    if (state == PcsIdle || state == who) {
        state = who;
        velocity = vel;
        strength = amount;
        return true;
    }
    if (amount > strength) {
        state = who;
        velocity = vel;
        strength = amount;
        timer = 0.5f;
        return true;
    }
    return false;
}
bool PelletCarry::pullable(int who, float amount) const {
    if (state == PcsIdle || state == who) return true;
    return amount > strength;
}
void PelletCarry::giveup(int who) {
    if (state != who) return;
    state = PcsIdle;
    velocity = Vec3();
    strength = 0.0f;
}

// ---------------------------------------------------------------- fsm helpers
int Fsm::randInt(int count) {
    mRng = mRng * 1664525u + 1013904223u;
    const int v = int((float(mRng >> 8) / 16777216.0f) * float(count));
    return v >= count ? count - 1 : v;
}

const PelletInfo* Fsm::find(std::uint64_t id) const {
    if (!id || !mIn) return nullptr;
    for (std::size_t i = 0; i < mIn->count; ++i)
        if (mIn->pellets[i].id == id) return &mIn->pellets[i];
    return nullptr;
}

float Fsm::angDistTo(const Vec3& t) const {
    return angDist(std::atan2(t.x - mPos.x, t.z - mPos.z), mFaceDir);
}
float Fsm::turnToTarget(const Vec3& target, float speed, float maxDeg) {
    const float a = angDistTo(target);
    mFaceDir = roundAng(clampAbs(a * speed, toRad(maxDeg)) + mFaceDir);
    return a;
}
void Fsm::setTargetSpeed(float speed) {
    mTargetVel = {speed * std::sin(mFaceDir), mTargetVel.y, speed * std::cos(mFaceDir)};
}
void Fsm::walkToTarget(const Vec3& target, float speed, float turn, float maxDeg) {
    turnToTarget(target, turn, maxDeg);  // EnemyFunc::walkToTarget (enemyAction.cpp:2102-2107)
    setTargetSpeed(speed);
}

void Fsm::addDamage(float damage, DamageKind kind) {
    if (mOut->damageKind == DamageKind::None) mOut->hpBefore = mHealth;
    mHealth -= damage;
    mOut->hpAfter = mHealth;
    mOut->damageKind = kind;
}

void Fsm::endStickCargo() {
    if (mStuck) mOut->release = true;
    mStuck = false;
}

// isTargetable (panModoki.cpp:1532-1564).
bool Fsm::isTargetable(const PelletInfo& p) const {
    if (!p.pickable) return false;   // panmodokiCarryable + P1 exclusions (host)
    if (p.otherTekiStuck) return false;
    const float s = (float(p.carryMin) + float(p.carryMax)) * 0.5f;
    if (p.id == mCarryPellet) return mCarry.pullable(PcsBreadbug, s);
    // Another pellet's PelletCarry: Pikmin carriers hold it at their strength.
    return p.pikiStrength <= 0.0f || s > p.pikiStrength;
}

// canTarget(pelMinWeight, weightLimit): PanModoki.h:16 strictly lighter than the
// limit (weightLimit > pelMinWeight), OoPanModoki.h:16 at or above it
// (weightLimit <= pelMinWeight); the limit is proper ip01.
bool Fsm::canTarget(int pelMinWeight) const {
    return mParams.giant ? (mParams.maxCarryWeight <= pelMinWeight) : (mParams.maxCarryWeight > pelMinWeight);
}

// findNearestPellet (panModoki.cpp:1047-1088).
const PelletInfo* Fsm::findNearestPellet() const {
    const PelletInfo* best = nullptr;
    const float maxAngle = toRad(mParams.searchAngle);
    float minDist = mParams.searchDistance < 0.0f ? kFltMax : mParams.searchDistance * mParams.searchDistance;
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const PelletInfo& p = mIn->pellets[i];
        if (!p.pickable || !p.alive || p.captured || !isTargetable(p)) continue;
        if (!canTarget(p.carryMin)) continue;
        if (std::fabs(p.bottomY - mPos.y) > 10.0f) continue;
        if (std::fabs(angDistTo(p.pos)) > maxAngle) continue;
        const float d = sqr2D(mPos, p.pos);
        if (d < minDist) { best = &p; minDist = d; }
    }
    return best;
}

bool Fsm::canBack() const {  // panModoki.cpp:1029-1041
    if (!cargo()) return false;
    return mCarry.pullable(PcsBreadbug, mCarryStrength);
}

// releaseCarryTarget (panModoki.cpp:1112-1133).
void Fsm::releaseCarryTarget() {
    if (cargo()) {
        if (mState == State::Back) mOut->releaseReverse = true;
        endStickCargo();
        mCarry.giveup(PcsBreadbug);
    } else {
        endStickCargo();
    }
    mTarget = 0;
}

// checkNearHomeGraphIndex (panModoki.cpp:1139-1175), nearest open waypoint.
void Fsm::checkNearHomeGraphIndex() {
    const int idx = mIn && mIn->route ? mIn->route->nearest(mPos) : -1;
    mWp1 = mWp2 = mWp3 = idx;
    WayPointInfo wp;
    if (idx >= 0 && mIn->route->get(idx, wp)) mNextWp = wp.pos;
    else mNextWp = mHome;
    turnToTarget(mNextWp, 1.0f, 360.0f);
}

// findNextRoutePoint (panModoki.cpp:770-850).
void Fsm::findNextRoutePoint(bool stuck) {
    const Route* route = mIn ? mIn->route : nullptr;
    if (!route) { mNextWp = mHome; return; }
    if (mFindNextRouteCounter > 0 && stuck) {
        if (mWp3 == mWp2 && mWp2 == mWp1) { mNextWp = mHome; return; }
        const int idx = route->nearest(mPos);   // nearest edge -> nearest open waypoint
        WayPointInfo wp;
        if (idx < 0 || !route->get(idx, wp)) { mNextWp = mHome; return; }
        if (idx == mWp2) {
            // Same edge as before: back off 100 units against the face direction.
            mNextWp = mPos;
            mNextWp.x = -(std::sin(mFaceDir) * 100.0f - mNextWp.x);
            mNextWp.z = -(std::cos(mFaceDir) * 100.0f - mNextWp.z);
            return;
        }
        mWp3 = mWp2;
        mWp2 = idx;
        mNextWp = wp.pos;
        return;
    }
    WayPointInfo current;
    if (mWp2 < 0 || !route->get(mWp2, current)) { mNextWp = mHome; return; }
    int candidates[8];
    int count = 0;
    for (int l = 0; l < current.linkCount && l < 8; ++l) {
        WayPointInfo link;
        if (route->get(current.links[l], link) && link.open && link.linkCount > 1) candidates[count++] = link.index;
    }
    if (count) {
        const int idx = candidates[randInt(count)];
        if (count == 1 || idx != mWp3) {
            mWp3 = mWp2;
            mWp2 = idx;
        }
    }
    WayPointInfo next;
    if (route->get(mWp2, next)) mNextWp = next.pos;
}

// isReachToGoal (panModoki.cpp:995-1023).
bool Fsm::isReachToGoal(float radius) {
    if (mHealth <= 0.0f) return false;
    const PelletInfo* t = cargo();
    if (mTarget && t) radius += t->radius;
    else radius *= 2.0f;
    if (sqr2D(mPos, mNextWp) < radius * radius) {
        if (mState == State::Walk && mTarget && t && sqr2D(t->pos, mPos) < radius * radius) transit(State::Stick);
        mMoveSpeedTimer = 0;
        return true;
    }
    return false;
}

// walkFunc (panModoki.cpp:921-989); the floor-normal push is not ported.
void Fsm::walkFunc() {
    float moveSpeed = mParams.moveSpeed;
    float rotSpeed = mParams.maxTurnAngle;
    float rotAccel = mParams.turnSpeed;
    // panModoki.cpp:926-929: the slack box is 100 (PanModoki), 150 (OoPanModoki).
    if (std::fabs(mNextWp.x - mPos.x) < mParams.waypointSlack && std::fabs(mNextWp.z - mPos.z) < mParams.waypointSlack) {
        ++mMoveSpeedTimer;
        if (mMoveSpeedTimer > 100) moveSpeed *= 0.5f;
        if (mMoveSpeedTimer > 200) mMoveSpeedTimer = 0;
    } else {
        mMoveSpeedTimer = 0;
    }
    if (!mFindNextRouteCounter) {
        const PelletInfo* p = findNearestPellet();
        mTarget = p ? p->id : 0;
        if (p) mNextWp = p->pos;
    } else {
        rotSpeed = mParams.maxFastTurnAngle;
        rotAccel = mParams.fastTurnSpeed;
    }
    walkToTarget(mNextWp, moveSpeed, rotAccel, rotSpeed);
    if (!mFindNextRouteCounter) {
        if (++mMoveToWpTimer > 60) {
            if (sqr2D(mPos, mPrevCheck) < 100.0f) {
                mFindNextRouteCounter = 120;
                mTarget = 0;
                findNextRoutePoint(true);
            }
            mPrevCheck = mPos;
            mMoveToWpTimer = 0;
        }
    }
}

// setPathFinder (panModoki.cpp:1439-1502) with the host's synchronous path.
void Fsm::setPathFinder() {
    mPathfinding = false;
    mPath.clear();
    const Route* route = mIn ? mIn->route : nullptr;
    if (!route) return;
    if (mWp1 < 0) return;
    // #898 fix: start from the nearest carry-route EDGE when the host has one,
    // taking whichever end gives the shorter trip home (distance to the end +
    // path length); else the nearest waypoint.
    int starts[2] = {-1, -1};
    int ea = -1, eb = -1;
    if (route->nearestEdge(mPos, ea, eb)) { starts[0] = ea; starts[1] = eb; }
    else starts[0] = route->nearest(mPos);
    std::vector<int> nodes;
    float bestCost = 0.0f;
    for (int from : starts) {
        if (from < 0) continue;
        std::vector<int> cand;
        if (!route->path(from, mWp1, cand) || cand.empty()) continue;
        float cost = 0.0f;
        WayPointInfo a, b;
        if (route->get(cand.front(), a)) cost += std::sqrt(sqr2D(mPos, a.pos));
        for (std::size_t i = 1; i < cand.size(); ++i)
            if (route->get(cand[i - 1], a) && route->get(cand[i], b)) cost += std::sqrt(sqr2D(a.pos, b.pos));
        if (nodes.empty() || cost < bestCost) { nodes = cand; bestCost = cost; }
    }
    if (nodes.empty()) return;
    mPath = nodes;
    mWp3 = mWp2;
    mWp2 = nodes.front();
    WayPointInfo wp;
    if (route->get(mWp2, wp)) mNextWp = wp.pos;
    mPathfinding = true;
}

// #898 port fallback (no route path): home reached when within the relaxed
// home radius the source uses for a slowed carry (isCarryToGoal, 60 units).
bool Fsm::isCarryHomeDirect() const {
    return sqr2D(mPos, mHome) < 60.0f * 60.0f;
}

// isCarryToGoal (panModoki.cpp:856-915).
bool Fsm::isCarryToGoal() {
    if (!mPathfinding) return false;
    float homeR = mParams.homeRadius;
    if (mMoveSpeedTimer > 100) homeR = 60.0f;
    if (sqr2D(mPos, mHome) < homeR * homeR) {
        mPathfinding = false;
        return true;
    }
    float rad2 = 30.0f, rad3 = 50.0f;
    if (mMoveSpeedTimer > 100) { rad2 = 60.0f; rad3 = 75.0f; }
    rad2 *= rad2;
    rad3 *= rad3;
    const float d = sqr2D(mPos, mNextWp);
    const PelletInfo* p = cargo();
    const float something = p ? sqr2D(p->pos, mNextWp) : -1.0f;
    if (d < rad2 || (something > 0.0f && something < rad3)) {
        mMoveSpeedTimer = 0;
        if (mWp2 == mWp1) {
            mNextWp = mHome;
            if (something < rad3) return true;
        } else {
            for (std::size_t i = 0; i < mPath.size(); ++i) {
                if (mPath[i] != mWp2) continue;
                mWp3 = mWp2;
                mWp2 = i + 1 < mPath.size() ? mPath[i + 1] : mWp1;
                WayPointInfo wp;
                if (mIn->route && mIn->route->get(mWp2, wp)) mNextWp = wp.pos;
                return false;
            }
        }
    }
    return false;
}

// setCarryDir / changeCarryDir (panModoki.cpp:1281-1316).
void Fsm::setCarryDir(bool direct) {
    mCarryDir = direct ? mFaceDir : roundAng(mFaceDir + kPi);
    if (const PelletInfo* p = cargo()) {
        mCarryStrength = (float(p->carryMin) + float(p->carryMax)) * 0.5f;
        if (mCarryPellet != p->id) {
            // The PelletCarry belongs to the pellet: Pikmin already hauling it
            // hold it at their strength.
            mCarry.reset();
            if (p->pikiStrength > 0.0f) mCarry.pull(PcsCarry, p->velocity, p->pikiStrength);
            mCarryPellet = p->id;
        }
    }
}
void Fsm::changeCarryDir(bool direct) {
    mCarryDir = direct ? mFaceDir : roundAng(mFaceDir + kPi);
}

// carryTarget (panModoki.cpp:1190-1275); slope push not ported.
void Fsm::carryTarget(float scale) {
    const float speed = scale * mParams.carrySpeed;
    float turn = mParams.turnSpeed, maxTurn = mParams.maxTurnAngle;
    const PelletInfo* p = cargo();
    if (mState == State::Pulled) {
        turn *= 0.5f;
        if (p && !p->inGoal) {
            mNextWp = p->pos;
            mNextWp.x = -(p->velocity.x * 10.0f - mNextWp.x);
            mNextWp.z = -(p->velocity.z * 10.0f - mNextWp.z);
        }
    }
    const Vec3 wp = mNextWp;
    if (sqr2D(mPos, mNextWp) < 10000.0f) {
        turn = mParams.fastTurnSpeed;
        maxTurn = mParams.maxFastTurnAngle;
    }
    if (!p) return;
    mFaceDir = mCarryDir;
    walkToTarget(wp, speed, turn, maxTurn);
    mCarryDir = mFaceDir;
    const Vec3 vel{mTargetVel.x, p->velocity.y, mTargetVel.z};
    if (mCarry.pull(PcsBreadbug, vel, mCarryStrength)) {
        mOut->pulled = true;
        mOut->pullVelocity = vel;
        mOut->pullStrength = mCarryStrength;
    }
    mFaceDir = roundAng(mFaceDir + angDistTo(p->pos));  // face the cargo
}

// pressCallBack (panModoki.cpp:462-515), mCanPressType = 0 for PanModoki.
bool Fsm::pressCallBack() {
    if (mHealth <= 0.0f) return false;
    switch (mState) {
    case State::Walk: case State::Wait: case State::Stick: case State::Back: case State::Pulled:
        mCurrentVel = Vec3();
        mTargetVel = Vec3();
        mCanReactToPress = false;
        transit(State::Damage);
        return true;
    default:
        return false;
    }
}

// ---------------------------------------------------------------- fsm
void Fsm::init(const Params& params, const Bank& bank, const Vec3& home, float faceDir,
               std::uint32_t seed, const Route* route) {
    mParams = params;
    mBank = bank;
    mRng = seed ? seed : 1u;
    mHome = mPos = mNextWp = mPrevCheck = mStartPos = home;
    mFaceDir = mCarryDir = roundAng(faceDir);
    mTargetVel = mCurrentVel = Vec3();
    mHealth = params.health;
    mTarget = mCarryPellet = 0;
    mStuck = false;
    mCarry.reset();
    mWp1 = mWp2 = mWp3 = -1;
    mPath.clear();
    mPathfinding = mCanReactToPress = mNoInterrupt = mConstrained = mHidden = false;
    mFindNextRouteCounter = mMoveToWpTimer = mMoveSpeedTimer = mStateTimer = 0;
    mAnim = Animator();
    mState = mNext = State::Null;
    TickInput stub;
    stub.position = home;
    stub.route = route;
    TickOutput sink;
    mIn = &stub;
    mOut = &sink;
    transit(State::Appear);  // mFsm->start(this, PANMODOKI_Appear)
    mIn = nullptr;
    mOut = nullptr;
}

void Fsm::transit(State next) {
    if (mState == State::Pulled) { /* cleanup: fadePulledSmokeEffect */ }
    if (next == State::Null) next = State::Walk;  // documented guard (see header)
    const int prevAnim = mAnim.anim();
    mState = next;
    mOut->entered.push_back(next);
    const Clip* c = mBank.clip;
    switch (next) {
    case State::Dead:  // StateDead::init
        if (cargo() || mStuck) { endStickCargo(); mTarget = 0; }
        mAnim.start(&c[AnimDead], AnimDead);
        mAnim.setSpeed(kDefaultAnimSpeed);
        mCurrentVel = mTargetVel = Vec3();
        break;
    case State::Walk:  // StateWalk::init
        if (mAnim.anim() != AnimWalk) {
            mAnim.start(&c[AnimWalk], AnimWalk);
            mAnim.setSpeed(kDefaultAnimSpeed * mParams.walkAnimSpeed);
        }
        mNext = State::Null;
        mTarget = 0;
        break;
    case State::Back:  // StateBack::init
        if (prevAnim != AnimBack) mAnim.start(&c[AnimBack], AnimBack);
        mAnim.setSpeed(kDefaultAnimSpeed * mParams.walkAnimSpeed);
        if (prevAnim == AnimPulled) mAnim.setFrame(float(mAnim.firstKeyFrame()));
        mTargetVel = mCurrentVel = Vec3();
        if (cargo()) mOut->stopCargo = true;
        setPathFinder();
        mNext = State::Null;
        mBackTimer = mBackStuck = 0;
        mBackCheck = mPos;
        break;
    case State::Pulled:  // StatePulled::init
        mAnim.start(&c[AnimPulled], AnimPulled);
        mAnim.setSpeed(kDefaultAnimSpeed * mParams.walkAnimSpeed);
        if (prevAnim == AnimBack) mAnim.setFrame(float(mAnim.firstKeyFrame()));
        mTargetVel = mCurrentVel = Vec3();
        mNext = State::Null;
        break;
    case State::Appear:  // StateAppear::init
        mHidden = false;
        mAnim.start(&c[AnimAppear], AnimAppear);
        mAnim.setSpeed(kDefaultAnimSpeed);
        checkNearHomeGraphIndex();
        mConstrained = true;
        break;
    case State::Hide:  // StateHide::init
        mAnim.start(&c[AnimHide], AnimHide);
        mAnim.setSpeed(kDefaultAnimSpeed);
        mTargetVel = Vec3();
        mStateTimer = 0;
        break;
    case State::Damage: {  // StateDamage::init
        mAnim.start(&c[AnimDamage], AnimDamage);
        mAnim.setSpeed(kDefaultAnimSpeed);
        mTargetVel = Vec3();
        if (cargo() || mStuck) {
            mCarry.giveup(PcsBreadbug);
            endStickCargo();
            mTarget = 0;
        }
        const bool suck = mCanReactToPress;
        addDamage(suck ? mParams.suckDamage : mParams.pressDamage, suck ? DamageKind::Suck : DamageKind::Press);
        break;
    }
    case State::Wait:  // StateWait::init
        mAnim.start(&c[AnimWait], AnimWait);
        mAnim.setSpeed(kDefaultAnimSpeed);
        mTargetVel = Vec3();
        mStateTimer = 0;
        mNext = State::Walk;
        break;
    case State::Stick: {  // StateStick::init
        if (mAnim.anim() != AnimWalk) {
            mAnim.start(&c[AnimWalk], AnimWalk);
            mAnim.setSpeed(kDefaultAnimSpeed * mParams.walkAnimSpeed);
        }
        mTargetVel = mCurrentVel = Vec3();
        const PelletInfo* p = cargo();
        if (!p || !isTargetable(*p) || !p->slotFree) {
            transit(State::Walk);
            return;
        }
        mStateTimer = 0;
        mNext = State::Walk;
        break;
    }
    case State::Sucked:  // StateSucked::init
        mAnim.start(&c[AnimWait], AnimWait);
        mAnim.setSpeed(kDefaultAnimSpeed);
        if (cargo() || mStuck) { endStickCargo(); mTarget = 0; }
        mCanReactToPress = true;
        break;
    case State::CarryEnd:  // StateCarryEnd::init
        mConstrained = true;
        mStartPos = mPos;
        break;
    default:
        break;
    }
}

void Fsm::execState() {
    TickOutput& o = *mOut;
    const PelletInfo* p = cargo();
    switch (mState) {
    case State::Dead:
        if (mAnim.is(KeyEnd)) o.killRequest = true;
        break;
    case State::Walk: {
        if (mHealth <= 0.0f) { transit(State::Dead); return; }
        if (isReachToGoal(mParams.carrySizeDiff)) findNextRoutePoint(false);
        if (mState != State::Walk) return;  // isReachToGoal -> Stick
        if (mNext == State::Null) walkFunc();
        if (mAnim.is(KeyEnd)) transit(mNext == State::Null ? State::Walk : mNext);
        break;
    }
    case State::Back: {
        if (mHealth <= 0.0f) { transit(State::Dead); return; }
        if (mNext == State::Null) {
            if (!mPathfinding) setPathFinder();       // isEndPathFinder retry
            if (mPathfinding) {
                carryTarget(1.0f);
            } else {
                // #898 port fallback: no route-graph path home (the P1 carry
                // graph can be split by closed gates, or have no edge near the
                // nest). Standing still with the cargo is a deadlock, so haul
                // straight at the nest; the watchdog below bounds a wedge.
                mNextWp = mHome;
                carryTarget(1.0f);
                if (isCarryHomeDirect()) {
                    mTargetVel = mCurrentVel = Vec3();
                    transit(State::CarryEnd);
                    return;
                }
            }
            // #898 port watchdog (not in source): the P1 map can wedge a
            // hauled carcass against a wall on the way to a route node. Every
            // 60 ticks without 10 units of progress, skip to the next node of
            // the path (home after the last); after kBackStuckRelease such
            // checks in a row, drop the cargo (releaseCarryTarget -> Wait) so
            // neither the Breadbug nor the cargo is stuck forever.
            if (++mBackTimer >= 60) {
                mBackTimer = 0;
                if (sqr2D(mPos, mBackCheck) < 100.0f) {
                    if (++mBackStuck >= kBackStuckRelease) {
                        mOut->backStuckRelease = true;
                        releaseCarryTarget();
                        transit(State::Wait);
                        return;
                    }
                    mOut->backStuckSkip = true;
                    bool advanced = false;
                    for (std::size_t i = 0; i < mPath.size(); ++i) {
                        if (mPath[i] != mWp2) continue;
                        mWp3 = mWp2;
                        mWp2 = i + 1 < mPath.size() ? mPath[i + 1] : mWp1;
                        WayPointInfo wp;
                        if (mIn->route && mIn->route->get(mWp2, wp)) { mNextWp = wp.pos; advanced = true; }
                        break;
                    }
                    if (!advanced) mNextWp = mHome;
                } else {
                    mBackStuck = 0;
                }
                mBackCheck = mPos;
            }
            if (!canBack()) {
                transit(State::Pulled);
                return;
            } else if (!mTarget) {
                mAnim.finish();
                mNext = State::Walk;
            }
            if (isCarryToGoal()) {
                mTargetVel = mCurrentVel = Vec3();
                transit(State::CarryEnd);
                return;
            }
            if ((p = cargo())) {
                const bool check = (p->carcass && !p->alive) || std::fabs(p->pos.y - mPos.y) > 50.0f
                                || p->otherTekiStuck;
                if (check) {
                    releaseCarryTarget();
                    transit(State::Wait);
                    return;
                }
            }
        }
        if (mAnim.is(KeyEnd)) {
            const State next = mNext;
            transit(next);
            if (next == State::Pulled) changeCarryDir(true);
        }
        break;
    }
    case State::Pulled: {
        if (mHealth <= 0.0f) { transit(State::Dead); return; }
        if (mNext == State::Null) {
            if (p) {
                if (canBack()) {
                    if (!p->inGoal && p->alive) {
                        transit(State::Back);
                        return;
                    }
                } else {
                    const bool check = (p->carcass && !p->alive) || std::fabs(p->pos.y - mPos.y) > 50.0f
                                    || p->otherTekiStuck;
                    if (check) {
                        releaseCarryTarget();
                        transit(State::Wait);
                        return;
                    }
                }
            } else {
                mAnim.finish();
                mNext = State::Walk;
            }
        }
        carryTarget(1.0f);
        if (mAnim.is(KeyEnd)) {
            const State next = mNext;
            transit(next);
            if (next == State::Back) changeCarryDir(false);
            return;
        }
        if ((p = cargo()) && p->inGoal) mNoInterrupt = true;  // checkSucked
        break;
    }
    case State::Appear:
        if (mAnim.is(KeyEnd)) {
            transit(State::Walk);
            mConstrained = false;
        }
        break;
    case State::Hide: {
        if (mAnim.is(KeyEnd)) {
            mHealth = mParams.health;       // CG_GENERALPARMS mHealth
            o.refilled = true;
            if (mTarget || mStuck) o.consumeCargo = true;  // endCarry
            mStuck = false;
            mTarget = 0;
            mCarry.reset();
            mCarryPellet = 0;
            mHidden = true;
        } else if (mTarget) {
            o.holdCargo = true;
        }
        if (!mTarget) {
            if (++mStateTimer > mParams.hideTime) transit(State::Appear);
        }
        break;
    }
    case State::Damage:
        if (mAnim.is(KeyEnd)) transit(mHealth <= 0.0f ? State::Dead : State::Wait);
        break;
    case State::Wait:
        if (mHealth <= 0.0f) { transit(State::Dead); return; }
        ++mStateTimer;
        if (float(mStateTimer) > mParams.waitTime && !mAnim.isFinishing()) mAnim.finish();
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    case State::Stick: {
        if (mHealth <= 0.0f) { transit(State::Dead); return; }
        if (!p) { transit(State::Walk); return; }
        const float dist = sqr2D(p->pos, mPos);
        float stickR = p->radius + 1.2f * mParams.carrySizeDiff;
        stickR *= stickR;
        if (dist < stickR) {
            if (isTargetable(*p) && p->slotFree) {
                mCurrentVel = mTargetVel = Vec3();
                o.stickTo = p->id;
                mStuck = true;
                setCarryDir(false);
                transit(State::Back);
            } else {
                transit(State::Walk);
            }
        } else {
            walkToTarget(p->pos, 0.5f * mParams.moveSpeed, mParams.fastTurnSpeed, mParams.maxFastTurnAngle);
            turnToTarget(p->pos, mParams.fastTurnSpeed, mParams.maxFastTurnAngle);
            const float rad = 2.5f * mParams.carrySizeDiff;
            if (++mStateTimer > 200 || dist > rad * rad || !isTargetable(*p)) transit(mNext);
        }
        break;
    }
    case State::Sucked:
        mCanReactToPress = true;
        break;
    case State::CarryEnd: {
        if (mHealth <= 0.0f) { transit(State::Dead); return; }
        o.holdCargo = mTarget != 0;
        const Vec3 diff{mHome.x - mPos.x, 0.0f, mHome.z - mPos.z};
        if (std::fabs(diff.x) < 2.0f && std::fabs(diff.z) < 2.0f) {
            o.homeNudge = diff;  // onSetPosition(home)
            if (mAnim.is(KeyLoopEnd)) { transit(State::Hide); return; }
        } else {
            turnToTarget(mStartPos, mParams.turnSpeed, mParams.maxTurnAngle);
            o.homeNudge = {diff.x * 0.05f, 0.0f, diff.z * 0.05f};  // forceMovePosition
        }
        if (mAnim.is(KeyEnd)) transit(State::Hide);
        break;
    }
    default:
        break;
    }
}

TickOutput Fsm::tick(const TickInput& in) {
    TickOutput out;
    if (mState == State::Null || !finite(in.position) || !finite(in.externalDamage) || in.presses < 0
        || (in.count && !in.pellets)) return out;
    out.valid = true;
    mIn = &in;
    mOut = &out;
    mPos = in.position;
    // doSimulation: mFindNextRouteCounter decrements every update.
    if (--mFindNextRouteCounter < 0) mFindNextRouteCounter = 0;
    // The host's stick truth: a cargo the host no longer holds for us.
    if (mStuck && in.held != mTarget && !in.suckFinished) {
        mStuck = false;
        mCarry.giveup(PcsBreadbug);
        mTarget = 0;
    }
    // Cargo gone from the pellet list (killed): drop the reference.
    if (mTarget && !cargo() && !in.suckFinished) {
        mStuck = false;
        mTarget = 0;
    }
    // EnemyBase::bombCallBack -> addDamage (bombs hurt; attacks do not).
    if (in.externalDamage > 0.0f) addDamage(in.externalDamage, DamageKind::External);
    // InteractSuckFinish -> suckFinish (panModoki.cpp:1381-1392).
    if (in.suckFinished && (mTarget || mStuck)) {
        mStuck = false;
        mOut->release = true;
        mCarry.giveup(PcsBreadbug);
        transit(State::Sucked);
        mTarget = 0;
    }
    // pressCallBack per thrown-Pikmin landing.
    for (int k = 0; k < in.presses; ++k)
        if (!pressCallBack()) out.pressRejected = true;
    // bounceCallback: Sucked -> Damage (container damage).
    if (in.bounced && mState == State::Sucked) transit(State::Damage);
    // The held cargo's PelletCarry: Pikmin carriers pull first.
    if (const PelletInfo* p = cargo()) {
        if (mCarryPellet == p->id) {
            if (p->pikiStrength > 0.0f) mCarry.pull(PcsCarry, p->velocity, p->pikiStrength);
            else mCarry.giveup(PcsCarry);
            if (mCarry.timer > 0.0f) mCarry.timer -= kSourceDelta;
            out.contest = true;
            out.contestPiki = p->pikiStrength;
            out.contestSelf = mCarryStrength;
        }
    }
    execState();
    out.canBack = canBack();
    // doSimulationGround (x/z): a stuck Breadbug rides its cargo (isStickTo:
    // mAcceleration = 0 and the slot drives mPosition); constrained ones hold.
    if (mStuck || mConstrained || mState == State::Dead) {
        mCurrentVel = Vec3();
    } else {
        const float blend = kSourceDelta / mParams.accel;
        mCurrentVel.x += (mTargetVel.x - mCurrentVel.x) * blend;
        mCurrentVel.z += (mTargetVel.z - mCurrentVel.z) * blend;
    }
    mAnim.animate(kSourceDelta);
    out.faceDir = mFaceDir;
    out.velocity = {mCurrentVel.x, 0.0f, mCurrentVel.z};
    out.hidden = mHidden;
    if (out.damageKind == DamageKind::None) out.hpBefore = out.hpAfter = mHealth;
    mIn = nullptr;
    mOut = nullptr;
    return out;
}

} // namespace p2breadbugfsm
