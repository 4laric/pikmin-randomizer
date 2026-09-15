#include "../pc_port/pc_p2_groink_arena.cpp"

#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>

namespace {
bool writeProfile(const char* path, const char* text)
{
    std::ofstream output(path, std::ios::binary);
    return static_cast<bool>(output << text);
}
bool goodTrace(void*, const P2GroinkVec3& position, const P2GroinkVec3& velocity,
               float delta, float radius, P2GroinkTraceResult& result)
{
    if (radius != P2GroinkPolicy::kShellRadius) return false;
    result.position = { position.x + velocity.x * delta, position.y + velocity.y * delta,
                        position.z + velocity.z * delta };
    result.velocity = velocity;
    return true;
}
bool failedTrace(void*, const P2GroinkVec3&, const P2GroinkVec3&, float, float,
                 P2GroinkTraceResult&)
{
    return false;
}
bool invalidTrace(void*, const P2GroinkVec3&, const P2GroinkVec3&, float, float,
                  P2GroinkTraceResult& result)
{
    result.position = { INFINITY, 0.0f, 0.0f };
    result.velocity = {};
    return true;
}
bool check(bool condition, const char* label)
{
    if (condition) return true;
    std::fprintf(stderr, "FAIL %s\n", label);
    return false;
}
bool lockAndFire()
{
    for (int frame = 0; frame < 40; ++frame) {
        if (!pc_p2_groink_arena_update(P2GroinkPolicy::kSourceDelta, frame == 39,
                                       goodTrace, nullptr)) return false;
    }
    return sArena.policy.shell().active;
}
}

int main(int argc, char** argv)
{
    if (argc != 3) {
        std::fputs("usage: p2_groink_arena_test <staged-profile> <new-scratch-profile>\n", stderr);
        return 2;
    }
    const char* stagedProfile = argv[1];
    const char* scratchProfile = argv[2];
    std::ifstream existing(scratchProfile, std::ios::binary);
    if (existing) {
        std::fputs("refusing to overwrite scratch profile\n", stderr);
        return 2;
    }
    const char* valid =
        "P2_GROINK_ARENA_1\n"
        "model groink_attack.mod\n"
        "params 250 15\n"
        "owner 0 0 0 0\n"
        "target 0 0 250\n"
        "muzzle 0 2 0 0 0 0 3 0 0.5 0 0 0\n";
    bool ok = writeProfile(scratchProfile, valid);
    ArenaState parsed;
    ok &= check(parseProfile(scratchProfile, parsed), "generated profile parses");
    ok &= check(parsed.searchDistance == 250.0f && parsed.attackRadius == 15.0f,
                "profile parameters");
    ArenaState staged;
    ok &= check(parseProfile(stagedProfile, staged), "stage profile parses");
    ok &= writeProfile(scratchProfile, "P2_GROINK_ARENA_1\nmodel groink_attack.mod\nparams 0 15\nowner 0 0 0 0\n"
                       "target 0 0 250\nmuzzle 0 2 0 0 0 0 3 0 0.5 0 0 0\n");
    ArenaState invalid;
    ok &= check(!parseProfile(scratchProfile, invalid), "zero search distance rejected");
    ok &= writeProfile(scratchProfile, "P2_GROINK_ARENA_1\r\nmodel groink_attack.mod\r\nparams 250 15\r\n"
                       "owner 0 0 0 0\r\ntarget 0 0 250\r\nmuzzle 0 0 0 0 0 0 3 0 0.5 0 0 0\r\n");
    ok &= check(parseProfile(scratchProfile, invalid), "CRLF profile parses before setup validation");
    bool validMuzzle = false;
    P2GroinkMuzzle degenerate = worldMuzzle(invalid, validMuzzle);
    p2_groink_rotate_vertical(degenerate, 0.0f, validMuzzle);
    ok &= check(!validMuzzle, "degenerate muzzle rejected by setup validation");
    ok &= writeProfile(scratchProfile, (std::string(valid) + "unexpected\n").c_str());
    ok &= check(!parseProfile(scratchProfile, invalid), "trailing profile data rejected");
    const std::string oversized(4097, 'x');
    ok &= writeProfile(scratchProfile, oversized.c_str());
    ok &= check(!parseProfile(scratchProfile, invalid), "oversized profile rejected");

    ok &= writeProfile(scratchProfile, valid);
    ok &= check(parseProfile(scratchProfile, sArena), "simulation profile parses");
    sArena.ready = true;
    ok &= check(lockAndFire(), "locked event four emits shell");
    const P2GroinkVec3 before = sArena.policy.shell().position;
    ok &= check(pc_p2_groink_arena_update(P2GroinkPolicy::kSourceDelta, true, goodTrace, nullptr),
                "active event four still updates");
    const P2GroinkVec3 after = sArena.policy.shell().position;
    ok &= check(before.x != after.x || before.y != after.y || before.z != after.z,
                "active shell moved");
    const P2GroinkVec3 unchanged = sArena.policy.shell().position;
    ok &= check(!pc_p2_groink_arena_update(P2GroinkPolicy::kSourceDelta, false, nullptr, nullptr),
                "null trace refused");
    ok &= check(sArena.policy.shell().position.x == unchanged.x
                && sArena.policy.shell().position.y == unchanged.y
                && sArena.policy.shell().position.z == unchanged.z, "null trace no mutation");
    ok &= check(!pc_p2_groink_arena_update(P2GroinkPolicy::kSourceDelta, false, failedTrace, nullptr),
                "trace failure rejected");
    ok &= check(!sArena.policy.shell().active, "trace failure recycled shell");

    sArena = ArenaState{};
    ok &= check(parseProfile(scratchProfile, sArena), "invalid-terminal profile parses");
    sArena.ready = true;
    ok &= check(lockAndFire(), "invalid-terminal shell emits");
    ok &= check(!pc_p2_groink_arena_update(P2GroinkPolicy::kSourceDelta, false, invalidTrace, nullptr),
                "invalid trace terminal propagated");
    ok &= check(!sArena.policy.shell().active, "invalid trace terminal recycled shell");
    pc_p2_groink_arena_reset();
    ok &= check(!pc_p2_groink_arena_update(P2GroinkPolicy::kSourceDelta, false, goodTrace, nullptr),
                "reset clears arena state");
    std::remove(scratchProfile);
    if (ok) std::puts("p2_groink_arena_test PASS");
    return ok ? 0 : 1;
}
