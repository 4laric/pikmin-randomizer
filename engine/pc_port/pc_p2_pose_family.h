#pragma once
// Interpolated presentation for dedicated P2 family draw paths (#895).
//
// Frog, Tank, Kabuto, Sheargrub, Chappy and similar modules load their pose
// banks as one Shape per pose and used to draw the single nearest pose. This
// helper decodes the same files' positions/normals once (p2pose::decodeBaked)
// and, per actor, writes the lerped pose into a private Shape with a crossfade
// on clip change (p2pose::present). Any decode/topology failure disables the
// helper for that bank and the module keeps its nearest-pose Shape draw, so
// adoption is fail-soft. Fade time advances through pc_p2_pose_family_tick,
// called from BTeki::update.
#include "pc_p2_batch2_clock.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_motion.h"
#include "pc_p2_pose_shape.h"
#include "Shape.h"
#include "system.h"

#include <cstdio>
#include <fstream>
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
};

class Bank {
public:
    // `tag` names the family in log markers (e.g. "FROG").
    explicit Bank(const char* tag = "FAMILY") : tag_(tag) {}
    void reset() { clips_.clear(); topology_.clear(); base_.clear(); owner_ = nullptr; ok_ = true; }
    bool ready() const { return ok_ && owner_ && !clips_.empty(); }
    const char* tag() const { return tag_; }
    // `load` is the gameflow path of pose i (without the assets/dataDir/ prefix).
    // `owner` is an already loaded Shape of this bank whose materials every
    // pose shares. Returns false (and disables the bank) on any mismatch.
    template <class PathOf>
    bool addClip(const std::string& name, int count, int duration, const std::vector<int>& explicitFrames,
                 PathOf loadPath, Shape* owner) {
        if (!ok_) return false;
        if (count < 1 || count > 64 || !owner) return disable(name, "count");
        Clip clip;
        clip.duration = duration < 2 ? (count >= 2 ? count : 2) : duration;
        clip.frames = int(explicitFrames.size()) == count ? explicitFrames
                                                          : p2batch2clock::uniformFrames(count, clip.duration);
        for (int i = 0; i < count; ++i) {
            const std::string rel = "assets/dataDir/" + loadPath(i);
            std::ifstream file(rel, std::ios::binary | std::ios::ate);
            if (!file) return disable(name, "missing");
            const auto size = file.tellg();
            if (size <= 0 || size > 1024 * 1024) return disable(name, "size");
            file.seekg(0);
            std::vector<unsigned char> raw(std::size_t(size), 0);
            if (!file.read(reinterpret_cast<char*>(raw.data()), size)) return disable(name, "read");
            p2pose::Baked baked;
            if (!p2pose::decodeBaked(raw, baked)) return disable(name, "decode");
            if (topology_.empty()) {
                topology_ = baked.topology;
                base_ = loadPath(i);
            } else if (baked.topology != topology_) {
                return disable(name, "topology");
            }
            clip.poses.push_back(std::move(baked.pose));
        }
        if (!owner_) owner_ = owner;
        clips_[name] = std::move(clip);
        return true;
    }
    // Adopt vectors already decoded (and topology-checked across clips) by
    // p2poseload::loadClip. `basePath` is the gameflow path of this clip's
    // pose 0; the first adopted clip supplies the private-geometry base.
    bool adopt(const std::string& name, std::vector<p2pose::Baked>&& baked, int duration,
               const std::vector<int>& explicitFrames, const std::string& basePath, Shape* owner) {
        if (!ok_) return false;
        const int count = int(baked.size());
        if (count < 1 || count > 64 || !owner) return disable(name, "count");
        Clip clip;
        clip.duration = duration < 2 ? (count >= 2 ? count : 2) : duration;
        clip.frames = int(explicitFrames.size()) == count ? explicitFrames
                                                          : p2batch2clock::uniformFrames(count, clip.duration);
        for (auto& pose : baked) clip.poses.push_back(std::move(pose.pose));
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

private:
    bool disable(const std::string& clip, const char* why) {
        ok_ = false;
        std::printf("P2_%s_INTERPOLATION_DISABLED clip=%s reason=%s fallback=nearest\n", tag_, clip.c_str(), why);
        return false;
    }
    const char* tag_;
    std::map<std::string, Clip> clips_;
    std::vector<unsigned char> topology_;
    std::string base_;
    Shape* owner_ = nullptr;
    bool ok_ = true;
};

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
    void clear() { tracks_.clear(); }
    void forget(const void* actor) { tracks_.erase(actor); }
    void advance(const void* actor, float seconds) {
        auto it = tracks_.find(actor);
        if (it != tracks_.end()) it->second.fade.advance(seconds);
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
        const p2pose::Presented shown = p2pose::present(
            it->second, clip, poses.size(), [&poses](std::size_t i) -> const p2pose::Pose& { return poses[i]; },
            entry->frames, sourceFrame, tune);
        if (!shown.ok) return nullptr;
        if (shown.crossfadeStarted && crossfadeLogs_ < 32u) {
            ++crossfadeLogs_;
            std::printf("P2_%s_CROSSFADE token=%u clip=%s ms=%d\n", bank.tag(), token, clip.c_str(),
                        int(tune.crossfadeSeconds * 1000.f + .5f));
        }
        if (blendLogged_.insert(clip).second) {
            std::printf("P2_%s_BLEND clip=%s poses=%zu left=%zu right=%zu weight=%.5f lerp=%d\n", bank.tag(),
                        clip.c_str(), poses.size(), shown.span.left, shown.span.right, shown.span.weight,
                        int(tune.lerp));
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
