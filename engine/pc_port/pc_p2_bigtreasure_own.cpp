#include "pc_p2_bigtreasure_own.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <map>
#include <sstream>

namespace p2btown {
namespace {

constexpr float kFlickBackwardAngle = -1000.0f; // EnemyFunc.h:9

float toRad(float deg) { return deg * kPi / 180.0f; }

// clampAngle / roundAng: [0, 2pi).
float round0(float a) {
    if (!std::isfinite(a)) return 0.0f;
    a = std::fmod(a, kTau);
    if (a < 0.0f) a += kTau;
    return a;
}
// Signed shortest difference in [-pi, pi].
float signedAngle(float a) {
    a = round0(a);
    if (a > kPi) a -= kTau;
    return a;
}
float distXZ2(const Vec3& a, const Vec3& b) {
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}
float dist3(const Vec3& a, const Vec3& b) {
    const float dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

const char* const kAnimNames[AnimCount] = {
    "appear", "appear2", "wait1",
    "preattackf", "attackf", "attackendf",
    "preattackfr", "attackfr", "attackendfr",
    "preattackfl", "attackfl", "attackendfl",
    "preattackfb", "attackfb", "attackendfb",
    "preattackw", "attackw", "attackendw",
    "preattackg", "attackg", "attackendg",
    "preattacke", "attacke", "attackende",
    "dropitem", "wait2", "flick", "dead", "move1", "wait2",
};
const char* const kJointNames[JointCount] = {
    "otakara_elec", "otakara_fire", "otakara_gas", "otakara_water", "otakara_loozy", "kosi",
    "otakara_elec_eff", "otakara_fire_eff", "otakara_gas_eff", "otakara_water_eff",
};

bool finitePositive(float v) { return std::isfinite(v) && v > 0.0f; }

} // namespace

const char* stateName(State state) {
    switch (state) {
    case State::Null: return "null";
    case State::Dead: return "dead";
    case State::Stay: return "stay";
    case State::Land: return "land";
    case State::Wait: return "wait";
    case State::ItemWait: return "itemwait";
    case State::Flick: return "flick";
    case State::PreAttack: return "preattack";
    case State::Attack: return "attack";
    case State::PutItem: return "putitem";
    case State::DropItem: return "dropitem";
    case State::Walk: return "walk";
    case State::ItemWalk: return "itemwalk";
    }
    return "?";
}

const char* animClipName(int anim) { return anim >= 0 && anim < AnimCount ? kAnimNames[anim] : nullptr; }
const char* jointName(int joint) { return joint >= 0 && joint < JointCount ? kJointNames[joint] : nullptr; }

// ---------------------------------------------------------------------------
// enemyparm.txt
bool parseEnemyParm(std::istream& in, Params& out, std::string& error) {
    Params p;
    std::vector<std::map<std::string, std::string>> blocks;
    std::map<std::string, std::string> cur;
    bool open = false;
    std::string line;
    while (std::getline(in, line)) {
        const std::size_t hash = line.find('#');
        if (hash != std::string::npos) line.resize(hash);
        std::istringstream row(line);
        std::string tag;
        if (!(row >> tag)) continue;
        if (tag == "{") {
            if (open) { error = "nested block"; return false; }
            open = true;
            cur.clear();
            continue;
        }
        if (tag == "}") {
            if (!open) { error = "unbalanced block"; return false; }
            open = false;
            blocks.push_back(cur);
            continue;
        }
        if (!open) { error = "row outside block"; return false; }
        if (tag.size() < 3 || tag.front() != '{' || tag.back() != '}') { error = "bad tag " + tag; return false; }
        const std::string name = tag.substr(1, tag.size() - 2);
        if (name == "_eof") continue;
        std::string kind, value;
        if (!(row >> kind >> value)) { error = "short row " + name; return false; }
        cur[name] = value;
    }
    if (open) { error = "unterminated block"; return false; }
    auto num = [&](const std::map<std::string, std::string>& b, const char* tag, float& dst) -> bool {
        auto it = b.find(tag);
        if (it == b.end()) return true;
        char* end = nullptr;
        const double v = std::strtod(it->second.c_str(), &end);
        if (!end || *end || !std::isfinite(v)) { error = std::string("bad value ") + tag; return false; }
        dst = float(v);
        return true;
    };
    auto inum = [&](const std::map<std::string, std::string>& b, const char* tag, int& dst) -> bool {
        float f = float(dst);
        if (!num(b, tag, f)) return false;
        dst = int(f);
        return true;
    };
    const std::map<std::string, std::string>* general = nullptr;
    const std::map<std::string, std::string>* proper = nullptr;
    for (const auto& b : blocks) {
        if (b.count("fp00")) general = &b;
        else if (b.count("fe00") || b.count("fw00") || (b.count("fp01") && b.count("fp20"))) proper = &b;
    }
    if (!general) { error = "missing general block"; return false; }
    const auto& g = *general;
    if (!num(g, "fp00", p.health) || !num(g, "fp06", p.moveSpeed) || !num(g, "fp28", p.maxTurnAngle)
        || !num(g, "fp09", p.territoryRadius) || !num(g, "fp10", p.homeRadius) || !num(g, "fp11", p.privateRadius)
        || !num(g, "fp12", p.sightRadius) || !num(g, "fp13", p.viewAngle) || !num(g, "fp16", p.shakeChance)
        || !num(g, "fp17", p.shakeKnockback) || !num(g, "fp18", p.shakeDamage) || !num(g, "fp24", p.attackDamage)
        || !inum(g, "ip01", p.shakeOffBlowA) || !inum(g, "ip02", p.shakeOffSticking1)
        || !inum(g, "ip03", p.shakeOffBlowB) || !inum(g, "ip04", p.shakeOffSticking2)
        || !inum(g, "ip05", p.shakeOffBlowC) || !inum(g, "ip06", p.shakeOffSticking3)
        || !inum(g, "ip07", p.shakeOffBlowD))
        return false;
    if (proper) {
        const auto& q = *proper;
        if (!num(q, "fp01", p.baseFactor) || !num(q, "fp02", p.raiseDecelFactor)
            || !num(q, "fp03", p.downwardDecelFactor) || !num(q, "fp04", p.minReducedAccel)
            || !num(q, "fp05", p.maxDecelAccel) || !num(q, "fp06", p.legSwing) || !num(q, "fp10", p.elecWait)
            || !num(q, "fp11", p.fireWait1) || !num(q, "fp31", p.fireWait2) || !num(q, "fp12", p.gasWait)
            || !num(q, "fp13", p.waterWait) || !num(q, "fp20", p.elecAttackMax) || !num(q, "fp21", p.fireAttackMax)
            || !num(q, "fp22", p.gasAttackMax) || !num(q, "fp23", p.waterAttackMax))
            return false;
    }
    if (!finitePositive(p.health) || !finitePositive(p.moveSpeed) || !finitePositive(p.maxTurnAngle)
        || !finitePositive(p.territoryRadius) || p.homeRadius < 0.0f || p.homeRadius > p.territoryRadius
        || !finitePositive(p.privateRadius) || !finitePositive(p.sightRadius) || p.shakeChance < 0.0f
        || p.shakeKnockback < 0.0f || p.shakeDamage < 0.0f || p.attackDamage < 0.0f
        || !(p.minReducedAccel <= p.maxDecelAccel) || !finitePositive(p.elecWait) || !finitePositive(p.fireWait1)
        || !finitePositive(p.fireWait2) || !finitePositive(p.gasWait) || !finitePositive(p.waterWait)
        || !finitePositive(p.elecAttackMax) || !finitePositive(p.fireAttackMax) || !finitePositive(p.gasAttackMax)
        || !finitePositive(p.waterAttackMax)) {
        error = "nonphysical value";
        return false;
    }
    p.retail = proper != nullptr;
    out = p;
    return true;
}

// ---------------------------------------------------------------------------
// Bank.
//   P2_BIGTREASURE_BANK_1
//   legs <distance> <a0> <a1> <a2> <a3>          (radians, rhand lhand rfoot lfoot)
//   bind <joint> <12 floats row-major 3x4>
//   clip <anim> <name> <frames> <poses>
//   pose <anim> <index> <frame>
//   joint <anim> <index> <joint> <12 floats>
//   end
Bank defaultBank() {
    Bank b;
    // Retail bind-pose otakara_* capture transforms (bigtreasure.json
    // boss.capture_transforms, research import): weapons ride at ~125 u.
    auto set = [&](int j, float x, float y, float z) {
        b.bind[j] = Mat34{};
        b.bind[j].m[0][3] = x;
        b.bind[j].m[1][3] = y;
        b.bind[j].m[2][3] = z;
    };
    set(JointElec, 0.0f, 125.0f, 56.7f);
    set(JointFire, 52.7f, 123.8f, 0.9f);
    set(JointGas, 0.0f, 125.0f, -50.0f);
    set(JointWater, -50.0f, 125.0f, 0.0f);
    set(JointLoozy, 0.0f, 141.5f, 15.0f);
    set(JointKosi, 0.0f, 159.5f, 0.0f);
    // *_eff bind transforms (capture_transforms reference joints); gas/water
    // eff default to their weapon joint until the bank stages them.
    b.bind[JointElecEff] = Mat34{{{0, 0, -1, 0}, {0, 1, 0, 124.6f}, {1, 0, 0, 68.7f}}};
    b.bind[JointFireEff] = Mat34{{{1, 0, 0, 72.7f}, {0, 1, 0, 124.3f}, {0, 0, 1, 1.5f}}};
    b.bind[JointGasEff] = b.bind[JointGas];
    b.bind[JointWaterEff] = b.bind[JointWater];
    for (int a = 0; a < AnimCount; ++a) b.clip[a].name = kAnimNames[a];
    return b;
}

bool parseBank(std::istream& in, Bank& bank, std::string& error) {
    Bank b = defaultBank();
    std::string magic;
    if (!(in >> magic) || magic != "P2_BIGTREASURE_BANK_1") { error = "bad magic"; return false; }
    auto jointIndex = [](const std::string& name) {
        for (int j = 0; j < JointCount; ++j)
            if (name == kJointNames[j]) return j;
        return -1;
    };
    auto readMat = [&](std::istream& s, Mat34& m) {
        for (int r = 0; r < 3; ++r)
            for (int c = 0; c < 4; ++c)
                if (!(s >> m.m[r][c]) || !std::isfinite(m.m[r][c]) || std::fabs(m.m[r][c]) > 100000.0f) return false;
        return true;
    };
    std::string word;
    bool ended = false;
    int poseTotal = 0;
    while (in >> word) {
        if (word == "end") { ended = true; break; }
        if (word == "legs") {
            LegLayout l;
            if (!(in >> l.distance >> l.angle[0] >> l.angle[1] >> l.angle[2] >> l.angle[3])
                || !finitePositive(l.distance) || l.distance > 2000.0f) { error = "bad legs"; return false; }
            for (float a : l.angle) if (!std::isfinite(a) || std::fabs(a) > 7.0f) { error = "bad leg angle"; return false; }
            l.staged = true;
            b.legs = l;
        } else if (word == "bind") {
            std::string name;
            Mat34 m;
            if (!(in >> name) || jointIndex(name) < 0 || !readMat(in, m)) { error = "bad bind"; return false; }
            b.bind[jointIndex(name)] = m;
        } else if (word == "clip") {
            int anim = -1, frames = 0, poses = 0;
            std::string name;
            if (!(in >> anim >> name >> frames >> poses) || anim < 0 || anim >= AnimCount
                || frames < 1 || frames > 10000 || poses < 0 || poses > 64 || name.size() > 32) { error = "bad clip"; return false; }
            if (name != kAnimNames[anim]) { error = "clip name/anim mismatch " + name; return false; }
            b.clip[anim].frames = frames;
            b.clip[anim].poses.assign(std::size_t(poses), PoseJoints{});
            poseTotal += poses;
            if (poseTotal > 1536) { error = "too many poses"; return false; }
        } else if (word == "pose") {
            int anim = -1, index = -1, frame = -1;
            if (!(in >> anim >> index >> frame) || anim < 0 || anim >= AnimCount || index < 0
                || index >= int(b.clip[anim].poses.size()) || frame < 0 || frame >= b.clip[anim].frames) { error = "bad pose"; return false; }
            if (index > 0 && b.clip[anim].poses[std::size_t(index - 1)].frame > frame) { error = "pose frames not ascending"; return false; }
            b.clip[anim].poses[std::size_t(index)].frame = frame;
        } else if (word == "joint") {
            int anim = -1, index = -1;
            std::string name;
            Mat34 m;
            if (!(in >> anim >> index >> name) || anim < 0 || anim >= AnimCount || index < 0
                || index >= int(b.clip[anim].poses.size()) || jointIndex(name) < 0 || !readMat(in, m)) { error = "bad joint"; return false; }
            PoseJoints& pj = b.clip[anim].poses[std::size_t(index)];
            pj.joint[jointIndex(name)] = m;
            pj.have[jointIndex(name)] = true;
        } else {
            error = "unknown row " + word;
            return false;
        }
    }
    if (!ended) { error = "missing end"; return false; }
    b.staged = true;
    bank = b;
    return true;
}

// ---------------------------------------------------------------------------
// Gait.
void Gait::init(const GaitParams& params, const LegLayout& legs, const Vec3& position, float faceDir) {
    mParams = params;
    for (int i = 0; i < 4; ++i) mLegAngle[i] = legs.angle[i];
    mDistance = legs.distance;
    mActive = mInMotion = mOnGround = false;
    mCentre = mTrace = position;
    mTraceVel = {};
    mFaceDir = round0(faceDir);
    mSteps = 0;
    for (int i = 0; i < 4; ++i) {
        mLegState[i] = 0;
        mLeg[i] = Leg{};
        const float a = mFaceDir + mLegAngle[i];
        mLeg[i].pos = {position.x + mDistance * std::sin(a), position.y, position.z + mDistance * std::cos(a)};
        mLegTarget[i] = mLeg[i].pos;
    }
}

void Gait::startProgramedIK(const Vec3& ownerPos, float faceDir) {
    // IKSystemMgr::startProgramedIK (IKSystemMgr.cpp:99-121): feet stay where
    // the Land clip left them (the staged leg layout around the owner).
    mActive = true;
    mInMotion = false;
    mOnGround = false;
    mFaceDir = round0(faceDir);
    for (int i = 0; i < 4; ++i) {
        mLegState[i] = 0;
        const float a = mFaceDir + mLegAngle[i];
        mLeg[i] = Leg{};
        mLeg[i].pos = {ownerPos.x + mDistance * std::sin(a), ownerPos.y, ownerPos.z + mDistance * std::cos(a)};
        mLeg[i].grounded = true;
    }
    mCentre = ownerPos;
}

void Gait::startIKMotion() {
    mInMotion = true;
    mOnGround = false;
    for (int& s : mLegState) s = 0;
}

bool Gait::isFinishIKMotion() const {
    if (mInMotion) return false;
    for (int s : mLegState)
        if (s != 3) return false;
    return true;
}

void Gait::startMove(int leg) {
    // IKSystemBase::startMovePosition: top = current foot, bottom = target,
    // middle = lerp(top, bottom, mMoveInterpolationRate) (+ height offset).
    Leg& l = mLeg[leg];
    l.grounded = false;
    l.ratio = 0.0f;
    l.timer = 0.0f;
    l.top = l.pos;
    l.bottom = mLegTarget[leg];
    const float f = mParams.moveInterpolation;
    l.middle = {f * l.bottom.x + (1.0f - f) * l.top.x, f * l.bottom.y + (1.0f - f) * l.top.y,
                f * l.bottom.z + (1.0f - f) * l.top.z};
    ++mSteps;
}

void Gait::setNextCentrePosition(const Vec3& ownerPos, float ownerFace, const Vec3& target) {
    // IKSystemMgr::setNextCentrePosition (IKSystemMgr.cpp:355-399).
    float angleDist = signedAngle(std::atan2(target.x - ownerPos.x, target.z - ownerPos.z) - ownerFace);
    Vec3 next;
    if (std::fabs(angleDist) <= toRad(mParams.viewAngle)) {
        next = {target.x, 0.0f, target.z};
        const float dx = next.x - ownerPos.x, dz = next.z - ownerPos.z;
        const float dist = std::sqrt(dx * dx + dz * dz);
        if (dist > mParams.moveSpeed && dist > 0.0f) {
            next = {ownerPos.x + dx / dist * mParams.moveSpeed, 0.0f, ownerPos.z + dz / dist * mParams.moveSpeed};
        } else if (dist < mParams.minimumMoveSpeed && dist > 0.0f) {
            next = {ownerPos.x + dx / dist * mParams.minimumMoveSpeed, 0.0f,
                    ownerPos.z + dz / dist * mParams.minimumMoveSpeed};
        }
    } else {
        next = {ownerPos.x, 0.0f, ownerPos.z};
        const float maxTurn = toRad(mParams.maxTurnAngle);
        if (!(std::fabs(angleDist) <= maxTurn)) angleDist = angleDist > 0.0f ? maxTurn : -maxTurn;
    }
    const float newFace = angleDist + ownerFace;
    for (int i = 0; i < 4; ++i) {
        const float a = newFace + mLegAngle[i];
        mLegTarget[i] = {next.x + mDistance * std::sin(a), ownerPos.y, next.z + mDistance * std::cos(a)};
    }
}

int Gait::update(const Vec3& ownerPos, float ownerFace, const Vec3& target, float dt) {
    if (!mActive) {
        mCentre = mTrace = ownerPos; // calcTraceCentrePosition, IK inactive
        mFaceDir = round0(ownerFace);
        return -1;
    }
    // IKSystemBase::update per leg (moveBottomJointPosition + onGround).
    for (Leg& l : mLeg) {
        if (l.grounded) continue;
        l.timer += l.ratio < 1.0f ? mParams.raiseSlow : mParams.downAccel;
        l.timer = std::min(std::max(l.timer, mParams.minDecel), mParams.maxDecel);
        l.ratio += (mParams.bottomSpeed + l.timer) * dt;
        const float t = l.ratio;
        // calcLagrange: knots at t = 0 (top), 1 (middle), 2 (bottom).
        const float a = (t - 1.0f) * (t - 2.0f) * 0.5f, b = -t * (t - 2.0f), c = t * (t - 1.0f) * 0.5f;
        l.pos = {a * l.top.x + b * l.middle.x + c * l.bottom.x, l.top.y, a * l.top.z + b * l.middle.z + c * l.bottom.z};
        // onGroundPosition on flat ground: the curve passes below the
        // floor once t > 2 (y = g + h*t*(2-t)); the foot then rests there.
        if (l.ratio > 1.0f && l.ratio > 2.0f) {
            l.grounded = true;
            l.pos = l.bottom;
        }
    }
    int landed = -1;
    // updateController (IKSystemMgr.cpp:287-353).
    if (mInMotion) {
        bool all3 = true;
        for (int s : mLegState) if (s != 3) all3 = false;
        if (all3) for (int& s : mLegState) s = 0;
        bool all0 = true;
        for (int s : mLegState) if (s != 0) all0 = false;
        if (all0) {
            setNextCentrePosition(mCentre, mFaceDir, target);
            startMove(0);
            mLegState[0] = 1;
        }
    }
    for (int i = 0; i < 4; ++i) {
        if (mLegState[i] == 1) {
            if (mLeg[i].grounded) mLegState[i] = 2;
        } else if (mLegState[i] == 2) {
            mLegState[i] = 3;
            landed = i;
            const int next = i + 1 > 3 ? i - 3 : i + 1;
            if (next > 0 && !mOnGround) {
                startMove(next);
                mLegState[next] = 1;
            }
        }
    }
    // calcFaceDir (front feet midpoint from the previous centre), then
    // calcCentrePosition (foot average).
    const float mx = (mLeg[0].pos.x + mLeg[1].pos.x) * 0.5f, mz = (mLeg[0].pos.z + mLeg[1].pos.z) * 0.5f;
    if (std::fabs(mx - mCentre.x) + std::fabs(mz - mCentre.z) > 1e-4f) mFaceDir = round0(std::atan2(mx - mCentre.x, mz - mCentre.z));
    Vec3 c{0.0f, ownerPos.y, 0.0f};
    for (const Leg& l : mLeg) { c.x += l.pos.x; c.z += l.pos.z; }
    c.x *= 0.25f;
    c.z *= 0.25f;
    mCentre = c;
    // calcTraceCentrePosition (IKSystemMgr.cpp:474-487), IKSystemParms
    // defaults mTraceMoveRate 0.1 / mTraceVelocityDampingFactor 0.7 (the
    // landing height kick only moves y, which the host owns here).
    mTraceVel.x += (mCentre.x - mTrace.x) * 0.1f;
    mTraceVel.z += (mCentre.z - mTrace.z) * 0.1f;
    mTrace.x += mTraceVel.x;
    mTrace.z += mTraceVel.z;
    mTrace.y = mCentre.y;
    mTraceVel.x *= 0.7f;
    mTraceVel.z *= 0.7f;
    return landed;
}

// ---------------------------------------------------------------------------
// Animator.
bool Animator::load(const p2retail::Table& table, std::string& error) {
    mLoaded = false;
    for (bool& h : mHave) h = false;
    for (int a = 0; a < AnimCount; ++a) {
        const std::string want = std::string(kAnimNames[a]) + ".bca";
        for (const auto& m : table.motions) {
            if (m.name != want) continue;
            mMotion[a] = m;
            if (a == AnimWait2_2) mMotion[a].events.clear(); // registry slot 29 carries no events
            mHave[a] = true;
            break;
        }
        if (!mHave[a]) { error = "missing clip " + want; return false; }
    }
    mLoaded = true;
    mAnim = -1;
    return true;
}

bool Animator::start(int anim) {
    if (!mLoaded || anim < 0 || anim >= AnimCount || !mHave[anim]) return false;
    if (!mPlayer.start(mMotion[anim])) return false;
    mAnim = anim;
    mStopped = false;
    return true;
}

void Animator::animate() {
    // doAnimationCullingOff: mCurAnim->mIsPlaying = false, then animate(1 frame).
    mPlaying = false;
    if (!mLoaded || mAnim < 0 || mStopped) return;
    mPlayer.advance(1.0f, [this](const p2retail::Event& e) {
        mType = e.type;
        mPlaying = true;
    });
}

// ---------------------------------------------------------------------------
// FSM.
float Fsm::randWeightFloat(float range) {
    mRng = mRng * 1103515245u + 12345u;
    const float u = float((mRng >> 8) & 0xFFFFu) / 65536.0f;
    return range * u;
}

float Fsm::roundAngle(float a) const { return round0(a); }

float Fsm::angDist(const Vec3& to) const {
    return signedAngle(std::atan2(to.x - mPos.x, to.z - mPos.z) - mFaceDir);
}

void Fsm::init(const Params& params, const Bank& bank, const Animator& animator, const Vec3& position,
               float faceDir, std::uint32_t seed) {
    mParams = params;
    mBank = bank;
    mAnim = animator;
    mRng = seed ? seed : 1u;
    mPos = mHome = mTarget = position;
    mFaceDir = round0(faceDir);
    mHealth = params.health;
    GaitParams g;
    g.moveSpeed = params.moveSpeed;
    g.maxTurnAngle = params.maxTurnAngle;
    g.bottomSpeed = params.baseFactor;
    g.raiseSlow = params.raiseDecelFactor;
    g.downAccel = params.downwardDecelFactor;
    g.minDecel = params.minReducedAccel;
    g.maxDecel = params.maxDecelAccel;
    mGait.init(g, bank.legs, position, mFaceDir);
    mOwn = P2BigTreasureOwnership();
    for (int w = 0; w < P2BTWEAPON_Count; ++w) mOwn.attachWeapon(w); // setupTreasure
    mOwn.attachLouie();
    mLouie = true;
    mElements.reset();
    mAttackIndex = -1;
    mFireVariant = 0;
    mFlickTimer = 0.0f;
    mStateTimer = 0.0f;
    mNext = State::Null;
    resetAttackLimitTimer(); // onInit
    // FSM start in Stay (onInit: mFsm->start(this, BIGTREASURE_Stay)).
    TickOutput scratch;
    mState = State::Stay;
    initState(State::Stay, scratch);
}

const Mat34& Fsm::jointModel(int joint) const {
    static const Mat34 identity;
    if (joint < 0 || joint >= JointCount) return identity;
    const int anim = mAnim.anim();
    if (anim >= 0 && anim < AnimCount) {
        const ClipBank& c = mBank.clip[anim];
        if (!c.poses.empty()) {
            // #972: bracket the live frame between the two staged poses and lerp the
            // joint matrix, so weapons and emit joints follow the interpolated body
            // mesh instead of snapping between poses (48 poses/clip).
            const float f = mAnim.frame();
            std::size_t hi = 0;
            while (hi < c.poses.size() && float(c.poses[hi].frame) < f) ++hi;
            std::size_t lo = hi > 0 ? hi - 1 : 0;
            if (hi >= c.poses.size()) hi = c.poses.size() - 1;
            const PoseJoints& a = c.poses[lo];
            const PoseJoints& b = c.poses[hi];
            if (a.have[joint] && b.have[joint]) {
                const float span = float(b.frame - a.frame);
                const float w = span > 0.0f ? std::max(0.0f, std::min(1.0f, (f - float(a.frame)) / span)) : 0.0f;
                Mat34& out = mJointCache[joint];
                for (int r = 0; r < 3; ++r)
                    for (int k = 0; k < 4; ++k) out.m[r][k] = a.joint[joint].m[r][k] + (b.joint[joint].m[r][k] - a.joint[joint].m[r][k]) * w;
                return out;
            }
            std::size_t best = 0;
            for (std::size_t k = 1; k < c.poses.size(); ++k)
                if (std::fabs(float(c.poses[k].frame) - f) < std::fabs(float(c.poses[best].frame) - f)) best = k;
            if (c.poses[best].have[joint]) return c.poses[best].joint[joint];
        }
    }
    return mBank.bind[joint];
}

Vec3 Fsm::jointWorld(int joint) const {
    const Mat34& m = jointModel(joint);
    const float x = m.m[0][3], y = m.m[1][3], z = m.m[2][3];
    // Model faces +Z; world = T(pos) * RotY(faceDir).
    const float s = std::sin(mFaceDir), c = std::cos(mFaceDir);
    return {mPos.x + c * x + s * z, mPos.y + y, mPos.z - s * x + c * z};
}

Vec3 Fsm::jointPoint(int joint, const Vec3& local) const {
    const Mat34& m = jointModel(joint);
    const float x = m.m[0][0] * local.x + m.m[0][1] * local.y + m.m[0][2] * local.z + m.m[0][3];
    const float y = m.m[1][0] * local.x + m.m[1][1] * local.y + m.m[1][2] * local.z + m.m[1][3];
    const float z = m.m[2][0] * local.x + m.m[2][1] * local.y + m.m[2][2] * local.z + m.m[2][3];
    const float s = std::sin(mFaceDir), c = std::cos(mFaceDir);
    return {mPos.x + c * x + s * z, mPos.y + y, mPos.z - s * x + c * z};
}

Vec3 Fsm::collCentre(const CollNode& node) const {
    const int weapon = weaponForPartId(node.id);
    if (weapon >= 0) return jointPoint(weapon, node.offset);
    // Leg chains: lft (lfoot, gait leg 3), lht (lhand, 1), rft (rfoot, 2),
    // rht (rhand, 0). Link 1 is the hip (kosi frame, its retail offset);
    // links 2..5 run on a polyline from the hip to the gait foot (no leg IK
    // joint solve in P1; the feet are the ported IKSystemBase feet).
    if (node.id.size() == 4 && node.id[3] >= '2' && node.id[3] <= '5') {
        const std::string leg = node.id.substr(0, 3);
        const int gaitLeg = leg == "rht" ? 0 : leg == "lht" ? 1 : leg == "rft" ? 2 : leg == "lft" ? 3 : -1;
        if (gaitLeg >= 0) {
            const int link = node.id[3] - '0';
            const Vec3 hip = jointPoint(JointKosi, {0.0f, -20.0f, 0.0f});
            const Vec3& f = mGait.foot(gaitLeg);
            const Vec3 foot{f.x, mPos.y, f.z};
            static const float kFrac[6] = {0.0f, 0.0f, 0.3f, 0.55f, 0.8f, 1.0f};
            static const float kLift[6] = {0.0f, 0.0f, 30.0f, 30.0f, 15.0f, 0.0f};
            const float t = kFrac[link];
            return {hip.x + (foot.x - hip.x) * t, hip.y + (foot.y - hip.y) * t + kLift[link],
                    hip.z + (foot.z - hip.z) * t};
        }
    }
    // Joint 0 (kosi): the root bound sphere, tam1/tam2, the leg hips.
    return jointPoint(JointKosi, node.offset);
}

int weaponForPartId(const std::string& id) {
    // setupTreasure collTags: 'elec', 'fire', 'gasi', 'mizu'.
    if (id == "elec") return P2BTWEAPON_Elec;
    if (id == "fire") return P2BTWEAPON_Fire;
    if (id == "gasi") return P2BTWEAPON_Gas;
    if (id == "mizu") return P2BTWEAPON_Water;
    return -1;
}

namespace {
struct CollReader {
    std::vector<std::string> tok;
    std::size_t at = 0;
    std::vector<CollNode>* out = nullptr;
    bool next(std::string& t) {
        if (at >= tok.size()) return false;
        t = tok[at++];
        return true;
    }
    bool number(float& v) {
        std::string t;
        if (!next(t)) return false;
        char* end = nullptr;
        v = std::strtof(t.c_str(), &end);
        return end && *end == 0 && std::isfinite(v);
    }
    bool tag(std::string& v) {
        std::string t;
        if (!next(t) || t.size() != 6 || t.front() != '{' || t.back() != '}') return false;
        v = t.substr(1, 4);
        return true;
    }
    // node := count radius {id} {code} x y z joint attribute [ '{' node*count '}' ]
    bool node(int parent, int depth) {
        if (depth > 16 || out->size() >= 128) return false;
        float c = 0, r = 0, x = 0, y = 0, z = 0, j = 0, a = 0;
        CollNode n;
        if (!number(c) || !number(r) || !tag(n.id) || !tag(n.code) || !number(x) || !number(y) || !number(z)
            || !number(j) || !number(a))
            return false;
        if (c < 0.0f || c > 64.0f || r < 0.0f || r > 10000.0f || j < 0.0f || j > 255.0f) return false;
        n.radius = r;
        n.offset = {x, y, z};
        n.joint = int(j);
        n.attribute = int(a);
        n.parent = parent;
        out->push_back(n);
        const int self = int(out->size()) - 1;
        const int count = int(c);
        if (count == 0) return true;
        std::string b;
        if (!next(b) || b != "{") return false;
        for (int i = 0; i < count; ++i)
            if (!node(self, depth + 1)) return false;
        return next(b) && b == "}";
    }
};
} // namespace

bool parseCollTree(std::istream& in, std::vector<CollNode>& out, std::string& error) {
    out.clear();
    CollReader r;
    r.out = &out;
    std::string line;
    while (std::getline(in, line)) {
        const auto hash = line.find('#');
        if (hash != std::string::npos) line.erase(hash);
        std::istringstream ls(line);
        std::string t;
        while (ls >> t) r.tok.push_back(t);
    }
    if (!r.node(-1, 0)) {
        error = "malformed node";
        out.clear();
        return false;
    }
    if (r.at != r.tok.size()) {
        error = "trailing tokens";
        out.clear();
        return false;
    }
    int weapons = 0;
    for (const CollNode& n : out) weapons += weaponForPartId(n.id) >= 0 ? 1 : 0;
    if (weapons != P2BTWEAPON_Count) {
        error = "weapon parts";
        out.clear();
        return false;
    }
    return true;
}

bool Fsm::isStartFlick() const {
    // EnemyFunc::isStartFlick(enemy, false) (enemyAction.cpp:1209-1243).
    const float v = mFlickTimer >= 0.0f ? mFlickTimer + 0.5f : mFlickTimer - 0.5f;
    const int flickInt = int(static_cast<unsigned char>(int(v)));
    const Params& p = mParams;
    if (mStuck < p.shakeOffSticking1) return flickInt > p.shakeOffBlowA;
    if (mStuck < p.shakeOffSticking2) return flickInt > p.shakeOffBlowB;
    if (mStuck < p.shakeOffSticking3) return flickInt > p.shakeOffBlowC;
    return flickInt > p.shakeOffBlowD;
}

bool Fsm::isAttackLimitTime(TickOutput& out) {
    // BigTreasure.cpp:356-403. 300 u cell sphere, 225 u XZ box, 3x accrual
    // while a creature in range is stuck to something other than the Titan.
    bool check = false;
    float inc = kSourceDelta;
    const float factor = 2.0f * float(mOwn.weaponCount()) + 4.0f;
    for (std::size_t i = 0; mIn && i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.alive || !(c.navi || c.pikmin)) continue;
        if (dist3(c.pos, mPos) > 300.0f + 20.0f) continue; // cell sphere (creature radius slack)
        if (!check && std::fabs(mPos.x - c.pos.x) < 225.0f && std::fabs(mPos.z - c.pos.z) < 225.0f) check = true;
        if (c.stuckElsewhere) inc = 3.0f * kSourceDelta;
    }
    bool result = false;
    if (mAttackLimitTimer > factor) result = check;
    else mAttackLimitTimer += inc;
    out.attackLimit = result;
    return result;
}

void Fsm::getTargetPosition() {
    // BigTreasure.cpp:409-439.
    const Params& p = mParams;
    if (distXZ2(mPos, mHome) < p.territoryRadius * p.territoryRadius) {
        const Candidate* best = nullptr;
        float bestD = 0.0f;
        for (std::size_t i = 0; mIn && i < mIn->count; ++i) {
            const Candidate& c = mIn->candidates[i];
            if (!c.pikmin || !c.alive || c.buried || c.stuckToSelf) continue; // ConditionNotStickClient
            const float d = dist3(c.pos, mPos);
            if (d > p.sightRadius) continue;
            if (std::fabs(angDist(c.pos)) > toRad(p.viewAngle)) continue;
            if (!best || d < bestD) { best = &c; bestD = d; }
        }
        if (best) {
            mTarget = best->pos;
        } else if (distXZ2(mPos, mTarget) < 625.0f) {
            const float range = p.territoryRadius - p.homeRadius;
            const float randDist = p.homeRadius + randWeightFloat(range);
            const float ang2 = std::atan2(mPos.x - mHome.x, mPos.z - mHome.z);
            const float ang1 = randWeightFloat(kPi);
            const float a = ang2 + ang1 + kPi / 2.0f;
            mTarget = {randDist * std::sin(a) + mHome.x, mHome.y, randDist * std::cos(a) + mHome.z};
        }
    } else {
        mTarget = mHome;
    }
}

void Fsm::setTreasureAttack(TickOutput& out) {
    // BigTreasure.cpp:984-1035: weight 12000 - hp per live weapon.
    float total = 0.0f;
    for (int w = 0; w < P2BTWEAPON_Count; ++w)
        if (mOwn.isWeaponAttached(w)) total += P2BigTreasureOwnership::kPickWeightBase - mOwn.weaponHealth(w);
    mAttackIndex = total > 0.0f ? mOwn.pickWeapon(randWeightFloat(total)) : -1;
    for (int tries = 0; mForcedCount > 0 && tries < mForcedCount; ++tries) {
        const int w = mForced[(mForcedAt++) % mForcedCount];
        if (mOwn.isWeaponAttached(w)) { mAttackIndex = w; break; }
    }
    out.pickedWeapon = mAttackIndex;
}

int Fsm::preAttackAnim() const {
    switch (mAttackIndex) {
    case P2BTWEAPON_Elec: return AnimPreAttackE;
    case P2BTWEAPON_Fire: return AnimPreAttackF;
    case P2BTWEAPON_Gas: return AnimPreAttackG;
    case P2BTWEAPON_Water: return AnimPreAttackW;
    default: return AnimDropItem;
    }
}
int Fsm::attackAnim() const {
    switch (mAttackIndex) {
    case P2BTWEAPON_Elec: return AnimAttackE;
    case P2BTWEAPON_Fire: {
        const int cur = mAnim.anim();
        if (cur == AnimPreAttackF) return AnimAttackF;
        if (cur == AnimPreAttackFR) return AnimAttackFR;
        if (cur == AnimPreAttackFL) return AnimAttackFL;
        return AnimAttackFB;
    }
    case P2BTWEAPON_Gas: return AnimAttackG;
    case P2BTWEAPON_Water: return AnimAttackW;
    default: return AnimDropItem;
    }
}
int Fsm::putItemAnim() const {
    switch (mAttackIndex) {
    case P2BTWEAPON_Elec: return AnimAttackEndE;
    case P2BTWEAPON_Fire: {
        const int cur = mAnim.anim();
        if (cur == AnimAttackF) return AnimAttackEndF;
        if (cur == AnimAttackFR) return AnimAttackEndFR;
        if (cur == AnimAttackFL) return AnimAttackEndFL;
        return AnimAttackEndFB;
    }
    case P2BTWEAPON_Gas: return AnimAttackEndG;
    case P2BTWEAPON_Water: return AnimAttackEndW;
    default: return AnimDropItem;
    }
}
int Fsm::fireAttackAnim() {
    // BigTreasure.cpp:1116-1146: nearest captain (180 deg, 1280 u) angle
    // relative to the face direction, else a random angle.
    float angle = 0.0f;
    const Candidate* navi = nullptr;
    float bestD = 0.0f;
    for (std::size_t i = 0; mIn && i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.navi || !c.alive) continue;
        const float d = dist3(c.pos, mPos);
        if (d > 1280.0f || std::fabs(angDist(c.pos)) > toRad(180.0f)) continue;
        if (!navi || d < bestD) { navi = &c; bestD = d; }
    }
    if (navi) angle = round0(round0(std::atan2(navi->pos.x - mPos.x, navi->pos.z - mPos.z)) - mFaceDir);
    else angle = randWeightFloat(kTau);
    if (angle > kPi / 4 && angle <= 3 * kPi / 4) return AnimPreAttackFL;
    if (angle > 3 * kPi / 4 && angle <= 5 * kPi / 4) return AnimPreAttackFB;
    if (angle > 5 * kPi / 4 && angle <= 7 * kPi / 4) return AnimPreAttackFR;
    return AnimPreAttackF;
}
float Fsm::preAttackTimeMax() const {
    switch (mAttackIndex) {
    case P2BTWEAPON_Elec: return mParams.elecWait;
    case P2BTWEAPON_Fire: return mOwn.isNormalAttack(P2BTWEAPON_Fire) ? mParams.fireWait1 : mParams.fireWait2;
    case P2BTWEAPON_Gas: return mParams.gasWait;
    case P2BTWEAPON_Water: return mParams.waterWait;
    default: return 5.0f;
    }
}
float Fsm::attackTimeMax() const {
    switch (mAttackIndex) {
    case P2BTWEAPON_Elec: return mParams.elecAttackMax;
    case P2BTWEAPON_Fire: return mParams.fireAttackMax;
    case P2BTWEAPON_Gas: return mParams.gasAttackMax;
    case P2BTWEAPON_Water: return mParams.waterAttackMax;
    default: return 5.0f;
    }
}

void Fsm::flickStick(TickOutput& out, const char* reason) {
    // EnemyFunc::flickStickPikmin(titan, shakeChance, shakeKnockback,
    // shakeDamage, -1000): each stuck Pikmin with randFloat < chance.
    for (std::size_t i = 0; mIn && i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.pikmin || !c.stuckToSelf || !c.alive) continue;
        if (mParams.shakeChance > randWeightFloat(1.0f)) out.flick.push_back(c.id);
    }
    out.flickKnockback = mParams.shakeKnockback;
    out.flickDamage = mParams.shakeDamage;
    out.flickAngle = round0(kFlickBackwardAngle + kPi);
    out.flickReason = reason;
}

void Fsm::transit(State next, TickOutput& out) {
    if (next == State::Null) next = mState; // unreachable in source order; never index -1
    const State from = mState;
    cleanup(from, out);
    mState = next;
    out.entered.push_back({from, next});
    initState(next, out);
}

void Fsm::cleanup(State state, TickOutput& out) {
    switch (state) {
    case State::Land:
        // StateLand::cleanup: bitter immune off; startProgramedIK.
        mGait.startProgramedIK(mPos, mFaceDir);
        break;
    case State::Attack:
        // StateAttack::cleanup: finishAttack.
        mElements.finish();
        out.attackFinished = true;
        break;
    default:
        break;
    }
}

void Fsm::initState(State state, TickOutput& out) {
    mNext = State::Null;
    switch (state) {
    case State::Dead:
        mGait.forceFinishIKMotion();
        startBlend(AnimDead);
        break;
    case State::Stay:
        mStateTimer = 0.0f;
        mAnim.start(AnimAppear);
        mAnim.stop();
        break;
    case State::Land:
        mAnim.resume(); // startMotion(): continue appear
        flickStick(out, "land");
        break;
    case State::Wait:
        mStateTimer = randWeightFloat(5.0f);
        startBlend(AnimWait2);
        break;
    case State::ItemWait:
        mStateTimer = randWeightFloat(5.0f);
        startBlend(AnimWait1);
        break;
    case State::Flick:
        mStateTimer = 0.0f;
        startBlend(AnimFlick);
        break;
    case State::PreAttack:
        mStateTimer = 0.0f;
        resetAttackLimitTimer();
        setTreasureAttack(out);
        startBlend(preAttackAnim());
        break;
    case State::Attack:
        mStateTimer = 0.0f;
        startBlend(attackAnim());
        break;
    case State::PutItem:
        mStateTimer = 0.0f;
        startBlend(putItemAnim());
        break;
    case State::DropItem:
        mStateTimer = 0.0f;
        startBlend(AnimDropItem);
        break;
    case State::Walk:
        mStateTimer = randWeightFloat(10.0f);
        startBlend(AnimWait2_2);
        mGait.startIKMotion();
        getTargetPosition();
        break;
    case State::ItemWalk:
        mStateTimer = randWeightFloat(10.0f);
        startBlend(AnimMove1);
        mGait.startIKMotion();
        getTargetPosition();
        break;
    case State::Null:
        break;
    }
}

void Fsm::exec(TickOutput& out) {
    const float dt = kSourceDelta;
    const bool end = mAnim.is(KeyEnd);
    switch (mState) {
    case State::Dead:
        if (mAnim.is(Key100)) {
            out.throwupItem = true;
            if (mLouie) {
                P2BigTreasureDropEvent ev;
                if (mOwn.releaseLouie(&ev)) {
                    out.louieReleased = true;
                    out.drops.push_back({-1, jointWorld(JointLoozy), ev.velocity});
                }
                mLouie = false;
            }
        } else if (end) {
            out.killRequest = true;
        }
        break;
    case State::Stay:
        if (mStateTimer < 0.01f) {
            bool target = false;
            for (std::size_t i = 0; mIn && i < mIn->count && !target; ++i) {
                const Candidate& c = mIn->candidates[i];
                if (c.alive && (c.navi || c.pikmin) && dist3(c.pos, mPos) < mParams.privateRadius) target = true;
            }
            // startBigTreasureBootUpDemo() is false (no movie): timer = 4.
            if (target) mStateTimer = 4.0f;
        } else {
            mStateTimer += dt;
            if (mStateTimer > 4.0f) transit(State::Land, out);
        }
        break;
    case State::Land:
        if (mAnim.playing()) {
            const int k = mAnim.latched();
            if (k == Key2 || k == Key4 || k == Key6 || k == Key8 || k == Key9) {
                flickStick(out, "land");
            } else if (k == Key10) {
                if (!isCaptured()) mAnim.start(AnimAppear2);
            } else if (k == KeyEnd) {
                if (mHealth <= 0.0f) transit(State::Dead, out);
                else if (isStartFlick()) transit(isCaptured() ? State::PreAttack : State::Flick, out);
                else transit(isCaptured() ? State::ItemWalk : State::Walk, out);
            }
        }
        break;
    case State::Wait:
        mStateTimer += dt;
        if (mHealth <= 0.0f) { mNext = State::Dead; mAnim.finish(); }
        else if (isStartFlick()) { mNext = State::Flick; mAnim.finish(); }
        else if (mStateTimer > 5.0f) { mNext = State::Walk; mAnim.finish(); }
        if (end) transit(mNext, out);
        break;
    case State::ItemWait:
        if (!isCaptured()) { transit(State::DropItem, out); break; }
        if (isStartFlick() || isAttackLimitTime(out)) { mNext = State::PreAttack; mAnim.finish(); }
        else if (mStateTimer > 5.0f) { mNext = State::ItemWalk; mAnim.finish(); }
        mStateTimer += dt;
        if (end) transit(mNext, out);
        break;
    case State::Flick:
        if (mAnim.is(Key2)) {
            flickStick(out, "flick");
            mFlickTimer = 0.0f;
        } else if (end) {
            transit(mHealth <= 0.0f ? State::Dead : State::Walk, out);
        }
        break;
    case State::PreAttack:
        if (!isCaptured()) { transit(State::DropItem, out); break; }
        if (!isCaptured(mAttackIndex)) { transit(State::PreAttack, out); break; }
        if (mStateTimer > preAttackTimeMax()) mAnim.finish();
        mStateTimer += dt;
        if (mAnim.is(Key2)) {
            flickStick(out, "preattack");
            mFlickTimer = 0.0f;
        } else if (mAnim.is(Key3)) {
            const int fire = fireAttackAnim();
            if (fire != AnimPreAttackF) mAnim.start(fire);
            mFireVariant = fire == AnimPreAttackFR ? 1 : fire == AnimPreAttackFL ? 2 : fire == AnimPreAttackFB ? 3 : 0;
        } else if (end) {
            transit(State::Attack, out);
        }
        break;
    case State::Attack:
        if (!isCaptured()) { transit(State::DropItem, out); break; }
        if (!isCaptured(mAttackIndex)) { transit(State::PreAttack, out); break; }
        if (mStateTimer > attackTimeMax()) mAnim.finish();
        mStateTimer += dt;
        if (mAnim.is(Key2)) {
            // startAttack: start*Attack is a no-op while that element runs.
            if (!(mElements.active() && mElements.activeWeapon() == mAttackIndex)) {
                if (mAttackIndex == P2BTWEAPON_Fire) {
                    // fire variant from the running anim
                    const int cur = mAnim.anim();
                    mFireVariant = cur == AnimAttackFR ? 1 : cur == AnimAttackFL ? 2 : cur == AnimAttackFB ? 3 : 0;
                }
                const float hp = mOwn.weaponHealth(mAttackIndex);
                const Vec3 emit = jointWorld(mAttackIndex);
                mElements.setAim(buildAim(mAttackIndex));
                if (mElements.start(mAttackIndex, emit, mIn ? mIn->groundY : mPos.y, hp, randWeightFloat(1.0f),
                                    randWeightFloat(1.0f))) {
                    out.attackStarted = mAttackIndex;
                    out.fireVariant = mAttackIndex == P2BTWEAPON_Fire ? mFireVariant : -1;
                }
            }
        } else if (end) {
            transit(State::PutItem, out);
        }
        break;
    case State::PutItem:
        if (!isCaptured()) { transit(State::DropItem, out); break; }
        if (!isCaptured(mAttackIndex)) { transit(State::PreAttack, out); break; }
        if (end) transit(isStartFlick() ? State::PreAttack : State::ItemWalk, out);
        break;
    case State::DropItem:
        if (end) {
            if (mHealth <= 0.0f) transit(State::Dead, out);
            else if (isStartFlick()) transit(State::Flick, out);
            else transit(State::Walk, out);
        }
        break;
    case State::Walk:
        getTargetPosition();
        if (mHealth <= 0.0f) { transit(State::Dead, out); break; }
        if (isStartFlick()) { mNext = State::Flick; mGait.finishIKMotion(); }
        else if (mStateTimer > 10.0f) { mNext = State::Wait; mGait.finishIKMotion(); }
        mStateTimer += dt;
        if (end) {
            if (mGait.isFinishIKMotion()) transit(mNext, out);
            else mAnim.start(AnimWait2_2);
        }
        break;
    case State::ItemWalk: {
        getTargetPosition();
        if (mHealth <= 0.0f) { transit(State::Dead, out); break; }
        if (mAnim.anim() == AnimMove1 && !isCaptured()) {
            mAnim.start(AnimDropItem); // startBlendAnimation(24, true)
        } else {
            if (isStartFlick() || isAttackLimitTime(out)) {
                mNext = isCaptured() ? State::PreAttack : State::Flick;
                mGait.finishIKMotion();
            } else if (mStateTimer > 10.0f) {
                mNext = isCaptured() ? State::ItemWait : State::Wait;
                mGait.finishIKMotion();
            }
        }
        mStateTimer += dt;
        const State before = mState;
        if (mGait.isFinishIKMotion()) transit(mNext, out);
        // Source does not return after the IK transit: an END latched this
        // tick still restarts the walk clip (BigTreasureState.cpp:850-865).
        if (end && before == State::ItemWalk) mAnim.start(isCaptured() ? AnimMove1 : AnimWait2);
        break;
    }
    case State::Null:
        break;
    }
}

void Fsm::applyHits(TickOutput& out) {
    // BigTreasure::damageCallBack (BigTreasure.cpp:248-275) per counted hit.
    for (std::size_t i = 0; mIn && i < mIn->hitCount; ++i) {
        const Hit& h = mIn->hits[i];
        if (!(h.damage > 0.0f) || !std::isfinite(h.damage)) continue;
        // StateDead::init -> deathProcedure -> setAlive(false): a dead Titan
        // takes no further damage (Pikmin drop a non-alive stick target).
        if (mState == State::Dead) {
            out.deadHits += 1;
            continue;
        }
        // mTreasureCollParts[i] == collpart: only a captured weapon's own part
        // (a dropped weapon's part pointer is cleared, so it is "other").
        const bool hasPart = h.part != PartNone;
        const int coll = h.part >= 0 && h.part < P2BTWEAPON_Count && mOwn.isWeaponAttached(h.part) ? h.part : -1;
        bool pinch = false;
        const P2BigTreasureDamageResult r = mOwn.damageCallBack(h.fromPiki, hasPart, coll, h.damage,
                                                                static_cast<P2BigTreasurePhase>(int(mState)), false, &pinch);
        const float adjusted = mState == State::Land ? h.damage * P2BigTreasureOwnership::kLandDamageFactor : h.damage;
        if (r == P2BTDMG_Weapon) {
            out.weaponHits[coll] += 1;
            out.weaponDamage[coll] += adjusted;
            if (pinch) out.pinchSmoke[coll] = true;
            mFlickTimer += 1.0f;
        } else if (r == P2BTDMG_Body) {
            out.bodyDamage += adjusted;
            out.bodyHits += 1;
            mFlickTimer += 1.0f; // addDamage(adjusted, 1.0f)
        } else {
            out.ignoredHits += 1;
        }
    }
    mHealth -= out.bodyDamage;
}

Vec3 Fsm::jointAxisWorld(int joint, int column) const {
    const Mat34& m = jointModel(joint);
    const float x = m.m[0][column], y = m.m[1][column], z = m.m[2][column];
    const float s = std::sin(mFaceDir), c = std::cos(mFaceDir);
    Vec3 v{c * x + s * z, y, -s * x + c * z};
    const float len = std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
    if (len > 1e-6f) { v.x /= len; v.y /= len; v.z /= len; }
    return v;
}

bool Fsm::poseHasJoint(int joint) const {
    const int anim = mAnim.anim();
    if (anim < 0 || anim >= AnimCount || mBank.clip[anim].poses.empty()) return false;
    for (const auto& p : mBank.clip[anim].poses) if (p.have[joint]) return true;
    return false;
}

P2BigTreasureElementAim Fsm::buildAim(int weapon) {
    P2BigTreasureElementAim aim;
    aim.set = true;
    const int eff = weapon == P2BTWEAPON_Elec ? JointElecEff : weapon == P2BTWEAPON_Fire ? JointFireEff
                    : weapon == P2BTWEAPON_Gas ? JointGasEff : JointWaterEff;
    aim.emit = jointWorld(eff);
    if (poseHasJoint(JointFireEff)) {
        // updateFireEmitPosition: direction = otakara_fire_eff column 0.
        aim.direction = jointAxisWorld(JointFireEff, 0);
    } else {
        // Unstaged bank fallback: face + fire variant (F, FR right, FL left, FB back).
        const float yaw = mFaceDir + (mFireVariant == 1 ? -kPi / 2 : mFireVariant == 2 ? kPi / 2 : mFireVariant == 3 ? kPi : 0.0f);
        aim.direction = {std::sin(yaw), 0.0f, std::cos(yaw)};
        // (retail attackf* poses hold otakara_fire_eff at y ~29 above the owner)
        if (weapon == P2BTWEAPON_Fire) aim.emit = {mPos.x, mPos.y + 30.0f, mPos.z};
    }
    if (weapon == P2BTWEAPON_Water) {
        // getWaterTargetCreature: a random non-Blue Pikmin, else the nearest
        // captain (180 deg, 1280 u), else a random point within 500 u.
        std::vector<const Candidate*> list;
        const Candidate* navi = nullptr;
        float bestD = 0.0f;
        for (std::size_t i = 0; mIn && i < mIn->count; ++i) {
            const Candidate& c = mIn->candidates[i];
            if (!c.alive) continue;
            if (c.pikmin && !c.blue) list.push_back(&c);
            if (c.navi) {
                const float d = dist3(c.pos, mPos);
                if (d <= 1280.0f && (!navi || d < bestD)) { navi = &c; bestD = d; }
            }
        }
        aim.haveWaterTarget = true;
        if (!list.empty()) {
            std::size_t k = std::size_t(float(list.size()) * randWeightFloat(1.0f));
            if (k >= list.size()) k = list.size() - 1;
            aim.waterTarget = list[k]->pos;
        } else if (navi) {
            aim.waterTarget = navi->pos;
        } else {
            const float d = randWeightFloat(500.0f), a = randWeightFloat(kTau);
            aim.waterTarget = {mPos.x + d * std::sin(a), mPos.y, mPos.z + d * std::cos(a)};
        }
    }
    return aim;
}

void Fsm::updateAttack(TickOutput& out) {
    if (!mElements.active()) return;
    const int weapon = mElements.activeWeapon();
    const P2BigTreasureElementAim aim = buildAim(weapon);
    mElements.setAim(aim);
    P2BigTreasureElementStats stats;
    if (mIn) mElements.tick(kSourceDelta, mIn->element, stats);
    out.attackNodes = stats.nodes;
    out.attackEmits = stats.emits;
    if (stats.nodes <= 0 || !mIn) return;
    for (std::size_t i = 0; i < mIn->count; ++i) {
        const Candidate& c = mIn->candidates[i];
        if (!c.alive || !(c.navi || c.pikmin)) continue;
        // Source receivers stimulate every creature inside a node on every
        // update (no per-attack handled set); the receiver's own state gates
        // repeats. A captain's refusal falls back to flick-or-attack.
        if (!mElements.queryHit(c.pos)) continue;
        ElementHit eh;
        eh.id = c.id;
        eh.navi = c.navi;
        if (c.navi) {
            // FIRE 0.33, GAS 0.67, WATER 1.0, ELEC 0.5 (BigTreasureAttack.cpp:9-12)
            const float chance = weapon == P2BTWEAPON_Fire ? 0.33f : weapon == P2BTWEAPON_Gas ? 0.67f
                               : weapon == P2BTWEAPON_Water ? 1.0f : 0.5f;
            eh.naviFlick = randWeightFloat(1.0f) < chance;
        }
        eh.hit = p2_bigtreasure_receiver_resolve(weapon, aim.emit, mParams.attackDamage, c.pos);
        out.elementHits.push_back(eh);
    }
}

void Fsm::updateTreasure(TickOutput& out) {
    // updateTreasure -> dropTreasure (BigTreasure.cpp:748-822): each weapon at
    // 0 HP is released with (0,100,0); setupBigTreasureCollision flicks the
    // Pikmin stuck to that part (flickStickCollPartPikmin, 10 / 0 / backward).
    P2BigTreasureDropEvent drops[P2BTWEAPON_Count];
    // Positions before the ownership releases them (joint of the live pose).
    Vec3 where[P2BTWEAPON_Count];
    for (int w = 0; w < P2BTWEAPON_Count; ++w) where[w] = jointWorld(w);
    const std::size_t n = mOwn.update(drops, P2BTWEAPON_Count);
    for (std::size_t k = 0; k < n && k < P2BTWEAPON_Count; ++k) {
        const int w = drops[k].weapon;
        out.drops.push_back({w, where[w], drops[k].velocity});
        for (std::size_t i = 0; mIn && i < mIn->count; ++i) {
            const Candidate& c = mIn->candidates[i];
            if (c.pikmin && c.alive && c.stuckToSelf && c.stuckPart == w) out.partFlick.push_back(c.id);
        }
    }
    out.partFlickAngle = kFlickBackwardAngle;
}

TickOutput Fsm::tick(const TickInput& in) {
    TickOutput out;
    out.valid = true;
    mIn = &in;
    mPos = in.position;
    mHealth = in.health;
    mStuck = 0;
    for (std::size_t i = 0; i < in.count; ++i)
        if (in.candidates[i].pikmin && in.candidates[i].alive && in.candidates[i].stuckToSelf) ++mStuck;
    // EnemyBase::update order: damage (collision callbacks + doUpdateCommon:
    // updateAttack), doUpdate (FSM exec + updateIKSystem), doAnimation
    // (animate, updateTreasure).
    applyHits(out);
    updateAttack(out);
    exec(out);
    out.legLanded = mGait.update(mPos, mFaceDir, mTarget, kSourceDelta);
    out.ikActive = mGait.active();
    if (mGait.active()) {
        mFaceDir = mGait.faceDir();
        const Vec3& c = mGait.centre();
        out.velocity = {(c.x - mPos.x) / kSourceDelta, 0.0f, (c.z - mPos.z) / kSourceDelta};
        // A blocked host must not be yanked: cap the correction speed.
        const float sp = std::sqrt(out.velocity.x * out.velocity.x + out.velocity.z * out.velocity.z);
        const float cap = 3.0f * mParams.moveSpeed;
        if (sp > cap) { out.velocity.x *= cap / sp; out.velocity.z *= cap / sp; }
    }
    if (mState == State::Dead || mState == State::Stay || mState == State::Land) out.velocity = {};
    out.faceDir = mFaceDir;
    mAnim.animate();
    updateTreasure(out);
    mIn = nullptr;
    return out;
}

} // namespace p2btown
