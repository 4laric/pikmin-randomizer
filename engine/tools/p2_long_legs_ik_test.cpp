// Engine-free tests for the ported P2 Long Legs leg IK (#173 Man-at-Legs walk).
//
// The leg joint matrices below are the retail Man-at-Legs bind skeleton
// (enemy/data/Houdai enemy.bmd JNT1, as written to longlegs_Houdai_skin_00.txt
// by experimental/pikmin2_long_legs_visual.py), legs in Houdai::setupIKSystem
// order: rhand, lhand, rfoot, lfoot; top, middle, bottom.
#include "pc_p2_long_legs_ik.h"

#include <cmath>
#include <cstdio>
#include <string>

using namespace p2ik;

namespace {
int failures = 0;
void check(bool ok, const char* what)
{
    if (!ok) {
        ++failures;
        std::printf("FAIL %s\n", what);
    }
}
bool near(float a, float b, float eps) { return std::fabs(a - b) <= eps; }
float dist(const V3& a, const V3& b)
{
    return std::sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y) + (a.z - b.z) * (a.z - b.z));
}

const float kBind[4][3][12] = {
    {{-0.640920793f, 0.298749303f, 0.707085137f, -35.5951796f, -0.422520812f, -0.906353221f, -4.24003211e-05f, 132.060885f, 0.640856224f, -0.298785361f, 0.707128424f, 35.5877855f},
     {-0.000166273811f, 0.707128406f, 0.707085137f, -80.8037084f, -0.999999981f, -0.000192741756f, -4.24003211e-05f, 102.257598f, 0.00010630236f, -0.70708513f, 0.707128424f, 80.7917584f},
     {-0.707128418f, -9.84787234e-05f, 0.707085137f, -80.8202029f, 9.68679582e-05f, -0.999999994f, -4.24003211e-05f, 3.06944402f, 0.707085137f, 3.85114214e-05f, 0.707128424f, 80.8023044f}},
    {{0.64071687f, -0.298865792f, 0.707220709f, 35.5872156f, -0.422643688f, -0.906295926f, -9.3194554e-05f, 132.05406f, 0.6409791f, -0.298842657f, -0.706992829f, 35.5946101f},
     {-2.54941703e-05f, -0.706992835f, 0.707220709f, 80.7813605f, -0.999999994f, -5.716458e-05f, -9.3194554e-05f, 102.242109f, 0.000106315857f, -0.707220707f, -0.706992829f, 80.8072518f},
     {0.706992829f, -9.32762591e-05f, 0.707220709f, 80.7788318f, -3.87092188e-05f, -0.999999995f, -9.3194554e-05f, 3.05395362f, 0.707220714f, 3.85119202e-05f, -0.706992829f, 80.817797f}},
    {{-0.640797899f, 0.298827609f, -0.707163427f, -35.5883551f, -0.422520824f, -0.906353207f, -0.000131377733f, 132.060884f, -0.6409791f, 0.298707087f, 0.707050118f, -35.5946101f},
     {-4.33608163e-05f, 0.707050129f, -0.707163427f, -80.7882152f, -0.999999973f, -0.000192725151f, -0.000131377733f, 102.257599f, -0.000229178821f, 0.707163402f, 0.707050118f, -80.8072515f},
     {-0.70705013f, 2.4426766e-05f, -0.707163427f, -80.7925168f, 9.68513536e-05f, -0.999999987f, -0.000131377733f, 3.06944511f, -0.707163421f, -0.000161380378f, 0.707050118f, -80.829984f}},
    {{0.640766142f, -0.298947013f, -0.707141736f, 35.5940402f, -0.422800406f, -0.90622283f, -5.05820869e-06f, 132.05406f, -0.640826473f, 0.298983054f, -0.707071824f, -35.5877855f},
     {-7.8275175e-05f, -0.70707182f, -0.707141736f, 80.7916595f, -0.999999993f, 0.000115761996f, -5.05820869e-06f, 102.231053f, 8.54366555e-05f, 0.707141731f, -0.707071824f, -80.7896618f},
     {0.707071809f, -0.000146064836f, -0.707141736f, 80.7838969f, -0.000211635794f, -0.999999978f, -5.05820869e-06f, 3.04289773f, -0.70714172f, 0.000153233019f, -0.707071824f, -80.781189f}},
};

M34 fromRow(const float* v)
{
    M34 m;
    for (int r = 0; r < 3; ++r)
        for (int c = 0; c < 4; ++c) m.m[r][c] = v[r * 4 + c];
    return m;
}

// Body matrix: translate + yaw (P1/P2 facing: forward = (sin a, 0, cos a)).
M34 body(const V3& pos, float face)
{
    M34 m;
    const float c = std::cos(face), s = std::sin(face);
    m.m[0][0] = c;  m.m[0][1] = 0; m.m[0][2] = s;  m.m[0][3] = pos.x;
    m.m[1][0] = 0;  m.m[1][1] = 1; m.m[1][2] = 0;  m.m[1][3] = pos.y;
    m.m[2][0] = -s; m.m[2][1] = 0; m.m[2][2] = c;  m.m[2][3] = pos.z;
    return m;
}

void fk(const M34& b, M34 out[4][3])
{
    for (int l = 0; l < 4; ++l)
        for (int j = 0; j < 3; ++j) out[l][j] = mul(b, fromRow(kBind[l][j]));
}

float flatGround(void*, float, float) { return 0.0f; }
float slopeGround(void*, float x, float) { return 0.25f * x; }

void testLagrange()
{
    const V3 cp[3] = {V3(0, 0, 0), V3(5, 40, 1), V3(10, 0, 2)};
    V3 o;
    calcLagrange(cp, 0.0f, o);
    check(near(o.x, 0, 1e-5f) && near(o.y, 0, 1e-5f), "lagrange t=0 is the lift point");
    calcLagrange(cp, 1.0f, o);
    check(near(o.x, 5, 1e-5f) && near(o.y, 40, 1e-5f) && near(o.z, 1, 1e-5f), "lagrange t=1 is the swing apex");
    calcLagrange(cp, 2.0f, o);
    check(near(o.x, 10, 1e-5f) && near(o.y, 0, 1e-5f), "lagrange t=2 is the landing point");
}

void testBindReproduced()
{
    // startProgramedIK on the bind skeleton then makeMatrix must give back the
    // bind matrices: the source IK frame construction matches the authored
    // leg joint frames, so a planted, unmoved Man-at-Legs draws its bind pose.
    const Parms p = houdaiParms();
    const M34 b = body(V3(100, 0, -50), 0.7f);
    M34 legs[4][3];
    fk(b, legs);
    Mgr mgr;
    mgr.init(V3(100, 0, -50), 0.7f);
    mgr.startProgramedIK(legs, V3(100, 0, -50), 0.7f);
    M34 posed[4][3];
    fk(b, posed);
    mgr.makeMatrix(posed, p);
    float worst = 0.0f;
    for (int l = 0; l < 4; ++l)
        for (int j = 0; j < 3; ++j)
            for (int r = 0; r < 3; ++r)
                for (int c = 0; c < 4; ++c)
                    worst = std::fmax(worst, std::fabs(posed[l][j].m[r][c] - legs[l][j].m[r][c]));
    std::printf("bind_reproduction_max_error=%.6f\n", worst);
    // The authored knees sit ~0.01 units off the vertical plane the source
    // getMiddleDirection hint spans (retail JNT1 rounding), so the rest pose
    // matches to about a hundredth of a unit, not bit-exactly.
    check(worst < 0.05f, "IK at rest reproduces the bind leg joints");
    check(near(mgr.distanceOffset(), 114.3f, 0.5f), "IK distance offset is the bind foot radius");
    // Leg angles: rhand front-right (-45 deg from face), lhand front-left.
    check(near(mgr.legAngle(0), -0.785f, 0.01f), "rhand leg angle -45 deg");
    check(near(mgr.legAngle(1), 0.785f, 0.01f), "lhand leg angle +45 deg");
}

void testWalkCycle()
{
    const Parms p = houdaiParms();
    V3 pos(0, 0, 0);
    float face = 0.0f;
    M34 legs[4][3];
    fk(body(pos, face), legs);
    Mgr mgr;
    mgr.init(pos, face);
    mgr.startProgramedIK(legs, pos, face);
    mgr.setTargetPosition(V3(0, 0, 2000));
    mgr.startIKMotion();
    const float dt = 1.0f / 30.0f;
    int liftOrder[16];
    int lifts = 0;
    float apex[4] = {0, 0, 0, 0};
    V3 planted[4];
    for (int i = 0; i < 4; ++i) planted[i] = mgr.leg(i).target;
    bool plantedStill = true;
    int ticks = 0;
    int firstCycleTicks = -1;
    V3 centreAfterCycle;
    float sourceOverreach = 0.0f;
    for (; ticks < 300 && mgr.cycles() < 3; ++ticks) {
        fk(body(mgr.centre(), mgr.faceDir()), legs);
        mgr.update(p, dt, flatGround, nullptr, legs);
        {
            // Source draw: the body sits on the trace centre (doAnimationIKSystem).
            M34 drawn[4][3];
            fk(body(mgr.traceCentre(), mgr.faceDir()), drawn);
            for (int l = 0; l < 4; ++l)
                sourceOverreach = std::fmax(sourceOverreach, dist(drawn[l][0].col(3), mgr.leg(l).target)
                                                                 - mgr.leg(l).topToMiddle - mgr.leg(l).middleToBottom);
        }
        for (int i = 0; i < 4; ++i) {
            if (mgr.liftedMask() & (1 << i)) {
                if (lifts < 16) liftOrder[lifts] = i;
                ++lifts;
            }
            if (mgr.legState(i) == 1) apex[i] = std::fmax(apex[i], mgr.leg(i).target.y);
            if (mgr.legState(i) == 3 || mgr.legState(i) == 0) {
                if (!(mgr.plantedMask() & (1 << i)) && dist(mgr.leg(i).target, planted[i]) > 1e-3f
                    && mgr.legState(i) == 3)
                    plantedStill = false;
            }
            if (mgr.plantedMask() & (1 << i)) planted[i] = mgr.leg(i).target;
        }
        if (mgr.cycles() == 2 && firstCycleTicks < 0) {
            firstCycleTicks = ticks;
            centreAfterCycle = mgr.centre();
        }
    }
    std::printf("walk: source_trace_overreach=%.2f\n", sourceOverreach);
    std::printf("walk: lifts=%d first_cycle_ticks=%d centre_after_cycle=%.1f,%.1f,%.1f apex=%.1f,%.1f,%.1f,%.1f\n",
                lifts, firstCycleTicks, centreAfterCycle.x, centreAfterCycle.y, centreAfterCycle.z,
                apex[0], apex[1], apex[2], apex[3]);
    check(lifts >= 8, "legs keep stepping while in motion");
    bool order = true;
    for (int i = 0; i < lifts && i < 16; ++i)
        if (liftOrder[i] != i % 4) order = false;
    check(order, "legs lift in source order rhand, lhand, rfoot, lfoot");
    for (int i = 0; i < 4; ++i) check(apex[i] > 20.0f, "each stepping foot swings above the ground");
    check(plantedStill, "planted feet stay where they landed");
    check(firstCycleTicks > 10 && firstCycleTicks < 60, "one four-leg cycle takes 10..60 source frames");
    check(near(centreAfterCycle.z, 250.0f, 3.0f) && near(centreAfterCycle.x, 0.0f, 1.0f),
          "one cycle carries the centre one IK stride (moveSpeed 250) toward the target");
    check(near(centreAfterCycle.y, 0.0f, 0.01f), "centre height is the weighted foot height");
    check(std::fabs(mgr.faceDir()) < 0.02f || std::fabs(mgr.faceDir() - 6.2832f) < 0.02f,
          "straight walk keeps facing");

    // Knee keeps both bone lengths while a leg is mid-step.
    fk(body(mgr.centre(), mgr.faceDir()), legs);
    M34 posed[4][3];
    fk(body(mgr.centre(), mgr.faceDir()), posed);
    mgr.makeMatrix(posed, p);
    for (int l = 0; l < 4; ++l) {
        const float a = dist(posed[l][0].col(3), posed[l][1].col(3));
        const float b = dist(posed[l][1].col(3), posed[l][2].col(3));
        check(near(a, mgr.leg(l).topToMiddle, 0.05f) || mgr.leg(l).topToMiddle + mgr.leg(l).middleToBottom
                  < dist(posed[l][0].col(3), posed[l][2].col(3)),
              "thigh length preserved");
        check(near(b, mgr.leg(l).middleToBottom, 0.05f) || mgr.leg(l).topToMiddle + mgr.leg(l).middleToBottom
                  < dist(posed[l][0].col(3), posed[l][2].col(3)),
              "shin length preserved");
        check(dist(posed[l][2].col(3), mgr.leg(l).target) < 1e-3f, "foot joint sits on the IK target");
    }

    // finishIKMotion: the running cycle completes, then isFinishIKMotion.
    mgr.finishIKMotion();
    int settle = 0;
    while (!mgr.isFinishIKMotion() && settle < 120) {
        fk(body(mgr.centre(), mgr.faceDir()), legs);
        mgr.update(p, dt, flatGround, nullptr, legs);
        ++settle;
    }
    std::printf("walk_finish_settle_ticks=%d\n", settle);
    check(mgr.isFinishIKMotion(), "finishIKMotion lets the cycle land all four legs");
}

// Host brain drives the strides (pc_p2_long_legs.cpp): every 60 source ticks
// P2HoudaiFsm::startStride picks the next centre (250 ahead) and the body
// interpolates to it linearly; startCycleTo steps the legs to that centre.
void testBrainDrivenFollow()
{
    const Parms p = houdaiParms();
    V3 from(0, 0, 0);
    float face = 0.0f;
    M34 legs[4][3];
    fk(body(from, face), legs);
    Mgr mgr;
    mgr.init(from, face);
    mgr.startProgramedIK(legs, from, face);
    const float dt = 1.0f / 30.0f;
    const int strideTicks = 60;
    float worstStretch = 0.0f;
    int lifts = 0;
    for (int stride = 0; stride < 4; ++stride) {
        // Third stride turns in place by 60 deg, the rest walk 250 ahead.
        const float nextFace = stride == 2 ? face + 1.0471976f : face;
        const V3 to = stride == 2 ? from : V3(from.x + 250.0f * std::sin(face), 0, from.z + 250.0f * std::cos(face));
        mgr.startCycleTo(to, nextFace, p, flatGround, nullptr);
        ++lifts;
        for (int t = 1; t <= strideTicks; ++t) {
            const float k = float(t) / strideTicks;
            const V3 b(from.x + (to.x - from.x) * k, 0, from.z + (to.z - from.z) * k);
            const float f = face + (nextFace - face) * k;
            fk(body(b, f), legs);
            mgr.update(p, dt, flatGround, nullptr, legs);
            M34 posed[4][3];
            fk(body(b, f), posed);
            mgr.makeMatrix(posed, p);
            for (int l = 0; l < 4; ++l) {
                if (t > 1 && (mgr.liftedMask() & (1 << l))) ++lifts;
                const float reach = dist(posed[l][0].col(3), mgr.leg(l).target);
                const float over = reach - (mgr.leg(l).topToMiddle + mgr.leg(l).middleToBottom);
                worstStretch = std::fmax(worstStretch, over);
            }
        }
        check(mgr.isFinishIKMotion(), "a brain stride's leg cycle lands all four legs within the stride");
        for (int l = 0; l < 4; ++l) {
            const float a = nextFace + mgr.legAngle(l);
            const V3 want(to.x + mgr.distanceOffset() * std::sin(a), 0, to.z + mgr.distanceOffset() * std::cos(a));
            check(dist(mgr.leg(l).target, want) < 2.0f, "each foot lands on its bind offset around the stride end (the source plants on first ground contact, ~1 unit short of t=2)");
        }
        from = to;
        face = nextFace;
    }
    std::printf("follow: lifts=%d worst_overreach=%.2f\n", lifts, worstStretch);
    check(lifts == 16, "four strides lift sixteen feet");
    // The source maths itself overreaches: a 250 stride against 170 units of leg
    // (testWalkCycle measures ~115 with the body on the source trace centre).
    check(worstStretch < 140.0f, "brain-driven overreach stays near the source trace-centre draw");
}

void testTurnInPlace()
{
    const Parms p = houdaiParms();
    V3 pos(0, 0, 0);
    M34 legs[4][3];
    fk(body(pos, 0.0f), legs);
    Mgr mgr;
    mgr.init(pos, 0.0f);
    mgr.startProgramedIK(legs, pos, 0.0f);
    mgr.setTargetPosition(V3(0, 0, -1000)); // directly behind
    mgr.startIKMotion();
    for (int t = 0; t < 200 && mgr.cycles() < 2; ++t) {
        fk(body(mgr.centre(), mgr.faceDir()), legs);
        mgr.update(p, 1.0f / 30.0f, flatGround, nullptr, legs);
    }
    float face = mgr.faceDir();
    if (face > 3.14159f) face -= 6.28318f;
    std::printf("turn: centre=%.2f,%.2f face_deg=%.2f\n", mgr.centre().x, mgr.centre().z, face * 57.29578f);
    check(dist(mgr.centre(), V3(0, 0, 0)) < 1.0f, "outside the IK view angle the centre stays");
    check(near(std::fabs(face) * 57.29578f, 60.0f, 1.0f), "and the body turns by the max turn angle (60 deg)");
}

void testSlopePlant()
{
    const Parms p = houdaiParms();
    V3 pos(0, 0, 0);
    M34 legs[4][3];
    fk(body(pos, 0.0f), legs);
    Mgr mgr;
    mgr.init(pos, 0.0f);
    mgr.startProgramedIK(legs, pos, 0.0f);
    mgr.setTargetPosition(V3(0, 0, 2000));
    mgr.startIKMotion();
    for (int t = 0; t < 200 && mgr.cycles() < 2; ++t) {
        fk(body(mgr.centre(), mgr.faceDir()), legs);
        mgr.update(p, 1.0f / 30.0f, slopeGround, nullptr, legs);
    }
    for (int i = 0; i < 4; ++i) {
        const V3 f = mgr.leg(i).target;
        check(near(f.y, 0.25f * f.x, 0.5f), "a landed foot sits on the sloped ground");
    }
}

void testSkinParse()
{
    const std::string text =
        "P2_LONG_LEGS_SKIN_1\njoints 2\n"
        "j 0 body 1 0 0 0 0 1 0 10 0 0 1 0\n"
        "j 1 foot 1 0 0 5 0 1 0 0 0 0 1 0\n"
        "positions 2\n0 1 2 3\n1 0 0 0\n"
        "normals 1\n1 0 1 0\nend\n";
    Skin skin;
    std::string error;
    check(skin.parse(text, &error), "skin sidecar parses");
    check(skin.joint("foot") == 1 && skin.joint("missing") < 0, "skin joint lookup");
    std::vector<V3> pos, nrm;
    skin.evaluate(skin.bind, pos, nrm);
    check(pos.size() == 2 && near(pos[0].y, 12.0f, 1e-5f) && near(pos[1].x, 5.0f, 1e-5f), "skin evaluates bind");
    Skin bad;
    check(!bad.parse("P2_LONG_LEGS_SKIN_1\njoints 1\nj 0 a 1 0 0 0 0 1 0 0 0 0 1 0\npositions 1\n3 0 0 0\n", &error),
          "skin rejects out-of-range joint");
}
} // namespace

int main()
{
    testLagrange();
    testBindReproduced();
    testWalkCycle();
    testTurnInPlace();
    testBrainDrivenFollow();
    testSlopePlant();
    testSkinParse();
    if (failures) {
        std::printf("P2_LONG_LEGS_IK_TEST_FAIL failures=%d\n", failures);
        return 1;
    }
    std::printf("P2_LONG_LEGS_IK_TEST_PASS\n");
    return 0;
}
