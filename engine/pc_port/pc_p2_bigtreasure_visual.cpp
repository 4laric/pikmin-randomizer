#include "pc_p2_bigtreasure_visual.h"

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
constexpr int kMaxClips = 32;
constexpr int kMaxPoses = 24;
constexpr int kMaxPellets = 8;
constexpr int kMaxEvents = 512;
constexpr std::streamoff kVisualProfileBytes = 16384;

struct ClipBank {
    std::string name;
    int duration = 0;
    int frames[kMaxPoses] = {};
    Shape* poses[kMaxPoses] = {};
    int poseCount = 0;
    const p2retail::Motion* motion = nullptr;
};

struct PelletBank {
    std::string name;
    Shape* shape = nullptr;
    float joint[12] = {}; // bind-pose otakara_* capture transform (3x4)
};

struct VisualState {
    bool ready = false;
    P2BigTreasureMotionBank motions;
    ClipBank clips[kMaxClips];
    int clipCount = 0;
    PelletBank pellets[kMaxPellets];
    int pelletCount = 0;
    int debugCount = 0;
    p2retail::Player player;
    const ClipBank* active = nullptr;
    P2BigTreasureVisualEvent events[kMaxEvents];
    int eventCount = 0;
    bool drew = false;
};

VisualState sVisual;

bool visualExhausted(std::istringstream& line)
{
    std::string extra;
    return !(line >> extra);
}

bool validClipName(const std::string& name)
{
    return !name.empty() && name.size() <= 32
        && name.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_") == std::string::npos;
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

ClipBank* findClip(const std::string& name)
{
    for (int i = 0; i < sVisual.clipCount; ++i) {
        if (sVisual.clips[i].name == name) {
            return &sVisual.clips[i];
        }
    }
    return nullptr;
}

void logEvent(const char* clip, int frame, int type)
{
    if (sVisual.eventCount >= kMaxEvents) {
        return;
    }
    P2BigTreasureVisualEvent& entry = sVisual.events[sVisual.eventCount++];
    std::snprintf(entry.clip, sizeof(entry.clip), "%s", clip);
    entry.frame = frame;
    entry.type  = type;
}
} // namespace

bool pc_p2_bigtreasure_visual_setup(const char* profilePath)
{
    pc_p2_bigtreasure_visual_reset();
    if (!profilePath || !*profilePath) {
        return false;
    }
    std::ifstream input(profilePath);
    if (!input) {
        return false;
    }
    input.seekg(0, std::ios::end);
    if (input.tellg() < 0 || input.tellg() > kVisualProfileBytes) {
        return false;
    }
    input.seekg(0);

    std::string line;
    if (!std::getline(input, line) || line != "P2_BIGTREASURE_VISUAL_1") {
        return false;
    }
    std::string eventsFile;
    struct PendingPellet {
        std::string name, file, joint;
        float matrix[12];
    };
    std::vector<PendingPellet> pendingPellets;
    struct PendingClip {
        std::string name;
        int poses, duration;
        int frames[kMaxPoses];
    };
    std::vector<PendingClip> pendingClips;
    int debugCount = 0;
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
        if (key == "events") {
            if (!eventsFile.empty() || !(values >> eventsFile) || !visualExhausted(values)
                || eventsFile.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_.") != std::string::npos) {
                return false;
            }
        } else if (key == "clip") {
            PendingClip clip;
            if (!(values >> clip.name >> clip.poses >> clip.duration) || !validClipName(clip.name)
                || clip.poses < 1 || clip.poses > kMaxPoses || clip.duration < 1
                || clip.duration > 10000) {
                return false;
            }
            int previous = -1;
            for (int i = 0; i < clip.poses; ++i) {
                if (!(values >> clip.frames[i]) || clip.frames[i] <= previous || clip.frames[i] < 0
                    || clip.frames[i] >= clip.duration) {
                    return false;
                }
                previous = clip.frames[i];
            }
            if (!visualExhausted(values)) {
                return false;
            }
            pendingClips.push_back(clip);
        } else if (key == "pellet") {
            PendingPellet pellet;
            if (!(values >> pellet.name >> pellet.file >> pellet.joint) || !validClipName(pellet.name)) {
                return false;
            }
            for (float& value : pellet.matrix) {
                if (!(values >> value) || !std::isfinite(value)) {
                    return false;
                }
            }
            if (!visualExhausted(values)) {
                return false;
            }
            pendingPellets.push_back(pellet);
        } else if (key == "pellet_debug") {
            std::string name, joint;
            if (!(values >> name >> joint) || !visualExhausted(values)) {
                return false;
            }
            ++debugCount;
        } else {
            return false;
        }
    }
    if (eventsFile.empty() || pendingClips.empty()
        || pendingClips.size() > static_cast<std::size_t>(kMaxClips)
        || pendingPellets.size() > static_cast<std::size_t>(kMaxPellets)) {
        return false;
    }
    if (!p2_bigtreasure_motion_load(eventsFile.c_str(), sVisual.motions)) {
        return false;
    }
    for (const PendingClip& pending : pendingClips) {
        ClipBank& clip = sVisual.clips[sVisual.clipCount];
        clip.name     = pending.name;
        clip.duration = pending.duration;
        clip.motion   = p2_bigtreasure_motion_find(sVisual.motions, pending.name.c_str());
        if (!clip.motion || clip.motion->duration != pending.duration) {
            pc_p2_bigtreasure_visual_reset();
            return false;
        }
        for (int i = 0; i < pending.poses; ++i) {
            char filename[96];
            std::snprintf(filename, sizeof(filename), "bigtreasure_%s_%02d.mod",
                          pending.name.c_str(), i);
            clip.poses[i] = loadPose(filename);
            if (!clip.poses[i]) {
                pc_p2_bigtreasure_visual_reset();
                return false;
            }
            clip.frames[i] = pending.frames[i];
        }
        clip.poseCount = pending.poses;
        attachTextures(clip.poses[0]);
        ++sVisual.clipCount;
    }
    for (const PendingPellet& pending : pendingPellets) {
        PelletBank& pellet = sVisual.pellets[sVisual.pelletCount];
        pellet.name  = pending.name;
        pellet.shape = loadPose(pending.file.c_str());
        if (!pellet.shape) {
            pc_p2_bigtreasure_visual_reset();
            return false;
        }
        std::memcpy(pellet.joint, pending.matrix, sizeof(pellet.joint));
        attachTextures(pellet.shape);
        ++sVisual.pelletCount;
    }
    sVisual.debugCount = debugCount;
    sVisual.ready      = true;
    std::printf("P2_BIGTREASURE_VISUAL_READY clips=%d pellets=%d pellet_debug=%d\n",
                sVisual.clipCount, sVisual.pelletCount, sVisual.debugCount);
    return true;
}

void pc_p2_bigtreasure_visual_reset()
{
    sVisual = VisualState();
}

bool pc_p2_bigtreasure_visual_ready()
{
    return sVisual.ready;
}

bool pc_p2_bigtreasure_visual_clip(const char* name)
{
    if (!sVisual.ready || !name) {
        return false;
    }
    ClipBank* clip = findClip(name);
    if (!clip || !sVisual.player.start(*clip->motion)) {
        return false;
    }
    sVisual.active = clip;
    return true;
}

int pc_p2_bigtreasure_visual_update(float sourceFrames)
{
    if (!sVisual.ready || !sVisual.active) {
        return -1;
    }
    int dispatched = 0;
    const std::string clip = sVisual.active->name;
    const p2retail::Update result = sVisual.player.advance(
        sourceFrames, [&](const p2retail::Event& event) {
            logEvent(clip.c_str(), event.frame, event.type);
            ++dispatched;
        });
    if (result == p2retail::Update::Invalid || result == p2retail::Update::Inactive
        || result == p2retail::Update::Reentrant) {
        return -1;
    }
    return dispatched;
}

const P2BigTreasureVisualEvent* pc_p2_bigtreasure_visual_events(int* count)
{
    if (count) {
        *count = sVisual.eventCount;
    }
    return sVisual.events;
}

const char* pc_p2_bigtreasure_visual_active_clip()
{
    return sVisual.active ? sVisual.active->name.c_str() : nullptr;
}

int pc_p2_bigtreasure_visual_pose_index()
{
    if (!sVisual.active) {
        return -1;
    }
    const int frame = sVisual.player.poseFrame();
    int index = 0;
    for (int i = 0; i < sVisual.active->poseCount; ++i) {
        if (sVisual.active->frames[i] <= frame) {
            index = i;
        }
    }
    return index;
}

bool pc_p2_bigtreasure_visual_completed()
{
    return sVisual.player.completed();
}

int pc_p2_bigtreasure_visual_pellet_count()
{
    return sVisual.pelletCount;
}

int pc_p2_bigtreasure_visual_debug_count()
{
    return sVisual.debugCount;
}

void pc_p2_bigtreasure_visual_draw(Graphics& gfx, const Matrix4f& ownerWorld)
{
    if (!sVisual.ready || !sVisual.active || !gfx.mCamera) {
        return;
    }
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
                       gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    const int pose = pc_p2_bigtreasure_visual_pose_index();
    Matrix4f view;
    gfx.mCamera->mLookAtMtx.multiplyTo(ownerWorld, view);
    Shape* boss = sVisual.active->poses[pose];
    boss->updateAnim(gfx, view, nullptr, nullptr);
    boss->drawshape(gfx, *gfx.mCamera, nullptr);
    for (int i = 0; i < sVisual.pelletCount; ++i) {
        const PelletBank& pellet = sVisual.pellets[i];
        Matrix4f joint;
        for (int r = 0; r < 3; ++r) {
            for (int c = 0; c < 4; ++c) {
                joint.mMtx[r][c] = pellet.joint[r * 4 + c];
            }
        }
        joint.mMtx[3][0] = joint.mMtx[3][1] = joint.mMtx[3][2] = 0.0f;
        joint.mMtx[3][3] = 1.0f;
        Matrix4f world, pelletView;
        ownerWorld.multiplyTo(joint, world);
        gfx.mCamera->mLookAtMtx.multiplyTo(world, pelletView);
        pellet.shape->updateAnim(gfx, pelletView, nullptr, nullptr);
        pellet.shape->drawshape(gfx, *gfx.mCamera, nullptr);
    }
    if (!sVisual.drew) {
        std::printf("P2_BIGTREASURE_VISUAL_DRAW clip=%s pose=%d pellets=%d pellet_debug=%d\n",
                    sVisual.active->name.c_str(), pose, sVisual.pelletCount, sVisual.debugCount);
        sVisual.drew = true;
    }
}
