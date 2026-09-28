#pragma once
// Compact pose-bank clip loader shared by batch2/batch3 (#895).
//
// Dense banks (12..64 poses per clip) would multiply scene-heap use if every
// pose became a full Shape. Instead each clip keeps at most
// p2motion::Tunables::fallbackShapes evenly spread poses as Shapes (pose 0 is
// always one: it is the material/texture owner and the private-geometry base)
// and decodes positions+normals for every pose. Draw paths render through a
// per-actor private Shape (p2pose::Track); the Shape slots only serve when the
// private geometry cannot be created or a clip does not decode, in which case
// every pose index aliases its nearest loaded slot.
//
// Budgets are resident bytes, not on-disk bytes: a Shape slot costs its file
// size, a decoded pose costs its vector payload (topology is compared, then
// dropped for every pose but the clip's first).
#include "pc_p2_animation.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_motion.h"
#include "Shape.h"
#include "Texture.h"
#include "Material.h"
#include "gameflow.h"

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

namespace p2poseload {

struct Limits {
    std::size_t fileBytes;   // one pose file (decodeBaked cap)
    std::size_t clipBytes;   // resident per clip
    std::size_t totalBytes;  // resident per setup
};

struct Clip {
    std::vector<Shape*> shapes;           // one per pose index (slots aliased)
    std::vector<p2pose::Baked> baked;     // one per pose when `vectors`
    std::vector<std::size_t> slots;       // pose indices loaded as Shapes
    std::size_t resident = 0;
    bool vectors = false;
};

struct Shared {
    std::vector<unsigned char> reference;  // render resources (tags 32/34/48)
    std::vector<unsigned char> topology;   // first decoded topology
    Shape* owner = nullptr;                // material/texture owner
};

inline void posePath(char* out, std::size_t size, bool assets, const std::string& prefix,
                     const std::string& species, const std::string& clip, int index) {
    std::snprintf(out, size, "%scourses/pikmin2room/%s_%s_%s_%02d.mod", assets ? "assets/dataDir/" : "",
                  prefix.c_str(), species.c_str(), clip.c_str(), index);
}

// Resident estimate without decoding: full size for Shape slots, 12 bytes per
// position/normal (tags 16/17 counts) for the rest. Returns false on a missing
// or unreadable file (the loader reports it).
inline bool estimate(const std::string& prefix, const std::string& species, const std::string& clip,
                     int poseCount, std::size_t& clipOut) {
    clipOut = 0;
    const auto slots = p2motion::shapeSlots(std::size_t(poseCount), std::size_t(p2motion::tunables().fallbackShapes));
    for (int i = 0; i < poseCount; ++i) {
        char rel[224];
        posePath(rel, sizeof(rel), true, prefix, species, clip, i);
        std::ifstream file(rel, std::ios::binary | std::ios::ate);
        if (!file) return false;
        const auto size = file.tellg();
        if (size <= 0) return false;
        if (p2motion::isSlot(slots, std::size_t(i))) { clipOut += std::size_t(size); continue; }
        std::size_t at = 0, vectors = 0;
        while (at + 12 <= std::size_t(size)) {
            unsigned char head[12];
            file.seekg(std::streamoff(at));
            if (!file.read(reinterpret_cast<char*>(head), 12)) break;
            auto be = [&head](int at) {
                return std::uint32_t(head[at]) << 24 | std::uint32_t(head[at + 1]) << 16
                    | std::uint32_t(head[at + 2]) << 8 | head[at + 3];
            };
            const std::uint32_t tag = be(0), bytes = be(4);
            if (tag == 16 || tag == 17) vectors += be(8);
            if (tag == 65535) break;
            at += 8 + std::size_t(bytes);
        }
        clipOut += vectors * sizeof(p2pose::Vec);
    }
    return true;
}

// Loads one clip. On failure returns false with `error` set; nothing already
// counted in `total` is rolled back (callers restore their own snapshot).
inline bool loadClip(const std::string& prefix, const std::string& species, const std::string& clip,
                     int poseCount, const Limits& limits, Shared& shared, std::size_t& total, Clip& out,
                     std::string& error) {
    out = Clip();
    if (poseCount == 0) return true;  // unconverted clip: no poses, never drawn
    if (poseCount < 0 || poseCount > 64) { error = "invalid pose count"; return false; }
    out.slots = p2motion::shapeSlots(std::size_t(poseCount), std::size_t(p2motion::tunables().fallbackShapes));
    std::vector<Shape*> loaded(std::size_t(poseCount), nullptr);
    bool vectors = true;
    std::vector<unsigned char> clipTopology;
    for (int i = 0; i < poseCount; ++i) {
        char rel[224];
        posePath(rel, sizeof(rel), true, prefix, species, clip, i);
        std::ifstream file(rel, std::ios::binary | std::ios::ate);
        if (!file) { error = "missing pose bank"; return false; }
        const auto size = file.tellg();
        if (size <= 0 || std::size_t(size) > limits.fileBytes) { error = "pose bank exceeds budget"; return false; }
        file.seekg(0);
        std::vector<unsigned char> data(std::size_t(size), 0), resources;
        if (!file.read(reinterpret_cast<char*>(data.data()), size) || !p2animation::resources(data, resources)) {
            error = "invalid pose resources";
            return false;
        }
        if (!shared.reference.empty() && shared.reference != resources) { error = "pose resources differ"; return false; }
        shared.reference = resources;
        const bool slot = p2motion::isSlot(out.slots, std::size_t(i));
        if (vectors) {
            p2pose::Baked baked;
            if (!p2pose::decodeBaked(data, baked)
                    || (!out.baked.empty() && (baked.pose.positions.size() != out.baked.front().pose.positions.size()
                                               || baked.pose.normals.size() != out.baked.front().pose.normals.size()))
                    || (!clipTopology.empty() && baked.topology != clipTopology)
                    || (clipTopology.empty() && !shared.topology.empty() && baked.topology != shared.topology)) {
                vectors = false;
                for (const auto& earlier : out.baked) out.resident -= p2motion::poseBytes(earlier.pose);
                out.baked.clear();
            } else {
                if (clipTopology.empty()) clipTopology = baked.topology;
                std::vector<unsigned char>().swap(baked.topology);
                out.resident += p2motion::poseBytes(baked.pose);
                out.baked.push_back(std::move(baked));
            }
        }
        if (slot) out.resident += std::size_t(size);
        if (out.resident > limits.clipBytes || total + out.resident > limits.totalBytes) {
            error = "pose bank exceeds budget";
            return false;
        }
        if (!slot) continue;
        char load[200];
        posePath(load, sizeof(load), false, prefix, species, clip, i);
        Shape* shape = gameflow.loadShape(load, true);
        if (!shape) { error = "pose load failed"; return false; }
        if (!shared.owner) {
            shared.owner = shape;
            for (int t = 0; t < shape->mTexAttrCount; ++t)
                if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
        } else {
            if (shape->mMaterialCount != shared.owner->mMaterialCount
                    || shape->mTexAttrCount != shared.owner->mTexAttrCount
                    || shape->mTevInfoCount != shared.owner->mTevInfoCount) {
                error = "material framing mismatch";
                return false;
            }
            for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
                auto* poly = shape->mMatpolyList[j];
                if (!poly || !poly->mMaterial) continue;
                int material = -1;
                for (int m = 0; m < shape->mMaterialCount; ++m)
                    if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
                if (material < 0) { error = "pose material not found"; return false; }
                poly->mMaterial = &shared.owner->mMaterialList[material];
            }
            shape->mMaterialList = shared.owner->mMaterialList;
            shape->mTexAttrList = shared.owner->mTexAttrList;
            shape->mTevInfoList = shared.owner->mTevInfoList;
        }
        loaded[std::size_t(i)] = shape;
    }
    out.vectors = vectors && out.baked.size() == std::size_t(poseCount);
    if (out.vectors && shared.topology.empty()) shared.topology = clipTopology;
    if (!out.vectors) out.baked.clear();
    out.shapes.resize(std::size_t(poseCount));
    for (std::size_t i = 0; i < out.shapes.size(); ++i) out.shapes[i] = loaded[p2motion::nearestSlot(out.slots, i)];
    total += out.resident;
    return true;
}

}  // namespace p2poseload
