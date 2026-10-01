#pragma once
// Compact pose-bank clip loader shared by every P2 pose-bank draw path (#895):
// batch2/batch3, Chappy and the dedicated families (Frog, Tank, Kabuto,
// Sheargrub, Dwarf Orange, Mamuta).
//
// Dense banks (12..64 poses per clip) would multiply scene-heap use if every
// pose became a full Shape. Instead each clip keeps at most
// p2motion::Tunables::fallbackShapes evenly spread poses as Shapes (pose 0 is
// always one: it is the material/texture owner and the private-geometry base)
// and decodes positions+normals for every pose. Draw paths render through a
// per-actor private Shape (p2pose::Track); the Shape slots only serve when the
// private geometry cannot be created.
//
// A clip whose vectors do not decode (a legacy or malformed bank) loads EVERY
// pose as a Shape instead, so it keeps its full density on the nearest-pose
// path; that fallback is reported by P2_POSE_LOADER_FALLBACK, never silent.
//
// Loading is transactional per clip: every pose file is read, resource-checked
// and decoded before the first Shape is created, so a rejected clip leaves no
// Shapes behind and never becomes the material owner. A failure after Shapes
// exist (gameflow load or material framing) restores the shared owner,
// reference and topology to their state before the clip.
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

// Resident budgets shared by every pose-bank loader (#895). The owner
// approved 1 MiB resident per clip (was 512 KiB) and 48 MiB per setup.
// PoseFileBytes is the p2pose::decodeBaked cap.
constexpr std::size_t PoseFileBytes = 1024 * 1024;
constexpr std::size_t ClipBytes = 1024 * 1024;
constexpr std::size_t TotalBytes = 48 * 1024 * 1024;

struct Limits {
    std::size_t fileBytes;   // one pose file (decodeBaked cap)
    std::size_t clipBytes;   // resident per clip
    std::size_t totalBytes;  // resident per setup
};

inline Limits defaultLimits() { return Limits{PoseFileBytes, ClipBytes, TotalBytes}; }

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

// Gameflow path of pose `index` for a bank stem ("frog_Frog_wait1" ->
// "courses/pikmin2room/frog_Frog_wait1_03.mod"); `assets` prefixes the
// on-disk "assets/dataDir/" root.
inline std::string stemPath(bool assets, const std::string& stem, int index) {
    char suffix[16];
    std::snprintf(suffix, sizeof(suffix), "_%02d.mod", index);
    return std::string(assets ? "assets/dataDir/" : "") + "courses/pikmin2room/" + stem + suffix;
}

inline std::string bankStem(const std::string& prefix, const std::string& species, const std::string& clip) {
    return prefix + "_" + species + "_" + clip;
}

inline void posePath(char* out, std::size_t size, bool assets, const std::string& prefix,
                     const std::string& species, const std::string& clip, int index) {
    std::snprintf(out, size, "%s", stemPath(assets, bankStem(prefix, species, clip), index).c_str());
}

// Resident estimate without decoding: full size for Shape slots, 12 bytes per
// position/normal (tags 16/17 counts) for the rest. Returns false on a missing
// or unreadable file (the loader reports it).
inline bool estimateStem(const std::string& stem, int poseCount, std::size_t& clipOut) {
    clipOut = 0;
    const auto slots = p2motion::shapeSlots(std::size_t(poseCount), std::size_t(p2motion::tunables().fallbackShapes));
    for (int i = 0; i < poseCount; ++i) {
        std::ifstream file(stemPath(true, stem, i), std::ios::binary | std::ios::ate);
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

inline bool estimate(const std::string& prefix, const std::string& species, const std::string& clip,
                     int poseCount, std::size_t& clipOut) {
    return estimateStem(bankStem(prefix, species, clip), poseCount, clipOut);
}

// Loads one clip from `<stem>_00.mod`..`<stem>_NN.mod`. On failure returns
// false with `error` set, `total` untouched and `shared` restored.
inline bool loadStem(const std::string& stem, int poseCount, const Limits& limits, Shared& shared,
                     std::size_t& total, Clip& out, std::string& error) {
    out = Clip();
    if (poseCount == 0) return true;  // unconverted clip: no poses, never drawn
    if (poseCount < 0 || poseCount > 64) { error = "invalid pose count"; return false; }
    const Shared before = shared;
    auto rollback = [&](const char* why) {
        shared = before;
        out = Clip();
        error = why;
        return false;
    };
    // Pass 1: read, resource-check and decode every pose; no Shapes yet.
    std::vector<std::size_t> sizes(std::size_t(poseCount), 0);
    std::vector<p2pose::Baked> baked;
    bool vectors = true;
    std::vector<unsigned char> clipTopology, reference = shared.reference;
    for (int i = 0; i < poseCount; ++i) {
        std::ifstream file(stemPath(true, stem, i), std::ios::binary | std::ios::ate);
        if (!file) return rollback("missing pose bank");
        const auto size = file.tellg();
        if (size <= 0 || std::size_t(size) > limits.fileBytes) return rollback("pose bank exceeds budget");
        sizes[std::size_t(i)] = std::size_t(size);
        file.seekg(0);
        std::vector<unsigned char> data(std::size_t(size), 0), resources;
        if (!file.read(reinterpret_cast<char*>(data.data()), size) || !p2animation::resources(data, resources))
            return rollback("invalid pose resources");
        if (!reference.empty() && reference != resources) return rollback("pose resources differ");
        reference = resources;
        if (!vectors) continue;
        p2pose::Baked pose;
        if (!p2pose::decodeBaked(data, pose)
                || (!baked.empty() && (pose.pose.positions.size() != baked.front().pose.positions.size()
                                       || pose.pose.normals.size() != baked.front().pose.normals.size()))
                || (!clipTopology.empty() && pose.topology != clipTopology)
                || (clipTopology.empty() && !shared.topology.empty() && pose.topology != shared.topology)) {
            vectors = false;
            baked.clear();
            continue;
        }
        if (clipTopology.empty()) clipTopology = pose.topology;
        std::vector<unsigned char>().swap(pose.topology);
        baked.push_back(std::move(pose));
    }
    // Slots: a few spread Shapes when every pose decoded. Otherwise as many
    // Shapes as the resident budget allows (every pose when it fits), spread
    // evenly, and the reduction is reported rather than silent.
    out.vectors = vectors && baked.size() == std::size_t(poseCount);
    auto residentOf = [&](const std::vector<std::size_t>& slots) {
        std::size_t bytes = 0;
        for (std::size_t i = 0; i < sizes.size(); ++i) {
            if (p2motion::isSlot(slots, i)) bytes += sizes[i];
            else if (out.vectors) bytes += p2motion::poseBytes(baked[i].pose);
        }
        return bytes;
    };
    auto fits = [&](std::size_t bytes) { return bytes <= limits.clipBytes && total + bytes <= limits.totalBytes; };
    if (out.vectors) {
        out.slots = p2motion::shapeSlots(std::size_t(poseCount), std::size_t(p2motion::tunables().fallbackShapes));
        out.resident = residentOf(out.slots);
    } else {
        for (std::size_t n = std::size_t(poseCount); n >= 1; --n) {
            out.slots = p2motion::shapeSlots(std::size_t(poseCount), n);
            out.resident = residentOf(out.slots);
            if (fits(out.resident)) break;
        }
    }
    if (!fits(out.resident)) return rollback("pose bank exceeds budget");
    if (!out.vectors) {
        std::printf("P2_POSE_LOADER_FALLBACK stem=%s poses=%d reason=vectors_undecodable shapes=%zu\n", stem.c_str(),
                    poseCount, out.slots.size());
    }
    // Pass 2: Shapes for the slots only.
    shared.reference = reference;
    std::vector<Shape*> loaded(std::size_t(poseCount), nullptr);
    for (std::size_t i : out.slots) {
        Shape* shape = gameflow.loadShape(stemPath(false, stem, int(i)).c_str(), true);
        if (!shape) return rollback("pose load failed");
        if (!shared.owner) {
            shared.owner = shape;
            for (int t = 0; t < shape->mTexAttrCount; ++t)
                if (shape->mTexAttrList[t].mTexture) shape->mTexAttrList[t].mTexture->attach();
        } else {
            if (shape->mMaterialCount != shared.owner->mMaterialCount
                    || shape->mTexAttrCount != shared.owner->mTexAttrCount
                    || shape->mTevInfoCount != shared.owner->mTevInfoCount)
                return rollback("material framing mismatch");
            for (int j = 0; j < shape->mTotalMatpolyCount; ++j) {
                auto* poly = shape->mMatpolyList[j];
                if (!poly || !poly->mMaterial) continue;
                int material = -1;
                for (int m = 0; m < shape->mMaterialCount; ++m)
                    if (poly->mMaterial == &shape->mMaterialList[m]) material = m;
                if (material < 0) return rollback("pose material not found");
                poly->mMaterial = &shared.owner->mMaterialList[material];
            }
            shape->mMaterialList = shared.owner->mMaterialList;
            shape->mTexAttrList = shared.owner->mTexAttrList;
            shape->mTevInfoList = shared.owner->mTevInfoList;
        }
        loaded[i] = shape;
    }
    if (out.vectors) {
        if (shared.topology.empty()) shared.topology = clipTopology;
        out.baked = std::move(baked);
    }
    out.shapes.resize(std::size_t(poseCount));
    for (std::size_t i = 0; i < out.shapes.size(); ++i) out.shapes[i] = loaded[p2motion::nearestSlot(out.slots, i)];
    total += out.resident;
    return true;
}

inline bool loadClip(const std::string& prefix, const std::string& species, const std::string& clip,
                     int poseCount, const Limits& limits, Shared& shared, std::size_t& total, Clip& out,
                     std::string& error) {
    return loadStem(bankStem(prefix, species, clip), poseCount, limits, shared, total, out, error);
}

// Seam continuity of a loaded clip (see p2motion::seamContinuous).
inline bool seamOf(const std::vector<p2pose::Baked>& baked, const std::vector<int>& frames) {
    return p2motion::seamContinuous(
        baked.size(), [&baked](std::size_t i) -> const p2pose::Pose& { return baked[i].pose; }, frames);
}

}  // namespace p2poseload
