#include "pc_p2_groink_arena.h"

#include "pc_p2_animation.h"
#include "Camera.h"
#include "Graphics.h"
#include "Shape.h"
#include "Texture.h"
#include "gameflow.h"
#include "sysNew.h"
#include "system.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace {
constexpr float kPi = 3.14159265358979323846f;
constexpr float kCoordinateLimit = 100000.0f;
constexpr float kParameterLimit = 1000.0f;
constexpr char kModelName[] = "groink_attack.mod";
constexpr char kModelPath[] = "courses/pikmin2room/groink_attack.mod";

struct ArenaState {
    Shape* shape = nullptr; // Cached by gameflow; this module never owns it.
    P2GroinkPolicy policy;
    P2GroinkVec3 owner;
    P2GroinkVec3 target;
    P2GroinkMuzzle localMuzzle;
    float ownerYaw = 0.0f;
    float searchDistance = 0.0f;
    float attackRadius = 0.0f;
    float aimAngle = 0.0f;
    bool ready = false;
    bool drew = false;
};

ArenaState sArena;

bool finite(float value) { return std::isfinite(value); }
bool finite(P2GroinkVec3 value)
{
    return finite(value.x) && finite(value.y) && finite(value.z);
}
bool bounded(P2GroinkVec3 value)
{
    return finite(value) && std::fabs(value.x) <= kCoordinateLimit
        && std::fabs(value.y) <= kCoordinateLimit && std::fabs(value.z) <= kCoordinateLimit;
}
bool exhausted(std::istringstream& line)
{
    std::string extra;
    return !(line >> extra);
}
bool parseHeader(const std::string& text, const char* first, const char* second)
{
    std::istringstream line(text);
    std::string actualFirst, actualSecond;
    return (line >> actualFirst >> actualSecond) && actualFirst == first && actualSecond == second
        && exhausted(line);
}
bool nextLine(std::ifstream& input, std::string& line)
{
    if (!std::getline(input, line)) return false;
    if (!line.empty() && line.back() == '\r') line.pop_back();
    return true;
}
bool parseProfile(const char* profilePath, ArenaState& parsed)
{
    if (!profilePath || !*profilePath) return false;
    std::ifstream input(profilePath);
    if (!input) return false;
    input.seekg(0, std::ios::end);
    if (input.tellg() < 0 || input.tellg() > 4096) return false;
    input.seekg(0);

    std::string line;
    if (!nextLine(input, line) || line != "P2_GROINK_ARENA_1") return false;
    if (!nextLine(input, line) || !parseHeader(line, "model", kModelName)) return false;

    {
        std::istringstream values;
        if (!nextLine(input, line)) return false;
        values.str(line);
        std::string key;
        if (!(values >> key >> parsed.searchDistance >> parsed.attackRadius) || key != "params"
            || !exhausted(values)) return false;
    }
    {
        std::istringstream values;
        if (!nextLine(input, line)) return false;
        values.str(line);
        std::string key;
        if (!(values >> key >> parsed.owner.x >> parsed.owner.y >> parsed.owner.z >> parsed.ownerYaw)
            || key != "owner" || !exhausted(values)) return false;
    }
    {
        std::istringstream values;
        if (!nextLine(input, line)) return false;
        values.str(line);
        std::string key;
        if (!(values >> key >> parsed.target.x >> parsed.target.y >> parsed.target.z) || key != "target"
            || !exhausted(values)) return false;
    }
    {
        float values[12];
        std::istringstream source;
        if (!nextLine(input, line)) return false;
        source.str(line);
        std::string key;
        if (!(source >> key) || key != "muzzle") return false;
        for (float& value : values) if (!(source >> value)) return false;
        if (!exhausted(source)) return false;
        parsed.localMuzzle = {
            { values[0], values[4], values[8] }, { values[1], values[5], values[9] },
            { values[2], values[6], values[10] }, { values[3], values[7], values[11] }
        };
    }
    if (nextLine(input, line)) return false;

    return bounded(parsed.owner) && bounded(parsed.target) && finite(parsed.ownerYaw)
        && std::fabs(parsed.ownerYaw) <= 2.0f * kPi && finite(parsed.searchDistance)
        && parsed.searchDistance > 0.0f && parsed.searchDistance <= kParameterLimit
        && finite(parsed.attackRadius) && parsed.attackRadius >= 0.0f
        && parsed.attackRadius <= kParameterLimit && bounded(parsed.localMuzzle.column0)
        && bounded(parsed.localMuzzle.column1) && bounded(parsed.localMuzzle.column2)
        && bounded(parsed.localMuzzle.column3);
}

Shape* loadModel()
{
    const std::string assetPath = std::string("assets/dataDir/") + kModelPath;
    std::ifstream input(assetPath, std::ios::binary | std::ios::ate);
    if (!input) return nullptr;
    const std::streamoff size = input.tellg();
    if (size <= 0 || size > 16 * 1024 * 1024) return nullptr;
    input.seekg(0);
    std::vector<unsigned char> data(static_cast<size_t>(size));
    std::vector<unsigned char> resources;
    if (!input.read(reinterpret_cast<char*>(data.data()), size)
        || !p2animation::resources(data, resources)) return nullptr;

    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    Shape* shape = gameflow.loadShape(kModelPath, true);
    if (shape) {
        for (int index = 0; index < shape->mTexAttrCount; ++index) {
            if (shape->mTexAttrList[index].mTexture) shape->mTexAttrList[index].mTexture->attach();
        }
    }
    gsys->setHeap(previousHeap);
    return shape;
}

P2GroinkMuzzle worldMuzzle(const ArenaState& state, bool& valid)
{
    valid = false;
    const float cosine = std::cos(state.ownerYaw);
    const float sine = std::sin(state.ownerYaw);
    if (!finite(cosine) || !finite(sine)) return {};
    const auto rotate = [cosine, sine](P2GroinkVec3 local) {
        return P2GroinkVec3{ cosine * local.x + sine * local.z, local.y,
                             -sine * local.x + cosine * local.z };
    };
    P2GroinkMuzzle world = { rotate(state.localMuzzle.column0), rotate(state.localMuzzle.column1),
                             rotate(state.localMuzzle.column2), rotate(state.localMuzzle.column3) };
    world.column3.x += state.owner.x;
    world.column3.y += state.owner.y;
    world.column3.z += state.owner.z;
    valid = finite(world.column0) && finite(world.column1) && finite(world.column2)
        && bounded(world.column3);
    return valid ? world : P2GroinkMuzzle{};
}

struct TraceBridge {
    P2GroinkTraceFn trace = nullptr;
    void* context = nullptr;
    bool failed = false;
};

bool requiredTrace(void* context, const P2GroinkVec3& position, const P2GroinkVec3& velocity,
                   float delta, float radius, P2GroinkTraceResult& result)
{
    TraceBridge& bridge = *static_cast<TraceBridge*>(context);
    if (!bridge.trace(bridge.context, position, velocity, delta, radius, result)) {
        bridge.failed = true;
        return false;
    }
    return true;
}
}

void pc_p2_groink_arena_reset()
{
    // Shape is retained in gameflow's cache. Clearing the pointer is enough.
    sArena = ArenaState{};
}

bool pc_p2_groink_arena_setup(const char* profilePath)
{
    pc_p2_groink_arena_reset();
    ArenaState parsed;
    if (!parseProfile(profilePath, parsed)) {
        std::fputs("P2_GROINK_ARENA invalid profile\n", stderr);
        return false;
    }
    bool validMuzzle = false;
    P2GroinkMuzzle muzzle = worldMuzzle(parsed, validMuzzle);
    p2_groink_rotate_vertical(muzzle, 0.0f, validMuzzle);
    if (!validMuzzle) {
        std::fputs("P2_GROINK_ARENA invalid muzzle\n", stderr);
        return false;
    }
    parsed.shape = loadModel();
    if (!parsed.shape) {
        std::fputs("P2_GROINK_ARENA invalid model groink_attack.mod\n", stderr);
        return false;
    }
    parsed.ready = true;
    sArena = parsed;
    std::printf("P2_GROINK_ARENA_READY model=groink_attack.mod visual_muzzle_alignment=unvalidated "
                "shellmarker=debug fixed_heading=owner_yaw_only no_ai=1 no_damage=1\n");
    return true;
}

bool pc_p2_groink_arena_update(float sourceDelta, bool fireEvent4,
                                P2GroinkTraceFn trace, void* context)
{
    if (!sArena.ready || !trace || !finite(sourceDelta)
        || std::fabs(sourceDelta - P2GroinkPolicy::kSourceDelta) > 0.000001f) return false;

    bool validMuzzle = false;
    P2GroinkMuzzle muzzle = worldMuzzle(sArena, validMuzzle);
    if (!validMuzzle) return false;
    P2GroinkAim aim = P2GroinkPolicy::aim(muzzle.column3, sArena.target, sArena.searchDistance,
                                          sArena.attackRadius, sourceDelta, sArena.aimAngle);
    if (!aim.valid) return false;
    sArena.aimAngle = aim.angle;
    muzzle = worldMuzzle(sArena, validMuzzle);
    if (!validMuzzle) return false;
    muzzle = p2_groink_rotate_vertical(muzzle, sArena.aimAngle, validMuzzle);
    if (!validMuzzle) return false;

    // Fixture policy has no FSM: the host supplies the source event-4 edge.
    bool commandAccepted = true;
    if (fireEvent4 && aim.locked && !sArena.policy.shell().active) {
        commandAccepted = sArena.policy.emit(muzzle, aim.shellSpeed, { 0.5f, 0.5f, 0.5f });
    }
    sArena.policy.clearTerminalStep();
    TraceBridge bridge{ trace, context };
    sArena.policy.update(sArena.owner, sourceDelta, requiredTrace, &bridge);
    if (bridge.failed) {
        // An arena has no MapMgr fallback. Do not retain a shell advanced by
        // P2GroinkPolicy's deliberately generic no-trace fallback.
        sArena.policy.recycle();
        return false;
    }
    return commandAccepted
        && sArena.policy.lastTerminalStep().reason != P2GroinkTerminalReason::Invalid;
}

void pc_p2_groink_arena_draw(Graphics& gfx)
{
    if (!sArena.ready || !sArena.shape || !gfx.mCamera) return;
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov,
                       gfx.mCamera->mAspectRatio, gfx.mCamera->mNear, gfx.mCamera->mFar, 1.0f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    Matrix4f world, view;
    world.makeSRT(Vector3f(1.0f, 1.0f, 1.0f), Vector3f(0.0f, sArena.ownerYaw, 0.0f),
                  Vector3f(sArena.owner.x, sArena.owner.y, sArena.owner.z));
    gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
    sArena.shape->updateAnim(gfx, view, nullptr, nullptr);
    sArena.shape->drawshape(gfx, *gfx.mCamera, nullptr);

    const P2GroinkShell& shell = sArena.policy.shell();
    if (shell.active) {
        const Vector3f position(shell.position.x, shell.position.y, shell.position.z);
        gfx.drawSphere(position, P2GroinkPolicy::kShellRadius, gfx.mCamera->mLookAtMtx);
    }
    if (!sArena.drew) {
        std::puts("P2_GROINK_ARENA_DRAW baked_attack_frame25 shellmarker=debug");
        sArena.drew = true;
    }
}
