#include "pc_p2_waterwraith_visual.h"

#include "Camera.h"
#include "Graphics.h"
#include "Matrix4f.h"
#include "Shape.h"
#include "Texture.h"
#include "gameflow.h"
#include "sysNew.h"
#include "system.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {
constexpr int kMaxSpecies = 4;
constexpr int kMaxClips = 48;
constexpr int kMaxPoses = 8;
constexpr std::streamoff kProfileBytes = 16384;

struct SpeciesBank {
    std::string name;
    int enemyId = 0;
};

struct ClipBank {
    std::string species;
    std::string name;
    int duration = 0;
    int poseCount = 0;
    int frames[kMaxPoses] = {};
    Shape* poses[kMaxPoses] = {};
};

struct ActiveClip {
    int clip = -1;
    float frame = 0.0f;
    bool looping = false;
};

struct VisualState {
    bool ready = false;
    SpeciesBank species[kMaxSpecies];
    int speciesCount = 0;
    ClipBank clips[kMaxClips];
    int clipCount = 0;
    ActiveClip active[kMaxSpecies];
    bool drew = false;
};

VisualState sVisual;

bool visualExhausted(std::istringstream& line)
{
    std::string extra;
    return !(line >> extra);
}

bool validName(const std::string& name)
{
    return !name.empty() && name.size() <= 32
        && name.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
               == std::string::npos;
}

void attachTextures(Shape* shape)
{
    if (!shape) {
        return;
    }
    for (int i = 0; i < shape->mTexAttrCount; ++i) {
        if (shape->mTexAttrList[i].mTexture) {
            shape->mTexAttrList[i].mTexture->attach();
        }
    }
}

Shape* loadPose(const char* filename)
{
    char path[192];
    std::snprintf(path, sizeof(path), "courses/pikmin2room/%s", filename);
    // After cutscene teardown the active heap is the reset movie heap, which
    // cannot fit these mods; force the App heap (Groink 1c89e687 pattern).
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    Shape* shape = gameflow.loadShape(path, true);
    gsys->setHeap(previousHeap);
    return shape;
}

int findSpecies(const std::string& name)
{
    for (int i = 0; i < sVisual.speciesCount; ++i) {
        if (sVisual.species[i].name == name) {
            return i;
        }
    }
    return -1;
}

int findClip(int speciesIndex, const std::string& name)
{
    for (int i = 0; i < sVisual.clipCount; ++i) {
        if (sVisual.clips[i].species == sVisual.species[speciesIndex].name
            && sVisual.clips[i].name == name) {
            return i;
        }
    }
    return -1;
}
} // namespace

bool pc_p2_waterwraith_visual_setup(const char* profilePath)
{
    pc_p2_waterwraith_visual_reset();
    if (!profilePath || !*profilePath) {
        return false;
    }
    std::ifstream input(profilePath);
    if (!input) {
        return false;
    }
    input.seekg(0, std::ios::end);
    if (input.tellg() < 0 || input.tellg() > kProfileBytes) {
        return false;
    }
    input.seekg(0);

    std::string line;
    if (!std::getline(input, line) || line != "P2_WATERWRAITH_VISUAL_1") {
        return false;
    }
    struct PendingClip {
        std::string species;
        std::string name;
        int poses = 0;
        int duration = 0;
        int frames[kMaxPoses] = {};
    };
    std::vector<PendingClip> pending;
    while (std::getline(input, line)) {
        if (!line.empty() && line.back() == '\r') {
            line.pop_back();
        }
        if (line.empty()) {
            continue;
        }
        std::istringstream values(line);
        std::string key;
        values >> key;
        if (key == "species") {
            std::string name;
            int enemyId = 0;
            if (!(values >> name >> enemyId) || !validName(name) || !visualExhausted(values)) {
                pc_p2_waterwraith_visual_reset();
                return false;
            }
            if (sVisual.speciesCount >= kMaxSpecies || findSpecies(name) >= 0) {
                pc_p2_waterwraith_visual_reset();
                return false;
            }
            sVisual.species[sVisual.speciesCount].name    = name;
            sVisual.species[sVisual.speciesCount].enemyId = enemyId;
            ++sVisual.speciesCount;
        } else if (key == "clip") {
            PendingClip clip;
            if (!(values >> clip.species >> clip.name >> clip.poses >> clip.duration)
                || !validName(clip.species) || !validName(clip.name) || clip.poses < 1
                || clip.poses > kMaxPoses || clip.duration < 1 || clip.duration > 10000) {
                pc_p2_waterwraith_visual_reset();
                return false;
            }
            int previous = -1;
            for (int i = 0; i < clip.poses; ++i) {
                if (!(values >> clip.frames[i]) || clip.frames[i] < 0
                    || clip.frames[i] >= clip.duration || clip.frames[i] <= previous) {
                    pc_p2_waterwraith_visual_reset();
                    return false;
                }
                previous = clip.frames[i];
            }
            if (!visualExhausted(values)) {
                pc_p2_waterwraith_visual_reset();
                return false;
            }
            pending.push_back(clip);
        } else {
            pc_p2_waterwraith_visual_reset();
            return false;
        }
    }
    if (sVisual.speciesCount == 0 || pending.empty()
        || pending.size() > static_cast<std::size_t>(kMaxClips)) {
        pc_p2_waterwraith_visual_reset();
        return false;
    }
    for (const PendingClip& entry : pending) {
        if (findSpecies(entry.species) < 0) {
            pc_p2_waterwraith_visual_reset();
            return false;
        }
        ClipBank& clip  = sVisual.clips[sVisual.clipCount];
        clip.species    = entry.species;
        clip.name       = entry.name;
        clip.duration   = entry.duration;
        clip.poseCount  = entry.poses;
        for (int i = 0; i < entry.poses; ++i) {
            char filename[128];
            std::snprintf(filename, sizeof(filename), "ww_%s_%s_%02d.mod",
                          entry.species.c_str(), entry.name.c_str(), i);
            clip.poses[i] = loadPose(filename);
            if (!clip.poses[i]) {
                pc_p2_waterwraith_visual_reset();
                return false;
            }
            clip.frames[i] = entry.frames[i];
        }
        attachTextures(clip.poses[0]);
        ++sVisual.clipCount;
    }
    sVisual.ready = true;
    std::printf("P2_WATERWRAITH_VISUAL_READY species=%d clips=%d\n", sVisual.speciesCount,
                sVisual.clipCount);
    return true;
}

void pc_p2_waterwraith_visual_reset()
{
    sVisual = VisualState();
}

bool pc_p2_waterwraith_visual_ready()
{
    return sVisual.ready;
}

int pc_p2_waterwraith_visual_species_count()
{
    return sVisual.speciesCount;
}

int pc_p2_waterwraith_visual_clip_count()
{
    return sVisual.clipCount;
}

bool pc_p2_waterwraith_visual_has_clip(const char* species, const char* clip)
{
    if (!sVisual.ready || !species || !clip) {
        return false;
    }
    const int speciesIndex = findSpecies(species);
    return speciesIndex >= 0 && findClip(speciesIndex, clip) >= 0;
}

bool pc_p2_waterwraith_visual_play(const char* species, const char* clip, bool looping)
{
    if (!sVisual.ready || !species || !clip) {
        return false;
    }
    const int speciesIndex = findSpecies(species);
    if (speciesIndex < 0) {
        return false;
    }
    const int clipIndex = findClip(speciesIndex, clip);
    if (clipIndex < 0) {
        return false;
    }
    sVisual.active[speciesIndex].clip    = clipIndex;
    sVisual.active[speciesIndex].frame   = 0.0f;
    sVisual.active[speciesIndex].looping = looping;
    return true;
}

int pc_p2_waterwraith_visual_update()
{
    if (!sVisual.ready) {
        return -1;
    }
    int activeCount = 0;
    for (int i = 0; i < sVisual.speciesCount; ++i) {
        ActiveClip& active = sVisual.active[i];
        if (active.clip < 0) {
            continue;
        }
        ++activeCount;
        const ClipBank& clip = sVisual.clips[active.clip];
        active.frame += 1.0f;
        if (active.frame >= static_cast<float>(clip.duration)) {
            if (active.looping) {
                active.frame = std::fmod(active.frame, static_cast<float>(clip.duration));
            } else {
                active.frame = static_cast<float>(clip.duration - 1);
            }
        }
    }
    return activeCount;
}

int pc_p2_waterwraith_visual_pose_index(const char* species)
{
    if (!sVisual.ready || !species) {
        return -1;
    }
    const int speciesIndex = findSpecies(species);
    if (speciesIndex < 0) {
        return -1;
    }
    const ActiveClip& active = sVisual.active[speciesIndex];
    if (active.clip < 0) {
        return -1;
    }
    const ClipBank& clip = sVisual.clips[active.clip];
    const int frame      = static_cast<int>(active.frame);
    int index            = 0;
    for (int i = 0; i < clip.poseCount; ++i) {
        if (clip.frames[i] <= frame) {
            index = i;
        }
    }
    return index;
}

bool pc_p2_waterwraith_visual_completed()
{
    if (!sVisual.ready) {
        return false;
    }
    bool any = false;
    for (int i = 0; i < sVisual.speciesCount; ++i) {
        const ActiveClip& active = sVisual.active[i];
        if (active.clip < 0) {
            continue;
        }
        if (active.looping) {
            return false;
        }
        any = true;
        const ClipBank& clip = sVisual.clips[active.clip];
        if (static_cast<int>(active.frame) < clip.duration - 1) {
            return false;
        }
    }
    return any;
}

int pc_p2_waterwraith_visual_draw(Graphics& gfx, const Matrix4f& ownerWorld)
{
    if (!sVisual.ready || !gfx.mCamera) {
        return 0;
    }
    int drawn = 0;
    for (int i = 0; i < sVisual.speciesCount; ++i) {
        if (sVisual.active[i].clip < 0) {
            continue;
        }
        Matrix4f offset;
        for (int r = 0; r < 4; ++r) {
            for (int c = 0; c < 4; ++c) {
                offset.mMtx[r][c] = (r == c) ? 1.0f : 0.0f;
            }
        }
        offset.mMtx[0][3] = static_cast<float>(i) * 80.0f;
        Matrix4f world;
        ownerWorld.multiplyTo(offset, world);
        drawn += pc_p2_waterwraith_visual_draw_species(gfx, sVisual.species[i].name.c_str(), world);
    }
    return drawn;
}

int pc_p2_waterwraith_visual_draw_species(Graphics& gfx, const char* species,
                                          const Matrix4f& world)
{
    if (!sVisual.ready || !gfx.mCamera || !species) {
        return 0;
    }
    const int speciesIndex = findSpecies(species);
    if (speciesIndex < 0) {
        return 0;
    }
    const ActiveClip& active = sVisual.active[speciesIndex];
    if (active.clip < 0) {
        return 0;
    }
    const int pose = pc_p2_waterwraith_visual_pose_index(species);
    if (pose < 0 || !sVisual.clips[active.clip].poses[pose]) {
        return 0;
    }
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
                       gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    Matrix4f view;
    gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
    Shape* shape = sVisual.clips[active.clip].poses[pose];
    shape->updateAnim(gfx, view, nullptr, nullptr);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    if (!sVisual.drew) {
        std::printf("P2_WATERWRAITH_VISUAL_DRAW species=1\n");
        sVisual.drew = true;
    }
    return 1;
}
