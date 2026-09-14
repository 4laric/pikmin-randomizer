#pragma once
#include "Creature.h"
#include "pc_p2_sarai_pose_bank.h"
#include <cstdint>
#include <string>
#include <vector>

class Graphics;
class Shape;
class CollPart;

// Private visual host for the staged P2 Sarai (Swooping Snitchbug, enemy ID 23)
// model. It is deliberately not registered as a P1 teki and does not implement
// the Attack -> CatchFly -> FallMeck capture FSM. This first slice loads the
// converted Sarai model, carries the two source mouth CollParts (rkamujnt /
// lkamujnt) and drives both mouth joint matrices from a sampled animated pose
// bank, mirroring the P2DemonHost visual surface.
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
    void sceneExit();

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
    void updateMouths();
    void resetMouthPose();
};
