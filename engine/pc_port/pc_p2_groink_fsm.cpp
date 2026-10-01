#include "pc_p2_groink_fsm.h"
#include "pc_p2_groink_target.h"

#include <algorithm>
#include <cmath>
#include <map>
#include <sstream>

namespace p2groinkfsm {
namespace {
constexpr float kFlickBackwardAngle = -1000.0f; // EnemyFunc.h:9
constexpr float kFltMax = 3.402823466e+38f;
float toRad(float degrees) { return degrees * (kPi / 180.0f); }
bool finite(float v) { return std::isfinite(v); }
bool finite(const P2GroinkVec3& v) { return finite(v.x) && finite(v.y) && finite(v.z); }
float sqr2D(const P2GroinkVec3& a, const P2GroinkVec3& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}
float sqr3D(const P2GroinkVec3& a, const P2GroinkVec3& b) {
    const float dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}
float clampAbs(float v, float limit) { return v > limit ? limit : (v < -limit ? -limit : v); }
bool angleWithin(float angle, float degrees) { return std::fabs(angle) <= toRad(degrees); }
P2GroinkVec3 rotY(const P2GroinkVec3& v, float face) {
    const float s = std::sin(face), c = std::cos(face);
    return {v.x * c + v.z * s, v.y, -v.x * s + v.z * c};
}
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

const char* stateName(State state) {
    switch (state) {
    case State::Dead: return "dead";
    case State::Rebirth: return "rebirth";
    case State::Lost: return "lost";
    case State::Attack: return "attack";
    case State::Flick: return "flick";
    case State::Turn: return "turn";
    case State::TurnHome: return "turnhome";
    case State::TurnPath: return "turnpath";
    case State::Walk: return "walk";
    case State::WalkHome: return "walkhome";
    case State::WalkPath: return "walkpath";
    default: return "null";
    }
}

const char* animDefaultName(int anim) {
    // MiniHoudai.h:181-191 comments name search1/turn1/attack1/flick1/dead1/
    // type5; walk and rebirth stems are not named in the source.
    static const char* names[AnimCount] = {"walk", "search1", "turn1", "attack1",
                                           "flick1", "dead1", "type5", "rebirth"};
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
        if (block.count("fp00") && block.count("fp14")) {
            if (general) { error = "duplicate general block"; return false; }
            general = &block;
        } else if (block.count("s003")) {
            creature = &block;
        } else if (general && !proper && block.count("fp11") && block.count("fp12")) {
            proper = &block;
        }
    }
    if (!general) { error = "missing general block"; return false; }
    Params p = out;
    auto f = [&](const std::map<std::string, float>& b, const char* tag, float& dst) {
        auto it = b.find(tag);
        if (it != b.end()) dst = it->second;
    };
    auto i = [&](const std::map<std::string, float>& b, const char* tag, int& dst) {
        auto it = b.find(tag);
        if (it != b.end()) dst = int(it->second);
    };
    if (creature) f(*creature, "s003", p.accel);
    const auto& g = *general;
    f(g, "fp00", p.health); f(g, "fp06", p.moveSpeed); f(g, "fp08", p.turnSpeed);
    f(g, "fp28", p.maxTurnAngle); f(g, "fp09", p.territoryRadius); f(g, "fp10", p.homeRadius);
    f(g, "fp11", p.privateRadius); f(g, "fp12", p.sightRadius); f(g, "fp25", p.fov);
    f(g, "fp13", p.viewAngle); f(g, "fp14", p.searchDistance); f(g, "fp16", p.shakeChance);
    f(g, "fp17", p.shakeKnockback); f(g, "fp18", p.shakeDamage); f(g, "fp19", p.shakeRange);
    f(g, "fp21", p.maxAttackAngle); f(g, "fp22", p.attackRadius); f(g, "fp23", p.attackHitAngle);
    f(g, "fp24", p.attackDamage); f(g, "fp29", p.alertDuration);
    i(g, "ip01", p.shakeOffBlowA); i(g, "ip02", p.shakeOffSticking1); i(g, "ip03", p.shakeOffBlowB);
    i(g, "ip04", p.shakeOffSticking2); i(g, "ip05", p.shakeOffBlowC); i(g, "ip06", p.shakeOffSticking3);
    i(g, "ip07", p.shakeOffBlowD);
    if (proper) { f(*proper, "fp11", p.healthGaugeTimer); f(*proper, "fp12", p.respawnRate); }
    if (!(p.health > 0.0f) || !(p.accel > 0.0f) || !(p.searchDistance > 0.0f) || p.moveSpeed < 0.0f
        || p.turnSpeed < 0.0f || p.maxTurnAngle < 0.0f || p.homeRadius <= 0.0f
        || p.territoryRadius <= 0.0f || p.attackRadius < 0.0f || p.attackHitAngle < 0.0f
        || p.attackDamage < 0.0f || !(p.respawnRate > 0.0f) || p.healthGaugeTimer < 0.0f) {
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
    // Retail (P2_GROINK_ATTACK.md, attack1.bca sha 98fab1f1...): 44 frames.
    bank.clip[AnimAttack] = make(44, {{11, Key2}, {22, Key3}, {25, Key4}, {32, Key5}});
    // Retail key events for the other clips (minihoudai/enemyanimmgr.txt,
    // disc-verified in the root docs/PIKMIN2_CANNON_PROJECTILE_ASSETS.md:102).
    // Their total frame counts are NOT known here: the counts below are
    // PLACEHOLDERS a few frames past the last event, replaced by the staged
    // bank (bca durations).
    bank.clip[AnimWalk] = make(36, {{10, KeyLoopStart}, {18, Key2}, {25, KeyLoopEnd}});
    bank.clip[AnimSearch] = make(60, {});
    bank.clip[AnimTurn] = make(30, {{5, KeyLoopStart}, {16, KeyLoopEnd}});
    bank.clip[AnimFlick] = make(40, {{10, Key2}});
    bank.clip[AnimDead] = make(70, {{32, Key2}, {52, Key3}});
    bank.clip[AnimCarry] = make(40, {{10, KeyLoopStart}, {29, KeyLoopEnd}});
    bank.clip[AnimRebirth] = make(60, {{32, Key2}, {45, Key3}});
    for (int a = 0; a < AnimCount; ++a) bank.clip[a].name = animDefaultName(a);
    // PLACEHOLDER kuti basis: forward +Z, up +Y, 30 up / 20 ahead of the root.
    bank.muzzle = {{0.0f, 0.0f, 1.0f}, {0.0f, 1.0f, 0.0f}, {-1.0f, 0.0f, 0.0f}, {0.0f, 30.0f, 20.0f}};
    return bank;
}

// Grammar (whitespace separated):
//   P2_GROINK_BANK_1 <clipCount>
//   clip <animId 0..7> <name> <frames> <eventCount> (<frame> <type>)* <poseCount> <poseFrame>*
//   [muzzle c0x c0y c0z c1x c1y c1z c2x c2y c2z c3x c3y c3z]
//   END
bool parseBank(std::istream& in, Bank& bank, std::string& error) {
    std::string word;
    int count = 0;
    if (!(in >> word >> count) || word != "P2_GROINK_BANK_1" || count < 1 || count > AnimCount) {
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
    while (in >> word) {
        if (word == "END") { bank = next; return true; }
        if (word == "muzzle") {
            float v[12];
            for (float& x : v) if (!(in >> x) || !finite(x) || std::fabs(x) > 10000.0f) { error = "bad muzzle"; return false; }
            next.muzzle = {{v[0], v[1], v[2]}, {v[3], v[4], v[5]}, {v[6], v[7], v[8]}, {v[9], v[10], v[11]}};
            next.muzzleStaged = true;
            continue;
        }
        error = "unexpected token " + word;
        return false;
    }
    error = "missing END";
    return false;
}

// ---------------------------------------------------------------- animator
std::size_t Animator::lowest(float minimum) const {
    // AnimInfo::getLowestAnimKey: first key (list order) with the lowest
    // frame >= (int)minimum; size() when none.
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
    mFinish = mCompleted = mStopped = false;
}

void Animator::animate(float dt) {
    mPlaying = false; // doAnimationCullingOff: mCurAnim->mIsPlaying = false
    if (!mClip) return;
    mTimer += mStopped ? 0.0f : mSpeed * dt;
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

// ---------------------------------------------------------------- fsm
float Fsm::randFloat() {
    mRng = mRng * 1664525u + 1013904223u;
    return float(mRng >> 8) / 16777216.0f;
}
int Fsm::randInt(int count) {
    const int v = int(randFloat() * float(count));
    return v >= count ? count - 1 : v;
}

void Fsm::init(const Params& params, const Bank& bank, bool fixed, const P2GroinkVec3& position,
               float faceDir, std::uint32_t seed, const Route* route) {
    mParams = params;
    mBank = bank;
    mFixed = fixed;
    mRng = seed ? seed : 1u;
    mFaceDir = roundAng(faceDir);
    mPos = position;
    mHome = position;              // EnemyBase birth: mHomePosition = birth position
    mTargetVel = mCurrentVel = {};
    mCaution = 128.0f;             // onInit mHealthGaugeTimer
    mAttackWait = 0.0f;
    mUpdateTimer = 0.0f;
    mFlickTimer = 0.0f;            // EnemyBase::onInit
    mNext = State::Null;
    mNearestWp = mOldNearestWp = -1; // resetWayPoint
    TickInput stub;
    stub.position = position;
    stub.route = route;
    TickOutput sink;
    mIn = &stub;
    mOut = &sink;
    setNearestWayPoint();
    mGun.reset();                  // setupShotGun
    mShells.reset();
    mAnim = Animator();
    mState = State::Null;
    transit(State::TurnPath);      // mFsm->start(this, TurnPath)
    mIn = nullptr;
    mOut = nullptr;
}

P2GroinkMuzzle Fsm::worldMuzzle(const P2GroinkVec3& position) const {
    const P2GroinkMuzzle& m = mBank.muzzle;
    P2GroinkMuzzle w{rotY(m.column0, mFaceDir), rotY(m.column1, mFaceDir), rotY(m.column2, mFaceDir),
                     rotY(m.column3, mFaceDir)};
    w.column3 = {w.column3.x + position.x, w.column3.y + position.y, w.column3.z + position.z};
    if (!mGun.rotating()) return w;
    bool valid = false;
    const P2GroinkMuzzle r = p2_groink_rotate_vertical(w, mGun.angle(), valid);
    return valid ? r : w;
}

float Fsm::angDistTo(const P2GroinkVec3& t) const {
    return angDist(std::atan2(t.x - mPos.x, t.z - mPos.z), mFaceDir);
}
float Fsm::turnToTarget(const P2GroinkVec3& target, float speed, float maxDeg) {
    const float a = angDistTo(target);
    mFaceDir = roundAng(clampAbs(a * speed, toRad(maxDeg)) + mFaceDir);
    return a;
}
bool Fsm::turnToTargetPos(const P2GroinkVec3& target, float speed, float maxDeg, float endDeg) {
    return angleWithin(turnToTarget(target, speed, maxDeg), endDeg);
}
bool Fsm::isTargetOutOfRange(const Candidate& t, float angle) const {
    // EnemyBase.h isTargetOutOfRange(target, angle, private, sight, fov, view)
    const float x = t.pos.x - mPos.x, y = t.pos.y - mPos.y, z = t.pos.z - mPos.z;
    const float d = x * x + z * z;
    const float pr = mParams.privateRadius * mParams.privateRadius;
    const float sr = mParams.sightRadius * mParams.sightRadius;
    return (d > pr && (d > sr && std::fabs(y) < mParams.fov)) || !angleWithin(angle, viewAngle());
}
float Fsm::viewAngle() const { // MiniHoudai.cpp:364-367
    return mCaution < mParams.alertDuration ? 180.0f : mParams.viewAngle;
}
float Fsm::homeDistSq() const { return sqr2D(mPos, mHome); }

const Candidate* Fsm::searchedTarget() {
    // getSearchedTarget -> EnemyFunc::getNearestPikminOrNavi(this, viewAngle,
    // sightRadius) (enemyAction.cpp:17-139): nearest captain inside the view
    // cone, then a Pikmin strictly nearer than it wins.
    const float cone = toRad(viewAngle());
    const float radius = mParams.sightRadius < 0.0f ? kFltMax : mParams.sightRadius * mParams.sightRadius;
    float minDist = radius;
    const Candidate* navi = nullptr;
    const Candidate* piki = nullptr;
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.navi || !c.alive) continue;
        if (std::fabs(angDistTo(c.pos)) > cone) continue;
        const float d = sqr2D(c.pos, mPos);
        if (d < minDist) { navi = &c; minDist = d; }
    }
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.pikmin || !c.searchable || !c.alive) continue;
        if (std::fabs(angDistTo(c.pos)) > cone) continue;
        const float d = sqr2D(c.pos, mPos);
        if (d < minDist) { piki = &c; minDist = d; }
    }
    const Candidate* target = piki ? piki : navi;
    mLastSearched = target ? target->id : 0;
    if (target) mCaution = 0.0f;
    return target;
}

bool Fsm::attackableTarget() {
    // Obj::isAttackableTarget (MiniHoudai.cpp:492-531). The cell iterator is
    // replaced by the source sphere test over the host snapshot (captains,
    // then Pikmin); p2_groink_select_target is the source lane test.
    const P2GroinkVec3 gun = worldMuzzle(mPos).column3;
    const P2GroinkVec3 dir{std::sin(mFaceDir), 0.0f, std::cos(mFaceDir)};
    const float scale = 0.5f * mParams.searchDistance;
    const P2GroinkVec3 center{dir.x * scale + mPos.x, mPos.y, dir.z * scale + mPos.z};
    const float sphere = 0.75f * mParams.searchDistance;
    std::vector<P2GroinkTargetCandidate> lane;
    std::vector<std::size_t> index;
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!(c.navi || c.pikmin)) continue;
        if (sqr3D(c.pos, center) > sphere * sphere) continue;
        P2GroinkTargetCandidate t;
        t.position = c.pos;
        t.alive = c.alive;
        t.captain = c.navi;
        t.pikmin = c.pikmin;
        lane.push_back(t);
        index.push_back(i);
    }
    P2GroinkTargetQuery q;
    q.muzzle = gun;
    q.direction = dir;
    q.searchDistance = mParams.searchDistance;
    const P2GroinkTargetResult r = p2_groink_select_target(q, lane.data(), lane.size());
    if (!r.valid || !r.found) return false;
    mTargetPos = r.position;
    return true;
}

bool Fsm::isStartFlick(bool reset) {
    // EnemyFunc::isStartFlick (enemyAction.cpp:326-365).
    const float v = mFlickTimer >= 0.0f ? mFlickTimer + 0.5f : mFlickTimer - 0.5f;
    const int blows = int(static_cast<unsigned char>(int(v)));
    const int stuck = mIn->stuckPikmin;
    const Params& p = mParams;
    bool result;
    if (stuck < p.shakeOffSticking1) result = blows > p.shakeOffBlowA;
    else if (stuck < p.shakeOffSticking2) result = blows > p.shakeOffBlowB;
    else if (stuck < p.shakeOffSticking3) result = blows > p.shakeOffBlowC;
    else result = blows > p.shakeOffBlowD;
    if (result && reset) mFlickTimer = 0.0f;
    return result;
}

void Fsm::setNearestWayPoint() { // MiniHoudai.cpp:383-394
    mOldNearestWp = mNearestWp;
    mNearestWp = mIn->route ? mIn->route->nearest(mPos) : -1;
    WayPointInfo wp;
    if (mNearestWp >= 0 && mIn->route->get(mNearestWp, wp)) {
        mWalkTarget = wp.pos;
    } else {
        mNearestWp = -1;
        mWalkTarget = mHome;
    }
}

void Fsm::setLinkWayPoint() { // MiniHoudai.cpp:400-441
    WayPointInfo wp;
    if (mNearestWp >= 0 && mIn->route && mIn->route->get(mNearestWp, wp)) {
        int list[8];
        int counter = 0;
        const int old = mOldNearestWp;
        for (int l = 0; l < wp.linkCount && l < 8; ++l) {
            const int idx = wp.links[l];
            if (idx < 0 || idx == old) continue;
            WayPointInfo link;
            if (mIn->route->get(idx, link) && link.open) list[counter++] = idx;
        }
        if (counter != 0) {
            mOldNearestWp = mNearestWp;
            mNearestWp = list[randInt(counter)];
            WayPointInfo chosen;
            mIn->route->get(mNearestWp, chosen);
            mWalkTarget = chosen.pos;
            return;
        }
        if (old >= 0) {
            WayPointInfo back;
            if (mIn->route->get(old, back) && back.open) {
                mOldNearestWp = mNearestWp;
                mNearestWp = old;
                mWalkTarget = back.pos;
                return;
            }
        }
    }
    setNearestWayPoint();
}

void Fsm::updateHomePosition() { // getForwardHomePosition (EnemyBase.h:405-417)
    mHome = {std::sin(mFaceDir) * mParams.homeRadius + mPos.x, mPos.y,
             std::cos(mFaceDir) * mParams.homeRadius + mPos.z};
}

void Fsm::updateTargetDistance() { // MiniHoudai.cpp:463-477
    float radius = mParams.homeRadius;
    WayPointInfo wp;
    if (mNearestWp >= 0 && mIn->route && mIn->route->get(mNearestWp, wp)) radius = wp.radius;
    if (sqr2D(mPos, mWalkTarget) < radius * radius) {
        setLinkWayPoint();
        mUpdateTimer = 0.0f;
    }
    if (mUpdateTimer > 5.0f) {
        mUpdateTimer = 0.0f;
        setNearestWayPoint();
        updateHomePosition();
    }
}

void Fsm::setTargetSpeed(float speed) {
    mTargetVel = {speed * std::sin(mFaceDir), mTargetVel.y, speed * std::cos(mFaceDir)};
}

void Fsm::walkVelocity() { // MiniHoudaiState.cpp:801-808 (and WalkHome/WalkPath)
    if (mAnim.isFinishing()) mTargetVel = {};
    else if (!mFixed) setTargetSpeed(mParams.moveSpeed);
    else mTargetVel = {};
}

void Fsm::transit(State next) {
    // EnemyStateMachine::transit: cleanup(current) then init(next).
    switch (mState) {
    case State::Rebirth: break; // disableEvent(EB_NoInterrupt)
    case State::Attack: case State::Turn: case State::Walk: break; // setEmotionCaution
    case State::Flick: mAnim.setSpeed(30.0f); break; // setAnimSpeed(30)
    default: break;
    }
    if (next == State::Null) {
        // Source would index mIdToIndexArray[-1]; only malformed clip data (a
        // looping clip without LOOP_END) gets here. Restart the current motion
        // instead of leaving the FSM stateless (documented guard).
        next = mState == State::Null ? State::TurnPath : mState;
    }
    mState = next;
    mOut->entered.push_back(next);
    const Clip* c = mBank.clip;
    switch (next) {
    case State::Dead:
        mTargetVel = {};
        mAnim.start(&c[AnimDead], AnimDead);
        break;
    case State::Rebirth:
        mNext = State::Null;
        mTargetVel = {};
        mAnim.start(&c[AnimRebirth], AnimRebirth);
        break;
    case State::Lost:
        mNext = State::Null;
        mTargetVel = {};
        mAnim.start(&c[AnimSearch], AnimSearch);
        break;
    case State::Attack:
        mNext = State::Null;
        mAttackWait = 0.0f;
        mCaution = 0.0f;
        mTargetVel = {};
        mAnim.start(&c[AnimAttack], AnimAttack);
        break;
    case State::Flick:
        mNext = State::Null;
        mCaution = 0.0f;
        mTargetVel = {};
        mAnim.start(&c[AnimFlick], AnimFlick);
        mAnim.setSpeed(45.0f);
        break;
    case State::Turn:
        mUpdateTimer = 0.0f;
        mNext = State::Null;
        mTargetVel = {};
        mAnim.start(&c[AnimTurn], AnimTurn);
        break;
    case State::TurnHome: case State::TurnPath:
        mNext = State::Null;
        mTargetVel = {};
        mAnim.start(&c[AnimTurn], AnimTurn);
        break;
    case State::Walk:
        mUpdateTimer = 0.0f;
        mNext = State::Null;
        mAnim.start(&c[AnimWalk], AnimWalk);
        break;
    case State::WalkHome: case State::WalkPath:
        mNext = State::Null;
        mAnim.start(&c[AnimWalk], AnimWalk);
        break;
    default: break;
    }
}

void Fsm::doFlick() {
    // EnemyFunc::flickStickPikmin / flickNearbyPikmin / flickNearbyNavi with
    // the source shake parameters and FLICK_BACKWARD_ANGLE.
    TickOutput& o = *mOut;
    o.flick = true;
    o.flickKnockback = mParams.shakeKnockback;
    o.flickDamage = mParams.shakeDamage;
    o.flickStickAngle = roundAng(kFlickBackwardAngle + kPi);
    o.flickNearbyAngle = kFlickBackwardAngle + kPi;
    const float range = mParams.shakeRange * mParams.shakeRange;
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.pikmin || !c.stuckToSelf) continue;
        // flickChance > randFloat(); flickCreature also requires !isStickToMouth.
        if (mParams.shakeChance > randFloat() && !c.stuckToMouth) o.flickStick.push_back(c.id);
    }
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.pikmin || c.stuckToSelf) continue; // ConditionPikminNearby
        if (sqr3D(c.pos, mPos) < range) o.flickPiki.push_back(c.id);
    }
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.navi) continue;
        if (sqr3D(c.pos, mPos) < range) o.flickNavi.push_back(c.id);
    }
    mFlickTimer = 0.0f;
}

// Attack END / Lost END (withFlick) and Flick END (!withFlick) share this
// ladder: MiniHoudaiState.cpp:188-251, 337-397, 444-499.
void Fsm::stateEndDecision(bool withFlick) {
    if (mIn->health <= 0.0f) { transit(State::Dead); return; }
    if (withFlick && isStartFlick(false)) { transit(State::Flick); return; }
    const float dist = homeDistSq();
    if (dist > mParams.territoryRadius * mParams.territoryRadius) {
        transit(std::fabs(angDistTo(mHome)) <= kQuarterPi ? State::WalkHome : State::TurnHome);
        return;
    }
    if (attackableTarget()) { transit(State::Attack); return; }
    if (const Candidate* t = searchedTarget()) {
        transit(std::fabs(angDistTo(t->pos)) <= toRad(mParams.maxAttackAngle) ? State::Walk : State::Turn);
        return;
    }
    if (dist < mParams.homeRadius * mParams.homeRadius) {
        transit(std::fabs(angDistTo(mWalkTarget)) <= kQuarterPi ? State::WalkPath : State::TurnPath);
        return;
    }
    transit(std::fabs(angDistTo(mHome)) <= kQuarterPi ? State::WalkHome : State::TurnHome);
}

void Fsm::execState() {
    const Params& p = mParams;
    const float health = mIn->health;
    switch (mState) {
    case State::Dead: // MiniHoudaiState.cpp:51-71
        if (mAnim.is(Key2)) {
            mOut->deadBomb = true;
            mOut->deadMuzzle = worldMuzzle(mPos);
        }
        else if (mAnim.is(KeyEnd)) mOut->killRequest = true;
        break;
    case State::Rebirth: // :99-156
        if (mAnim.is(Key2)) {
            doFlick();
        } else if (mAnim.is(KeyEnd)) {
            if (health <= 0.0f) { transit(State::Dead); return; }
            if (isStartFlick(false)) { transit(State::Flick); return; }
            if (attackableTarget()) { transit(State::Attack); return; }
            if (const Candidate* t = searchedTarget()) {
                transit(std::fabs(angDistTo(t->pos)) <= toRad(p.maxAttackAngle) ? State::Walk : State::Turn);
                return;
            }
            transit(std::fabs(angDistTo(mWalkTarget)) <= kQuarterPi ? State::WalkPath : State::TurnPath);
        }
        break;
    case State::Lost: // :184-253
        if (mAnim.is(KeyEnd)) stateEndDecision(true);
        break;
    case State::Attack: { // :282-400
        if (mAnim.isStopped()) {
            // Both source branches resume on (lockOn && wait > 0); aiming and
            // returning differ only in isFinishShotGun.
            if (mGun.locked() && mAttackWait > 0.0f) { mAttackWait = 0.0f; mAnim.resume(); }
        }
        if (mGun.rotating()) { /* setShotGunTargetPosition: mTargetPosition */ }
        mAttackWait += kSourceDelta;
        if (health <= 0.0f || isStartFlick(false)) {
            if (mAnim.isStopped()) mAnim.resume();
            mAnim.finish();
        }
        if (mAnim.is(Key2)) {
            mAttackWait = 0.0f;
            mAnim.stop();
            mGun.start();
        } else if (mAnim.is(Key3)) {
            // createSmokeLargeEffect / finishChargeEffect (effects only)
        } else if (mAnim.is(Key4)) {
            if (!mAnim.isFinishing() || !(health <= 0.0f)) {
                // MiniHoudaiShotGunMgr::emitShotGun (MiniHoudaiShotGun.cpp:407-451)
                std::array<P2GroinkVec3, P2GroinkVolley::kVolleySize> samples{};
                for (auto& s : samples) s = {randFloat(), randFloat(), randFloat()};
                const P2GroinkMuzzle muzzle = worldMuzzle(mPos);
                const auto e = mShells.emit(muzzle, mGun.speed(), samples);
                mOut->volley += e.valid ? int(e.count) : 0;
                mOut->burst = p2groinkburst::summarize(mShells, e);
                mOut->shotFired = true;
                mOut->volleyMuzzle = muzzle;
                mOut->volleySpeed = mGun.speed();
                mOut->volleyAngle = mGun.angle();
                mOut->volleyTarget = mTargetPos;
            }
        } else if (mAnim.is(Key5)) {
            mAttackWait = 0.0f;
            mAnim.stop();
            mGun.finish();
        } else if (mAnim.is(KeyEnd)) {
            stateEndDecision(true);
        }
        break;
    }
    case State::Flick: // :430-502
        if (mAnim.is(Key2)) doFlick();
        else if (mAnim.is(KeyEnd)) stateEndDecision(false);
        break;
    case State::Turn: { // :532-589
        if (health <= 0.0f) { mNext = State::Dead; mAnim.finish(); }
        else if (isStartFlick(false)) { mNext = State::Flick; mAnim.finish(); }
        else if (attackableTarget()) { mNext = State::Attack; mAnim.finish(); }
        else if (const Candidate* t = searchedTarget()) {
            mCaution = 0.0f;
            const float a = turnToTarget(t->pos, p.turnSpeed, p.maxTurnAngle);
            if (isTargetOutOfRange(*t, a)) { mNext = State::Lost; mAnim.finish(); }
            else if (angleWithin(a, p.maxAttackAngle)) { mNext = State::Walk; mAnim.finish(); }
        } else if (homeDistSq() < p.homeRadius * p.homeRadius) {
            mNext = turnToTargetPos(mWalkTarget, p.turnSpeed, p.maxTurnAngle, 45.0f) ? State::WalkPath : State::TurnPath;
            mAnim.finish();
        } else {
            mNext = turnToTargetPos(mHome, p.turnSpeed, p.maxTurnAngle, 45.0f) ? State::WalkHome : State::TurnHome;
            mAnim.finish();
        }
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::TurnHome: // :616-649 (both target branches turn home)
        if (health <= 0.0f) { mNext = State::Dead; mAnim.finish(); }
        else if (isStartFlick(false)) { mNext = State::Flick; mAnim.finish(); }
        else if (attackableTarget()) { mNext = State::Attack; mAnim.finish(); }
        else {
            searchedTarget();
            if (turnToTargetPos(mHome, p.turnSpeed, p.maxTurnAngle, 45.0f)) { mNext = State::WalkHome; mAnim.finish(); }
        }
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    case State::TurnPath: { // :675-711
        updateHomePosition();
        if (health <= 0.0f) { mNext = State::Dead; mAnim.finish(); }
        else if (isStartFlick(true)) { mNext = State::Flick; mAnim.finish(); }
        else if (attackableTarget()) { mNext = State::Attack; mAnim.finish(); }
        else if (const Candidate* t = searchedTarget()) {
            const float a = turnToTarget(t->pos, p.turnSpeed, p.maxTurnAngle);
            mNext = angleWithin(a, p.maxAttackAngle) ? State::Walk : State::Turn;
            mAnim.finish();
        } else if (turnToTargetPos(mWalkTarget, p.turnSpeed, p.maxTurnAngle, 45.0f)) {
            mNext = State::WalkPath;
            mAnim.finish();
        }
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::Walk: { // :738-821
        float turnSpeed = p.turnSpeed, maxTurn = p.maxTurnAngle;
        if (mAnim.isFinishing()) { turnSpeed = 0.01f; maxTurn = 1.0f; }
        if (health <= 0.0f) { mNext = State::Dead; mAnim.finish(); }
        else if (isStartFlick(false)) { mNext = State::Flick; mAnim.finish(); }
        else {
            const float dist = homeDistSq();
            if (dist > p.territoryRadius * p.territoryRadius) { mNext = State::Lost; mAnim.finish(); }
            else if (attackableTarget()) { mNext = State::Attack; mAnim.finish(); }
            else if (const Candidate* t = searchedTarget()) {
                mCaution = 0.0f;
                const float a = turnToTarget(t->pos, turnSpeed, maxTurn);
                if (isTargetOutOfRange(*t, a)) { mNext = State::Lost; mAnim.finish(); }
                else if (!(std::fabs(a) <= toRad(p.maxAttackAngle))) { mNext = State::Turn; mAnim.finish(); }
            } else if (dist < p.homeRadius * p.homeRadius) {
                mNext = turnToTargetPos(mWalkTarget, turnSpeed, maxTurn, 45.0f) ? State::WalkPath : State::TurnPath;
                mAnim.finish();
            } else {
                mNext = turnToTargetPos(mHome, turnSpeed, maxTurn, 45.0f) ? State::WalkHome : State::TurnHome;
                mAnim.finish();
            }
        }
        walkVelocity();
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::WalkHome: { // :847-931
        float turnSpeed = p.turnSpeed, maxTurn = p.maxTurnAngle;
        if (mAnim.isFinishing()) { turnSpeed = 0.01f; maxTurn = 1.0f; }
        if (health <= 0.0f) { mNext = State::Dead; mAnim.finish(); }
        else if (isStartFlick(false)) { mNext = State::Flick; mAnim.finish(); }
        else {
            const float dist = homeDistSq();
            const float a = turnToTarget(mHome, turnSpeed, maxTurn);
            if (dist < p.homeRadius * p.homeRadius) {
                if (attackableTarget()) { mNext = State::Attack; mAnim.finish(); }
                else if (const Candidate* t = searchedTarget()) {
                    mNext = std::fabs(angDistTo(t->pos)) <= toRad(p.maxAttackAngle) ? State::Walk : State::Turn;
                    mAnim.finish();
                } else {
                    mNext = std::fabs(angDistTo(mWalkTarget)) <= kQuarterPi ? State::WalkPath : State::TurnPath;
                    mAnim.finish();
                }
            } else if (attackableTarget()) { mNext = State::Attack; mAnim.finish(); }
            else if (!(std::fabs(a) <= kQuarterPi)) { mNext = State::TurnHome; mAnim.finish(); }
        }
        walkVelocity();
        mUpdateTimer += kSourceDelta;
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::WalkPath: { // :956-1018
        updateHomePosition();
        float turnSpeed = p.turnSpeed, maxTurn = p.maxTurnAngle;
        if (mAnim.isFinishing()) { turnSpeed = 0.01f; maxTurn = 1.0f; }
        if (health <= 0.0f) { mNext = State::Dead; mAnim.finish(); }
        else if (isStartFlick(true)) { mNext = State::Flick; mAnim.finish(); }
        else if (attackableTarget()) { mNext = State::Attack; mAnim.finish(); }
        else if (const Candidate* t = searchedTarget()) {
            const float a = turnToTarget(t->pos, turnSpeed, maxTurn);
            mNext = angleWithin(a, p.maxAttackAngle) ? State::Walk : State::Turn;
            mAnim.finish();
        } else if (!turnToTargetPos(mWalkTarget, turnSpeed, maxTurn, 45.0f)) {
            mNext = State::TurnPath;
            mAnim.finish();
        }
        walkVelocity();
        mUpdateTimer += 0.5f * kSourceDelta;
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    default: break;
    }
}

void Fsm::forceFinishShotGun() { mShells.reset(); }

void Fsm::startRebirth(const TickInput& in) {
    TickOutput sink;
    mIn = &in;
    mOut = &sink;
    mPos = in.position;
    transit(State::Rebirth);
    mIn = nullptr;
    mOut = nullptr;
}

TickOutput Fsm::tick(const TickInput& in) {
    TickOutput out;
    if (mState == State::Null || !finite(in.position) || !finite(in.health) || in.damageHits < 0
        || (in.count && !in.candidates)) return out;
    out.valid = true;
    mIn = &in;
    mOut = &out;
    mPos = in.position;
    // EnemyBase::addDamage per hit: EB_FlickEnabled is never disabled for
    // MiniHoudai, so every hit adds 1 to mFlickTimer and raises EB_TakingDamage.
    mFlickTimer += float(in.damageHits);
    mTakingDamage = in.damageHits > 0;
    // Obj::doUpdate: updateCaution, updateTargetDistance, FSM exec, shotgun.
    if (in.colliding || mTakingDamage || in.stuckPikmin != 0) mCaution = 0.0f;
    if (mCaution < mParams.alertDuration) mCaution += kSourceDelta;
    updateTargetDistance();
    const bool wasLocked = mGun.locked();
    execState();
    mGun.update(worldMuzzle(mPos).column3, mTargetPos, mParams.searchDistance, mParams.attackRadius, kSourceDelta);
    out.lockedOn = !wasLocked && mGun.locked();
    // Obj::doUpdateCommon -> MiniHoudaiShotGunMgr::doUpdateCommon: every live
    // shell traces once, then sweeps receivers (MiniHoudaiShotGun.cpp:86-255).
    if (mShells.activeCount() && in.trace) {
        mShells.update(mPos, kSourceDelta, in.trace, in.traceContext);
        out.terminals = int(mShells.terminalCount());
        for (std::size_t s = 0; s < mShells.segmentCount(); ++s) {
            const auto& seg = mShells.segments()[s];
            const float dx = seg.end.x - seg.start.x, dy = seg.end.y - seg.start.y, dz = seg.end.z - seg.start.z;
            const float dist = std::sqrt(dx * dx + dy * dy + dz * dz);
            if (!(dist > 0.0f)) continue;
            const P2GroinkVec3 mid{(seg.start.x + seg.end.x) * 0.5f, (seg.start.y + seg.end.y) * 0.5f,
                                   (seg.start.z + seg.end.z) * 0.5f};
            const float search = dist + mParams.attackHitAngle;
            P2GroinkHitInput hi;
            hi.start = seg.start;
            hi.end = seg.end;
            hi.radius = mParams.attackRadius;
            hi.terminalRadius = mParams.attackHitAngle;
            hi.damage = mParams.attackDamage;
            hi.terminal = seg.terminal;
            for (std::size_t i = 0; i < in.count; ++i) {
                const Candidate& c = in.candidates[i];
                if (!c.alive || sqr3D(c.pos, mid) > search * search) continue;
                P2GroinkHitCandidate hc;
                hc.position = c.pos;
                hc.alive = c.alive;
                hc.owner = c.owner;
                hc.cellRadius = c.cellRadius;
                hc.kind = c.navi ? P2GroinkCandidateKind::Captain
                        : c.pikmin ? P2GroinkCandidateKind::Pikmin
                        : c.teki ? P2GroinkCandidateKind::Enemy : P2GroinkCandidateKind::Other;
                const P2GroinkHitCommand cmd = p2_groink_classify_hit(hi, hc);
                if (cmd.valid && cmd.kind != P2GroinkHitKind::None) out.hits.push_back({c.id, seg.slot, seg.primary, cmd});
            }
        }
    }
    // doSimulationGround (enemyBase.cpp:1864-1878), x/z only; the host owns y.
    const float blend = kSourceDelta / mParams.accel;
    mCurrentVel.x += (mTargetVel.x - mCurrentVel.x) * blend;
    mCurrentVel.z += (mTargetVel.z - mCurrentVel.z) * blend;
    if (mFixed) mCurrentVel = {}; // EB_Constrained (MiniHoudai.cpp:42-44)
    // doAnimation: clear the latch, then advance.
    mAnim.animate(kSourceDelta);
    out.faceDir = mFaceDir;
    out.velocity = {mCurrentVel.x, 0.0f, mCurrentVel.z};
    mIn = nullptr;
    mOut = nullptr;
    return out;
}

} // namespace p2groinkfsm
