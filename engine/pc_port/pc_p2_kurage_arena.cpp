#include "pc_p2_kurage_arena.h"

#include "Camera.h"
#include "Collision.h"
#include "Creature.h"
#include "Graphics.h"
#include "Shape.h"
#include "gameflow.h"
#include "system.h"
#include "pc_p2_kurage_receiver.h"
#include "pc_p2_retail_player.h"
#include "pc_p2_kurage_visual.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

namespace {
class LesserHost final : public Creature {
public:
    LesserHost() : Creature(nullptr) { }
    void refresh(Graphics&) override { }
    void doKill() override { }
};
struct Host {
    Shape* shape = nullptr;
    Shape* attackShape = nullptr;
    LesserHost owner;
    CollPart mouth{};
    Vector3f position;
    float height = 90.0f;
    float radius = 35.0f;
    Vector3f mouthJointTranslation;
    bool sourceJointAvailable = false;
    float phase = 0.0f;
    bool ready = false;
    bool alive = false;
    // The event clock is supplied by Kurage attack.bca.  The converted MOD is
    // deliberately a static attack pose; it does not provide skeletal BCA/BTK
    // playback.
    p2retail::Player attackPlayer;
    bool attackPlaying = false;
    bool sucking = false;
    // Test-only frame injection retained for focused unit/fixture seams.  It
    // never drives the live host update path.
    bool attackFrameSeam = false;
    float attackFrame = 0.0f;
};
Host sHost;
// Retail Lesser Kurage suckPikmin() queries collision part ID 'suck'; hire1 is
// a BMD visual joint, not the source suction collision location.
constexpr char kSourceSuctionPart[] = "suck";
constexpr char kVisualHireJoint[] = "hire1";
constexpr int kSourceSuctionJoint = 4;
constexpr float kSourceSuctionRadius = 15.0f;
// Retail Kurage/attack.bca SHA-256 302660c6ba9c86fee11cc6aca98bd514e201a80d8530be3a5cce867a9dc74a4e.
// ANF1 is big-endian: loop attribute 2, duration 0x0078 (120), 12 joints.
// enemyanimmgr.txt supplies the source event table below.
const p2retail::Motion kAttackMotion{
    "attack.bca", "302660c6ba9c86fee11cc6aca98bd514e201a80d8530be3a5cce867a9dc74a4e",
    120, 2, {{37, 2}, {60, 0}, {67, 1}}
};

bool attackPoseActive()
{
    return sHost.attackFrameSeam
        ? sHost.attackFrame >= 37.0f && sHost.attackFrame < 67.0f
        : sHost.sucking;
}
bool suckingActive()
{
    return sHost.attackFrameSeam
        ? sHost.attackFrame >= 37.0f && sHost.attackFrame < 67.0f
        : sHost.sucking;
}

bool finite(float value) { return std::isfinite(value); }
bool valid(Vector3f value)
{
    return finite(value.x) && finite(value.y) && finite(value.z)
        && std::fabs(value.x) < 100000.0f && std::fabs(value.y) < 100000.0f
        && std::fabs(value.z) < 100000.0f;
}

void updateHostCollision()
{
    sHost.owner.mSRT.t = sHost.position;
    sHost.owner.mSRT.s.set(1.0f, 1.0f, 1.0f);
    sHost.owner.mSRT.r.set(0.0f, 0.0f, 0.0f);
    sHost.mouth.mPartType = PART_BoundSphere;
    sHost.mouth.mRadius = kSourceSuctionRadius;
    // enemycoll.txt binds suck to JNT1 index 4 with a zero offset.  The
    // converted preview MOD currently omits that JNT1 hierarchy, so the
    // bounded host uses the source offset from its origin until a collision-
    // tree world-matrix bridge can supply that joint's animated position.
    sHost.mouth.mCentre.set(sHost.position.x + sHost.mouthJointTranslation.x,
        sHost.position.y + sHost.mouthJointTranslation.y,
        sHost.position.z + sHost.mouthJointTranslation.z);
    sHost.mouth.mJointMatrix.makeIdentity();
}
}

void pc_p2_kurage_arena_reset()
{
    // Detach while the concrete host and its CollPart still exist.
    pc_p2_kurage_receiver_owner_invalidated(&sHost.owner);
    sHost.shape = nullptr; sHost.ready = sHost.alive = false; sHost.phase = 0.0f;
    sHost.attackPlayer.cancel(); sHost.attackPlaying = sHost.sucking = false;
    sHost.attackFrameSeam = false; sHost.attackFrame = 0.0f;
}

bool pc_p2_kurage_arena_setup(const char* profilePath)
{
    pc_p2_kurage_arena_reset();
    if (!profilePath || !*profilePath) return false;
    std::ifstream profile(profilePath);
    std::string header;
    if (!(profile >> header) || header != "P2_KURAGE_ARENA_1") return false;
    Host parsed;
    std::string key;
    if (!(profile >> key >> parsed.position.x >> parsed.position.y >> parsed.position.z)
        || key != "position" || !valid(parsed.position)) return false;
    if (!(profile >> key >> parsed.height >> parsed.radius)
        || key != "params" || !finite(parsed.height) || !finite(parsed.radius)
        || parsed.height <= 0.0f || parsed.height > 1000.0f || parsed.radius < 0.0f
        || parsed.radius > 1000.0f) return false;
    if (profile >> key) return false;
    if (!pc_p2_kurage_visual_setup()) return false;
    parsed.shape = pc_p2_kurage_visual_wait_shape();
    parsed.attackShape = pc_p2_kurage_visual_attack_shape();
    if (!parsed.shape || !parsed.attackShape) return false;
    parsed.sourceJointAvailable = parsed.shape->mJointCount > kSourceSuctionJoint;
    if (parsed.sourceJointAvailable)
        parsed.mouthJointTranslation = parsed.shape->mJointList[kSourceSuctionJoint].mTranslation;
    else
        parsed.mouthJointTranslation.set(0.0f, 0.0f, 0.0f);
    parsed.ready = parsed.alive = true;
    sHost.shape = parsed.shape; sHost.attackShape = parsed.attackShape; sHost.position = parsed.position; sHost.height = parsed.height;
    sHost.radius = parsed.radius; sHost.mouthJointTranslation = parsed.mouthJointTranslation;
    sHost.sourceJointAvailable = parsed.sourceJointAvailable;
    sHost.phase = 0.0f; sHost.ready = sHost.alive = true;
    sHost.owner.mStickListHead = nullptr;
    updateHostCollision();
    std::printf("P2_KURAGE_ARENA_READY species=Kurage id=57 visual=converted_wait source_part=%s joint=%d radius=%.1f offset=0,0,0 joint_translation=%s visual_joint=%s host_receiver=bounded\n", kSourceSuctionPart, kSourceSuctionJoint, kSourceSuctionRadius, sHost.sourceJointAvailable ? "wait_pose" : "unavailable_origin", kVisualHireJoint);
    return true;
}

bool pc_p2_kurage_arena_update(float delta, bool ownerAlive)
{
    if (!sHost.ready || !sHost.alive || !finite(delta) || delta < 0.0f || delta > 1.0f) return false;
    if (!ownerAlive) {
        // This private host is the lifecycle authority for its bounded receiver.
        // Release while the concrete owner and mouth still exist; callers must
        // not substitute this for P2's full Kurage health/bitter/FSM path.
        pc_p2_kurage_receiver_update(0.0f, false, true, false);
        return false;
    }
    sHost.phase += delta * 0.8f;
    if (!finite(sHost.phase)) { sHost.alive = false; return false; }
    sHost.position.y += std::sin(sHost.phase) * sHost.height * delta;
    if (!valid(sHost.position)) { sHost.alive = false; return false; }
    updateHostCollision();
    // Ordering contract: the Piki frame observes the previous receiver
    // velocity; this host tick refreshes the moving `suck` target and drives
    // the following frame.  Piki::doAI suppresses ordinary action writes for
    // receiver-owned Piki.  Health/bitter are intentionally unavailable on
    // this bounded host and remain the source-adapter defaults here.
    pc_p2_kurage_receiver_update(delta, true, true, false);
    return true;
}

bool pc_p2_kurage_arena_begin_attack()
{
    if (!sHost.ready || !sHost.alive || !sHost.attackPlayer.start(kAttackMotion)) return false;
    sHost.attackFrameSeam = false;
    sHost.attackFrame = 0.0f;
    sHost.attackPlaying = true;
    sHost.sucking = false;
    return true;
}

bool pc_p2_kurage_arena_tick_attack(float delta)
{
    if (!sHost.ready || !sHost.alive || !sHost.attackPlaying) return false;
    const auto result = sHost.attackPlayer.advance(delta, [](const p2retail::Event& event) {
        if (event.type == 2) {
            sHost.sucking = true;
        } else if (event.type == 1 || event.type == 1000) {
            // Kurage StateAttack leaves its sucking interval on type 1.  This
            // bounded static-pose host closes there instead of re-looping 60..67.
            sHost.sucking = false;
            sHost.attackPlaying = false;
            sHost.attackPlayer.cancel();
        }
    });
    return result == p2retail::Update::Ok || result == p2retail::Update::Replaced;
}

Creature* pc_p2_kurage_arena_owner()
{
    return sHost.ready && sHost.alive ? &sHost.owner : nullptr;
}

CollPart* pc_p2_kurage_arena_mouth()
{
    return sHost.ready && sHost.alive ? &sHost.mouth : nullptr;
}

int pc_p2_kurage_arena_scan_admit(float verticalOffset, float attackRadius, int maxAdmissions, bool admitEligible)
{
    // Retail attack.bca events: 37=KEYEVENT_2 starts suck, 67=type1 ends it.
    if (!sHost.ready || !sHost.alive || !suckingActive()) return 0;
    return pc_p2_kurage_receiver_scan_admit(verticalOffset, attackRadius, maxAdmissions, admitEligible);
}
void pc_p2_kurage_arena_set_attack_frame(float frame)
{
    sHost.attackFrameSeam = true;
    sHost.attackFrame = finite(frame) && frame >= 0.0f ? frame : 0.0f;
}
bool pc_p2_kurage_arena_attack_pose_active()
{
    return sHost.ready && attackPoseActive();
}

void pc_p2_kurage_arena_draw(Graphics& gfx)
{
    if (!sHost.ready || !sHost.alive || !sHost.shape || !gfx.mCamera) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    Matrix4f world;
    world.makeIdentity();
    world.mMtx[0][3] = sHost.position.x;
    world.mMtx[1][3] = sHost.position.y;
    world.mMtx[2][3] = sHost.position.z;
    Matrix4f matrix;
    gfx.mCamera->mLookAtMtx.multiplyTo(world, matrix);
    Shape* shape = attackPoseActive() ? sHost.attackShape : sHost.shape;
    shape->updateAnim(gfx, matrix, nullptr, nullptr);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    static bool logged = false;
    if (!logged) { std::printf("P2_KURAGE_DRAW position=%.2f,%.2f,%.2f\n", sHost.position.x, sHost.position.y, sHost.position.z); logged = true; }
}
