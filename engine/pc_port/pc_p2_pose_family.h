#pragma once
// Interpolated presentation for dedicated P2 family draw paths (#895).
//
// Frog, Tank, Kabuto, Sheargrub, Dwarf Orange, Mamuta and Chappy load their
// pose banks through p2poseload::loadStem (a few full Shapes per clip plus
// decoded positions/normals for every pose) and draw, per actor, the lerped
// pose through a private Shape with a crossfade on clip change and across a
// discontinuous loop seam (p2pose::present). The loaded Shapes stay the
// nearest-pose fallback: any private-Shape failure keeps that draw, and a
// clip whose vectors do not decode is drawn from its Shapes only (the loader
// reports P2_POSE_LOADER_FALLBACK). Fade time advances through
// pc_p2_pose_family_tick, called from BTeki::update.
#include "pc_p2_batch2_clock.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_loader.h"
#include "pc_p2_pose_motion.h"
#include "pc_p2_pose_shape.h"
#include "Shape.h"
#include "system.h"

#include <cstdio>
#include <map>
#include <set>
#include <string>
#include <vector>

class BTeki;

namespace p2posefamily {

struct Clip {
    std::vector<p2pose::Pose> poses;
    std::vector<int> frames;
    int duration = 1;
    bool seamContinuous = true;
    float holdFrame = 0.f;  // last visible pose's source frame (death clips stop here)
};

class Bank {
public:
    // `tag` names the family in log markers (e.g. "FROG").
    explicit Bank(const char* tag = "FAMILY") : tag_(tag) {}
    void reset() { clips_.clear(); base_.clear(); owner_ = nullptr; ok_ = true; }
    bool ready() const { return ok_ && owner_ && !clips_.empty(); }
    const char* tag() const { return tag_; }
    // Adopt vectors already decoded (and topology-checked across clips) by
    // p2poseload::loadStem. `basePath` is the gameflow path of this clip's
    // pose 0; the first adopted clip supplies the private-geometry base.
    bool adopt(const std::string& name, std::vector<p2pose::Baked>&& baked, int duration,
               const std::vector<int>& explicitFrames, const std::string& basePath, Shape* owner) {
        if (!ok_) return false;
        const int count = int(baked.size());
        if (count < 1 || count > 64 || !owner) return disable(name, "count");
        Clip clip;
        clip.duration = duration < 2 ? (count >= 2 ? count : 2) : duration;
        clip.frames = validFrames(explicitFrames, count, clip.duration)
            ? explicitFrames : p2batch2clock::uniformFrames(count, clip.duration);
        for (auto& pose : baked) clip.poses.push_back(std::move(pose.pose));
        auto poseAt = [&clip](std::size_t i) -> const p2pose::Pose& { return clip.poses[i]; };
        clip.seamContinuous = p2motion::seamContinuous(clip.poses.size(), poseAt, clip.frames);
        clip.holdFrame = float(clip.frames[p2motion::visibleEnd(clip.poses.size(), poseAt)]);
        if (base_.empty()) base_ = basePath;
        if (!owner_) owner_ = owner;
        clips_[name] = std::move(clip);
        return true;
    }
    const Clip* clip(const std::string& name) const {
        auto it = clips_.find(name);
        return ok_ && it != clips_.end() ? &it->second : nullptr;
    }
    Shape* owner() const { return owner_; }
    const std::string& basePath() const { return base_; }
    const p2pose::Pose* basePose() const {
        for (const auto& entry : clips_)
            if (!entry.second.poses.empty()) return &entry.second.poses.front();
        return nullptr;
    }
    std::size_t clipCount() const { return clips_.size(); }

    // Explicit frames are usable when they match the pose count and the
    // P2_BANK_FRAMES_1 contract (0 first, duration-1 last, strictly rising).
    static bool validFrames(const std::vector<int>& frames, int count, int duration) {
        if (int(frames.size()) != count || count < 1 || frames.front() != 0 || frames.back() != duration - 1)
            return false;
        for (std::size_t i = 1; i < frames.size(); ++i)
            if (frames[i] <= frames[i - 1]) return false;
        return true;
    }

private:
    bool disable(const std::string& clip, const char* why) {
        ok_ = false;
        std::printf("P2_%s_INTERPOLATION_DISABLED clip=%s reason=%s fallback=nearest\n", tag_, clip.c_str(), why);
        return false;
    }
    const char* tag_;
    std::map<std::string, Clip> clips_;
    std::string base_;
    Shape* owner_ = nullptr;
    bool ok_ = true;
};

// Load one family clip (`<stem>_00.mod`..) through the compact loader and
// adopt its vectors into `bank`. `shapes` receives one Shape per pose index
// (aliased to the nearest loaded slot). Returns false with `error` on a hard
// failure (missing/mismatched files, budget); the caller keeps its own
// fail-closed policy.
inline bool loadFamilyClip(Bank& bank, const std::string& name, const std::string& stem, int count, int duration,
                           const std::vector<int>& frames, p2poseload::Shared& shared, std::size_t& total,
                           std::vector<Shape*>& shapes, std::string& error,
                           const p2poseload::Limits& limits = p2poseload::defaultLimits()) {
    p2poseload::Clip loaded;
    if (!p2poseload::loadStem(stem, count, limits, shared, total, loaded, error)) return false;
    shapes = loaded.shapes;
    if (loaded.vectors)
        bank.adopt(name, std::move(loaded.baked), duration, frames, p2poseload::stemPath(false, stem, 0),
                   shared.owner);
    return true;
}

class Actors;
inline std::set<Actors*>& registry() {
    static std::set<Actors*> all;
    return all;
}

// Per-actor private geometry for one family.
class Actors {
public:
    Actors() { registry().insert(this); }
    ~Actors() { registry().erase(this); }
    Actors(const Actors&) = delete;
    Actors& operator=(const Actors&) = delete;
    // A reset or a forgotten actor clears its private-Shape failure too, so a
    // recycled actor address never inherits "interpolation disabled".
    void clear() { tracks_.clear(); failed_.clear(); }
    void forget(const void* actor) { tracks_.erase(actor); failed_.erase(actor); }
    bool failed(const void* actor) const { return failed_.count(actor) != 0; }
    void advance(const void* actor, float seconds) {
        auto it = tracks_.find(actor);
        if (it != tracks_.end()) it->second.advance(seconds);
    }
    // Returns the private Shape showing `clip` at `sourceFrame` (lerp +
    // crossfade), or nullptr when the caller should keep its nearest pose.
    Shape* draw(const void* actor, const Bank& bank, const std::string& clip, float sourceFrame,
                unsigned token = 0) {
        const Clip* entry = bank.clip(clip);
        if (!actor || !entry || !bank.ready()) return nullptr;
        auto it = tracks_.find(actor);
        if (it == tracks_.end()) {
            const p2pose::Pose* base = bank.basePose();
            if (!base || failed_.count(actor)) return nullptr;
            const int previousHeap = gsys->setHeap(SYSHEAP_App);
            Shape* model = p2pose::privateShape(bank.basePath().c_str(), *bank.owner(), *base);
            gsys->setHeap(previousHeap);
            if (!model) {
                failed_.insert(actor);
                std::printf("P2_%s_INTERPOLATION_DISABLED token=%u reason=private_shape fallback=nearest\n",
                            bank.tag(), token);
                return nullptr;
            }
            p2pose::Track track;
            track.shape = model;
            track.size(*base);
            it = tracks_.emplace(actor, std::move(track)).first;
            const p2motion::Tunables& tune = p2motion::tunables();
            std::printf("P2_%s_INTERPOLATION_READY token=%u positions=%d normals=%d lerp=%d crossfade_ms=%d "
                        "private_geometry=1 gameplay_clock=P1\n",
                        bank.tag(), token, model->mVertexCount, model->mNormalCount, int(tune.lerp),
                        int(tune.crossfadeSeconds * 1000.f + .5f));
        }
        const p2motion::Tunables& tune = p2motion::tunables();
        const auto& poses = entry->poses;
        // A death clip stops at its last visible pose (see p2motion::isDeathClip).
        if (p2motion::isDeathClip(clip) && sourceFrame > entry->holdFrame) sourceFrame = entry->holdFrame;
        const p2pose::Presented shown = p2pose::present(
            it->second, clip, poses.size(), [&poses](std::size_t i) -> const p2pose::Pose& { return poses[i]; },
            entry->frames, sourceFrame, tune, entry->seamContinuous);
        if (!shown.ok) return nullptr;
        if ((shown.crossfadeStarted || shown.wrapBlend) && crossfadeLogs_ < 32u) {
            ++crossfadeLogs_;
            std::printf("P2_%s_CROSSFADE token=%u clip=%s ms=%d cause=%s\n", bank.tag(), token, clip.c_str(),
                        int(tune.crossfadeSeconds * 1000.f + .5f), shown.wrapBlend ? "loop_seam" : "clip_change");
        }
        if (blendLogged_.insert(clip).second) {
            std::printf("P2_%s_BLEND clip=%s poses=%zu left=%zu right=%zu weight=%.5f lerp=%d seam=%s\n", bank.tag(),
                        clip.c_str(), poses.size(), shown.span.left, shown.span.right, shown.span.weight,
                        int(tune.lerp), entry->seamContinuous ? "continuous" : "blend");
        }
        return it->second.shape;
    }

private:
    std::map<const void*, p2pose::Track> tracks_;
    std::set<const void*> failed_;
    std::set<std::string> blendLogged_;
    unsigned crossfadeLogs_ = 0;
};

}  // namespace p2posefamily

// Advance every family's crossfade clock for one actor (BTeki::update).
inline void pc_p2_pose_family_tick(const BTeki* actor, float seconds) {
    for (p2posefamily::Actors* actors : p2posefamily::registry()) actors->advance(actor, seconds);
}
