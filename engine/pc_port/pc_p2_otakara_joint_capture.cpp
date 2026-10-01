// Otakara joint-matrix capture hook (#700).
//
// Observation-only: scans live Chappy-vehicle Teki actors, reads each
// carrier Shape's joint world matrices via getAnimMatrix(), and emits
// P2_OTAKARA_JOINT_CAPTURE markers. Never mutates actor, health, transport,
// generator or receiver state. Fail-closed on absent shape/joints/matrices.
#include "pc_p2_otakara_joint_capture.h"
#include "Creature.h"
#include "Generator.h"
#include "Matrix4f.h"
#include "Node.h"
#include "Shape.h"
#include "teki.h"
#include <cmath>
#include <cstdio>
#include <map>

namespace {
int sActorsCaptured = 0;
int sLastJoints = 0;
unsigned sLastGenerator = 0;
bool sReady = false;
bool sAbsentLogged = false;
unsigned long sPollTick = 0;
unsigned long sLastEmitTick = 0;
std::map<unsigned, bool> sSeen;

bool finiteJoint(const Matrix4f& m, float& x, float& y, float& z) {
    x = m.mMtx[0][3];
    y = m.mMtx[1][3];
    z = m.mMtx[2][3];
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z);
}
} // namespace

void pc_p2_otakara_joint_capture_setup() {
    pc_p2_otakara_joint_capture_reset();
}

void pc_p2_otakara_joint_capture_reset() {
    sActorsCaptured = 0;
    sLastJoints = 0;
    sLastGenerator = 0;
    sReady = false;
    sAbsentLogged = false;
    sPollTick = 0;
    sLastEmitTick = 0;
    sSeen.clear();
}

void pc_p2_otakara_joint_capture_poll() {
    if (!tekiMgr) return;
    ++sPollTick;
    int liveCarriers = 0;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        Teki* actor = static_cast<Teki*>(*it);
        if (!actor || !actor->isAlive() || actor->mTekiType != TEKI_Chappy) continue;
        ++liveCarriers;
        Shape* shape = (actor->mTekiShape != nullptr) ? actor->mTekiShape->mShape : nullptr;
        // The shape's animated matrices are allocated on first render/update;
        // reading them earlier would dereference null, so an unready carrier
        // is skipped (fail-closed) until its matrices exist.
        if (shape == nullptr || shape->mJointCount <= 0 || shape->mJointList == nullptr) continue;
        if (shape->mAnimMatrices == nullptr || shape->mAnimMtxCount == 0) continue;
        const unsigned generator = (actor->mGenerator != nullptr) ? actor->mGenerator->_70 : 0;
        const int joints = (shape->mJointCount < (int)shape->mAnimMtxCount)
            ? shape->mJointCount : (int)shape->mAnimMtxCount;
        int valid = 0;
        for (int j = 0; j < joints; ++j) {
            float x = 0.0f, y = 0.0f, z = 0.0f;
            if (!finiteJoint(shape->getAnimMatrix(j), x, y, z)) continue;
            ++valid;
        }
        if (valid <= 0) continue;
        const bool first = !sSeen[generator];
        sSeen[generator] = true;
        ++sActorsCaptured;
        sLastJoints = valid;
        sLastGenerator = generator;
        sReady = true;
        // Full per-joint output on first sighting and periodically after, so a
        // live tracked carrier is proven over time without flooding the log.
        if (first || sPollTick - sLastEmitTick >= 600) {
            sLastEmitTick = sPollTick;
            std::printf("[Pikipelago] P2_OTAKARA_JOINT_CAPTURE generator=%u teki=3 joints=%d\n",
                        generator, valid);
            for (int j = 0; j < joints; ++j) {
                float x = 0.0f, y = 0.0f, z = 0.0f;
                if (!finiteJoint(shape->getAnimMatrix(j), x, y, z)) continue;
                std::printf("[Pikipelago] P2_OTAKARA_JOINT generator=%u joint=%d xyz=%.3f,%.3f,%.3f\n",
                            generator, j, x, y, z);
            }
            std::fflush(stdout);
        }
    }
    // Absence is evidence, not a capture: a carrier with no Shape, no joints,
    // or no finite matrix (the "host has no otakara joint" case) is reported
    // once and can never satisfy ready().
    if (liveCarriers == 0 && !sAbsentLogged) {
        sAbsentLogged = true;
        std::printf("[Pikipelago] P2_OTAKARA_JOINT_ABSENT carriers=0\n");
        std::fflush(stdout);
    }
}

int pc_p2_otakara_joint_capture_actor_count() { return sActorsCaptured; }

int pc_p2_otakara_joint_capture_joint_count() { return sLastJoints; }

unsigned pc_p2_otakara_joint_capture_last_generator() { return sLastGenerator; }

bool pc_p2_otakara_joint_capture_ready() { return sReady; }
