#pragma once

// Engine-free port of the P2 Long Legs leg IK (#173 Man-at-Legs walk animation).
//
// Source: native/pikmin2-research src/plugProjectNishimuraU/IKSystemBase.cpp,
// IKSystemMgr.cpp, nslibmath.cpp (NsMathExp::calcLagrange / calcJointPos) and
// Houdai.cpp (setupIKSystem / setIKParameter / updateIKSystem /
// doAnimationIKSystem). One `Mgr::update` is one source frame
// (sys->getDeltaTime() = 1/30). The host supplies the ground height
// (mapMgr->getMinY) through a callback and the per-frame leg joint world
// matrices (the source J3D joint world matrices, which the port computes from
// the bind skeleton and the drawn body matrix); `Mgr::makeMatrix` rewrites the
// three joints of every leg exactly like the source joint callback does.
//
// Port boundaries (documented, not approximations of the maths):
//  * The body carries no clip playback (the port has no Houdai pose bank), so
//    the joint matrices handed to makeMatrix are the bind skeleton under the
//    drawn body matrix; with blend motion on (Flick/Shot) the source reads its
//    orientation hints from those matrices, i.e. from the bind pose here.
//  * JointGroundCallBack (water ripple / foot sound) is not ported; the host
//    reads the leg state edges instead.

#include <string>
#include <vector>

namespace p2ik {

struct V3 {
    float x = 0.0f, y = 0.0f, z = 0.0f;
    V3() = default;
    V3(float ax, float ay, float az) : x(ax), y(ay), z(az) {}
};

// Row-major 3x4, source Matrixf layout: column c of row r is m[r][c]; columns
// 0..2 are the joint axes, column 3 the translation.
struct M34 {
    float m[3][4] = {{1, 0, 0, 0}, {0, 1, 0, 0}, {0, 0, 1, 0}};
    V3 col(int c) const { return V3(m[0][c], m[1][c], m[2][c]); }
    void setCol(int c, const V3& v) { m[0][c] = v.x; m[1][c] = v.y; m[2][c] = v.z; }
};

M34 mul(const M34& a, const M34& b);         // a * b (affine)
bool inverse(const M34& a, M34& out);        // affine inverse
V3 apply(const M34& a, const V3& p);         // a * (p, 1)
V3 applyDir(const M34& a, const V3& d);      // a * (d, 0)

// Source NsMathExp helpers.
void calcLagrange(const V3* controlPoints, float t, V3& out);
void calcJointPos(const V3& top, const V3& bottom, float topToMiddle, float middleToBottom,
                  const V3& middleHint, V3& middleOut);

// IKSystemParms (IKSystemBase.h). Defaults are the source constructor values.
struct Parms {
    int legCount = -1;
    float footPositionOffset = 0.0f;
    float footPositionRadius = 0.0f;
    float moveInterpolationRate = 0.75f;
    float heightOffset = 120.0f;         // leg swing
    float bottomJointMoveSpeed = 3.0f;   // base factor
    float raiseSlowdownFactor = -0.15f;
    float downwardAccelFactor = 0.5f;
    float maxDecelFactor = 10.0f;
    float minDecelFactor = -2.0f;
    float bendFactor = 0.0f;
    float moveSpeed = 75.0f;
    float minimumMoveSpeed = 0.0f;
    float viewAngleDeg = 30.0f;          // mEnragedAngle (getViewAngle)
    float maxTurnAngleDeg = 60.0f;
    float traceMoveRate = 0.1f;
    float traceVelocityDamping = 0.7f;
    float traceHeightOffset = -1.5f;
};

// Houdai::setIKParameter with the retail disc parameters (US GPVE01 rev 0,
// houdai/enemyparm.txt; docs/PIKMIN2_LONG_LEGS_AUDIT.md "Legs"): bend 0.67,
// speed fp06 250, max turn fp28 60, base factor 9.0, raise decel -0.1,
// downward accel 0.5, min/max decel -2.0 / 10, leg swing 40.
Parms houdaiParms();

// Ground height under (x, z): the source mapMgr->getMinY.
typedef float (*GroundFn)(void* ctx, float x, float z);

enum Joint { TOP = 0, MIDDLE = 1, BOTTOM = 2 };

// IKSystemBase: one leg.
struct Leg {
    bool enabled = false;
    bool blend = false;
    bool onGround = true;
    bool wasOnGround = true;
    bool scaleJoints = false;
    float bendRatio = 0.0f;
    float moveRatio = 0.0f;
    float moveTimer = 0.0f;
    float topToMiddle = 0.0f;
    float middleToBottom = 0.0f;
    V3 target;
    V3 ik[3];

    // `joints` are the current world matrices of TOP/MIDDLE/BOTTOM.
    void startProgramedIK(const M34 joints[3]);
    void startMovePosition(V3 targetMove, const Parms& p, GroundFn ground, void* ctx);
    void update(const Parms& p, float dt, GroundFn ground, void* ctx, const M34& bottomJoint);
    void makeMatrix(M34 joints[3], const Parms& p) const;

private:
    void moveBottomJointPosition(const Parms& p, float dt);
    bool onGroundPosition(const Parms& p, GroundFn ground, void* ctx, const M34& bottomJoint);
    void makeBendRatio(const Parms& p);
};

constexpr int kLegCount = 4;

// IKSystemMgr.
class Mgr {
public:
    void init(const V3& ownerPos, float ownerFace);
    // IKSystemMgr::startProgramedIK: capture the current leg joints (world).
    void startProgramedIK(const M34 legJoints[kLegCount][3], const V3& ownerPos, float ownerFace);
    void startIKMotion();
    void finishIKMotion() { mInMotion = false; }
    void forceFinishIKMotion() { mInMotion = false; mOnGround = true; }
    void setBlend(bool on);
    bool isFinishIKMotion() const;
    // Port boundary (#173): the host brain (P2HoudaiFsm::startStride) already
    // applies the source setNextCentrePosition rule and owns the body stride,
    // so the draw IK executes that choice instead of re-deriving it from the
    // feet: one four-leg cycle (updateController's all-legs-0 branch) whose
    // leg targets are `next` plus the bind leg angles/radius at `newFace`.
    // Legs still in flight keep flying; the chain restarts at leg 0.
    void startCycleTo(const V3& next, float newFace, const Parms& p, GroundFn ground, void* ctx);
    // IKSystemMgr::doUpdate: legs, controller, face, centre and trace centre.
    // `legJoints` are the current world matrices (used for onGroundPosition's
    // foot sampling only when Parms::legCount > 0).
    void update(const Parms& p, float dt, GroundFn ground, void* ctx, const M34 legJoints[kLegCount][3]);
    void makeMatrix(M34 legJoints[kLegCount][3], const Parms& p) const;

    bool active() const { return mActive; }
    bool inMotion() const { return mInMotion; }
    int legState(int i) const { return mLegStates[i]; }
    const Leg& leg(int i) const { return mLegs[i]; }
    V3 centre() const { return mCentre; }
    V3 traceCentre() const { return mTrace; }
    float faceDir() const { return mFace; }
    float distanceOffset() const { return mDistanceOffset; }
    float legAngle(int i) const { return mLegAngle[i]; }
    V3 legTarget(int i) const { return mLegTarget[i]; }
    // IKSystemMgr::mTargetPosition (Houdai::setIKSystemTargetPosition).
    void setTargetPosition(const V3& t) { mTarget = t; }
    // Edges of the last update (the source JointGroundCallBack hooks).
    int liftedMask() const { return mLiftedMask; }
    int plantedMask() const { return mPlantedMask; }
    int cycles() const { return mCycles; }

private:
    void updateController(const Parms& p, GroundFn ground, void* ctx);
    void setNextCentrePosition(const Parms& p);
    void calcFaceDir();
    void calcCentrePosition();
    void calcTraceCentrePosition(const Parms& p);

    bool mActive = false;
    bool mInMotion = false;
    bool mOnGround = false;
    float mFace = 0.0f;
    float mDistanceOffset = 100.0f;
    float mLegAngle[kLegCount] = {0, 0, 0, 0};   // source mLegHeight (an angle)
    int mLegStates[kLegCount] = {0, 0, 0, 0};
    V3 mTarget;
    V3 mCentre;
    V3 mTrace;
    V3 mTraceVel;
    V3 mLegTarget[kLegCount];
    Leg mLegs[kLegCount];
    int mLiftedMask = 0, mPlantedMask = 0, mCycles = 0;
};

// Rigid skin sidecar `longlegs_<species>_skin_00.txt` (P2_LONG_LEGS_SKIN_1),
// written by experimental/pikmin2_long_legs_visual.py next to the bind .mod:
// every joint's bind model-space matrix and, in .mod order, the owning joint
// and joint-local value of each baked position and normal.
struct Skin {
    std::vector<std::string> names;
    std::vector<M34> bind;
    std::vector<int> posJoint, nrmJoint;
    std::vector<V3> posLocal, nrmLocal;
    int joint(const char* name) const;
    // Returns false (and leaves *error set) on any malformed input.
    bool parse(const std::string& text, std::string* error);
    // Evaluate positions/normals under per-joint model-space matrices.
    void evaluate(const std::vector<M34>& joints, std::vector<V3>& pos, std::vector<V3>& nrm) const;
};

// Houdai::setupIKSystem joint names, legs 0..3.
extern const char* const kHoudaiLegJoints[kLegCount][3];

} // namespace p2ik
