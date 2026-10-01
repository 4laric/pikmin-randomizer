#pragma once

// Engine-free sampled joint pose bank for the Man-at-Legs (Houdai, P2 source id 66)
// rig draw (#1012, parent #173).
//
// Source data: `longlegs_Houdai_rig_00.txt` (P2_HOUDAI_RIG_1), written by
// experimental/pikmin2_houdai_rig.py from the US GPVE01 rev 0 disc: the 22-joint
// hierarchy of enemy.bmd, the retail houdai/enemycoll.txt tree and, for each of
// the five clips the source plays (landing, wait, flick, attack, dead), the
// model-space 3x4 matrix of every joint at a set of sample frames (the uniform
// frames of the pose limit unioned with the animation key frames).
//
// `Rig::sample` interpolates between the two bracketing samples: translation and
// scale lerp, rotation slerps the matrix rotation (decomposed once at load).
// A sample pair whose rotation/scale split does not reproduce the matrix (shear
// from non-uniform scale under rotation) falls back to a componentwise lerp.
//
// `aimGun` is the pose-side half of HoudaiShotGunMgr::rotateLevel/rotateVertical
// (HoudaiShotGun.cpp:1727-1790): the head joint (tamajnt) turns about the model
// vertical axis through its origin and the gun joint pitches about its own local Z
// (PSMTXRotRad 'Z' post-concatenated, columns renormalised and rescaled), so that
// the gun local X axis (the barrel) points along the requested direction.
// Descendants of a turned joint follow (J3D computes children from the callback's
// modified matrix).

#include "pc_p2_long_legs_ik.h"

#include <string>
#include <vector>

namespace p2houdairig {

struct CollNode {
    std::string id;    // four characters, e.g. "tama"
    std::string code;  // four characters, e.g. "st__"
    float radius = 0.0f;
    int joint = 0;
    p2ik::V3 offset;   // joint-local
    int parent = -1;
    bool stickable() const { return !code.empty() && code[0] == 's'; }  // CollPart::isStickable
};

class Rig {
public:
    // Returns false and sets *error on any malformed or inconsistent input.
    bool parse(const std::string& text, std::string* error);
    bool ready() const { return !mJointNames.empty() && mClips.size() == 5; }

    int jointCount() const { return int(mJointNames.size()); }
    int joint(const char* name) const;
    int parent(int joint) const { return mParents[size_t(joint)]; }
    const std::string& jointName(int joint) const { return mJointNames[size_t(joint)]; }
    const std::vector<CollNode>& coll() const { return mColl; }

    enum Clip { Landing = 0, Wait = 1, Flick = 2, Attack = 3, Dead = 4, ClipCount = 5 };
    static const char* clipName(int clip);
    int duration(int clip) const { return mClips[size_t(clip)].duration; }
    int poseCount(int clip) const { return int(mClips[size_t(clip)].frames.size()); }
    const std::vector<int>& frames(int clip) const { return mClips[size_t(clip)].frames; }
    int totalPoses() const;
    int minPoses() const;

    // Model-space joint matrices of `clip` at source frame `frame` (clamped to
    // 0..duration-1; fractional frames interpolate). `out` is resized.
    void sample(int clip, float frame, std::vector<p2ik::M34>& out) const;

    // Model-space centre of collision node `node` for the given posed joints.
    p2ik::V3 collCentre(const std::vector<p2ik::M34>& joints, int node) const;

    // Turn the gun (see header comment) so its X axis points along `dir` (unit,
    // model space). `head`/`gun` are joint indices. Returns false when the
    // joints are degenerate and leaves `joints` untouched.
    bool aimGun(std::vector<p2ik::M34>& joints, int head, int gun, const p2ik::V3& dir) const;

private:
    struct Decomposed {
        bool ok = false;
        float s[3] = {1, 1, 1};
        float q[4] = {0, 0, 0, 1};  // x y z w
        float t[3] = {0, 0, 0};
    };
    struct ClipData {
        int duration = 0;
        std::vector<int> frames;
        std::vector<std::vector<p2ik::M34>> raw;       // [sample][joint]
        std::vector<std::vector<Decomposed>> decomp;   // [sample][joint]
    };
    static Decomposed decompose(const p2ik::M34& m);
    static p2ik::M34 compose(const Decomposed& d);

    std::vector<std::string> mJointNames;
    std::vector<int> mParents;
    std::vector<CollNode> mColl;
    std::vector<ClipData> mClips;
};

}  // namespace p2houdairig
