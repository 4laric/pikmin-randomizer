#pragma once
#include "Creature.h"
#include "pc_p2_sarai_pose_bank.h"
#include "pc_p2_sarai_fsm.h"
#include "pc_p2_sarai_captor.h"
#include "pc_p2_sarai_lifecycle.h"
#include "pc_p2_retail_player.h"
#include <cstdint>
#include <string>
#include <vector>

class Graphics;
class Shape;
class CollPart;
class Navi;
class BTeki;
class Piki;

// Private visual host for the staged P2 Sarai (Swooping Snitchbug, enemy ID 23)
// model. It is deliberately not registered as a P1 teki. It loads the converted
// Sarai model, carries the two source mouth CollParts (rkamujnt / lkamujnt) and
// drives both mouth joint matrices from a sampled animated pose bank, mirroring
// the P2DemonHost visual surface. An opt-in natural route additionally drives the
// isolated p2sarai::Fsm Wait/Move/Attack/CatchFly/FallMeck states against a live
// naviMgr captain through the shared mouth-stick captor bridge.
class P2SaraiHost final : public Creature {
public:
    P2SaraiHost();
    ~P2SaraiHost();

    bool load(const char* modelPath, const Vector3f& mouthA, const Vector3f& mouthB);
    void setPosition(const Vector3f& position);
    // Atomic pose update: source-local joint bases before the owner transform.
    bool setMouthPose(const Matrix4f& mouthA, const Matrix4f& mouthB);
    bool loadMouthPoses(const char* path);
    bool applyMouthFrame(int frame);
    bool loadPoseMeshes(const char* profile);
    bool preloadPoseMeshes(const char* profile);
    bool switchPoseMeshes(const char* profile);
    bool applyPoseFrame(int frame);
    int renderedPoseFrame() const { return mRenderedFrame; }
    bool hasRenderableShape() const { return mLoaded && mShape != nullptr; }
    unsigned renderCount() const { return mRenderCount; }
    Vector3f mouthCentre(unsigned slot) const;
    // Rest-pose effector. Admission/proximity may use this stable reference so
    // approach and capture share one point once the FSM slice lands.
    Vector3f staticMouthCentre(unsigned slot) const;
    // Fixture/owner access to the exact live mouth CollParts and generation
    // token; this does not transfer ownership.
    CollPart* mouthPart(unsigned slot) const { return slot < 2 ? mMouths[slot] : nullptr; }
    std::uint64_t ownerToken() const { return mOwnerToken; }
    // Mouth capture/attachment receiver (source eatPikmin + FallMeck/Flick).
    // These drive pc_p2_sarai_capture_bridge against the host's live mouth
    // CollParts; the captured Pikmin are carried (never swallowed) and released
    // on drop/flick/teardown. The host does not transfer mouth ownership.
    bool capturePiki(Piki* piki, unsigned slot);
    bool releasePiki(Piki* piki);
    unsigned carriedCount() const;
    unsigned dropOwned(float damage, float downSpeed);
    unsigned flickOwned();
    void sceneExit();

    // Ordinary spawned anchor binding (#242 admission). The host binds to the
    // spawned teki actor that owns the lane's generated slot; that actor is the
    // damage/lifetime anchor (real health, engine corpse on death) while this
    // host owns the Sarai behaviour and visual. Default-off; only the ordinary
    // manager setup binds.
    bool bindNativeActor(BTeki* actor, unsigned generatorId, int tekiType);
    void unbindNativeActor(BTeki* actor);
    bool revalidateNativeActor(BTeki* actor, unsigned generatorId, int tekiType);
    BTeki* boundNativeActor() const { return mBoundActor; }
    Vector3f position() const { return mSRT.t; }
    bool dead() const { return mDead; }

    // Opt-in natural captor route (#457). When enabled, update() acquires a live
    // target through the Sarai source target geometry (pc_p2_sarai_policy.h),
    // approaches under the source turn cap, runs the isolated p2sarai::Fsm
    // Attack/CatchFly/FallMeck clocks against the real two-mouth CollParts and
    // delivers capture/drop through the Pikmin mouth-stick bridge
    // (pc_p2_sarai_capture_bridge) for Pikmin targets. A captain-only fallback
    // through the shared pc_demon_capture bridge is kept ONLY for rooms that
    // stage zero Pikmin (private-room fixture accommodation, labelled at the
    // call site); retail getAttackableTarget() scans pikiMgr Pikmin and never
    // captains, so any staged Pikmin disables the captain path entirely.
    // Default-off: fixture-driven modes and the visual/pose route are unchanged.
    void enableNatural(float moveSpeed, float turnSpeed, float maxTurnAngleDegrees, float attackRange,
                       float territoryRadius, float viewAngleDegrees, float sightRadius, const Vector3f& home);
    void setNaturalMotions(const p2retail::Motion& wait, const p2retail::Motion& move,
                           const p2retail::Motion& attack, const p2retail::Motion& catchFly,
                           const p2retail::Motion& fallMeck);
    void setNaturalPoseProfiles(const char* waitProfile, const char* moveProfile, const char* attackProfile,
                                const char* catchProfile, const char* fallProfile);
    bool naturalEnabled() const { return mNaturalEnabled; }
    // Retail-scale campaign geometry (US GPVE01 rev 0 EnemyParmsBase general
    // defaults: fp09 territory 200, fp12 sight 200, fp13 view 90). The manager
    // selects these for seed-bridge campaign bindings; the private-room
    // fixture path keeps its room-wide accommodation. Speeds stay
    // fixture-tuned in both paths (labelled accommodation, not retail fp06).
    static constexpr float kCampaignTerritoryRadius = 200.0f;
    static constexpr float kCampaignSightRadius = 200.0f;
    static constexpr float kCampaignViewAngleDegrees = 90.0f;
    // Post-drop reacquisition delay in seconds. Transcribes FallMeck::cleanup
    // resetAttackableTimer(0): after a damaging drop the source cannot
    // immediately re-acquire. The captor 3 s acquisition gate re-arms on top,
    // so the observable gap is cooldown + gate. Never shortens an attack.
    static constexpr float kReacquireCooldownSeconds = 3.0f;
    // Pikmin-first targeting switch. ON by default once natural is enabled:
    // live Pikmin are scanned with the retail geometry and the captain path
    // is taken only when pikiMgr holds zero Pikmin (fixture accommodation).
    void enablePikminTargeting(bool enable) { mPikminTargeting = enable; }
    bool pikminTargeting() const { return mPikminTargeting; }
    // Seconds remaining before re-acquisition is allowed (0 when free).
    float reacquireCooldown() const { return mReacquireCooldown; }
    // Successful Pikmin mouth captures delivered through the Pikmin bridge.
    unsigned pikminCaptureCount() const { return mPikminCaptures; }
    // The live Pikmin currently chased (Attack mTargetCreature analogue).
    Piki* pikminTarget() const { return mPikminTarget; }
    // 1 Wait/Move (acquire/approach), 2 Attack, 3 CatchFly, 4 FallMeck.
    int naturalPhase() const;
    int naturalStateId() const { return int(mFsm.state()); }
    bool occupied() const { return mLifecycle.occupied(); }
    // Ticks inside the source Attack capture window during which admission was
    // attempted (16 < frame <= 30).
    unsigned captureWindowTicks() const { return mCaptureWindowTicks; }
    // Forced damaging drop through the registered receiver; used by the fixture
    // interruption path and by the FSM FallMeck Key3 event.
    bool forceDrop(Navi* target, float damage, float speed);
    void release(Navi* target);

    void refresh(Graphics&) override;
    void update() override;
    void doKill() override;

private:
    struct PoseSet {
        std::string profile;
        P2SaraiPoseBank bank;
        std::vector<Shape*> meshes;
    };
    Shape* mShape;
    CollPart* mMouths[2];
    Matrix4f mMouthLocal[2];
    Matrix4f mStaticMouth[2];
    P2SaraiPoseBank mPoseBank;
    std::vector<Shape*> mPoseMeshes;
    std::vector<PoseSet> mPoseSets;
    int mRenderedFrame = -1;
    bool mLoaded;
    bool mSceneExited;
    unsigned mRenderCount = 0;
    std::uint64_t mOwnerToken;
    BTeki* mBoundActor = nullptr;
    bool mDead = false;
    void updateMouths();
    void resetMouthPose();

    // Natural capture route state.
    p2sarai::Fsm mFsm;
    p2retail::Player mPlayer;
    P2SaraiCaptor mCaptor;
    bool mNaturalEnabled = false;
    bool mNaturalMotionsSet = false;
    bool mNaturalMotionStarted = false;
    // Lane-owned, engine-free transcript of the shared captor bridge binding
    // (owner token, mouth slot, stick pointers, authority) plus the shared escape
    // window. The host still delegates every real side effect to
    // pc_demon_capture / pc_demon_forced_release / pc_demon_release /
    // pc_demon_owner_lost unchanged; this only replaces the raw occupancy bool so
    // capture, voluntary escape, interruption and teardown share one contract.
    p2sarai::CaptureLifecycle mLifecycle;
    float mNatMoveSpeed = 0.0f;
    float mNatTurnSpeed = 0.0f;
    float mNatMaxTurnDegrees = 0.0f;
    float mNatAttackRange = 0.0f;
    float mNatTerritoryRadius = 0.0f;
    float mNatViewAngle = 0.0f;
    float mNatSightRadius = 0.0f;
    Vector3f mNatHome;
    float mFacingRadians = 0.0f;
    p2sarai::KeyEvent mNatKeyEvent = p2sarai::KeyEvent::None;
    p2retail::Motion mNatWait;
    p2retail::Motion mNatMove;
    p2retail::Motion mNatAttack;
    p2retail::Motion mNatCatchFly;
    p2retail::Motion mNatFallMeck;
    std::string mNatWaitProfile;
    std::string mNatMoveProfile;
    std::string mNatAttackProfile;
    std::string mNatCatchProfile;
    std::string mNatFallProfile;
    unsigned mCaptureWindowTicks = 0;
    // Pikmin-first natural target state (family-local #834). mPikminTarget is
    // the Attack mTargetCreature analogue, revalidated every tick; the
    // cooldown is the lane-owned attackable-timer analogue (see
    // kReacquireCooldownSeconds). Neither touches captain stick state.
    Piki* mPikminTarget = nullptr;
    float mReacquireCooldown = 0.0f;
    bool mPikminTargeting = true;
    unsigned mPikminCaptures = 0;
    int mStatusTicks = 0;
    // Nearest-first retail-geometry scan of pikiMgr. Returns the live target
    // (or nullptr) and reports how many Pikmin were enumerated at all via
    // `enumerated`, so the caller can tell "empty room" (captain fallback)
    // from "squad present but nobody targetable" (retail: no target).
    Piki* acquirePikminTarget(int& enumerated);
    void armReacquireCooldown();
    void updateNatural();
    bool startNaturalMotion(p2sarai::Motion motion);
    void applyNaturalPose();
};
