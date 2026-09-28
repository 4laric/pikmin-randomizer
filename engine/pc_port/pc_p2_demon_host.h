#pragma once
#include "Creature.h"
#include "pc_p2_demon_attack_window.h"
#include "pc_p2_demon_pose_bank.h"
#include "pc_p2_retail_player.h"
#include "pc_p2_demon_catchfly_policy.h"
#include "pc_p2_demon_captor.h"

class Graphics;
class Shape;
class Navi;
class CollPart;
class BTeki;
class P2DemonHost;
void pc_p2_demon_manager_reset();
void pc_p2_demon_manager_forget(BTeki* actor);
bool pc_p2_demon_manager_bind(P2DemonHost* host, BTeki* actor, unsigned generatorId, int tekiType);
void pc_p2_demon_manager_setup();
std::size_t pc_p2_demon_manager_binding_count();
std::size_t pc_p2_demon_manager_render_count();
bool pc_p2_demon_manager_is_bound(BTeki* actor);
int pc_p2_demon_manager_natural_phase();
std::size_t pc_p2_demon_manager_natural_binding_count();
void pc_p2_demon_manager_update();
void pc_p2_demon_manager_draw(Graphics& gfx);
void pc_p2_demon_manager_update_actor(BTeki* actor);
bool pc_p2_demon_manager_draw_actor(BTeki* actor, Graphics& gfx, const Matrix4f& matrix, bool corpse);

// Private host for the staged P2 Demon model. It is deliberately not registered
// as a P1 teki or a replacement for Sarai's full FSM.
class P2DemonHost final : public Creature {
public:
    P2DemonHost();
    ~P2DemonHost() = default;

    bool load(const char* modelPath, const Vector3f& mouthA, const Vector3f& mouthB);
    void setPosition(const Vector3f& position);
    // Atomic pose update: source-local joint bases, before the native mouth twist.
    bool setMouthPose(const Matrix4f& mouthA, const Matrix4f& mouthB);
    bool loadMouthPoses(const char* path);
    bool applyMouthFrame(int frame);
    bool loadPoseMeshes(const char* profile);
    bool preloadPoseMeshes(const char* profile);
    bool switchPoseMeshes(const char* profile);
    bool applyPoseFrame(int frame);
    int renderedPoseFrame() const { return mRenderedFrame; }
    bool beginAttack();
    bool beginTimedAttack(const p2retail::Motion& motion);
    P2DemonAttackDecision tickTimedAttack(Navi*, float sourceFrames, bool floorContact);
    bool beginCatchFly(const p2retail::Motion& motion);
    bool selectCatchFlyTarget(const Vector3f& home, float radius, float angle);
    bool selectCatchFlyTargetSeeded(const Vector3f& home, float radius, std::uint32_t seed);
    // Opt-in natural captor front end. When enabled, P2DemonHost::update()
    // acquires a live captain through the source target gate, approaches it and
    // runs the source Attack/CatchFly/FallMeck clocks against it. Default-off so
    // fixture-driven modes and the production line are unchanged.
    void enableNatural(float moveSpeed, float turnSpeed, float maxTurnAngleDegrees, float attackRange,
                       float territoryRadius, float viewAngleDegrees, float sightRadius, const Vector3f& home);
    void setNaturalMotions(const p2retail::Motion& attack, const p2retail::Motion& catchFly, const p2retail::Motion& fallMeck);
    void setNaturalPoseProfiles(const char* catchProfile, const char* fallProfile);
    bool naturalEnabled() const { return mNaturalEnabled; }
    int naturalPhase() const; // 0 idle, 1 approach, 2 attack, 3 CatchFly, 4 FallMeck
    bool bindNativeActor(BTeki* actor, unsigned generatorId, int tekiType);
    void unbindNativeActor(BTeki* actor);
    bool revalidateNativeActor(BTeki* actor, unsigned generatorId, int tekiType);
    BTeki* boundNativeActor() const { return mBoundActor; }
    bool hasRenderableShape() const { return mLoaded && mShape != nullptr; }
    unsigned renderCount() const { return mRenderCount; }
    P2DemonAttackDecision tickCatchFly(Navi* target, float sourceFrames, p2demon::CatchFlyInput input);
    bool beginFallMeck(const p2retail::Motion& motion);
    P2DemonAttackDecision tickFallMeck(Navi* target, float sourceFrames, float damage, float speed);
    bool updateAttack(Navi* target, float sourceFrame, bool floorContact);
    bool endAttack(Navi* target);
    bool forceDrop(Navi* target, float damage, float speed);
    void release(Navi* target);
    bool occupied() const;
    Vector3f mouthCentre(unsigned slot) const;
    // Rest-pose effector used for grab admission/proximity. The animated mouth
    // CollPart carries the sampled joint for following; admission stays on the
    // stable effector so approach and capture use one reference point.
    Vector3f staticMouthCentre(unsigned slot) const;
    // Fixture/owner access to the exact live mouth CollParts and generation
    // token. The caller must revoke capture (release or sceneExit) before the
    // host parts are disposed; this does not transfer ownership.
    CollPart* mouthPart(unsigned slot) const { return slot < 2 ? mMouths[slot] : nullptr; }
    std::uint64_t ownerToken() const { return mOwnerToken; }
    void sceneExit();

    void refresh(Graphics&) override;
    void update() override;
    void doKill() override;

private:
    struct PoseSet {
        std::string profile;
        P2DemonPoseBank bank;
        std::vector<Shape*> meshes;
    };
    Shape* mShape;
    CollPart* mMouths[2];
    Matrix4f mMouthLocal[2];
    Matrix4f mStaticMouth[2];
    P2DemonAttackWindow mWindow;
    p2retail::Player mAttackPlayer;
    P2DemonPoseBank mPoseBank;
    std::vector<Shape*> mPoseMeshes;
    std::vector<PoseSet> mPoseSets;
    int mRenderedFrame = -1;
    bool mLoaded;
    bool mAttackActive;
    int mClockMode = 0;
    float mCatchElapsedFrames = 0.0f;
    bool mClockFinished = false;
    bool mClockReleased = false;
    float mFacingRadians = 0.0f;
    p2demon::TargetPoint mCatchTarget;
    BTeki* mBoundActor = nullptr;
    unsigned mRenderCount = 0;
    unsigned mOccupied;
    std::uint64_t mOwnerToken;
    void updateMouths();
    void resetMouthPose();

    P2DemonCaptor mCaptor;
    bool mNaturalEnabled = false;
    bool mNaturalMotionsSet = false;
    float mNaturalMoveSpeed = 0;
    float mNaturalTurnSpeed = 0;
    float mNaturalMaxTurnDegrees = 0;
    float mNaturalAttackRange = 0;
    float mNaturalTerritoryRadius = 0;
    float mNaturalViewAngle = 0;
    float mNaturalSightRadius = 0;
    Vector3f mNaturalHome;
    p2retail::Motion mNaturalAttack;
    p2retail::Motion mNaturalCatchFly;
    p2retail::Motion mNaturalFallMeck;
    std::string mNaturalCatchProfile;
    std::string mNaturalFallProfile;
    void updateNatural();
};
