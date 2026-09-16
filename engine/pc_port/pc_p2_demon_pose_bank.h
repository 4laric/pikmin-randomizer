#pragma once
#include <array>
#include <cmath>
#include <fstream>
#include <string>
#include <vector>

struct P2DemonMouthFrame { int frame; std::string model; std::array<float, 24> values; };
// Sampled poses only: no interpolation or retail event scheduling is implied.
class P2DemonPoseBank {
    std::vector<P2DemonMouthFrame> frames;
public:
    bool load(const char* path) {
        if (!path) return false;
        std::ifstream in(path);
        std::string magic, digest;
        int count;
        if (!(in >> magic >> digest >> count) || (magic != "P2_DEMON_MOUTHS_1" && magic != "P2_DEMON_POSES_2")
            || digest.size() != 64 || digest.find_first_not_of("0123456789abcdef") != std::string::npos
            || count < 1 || count > 128) return false;
        std::vector<P2DemonMouthFrame> parsed;
        int previous = -1;
        for (int i = 0; i < count; ++i) {
            P2DemonMouthFrame pose{};
            if (!(in >> pose.frame) || pose.frame <= previous || pose.frame > 100000) return false;
            previous = pose.frame;
            if (magic == "P2_DEMON_POSES_2") {
                if (!(in >> pose.model) || pose.model.size() < 5 || pose.model.size() > 96
                    || pose.model.substr(pose.model.size()-4) != ".mod"
                    || pose.model.substr(0,pose.model.size()-4).find_first_not_of(
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_") != std::string::npos) return false;
            }
            for (float& x : pose.values)
                if (!(in >> x) || !std::isfinite(x) || std::fabs(x) > 1e6f) return false;
            parsed.push_back(pose);
        }
        std::string extra;
        if (in >> extra) return false;
        frames.swap(parsed); // Failed reload leaves the accepted bank unchanged.
        return true;
    }
    const std::vector<P2DemonMouthFrame>& samples() const { return frames; }
    const P2DemonMouthFrame* exact(int frame) const {
        for (const auto& pose : frames) if (pose.frame == frame) return &pose;
        return nullptr;
    }
};
