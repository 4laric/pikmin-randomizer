#pragma once
// Jellyfloat (Kurage 57 / OniKurage 72) pose-bank profile (#972). Engine-free.
//
// `p2-kurage-animation.txt` / `p2-onikurage-animation.txt` (root
// experimental/pikmin2_kurage_bank.py) list, per converted source clip, the
// baked pose frames and the world translation of the source `suck` part (the
// Proom joint) in each pose:
//
//   P2_KURAGE_ANIMATION_1
//   <clip> <count> <duration> <frame>*count <x y z>*count
//
// The pose meshes themselves are `<prefix><clip>_<NN>.mod` and load through the
// shared p2posefamily::loadFamilyClip. The Proom rows let the host hold a
// swallowed Pikmin or captain at the joint of the pose that is on screen
// instead of at one tabulated frame per clip.
#include <array>
#include <cmath>
#include <istream>
#include <string>
#include <vector>

namespace p2kuragebank {

struct Clip {
    std::string name;
    int duration = 1;
    std::vector<int> frames;
    std::vector<std::array<float, 3>> proom;
};

struct Profile {
    std::vector<Clip> clips;
    const Clip* find(const std::string& name) const {
        for (const Clip& clip : clips)
            if (clip.name == name) return &clip;
        return nullptr;
    }
};

// Strict parse: anything malformed rejects the whole profile (the caller then
// keeps the static per-clip meshes).
inline bool parse(std::istream& in, Profile& out) {
    out = Profile();
    std::string word;
    if (!(in >> word) || word != "P2_KURAGE_ANIMATION_1") return false;
    Profile parsed;
    while (in >> word) {
        Clip clip;
        clip.name = word;
        int count = 0;
        if (clip.name.empty() || clip.name.size() > 32 || parsed.find(clip.name) || parsed.clips.size() >= 16) return false;
        for (char c : clip.name)
            if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9'))) return false;
        if (!(in >> count >> clip.duration) || count < 2 || count > 64 || clip.duration < 2 || clip.duration > 10000)
            return false;
        for (int i = 0; i < count; ++i) {
            int frame = 0;
            if (!(in >> frame) || frame < 0 || frame >= clip.duration || (i && frame <= clip.frames.back())) return false;
            clip.frames.push_back(frame);
        }
        if (clip.frames.front() != 0 || clip.frames.back() != clip.duration - 1) return false;
        for (int i = 0; i < count; ++i) {
            std::array<float, 3> v{};
            if (!(in >> v[0] >> v[1] >> v[2]) || !std::isfinite(v[0]) || !std::isfinite(v[1]) || !std::isfinite(v[2]))
                return false;
            clip.proom.push_back(v);
        }
        parsed.clips.push_back(std::move(clip));
    }
    if (parsed.clips.empty()) return false;
    out = std::move(parsed);
    return true;
}

// Proom joint translation at a source frame: linear between the bracketing
// poses, clamped to the clip. Matches the pose lerp the bank draws with.
inline std::array<float, 3> proomAt(const Clip& clip, float frame) {
    const std::size_t n = clip.frames.size();
    if (!(frame > float(clip.frames.front()))) return clip.proom.front();
    if (!(frame < float(clip.frames.back()))) return clip.proom.back();
    std::size_t right = 1;
    while (right + 1 < n && float(clip.frames[right]) <= frame) ++right;
    const std::size_t left = right - 1;
    const float span = float(clip.frames[right] - clip.frames[left]);
    const float w = (frame - float(clip.frames[left])) / span;
    std::array<float, 3> out{};
    for (int i = 0; i < 3; ++i) out[i] = clip.proom[left][i] + (clip.proom[right][i] - clip.proom[left][i]) * w;
    return out;
}

// Corpse pose (#1065). Source Kurage/OniKurage leave no carcass
// (Kurage.cpp:36 / OniKurage.cpp:46 disable EB_LeaveCarcass): the death clip
// (dead1 airborne, dead2 grounded; OniKurageState.cpp:46-50) drops the bell,
// squashes it flat on the ground (source frames ~37-45), then swells and
// thrashes until the burst at key 93 (deathProcedure + body bomb effect,
// OniKurageState.cpp:80-88; enemyanimmgr "93 3") and the kill at the clip end
// (:90-91). By frame 95 every joint is scaled to nothing. The port keeps a
// P1-style carried carcass, so it needs a resting pose: the settled pose is the
// flattest visible pose of the death clip (smallest vertical extent, ignoring
// poses collapsed to a point), lifted so its lowest vertex rests on the ground.
struct Extent { float minY = 0.f, maxY = 0.f, width = 0.f; };

// Index of the settled pose, or -1 when no pose is visible. A pose is visible
// when its width and height exceed `collapsed` model units.
inline int settledIndex(const std::vector<Extent>& poses, float collapsed = 1.0f) {
    int best = -1;
    for (std::size_t i = 0; i < poses.size(); ++i) {
        const float height = poses[i].maxY - poses[i].minY;
        if (!(height > collapsed) || !(poses[i].width > collapsed)) continue;
        if (best < 0 || height < poses[std::size_t(best)].maxY - poses[std::size_t(best)].minY) best = int(i);
    }
    return best;
}

// Model-space vertical offset that puts a pose's lowest vertex at y = 0.
inline float groundLift(const Extent& pose) { return std::isfinite(pose.minY) ? -pose.minY : 0.f; }

}  // namespace p2kuragebank
