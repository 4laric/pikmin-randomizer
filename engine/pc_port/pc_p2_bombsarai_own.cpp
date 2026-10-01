#include "pc_p2_bombsarai_own.h"

#include <cmath>
#include <cstdlib>
#include <map>
#include <sstream>

namespace p2bsown {
namespace {
constexpr float kFlickBackwardAngle = -1000.0f; // EnemyFunc.h FLICK_BACKWARD_ANGLE
constexpr float kFltMax = 3.402823466e+38f;
constexpr float kHalfPi = 0.5f * kPi;
float toRad(float degrees) { return degrees * (kPi / 180.0f); }
bool finite(float v) { return std::isfinite(v); }
bool finite(const Vec3& v) { return finite(v.x) && finite(v.y) && finite(v.z); }
float sqrXZ(const Vec3& a, const Vec3& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}
float sqr3D(const Vec3& a, const Vec3& b) {
    const float dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}
float clampAbs(float v, float limit) { return v > limit ? limit : (v < -limit ? -limit : v); }
float roundAng(float angle) {
    if (angle < 0.0f) angle += kTau * std::ceil(-angle / kTau);
    angle = std::fmod(angle, kTau);
    return angle < 0.0f ? angle + kTau : angle;
}
float angDist(float first, float second) {
    const float distance = roundAng(first - second);
    return distance >= kPi ? distance - kTau : distance;
}

using Block = std::map<std::string, float>;
bool parseBlocks(std::istream& in, std::vector<Block>& blocks, std::string& error) {
    std::string text, line;
    while (std::getline(in, line)) {
        const std::size_t hash = line.find('#');
        if (hash != std::string::npos) line.erase(hash);
        text += line;
        text += '\n';
    }
    blocks.assign(1, Block{});
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
            Block& block = blocks.back();
            if (block.count(tag) && block[tag] != v) { error = "conflicting duplicate " + tag; return false; }
            block[tag] = v;
        }
    }
    return true;
}
void take(const Block& b, const char* tag, float& dst) {
    auto it = b.find(tag);
    if (it != b.end()) dst = it->second;
}
} // namespace

const char* stateName(State state) {
    switch (state) {
    case State::Dead: return "Dead";
    case State::Damage: return "Damage";
    case State::Wait: return "Wait";
    case State::BombWait: return "BombWait";
    case State::Move: return "Move";
    case State::BombMove: return "BombMove";
    case State::Supply: return "Supply";
    case State::Release: return "Release";
    case State::Fall: return "Fall";
    case State::TakeOff1: return "TakeOff1";
    case State::TakeOff2: return "TakeOff2";
    case State::Flick: return "Flick";
    case State::BombFlick: return "BombFlick";
    default: return "Null";
    }
}

const char* animDefaultName(int anim) {
    static const char* names[AnimCount] = {"dead1", "fall1", "flick1", "bflick1", "mogaki1",
                                           "release1", "run1", "run2", "supli1", "takeoff1",
                                           "takeoff2", "type5", "wait1", "wait2"};
    return anim >= 0 && anim < AnimCount ? names[anim] : "";
}

// ---------------------------------------------------------------- params
bool parseEnemyParm(std::istream& in, Params& out, std::string& error) {
    std::vector<Block> blocks;
    if (!parseBlocks(in, blocks, error)) return false;
    const Block* general = nullptr;
    const Block* proper = nullptr;
    const Block* creature = nullptr;
    for (const Block& block : blocks) {
        if (block.count("fp00") && block.count("fp14")) {
            if (general) { error = "duplicate general block"; return false; }
            general = &block;
        } else if (block.count("s003")) {
            creature = &block;
        } else if (general && !proper && block.count("fp01") && block.count("fp40")) {
            proper = &block;
        }
    }
    if (!general) { error = "missing general block"; return false; }
    if (!proper) { error = "missing BombSarai proper block"; return false; }
    Params p = out;
    if (creature) take(*creature, "s003", p.accel);
    const Block& g = *general;
    take(g, "fp00", p.health); take(g, "fp31", p.regenRate); take(g, "fp06", p.moveSpeed);
    take(g, "fp08", p.turnSpeed); take(g, "fp28", p.maxTurnAngle); take(g, "fp09", p.territoryRadius);
    take(g, "fp10", p.homeRadius); take(g, "fp12", p.sightRadius); take(g, "fp13", p.viewAngle);
    take(g, "fp16", p.shakeChance); take(g, "fp17", p.shakeKnockback); take(g, "fp18", p.shakeDamage);
    take(g, "fp20", p.maxAttackRange); take(g, "fp21", p.maxAttackAngle); take(g, "fp22", p.attackRadius);
    take(g, "fp24", p.attackDamage);
    const Block& q = *proper;
    take(q, "fp01", p.flightHeight); take(q, "fp03", p.transitHeight); take(q, "fp10", p.pitchRate);
    take(q, "fp11", p.pitchAmp); take(q, "fp21", p.freeRise); take(q, "fp22", p.ladenRise);
    take(q, "fp31", p.freeFlick); take(q, "fp32", p.ladenFlick); take(q, "fp40", p.struggleTime);
    if (!(p.health > 0.0f) || !(p.accel > 0.0f) || p.moveSpeed < 0.0f || p.turnSpeed < 0.0f
        || p.maxTurnAngle < 0.0f || !(p.territoryRadius > 0.0f) || !(p.homeRadius > 0.0f)
        || p.sightRadius < 0.0f || !(p.flightHeight > 0.0f) || p.struggleTime < 0.0f
        || p.freeFlick < 0.0f || p.freeFlick > 1.0f || p.ladenFlick < 0.0f || p.ladenFlick > 1.0f) {
        error = "nonphysical parameter value";
        return false;
    }
    p.retail = true;
    out = p;
    return true;
}

bool parseBombParm(std::istream& in, BombParams& out, std::string& error) {
    std::vector<Block> blocks;
    if (!parseBlocks(in, blocks, error)) return false;
    const Block* general = nullptr;
    const Block* proper = nullptr;
    for (const Block& block : blocks) {
        if (block.count("fp00") && block.count("fp14")) {
            if (general) { error = "duplicate general block"; return false; }
            general = &block;
        } else if (general && !proper && block.count("fp01") && block.count("fp02")) {
            proper = &block;
        }
    }
    if (!general || !proper) { error = "missing bomb general/proper block"; return false; }
    BombParams b = out;
    take(*general, "fp00", b.fuseHealth);
    take(*general, "fp22", b.blastRadius);
    take(*general, "fp24", b.naviPikiDamage);
    take(*proper, "fp01", b.tekiDamage);
    take(*proper, "fp02", b.blastHalfHeight);
    float induction = float(b.inductionLimit);
    take(*proper, "ip02", induction);
    b.inductionLimit = int(induction);
    if (!(b.fuseHealth > 0.0f) || !(b.blastRadius > 0.0f) || b.naviPikiDamage < 0.0f
        || b.tekiDamage < 0.0f || b.blastHalfHeight < 0.0f || b.inductionLimit < 0) {
        error = "nonphysical bomb parameter";
        return false;
    }
    b.retail = true;
    out = b;
    return true;
}

// ---------------------------------------------------------------- bank
Bank defaultBank() {
    // Retail GPVE01 bca frame counts + bombsarai/enemyanimmgr.txt key rows
    // (experimental/pikmin2_bombsarai_assets MGR_ROWS; supli1 frames from
    // the bca header). No poses: the draw falls back to the host.
    struct Row { int frames; std::vector<KeyEvent> events; };
    const Row rows[AnimCount] = {
        {105, {{10, 2}, {17, 6}, {24, 4}, {30, 3}, {36, 5}, {65, 2}, {66, 3}, {67, 4}, {68, 5}, {69, 6}, {83, 7}}},
        {25, {{2, 2}, {3, 3}, {4, 4}, {5, 5}, {6, 6}, {7, 7}, {9, 0}, {10, 1}, {11, 8}}},
        {30, {{15, 2}}},
        {30, {{15, 2}}},
        {55, {{0, 0}, {1, 2}, {13, 3}, {17, 2}, {22, 3}, {24, 1}, {26, 2}, {39, 3}}},
        {40, {{21, 2}}},
        {60, {{10, 0}, {49, 1}}},
        {50, {{5, 0}, {44, 1}}},
        {30, {}},
        {120, {{65, 0}, {104, 1}}},
        {70, {{32, 0}, {34, 1}}},
        {40, {{10, 0}, {29, 1}}},
        {60, {{10, 0}, {49, 1}}},
        {50, {{5, 0}, {44, 1}}},
    };
    Bank bank;
    for (int a = 0; a < AnimCount; ++a) {
        bank.clip[a].name = animDefaultName(a);
        bank.clip[a].frames = rows[a].frames;
        bank.clip[a].events = rows[a].events;
    }
    return bank;
}

bool parseBank(std::istream& in, Bank& bank, std::string& error) {
    std::string word;
    int count = 0;
    if (!(in >> word >> count) || word != "P2_BOMBSARAI_OWN_BANK_1" || count < 1 || count > AnimCount) {
        error = "bad bank header";
        return false;
    }
    Bank next = bank;
    bool seen[AnimCount] = {};
    for (int n = 0; n < count; ++n) {
        int id = -1, frames = 0, events = 0, poses = 0;
        Clip clip;
        if (!(in >> word >> id >> clip.name >> frames >> events) || word != "clip" || id < 0 || id >= AnimCount
            || seen[id] || frames < 1 || frames > 10000 || events < 0 || events > 64) {
            error = "bad clip row";
            return false;
        }
        seen[id] = true;
        clip.frames = frames;
        int previous = -1;
        for (int e = 0; e < events; ++e) {
            KeyEvent k;
            if (!(in >> k.frame >> k.type) || k.frame < 0 || k.frame >= frames || k.frame < previous || k.type < 0
                || k.type > 2000) {
                error = "bad key event";
                return false;
            }
            previous = k.frame;
            clip.events.push_back(k);
        }
        if (!(in >> poses) || poses < 0 || poses > 24) { error = "bad pose count"; return false; }
        for (int p = 0; p < poses; ++p) {
            Pose pose;
            if (!(in >> pose.frame >> pose.file >> pose.kamu.x >> pose.kamu.y >> pose.kamu.z) || pose.frame < 0
                || pose.frame >= frames || pose.file < 0 || pose.file > 99 || !finite(pose.kamu)
                || std::fabs(pose.kamu.x) > 10000.0f || std::fabs(pose.kamu.y) > 10000.0f
                || std::fabs(pose.kamu.z) > 10000.0f
                || (!clip.poses.empty() && pose.frame <= clip.poses.back().frame)) {
                error = "bad pose row";
                return false;
            }
            clip.poses.push_back(pose);
        }
        clip.staged = true;
        next.clip[id] = clip;
    }
    next.bombClipCount = 0;
    while (in >> word) {
        if (word == "END") {
            next.staged = true;
            bank = next;
            return true;
        }
        if (word == "bomb") {
            if (next.bombClipCount >= 2) { error = "too many bomb clips"; return false; }
            BombClip& b = next.bombClip[next.bombClipCount];
            int poses = 0;
            if (!(in >> b.name >> b.frames >> poses) || b.frames < 1 || b.frames > 10000 || poses < 0 || poses > 24) {
                error = "bad bomb row";
                return false;
            }
            for (int p = 0; p < poses; ++p) {
                int frame = 0, file = 0;
                if (!(in >> frame >> file) || frame < 0 || frame >= b.frames || file < 0 || file > 99) {
                    error = "bad bomb pose";
                    return false;
                }
                b.poseFrames.push_back(frame);
                b.poseFiles.push_back(file);
            }
            ++next.bombClipCount;
            continue;
        }
        error = "unexpected token " + word;
        return false;
    }
    error = "missing END";
    return false;
}

const Pose* nearestPose(const Clip& clip, float frame) {
    if (clip.poses.empty()) return nullptr;
    const Pose* best = &clip.poses.front();
    for (const Pose& p : clip.poses)
        if (std::fabs(float(p.frame) - frame) < std::fabs(float(best->frame) - frame)) best = &p;
    return best;
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
}

void Animator::animate(float dt) {
    mPlaying = false; // doAnimationCullingOff clears the latch
    if (!mClip) return;
    mTimer += 30.0f * dt;
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
float Fsm::flickChance(const Params& p, int stuck) {
    // BombSarai.cpp:326-330: popCount = clamp(stuck - 1, 0, 4),
    // limit = (4 - pop)/4 * fp31 + pop/4 * fp32.
    const int pop = stuck - 1 < 0 ? 0 : (stuck - 1 <= 4 ? stuck - 1 : 4);
    const float f = float(pop);
    return (4.0f - f) / 4.0f * p.freeFlick + f / 4.0f * p.ladenFlick;
}

float Fsm::randFloat() {
    mRng = mRng * 1664525u + 1013904223u;
    return float(mRng >> 8) / 16777216.0f;
}

void Fsm::init(const Params& params, const Bank& bank, const Vec3& position, float faceDir, std::uint32_t seed) {
    mParams = params;
    mBank = bank;
    mRng = seed ? seed : 1u;
    mPos = mHome = position; // EnemyBase birth: mHomePosition = birth position
    mTargetPos = position;
    mFaceDir = roundAng(faceDir);
    mTargetVel = mCurrentVel = {};
    mStateTimer = mBombCarryTimer = mPitchRatio = mFlickTimer = 0.0f;
    mUntargetable = false;
    mNext = State::Null;
    mState = State::Null;
    TickOutput sink;
    TickInput none;
    none.position = position;
    none.groundY = position.y;
    none.health = params.health;
    mIn = &none;
    mOut = &sink;
    transit(State::Wait); // onInit: mFsm->start(this, BOMBSARAI_Wait)
    mIn = nullptr;
    mOut = nullptr;
}

float Fsm::angDistTo(const Vec3& t) const {
    return angDist(std::atan2(t.x - mPos.x, t.z - mPos.z), mFaceDir);
}

void Fsm::turnToTarget(const Vec3& t, float factor, float maxDeg) {
    const float a = angDistTo(t);
    mFaceDir = roundAng(clampAbs(a * factor, toRad(maxDeg)) + mFaceDir);
}

void Fsm::walkToTarget(const Vec3& t) {
    // EnemyFunc::walkToTarget(pos): turnToTarget + setTargetSpeed(moveSpeed).
    turnToTarget(t, mParams.turnSpeed, mParams.maxTurnAngle);
    mTargetVel = {mParams.moveSpeed * std::sin(mFaceDir), mTargetVel.y, mParams.moveSpeed * std::cos(mFaceDir)};
}

float Fsm::setHeightVelocity(bool fast) {
    // BombSarai.cpp:202-224.
    const float minY = mIn->groundY;
    float rise = 6.0f;
    if (!fast) {
        const int n = mIn->stuckPikmin < 0 ? 0 : (mIn->stuckPikmin <= 5 ? mIn->stuckPikmin : 5);
        const float f = float(n);
        rise = (5.0f - f) / 5.0f * mParams.freeRise + f / 5.0f * mParams.ladenRise;
    }
    float height = mParams.flightHeight;
    if (mPos.y - minY > height - mParams.pitchAmp) {
        mPitchRatio += mParams.pitchRate * kSourceDelta; // addPitchRatio
        if (mPitchRatio > kTau) mPitchRatio -= kTau;
        height += mParams.pitchAmp * std::sin(mPitchRatio);
    }
    mCurrentVel.y = rise * ((minY + height) - mPos.y);
    mLastHeight = mPos.y - minY;
    return mLastHeight;
}

void Fsm::setRandTarget() {
    // BombSarai.cpp:230-245.
    float amp;
    if (mIn->inCave) {
        amp = 50.0f + 50.0f * randFloat();
    } else {
        amp = mParams.homeRadius + (mParams.territoryRadius - mParams.homeRadius) * randFloat();
    }
    const float toHome = std::atan2(mPos.x - mHome.x, mPos.z - mHome.z);
    const float theta = kHalfPi + (toHome + kPi * randFloat());
    mTargetPos = {amp * std::sin(theta) + mHome.x, mHome.y, amp * std::cos(theta) + mHome.z};
}

const Candidate* Fsm::attackablePikmin() const {
    // BombSarai.cpp:300-308: territory gate on the home distance, then
    // EnemyFunc::getNearestPikminOrNavi(viewAngle, sightRadius): nearest navi,
    // then a Piki strictly nearer (XZ) wins (enemyAction.cpp:17-60, 368-410).
    if (!(sqrXZ(mPos, mHome) < mParams.territoryRadius * mParams.territoryRadius)) return nullptr;
    const float cone = toRad(mParams.viewAngle);
    float minDist = mParams.sightRadius < 0.0f ? kFltMax : mParams.sightRadius * mParams.sightRadius;
    const Candidate* navi = nullptr;
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.navi || !c.alive) continue;
        if (std::fabs(angDistTo(c.pos)) > cone) continue;
        const float d = sqrXZ(c.pos, mPos);
        if (d < minDist) { navi = &c; minDist = d; }
    }
    const Candidate* piki = nullptr;
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.pikmin || !c.searchable) continue;
        if (std::fabs(angDistTo(c.pos)) > cone) continue;
        const float d = sqrXZ(c.pos, mPos);
        if (d < minDist) { piki = &c; minDist = d; }
    }
    return piki ? piki : navi;
}

bool Fsm::targetAttackable(const Candidate& c) const {
    // EnemyBase::isTargetAttackable: 3D separation < fp20, |angle| <= fp21.
    return sqr3D(c.pos, mPos) < mParams.maxAttackRange * mParams.maxAttackRange
        && std::fabs(angDistTo(c.pos)) <= toRad(mParams.maxAttackAngle);
}

State Fsm::nextStateOnHeight() {
    // BombSarai.cpp:314-340.
    if (mIn->health <= 0.0f) return State::Fall;
    const int stuck = mIn->stuckPikmin;
    if (stuck != 0) {
        if (mIn->stuckPurple > 0) return State::Fall;
        const float limit = flickChance(mParams, stuck);
        const float roll = randFloat();
        mOut->flickRolled = true;
        mOut->flickChance = limit;
        mOut->flickRoll = roll;
        if (roll < limit) return mIn->carrying ? State::BombFlick : State::Flick;
        return State::Fall;
    }
    return State::Null;
}

void Fsm::transit(State next) {
    // EnemyStateMachine::transit: cleanup(current) then init(next).
    switch (mState) {
    case State::Supply: mBombCarryTimer = 0.0f; break; // StateSupply::cleanup
    default: break;
    }
    if (next == State::Null) next = State::Wait; // never reached with retail data (documented guard)
    mState = next;
    mOut->entered.push_back(next);
    const Clip* c = mBank.clip;
    switch (next) {
    case State::Dead:
        mTargetVel = {};
        mUntargetable = false;
        mAnim.start(&c[AnimDead], AnimDead);
        break;
    case State::Damage:
        mStateTimer = 0.0f;
        mTargetVel = {};
        mUntargetable = false;
        mAnim.start(&c[AnimStruggle], AnimStruggle);
        break;
    case State::Wait:
        mUntargetable = true;
        mNext = State::Null;
        mStateTimer = 0.0f;
        mTargetVel = {};
        mAnim.start(&c[AnimWait], AnimWait);
        break;
    case State::BombWait:
        mUntargetable = true;
        mNext = State::Null;
        mStateTimer = 0.0f;
        mTargetVel = {};
        mAnim.start(&c[AnimBombWait], AnimBombWait);
        break;
    case State::Move:
        mUntargetable = true;
        mNext = State::Null;
        mStateTimer = 0.0f;
        setRandTarget();
        mTargetVel = {};
        mAnim.start(&c[AnimRun], AnimRun);
        break;
    case State::BombMove:
        mUntargetable = true;
        mNext = State::Null;
        mStateTimer = 0.0f;
        setRandTarget();
        mTargetVel = {};
        mAnim.start(&c[AnimBombRun], AnimBombRun);
        break;
    case State::Supply:
        mUntargetable = true;
        mNext = State::Null;
        mOut->supply = true; // supplyBomb()
        mTargetVel = {};
        mAnim.start(&c[AnimSupply], AnimSupply);
        break;
    case State::Release:
        mUntargetable = true;
        mNext = State::Null;
        mTargetVel = {};
        mAnim.start(&c[AnimRelease], AnimRelease);
        break;
    case State::Fall:
        mStateTimer = 0.0f;
        mTargetVel = {};
        mUntargetable = false;
        mAnim.start(&c[AnimFall], AnimFall);
        break;
    case State::TakeOff1:
        mFlickTimer = 0.0f;
        mUntargetable = false;
        mAnim.start(&c[AnimTakeOff1], AnimTakeOff1);
        break;
    case State::TakeOff2:
        mFlickTimer = 0.0f;
        mUntargetable = false;
        mAnim.start(&c[AnimTakeOff2], AnimTakeOff2);
        break;
    case State::Flick:
        mUntargetable = true;
        mAnim.start(&c[AnimFlick], AnimFlick);
        break;
    case State::BombFlick:
        mUntargetable = true;
        mAnim.start(&c[AnimBombFlick], AnimBombFlick);
        break;
    default: break;
    }
}

void Fsm::doFlick() {
    // EnemyFunc::flickStickPikmin(this, fp16, fp17, fp18, FLICK_BACKWARD_ANGLE):
    // every stuck Piki rolls shakeChance; flickCreature skips mouth-stuck.
    TickOutput& o = *mOut;
    o.flick = true;
    o.flickKnockback = mParams.shakeKnockback;
    o.flickDamage = mParams.shakeDamage;
    o.flickAngle = roundAng(kFlickBackwardAngle + kPi);
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.pikmin || !c.stuckToSelf) continue;
        if (mParams.shakeChance > randFloat() && !c.stuckToMouth) o.flickStick.push_back(c.id);
    }
    mFlickTimer = 0.0f;
}

void Fsm::execState() {
    const Params& p = mParams;
    const float health = mIn->health;
    switch (mState) {
    case State::Dead: // BombSaraiState.cpp:55-84
        if (mAnim.is(Key2)) mOut->balloon = 0;
        else if (mAnim.is(Key3)) mOut->balloon = 1;
        else if (mAnim.is(Key4)) mOut->balloon = 2;
        else if (mAnim.is(Key5)) mOut->balloon = 3;
        else if (mAnim.is(Key6)) mOut->balloon = 4;
        else if (mAnim.is(Key7)) mOut->down = true;
        else if (mAnim.is(KeyEnd)) mOut->killRequest = true;
        break;
    case State::Damage: // :116-148
        if (health <= 0.0f || mIn->stuckPikmin == 0 || mStateTimer > p.struggleTime) mAnim.finish();
        mStateTimer += kSourceDelta;
        if (mAnim.is(Key3)) {
            mOut->down = true;
        } else if (mAnim.is(KeyEnd)) {
            if (health <= 0.0f) { transit(State::Dead); return; }
            transit(health / p.health > 0.5f ? State::TakeOff1 : State::TakeOff2);
        }
        break;
    case State::Wait: { // :178-207
        const float height = setHeightVelocity(false);
        if (!mAnim.isFinishing()) {
            if (attackablePikmin()) {
                mNext = State::Supply;
                mAnim.finish();
            } else {
                mStateTimer += kSourceDelta;
                if (mStateTimer > 3.0f) {
                    mNext = State::Move;
                    mAnim.finish();
                }
            }
        }
        if (height > p.transitHeight || mStateTimer > 5.0f) {
            const State s = nextStateOnHeight();
            if (s != State::Null) { transit(s); return; }
        }
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::BombWait: { // :237-287
        const float height = setHeightVelocity(false);
        const Candidate* target = attackablePikmin();
        if (mBombCarryTimer > 15.0f) {
            mNext = State::Release;
            mAnim.finish();
        } else if (target) {
            if (targetAttackable(*target) || sqrXZ(mPos, target->pos) < p.attackRadius * p.attackRadius) {
                mNext = State::Release;
            } else {
                mNext = State::BombMove;
            }
            mAnim.finish();
        } else if (mStateTimer > 3.0f) {
            mNext = State::BombMove;
            mAnim.finish();
        }
        if (mIn->bitterQueued) { transit(State::Fall); return; }
        if (height > p.transitHeight || mStateTimer > 5.0f) {
            const State s = nextStateOnHeight();
            if (s != State::Null) { transit(s); return; }
        }
        mStateTimer += kSourceDelta;
        mBombCarryTimer += kSourceDelta;
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::Move: { // :318-355
        const float height = setHeightVelocity(false);
        if (!mAnim.isFinishing()) {
            if (attackablePikmin()) {
                mNext = State::Supply;
                mAnim.finish();
            } else {
                mStateTimer += kSourceDelta;
                const Vec3 targetPos = mTargetPos;
                if (mStateTimer > 5.0f || sqrXZ(mPos, targetPos) < 625.0f) {
                    mNext = State::Wait;
                    mAnim.finish();
                }
                walkToTarget(targetPos);
            }
        } else {
            mTargetVel = {};
        }
        if (height > p.transitHeight || mStateTimer > 5.0f) {
            const State s = nextStateOnHeight();
            if (s != State::Null) { transit(s); return; }
        }
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::BombMove: { // :386-444
        const float height = setHeightVelocity(false);
        const Candidate* target = attackablePikmin();
        Vec3 targetPos; // source: uninitialised when the attackable branch fires (never walked then)
        if (mBombCarryTimer > 15.0f) {
            mNext = State::Release;
            mAnim.finish();
        } else if (target) {
            if (targetAttackable(*target)) {
                mNext = State::Release;
                mAnim.finish();
            } else {
                targetPos = target->pos;
                if (sqrXZ(mPos, targetPos) < p.attackRadius * p.attackRadius) {
                    mNext = State::Release;
                    mAnim.finish();
                }
            }
        } else {
            targetPos = mTargetPos;
            if (mStateTimer > 5.0f || sqrXZ(mPos, targetPos) < 625.0f) {
                mNext = State::BombMove;
                mAnim.finish();
            }
        }
        if (mAnim.isFinishing()) mTargetVel = {};
        else walkToTarget(targetPos);
        if (mIn->bitterQueued) { transit(State::Fall); return; }
        if (height > p.transitHeight || mStateTimer > 5.0f) {
            const State s = nextStateOnHeight();
            if (s != State::Null) { transit(s); return; }
        }
        mStateTimer += kSourceDelta;
        mBombCarryTimer += kSourceDelta;
        if (mAnim.is(KeyEnd)) transit(mNext);
        break;
    }
    case State::Supply: // :477-489
        setHeightVelocity(false);
        if (mAnim.is(KeyEnd)) {
            const State s = nextStateOnHeight();
            transit(s != State::Null ? s : State::BombMove);
        }
        break;
    case State::Release: // :522-545
        setHeightVelocity(false);
        if (mAnim.is(Key2)) {
            mOut->throwBomb = true;
            mOut->throwKind = 0;
            mOut->throwVelocity = {50.0f * std::sin(mFaceDir), 100.0f, 50.0f * std::cos(mFaceDir)};
        } else if (mAnim.is(KeyEnd)) {
            const State s = nextStateOnHeight();
            transit(s != State::Null ? s : State::Wait);
            return;
        }
        break;
    case State::Fall: { // :580-626
        if (mPos.y - mIn->groundY < 35.0f || mStateTimer > 1.0f) mAnim.finish();
        mStateTimer += kSourceDelta;
        if (mAnim.is(Key2)) {
            mOut->throwBomb = true;
            mOut->throwKind = 1;
            mOut->throwVelocity = {100.0f * std::sin(mFaceDir), 300.0f, 100.0f * std::cos(mFaceDir)};
        } else if (mAnim.is(Key3)) mOut->balloon = 0;
        else if (mAnim.is(Key4)) mOut->balloon = 1;
        else if (mAnim.is(Key5)) mOut->balloon = 2;
        else if (mAnim.is(Key6)) mOut->balloon = 3;
        else if (mAnim.is(Key7)) mOut->balloon = 4;
        else if (mAnim.is(Key8)) mOut->down = true;
        else if (mAnim.is(KeyEnd)) transit(health <= 0.0f ? State::Dead : State::Damage);
        break;
    }
    case State::TakeOff1:
    case State::TakeOff2: { // :654-676, :703-725
        const bool fast = mState == State::TakeOff2;
        float height = 0.0f;
        if (mAnim.frame() > (fast ? 21.0f : 45.0f)) {
            mUntargetable = true;
            height = setHeightVelocity(fast);
        }
        if (health <= 0.0f || height > p.transitHeight) {
            const State s = nextStateOnHeight();
            if (s != State::Null) { transit(s); return; }
            mAnim.finish();
        }
        if (mAnim.is(KeyEnd)) transit(State::Move);
        break;
    }
    case State::Flick: // :751-772
        setHeightVelocity(false);
        if (mAnim.is(Key2)) {
            doFlick();
        } else if (mAnim.is(KeyEnd)) {
            const State s = nextStateOnHeight();
            transit(s != State::Null ? s : State::Move);
            return;
        }
        break;
    case State::BombFlick: // :799-825
        setHeightVelocity(false);
        if (mIn->bitterQueued) { transit(State::Fall); return; }
        if (mAnim.is(Key2)) {
            doFlick();
        } else if (mAnim.is(KeyEnd)) {
            const State s = nextStateOnHeight();
            transit(s != State::Null ? s : State::BombMove);
            return;
        }
        break;
    default: break;
    }
}

TickOutput Fsm::tick(const TickInput& in) {
    TickOutput out;
    if (mState == State::Null || !finite(in.position) || !finite(in.health) || !finite(in.groundY)
        || (in.count && !in.candidates)) return out;
    out.valid = true;
    mIn = &in;
    mOut = &out;
    mPos = in.position;
    mLastHeight = -1.0f;
    // Obj::doUpdate: mFsm->exec(this).
    execState();
    // collisionMapAndPlat: !EB_Untargetable -> doSimulationGround (host
    // gravity), else doSimulationFlying (blend toward mTargetVelocity).
    const float blend = kSourceDelta / mParams.accel;
    mCurrentVel.x += (mTargetVel.x - mCurrentVel.x) * blend;
    mCurrentVel.z += (mTargetVel.z - mCurrentVel.z) * blend;
    if (mUntargetable) mCurrentVel.y += (mTargetVel.y - mCurrentVel.y) * blend;
    // doAnimation: clear the latch, then advance one source tick.
    mAnim.animate(kSourceDelta);
    out.velocity = mCurrentVel;
    out.flying = mUntargetable;
    out.faceDir = mFaceDir;
    out.height = mLastHeight;
    mIn = nullptr;
    mOut = nullptr;
    return out;
}

} // namespace p2bsown
