// p2_damagumo_profile_mesh_fixture.cpp -- guarded fixture for the DangoMushi
// profile/mesh/slot binding, slot 312004 (#678).
//
// STATUS: engine-free contract fixture, NOT wired into CMakeLists.txt, never
// linked into production. Compiles standalone for contract review:
//
//   g++ -std=gnu++17 -Wall -Wextra -Werror -DP2_DAMAGUMO_BINDING_STANDALONE
//       tools/p2_damagumo_profile_mesh_fixture.cpp -o p2_damagumo_profile_mesh_fixture
// The macro selects the engine-free binding section of pc_p2_dangomushi.cpp;
// the production branch of that file is untouched native-line content.
//   ./p2_damagumo_profile_mesh_fixture                      (exit 0 on contract self-check)
//   ./p2_damagumo_profile_mesh_fixture --guard-negative      (exit 86/BLOCKED)
//
// Captain safety #632: the guard below mirrors
// scripts/p2_fixture_captain_guard.h (orimaDead/NaviDead/HP<=1 -> CAPTAIN_DOWN
// + exit BLOCKED/86). No live actors exist here; the negative path is exercised
// explicitly via --guard-negative, and live adoption is recorded N/A.

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "../pc_port/pc_p2_dangomushi.cpp"

namespace {

int failures = 0;

void check(bool ok, const char* name) {
    std::printf("%s %s\n", ok ? "PASS" : "FAIL", name);
    if (!ok) {
        ++failures;
    }
}

// Guard semantics mirror the canonical header: orimaDead/NaviDead/HP<=1 means
// captain-down. Returns true when observation must stop.
bool captain_down(bool orima_dead, bool navi_dead, float hp) {
    if (hp != hp) {
        return true;
    }
    return orima_dead || navi_dead || hp <= 1.0f;
}

void require_captain(bool orima_dead, bool navi_dead, float hp, int tick) {
    if (!captain_down(orima_dead, navi_dead, hp)) {
        return;
    }
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f orima_dead=%d dead_state=%d outcome=BLOCKED\n",
                tick, hp, orima_dead ? 1 : 0, navi_dead ? 1 : 0);
    std::fflush(nullptr);
    std::exit(86);
}

void make_hash(char out[65], const char* prefix, char fill) {
    std::size_t n = std::strlen(prefix);
    std::memcpy(out, prefix, n);
    for (std::size_t i = n; i < 64; ++i) {
        out[i] = fill;
    }
    out[64] = 0;
}

int run_self_check() {
    using namespace p2_dangomushi;
    const char* clips_all[] = {"landing", "wait", "flick", "dead", "extra"};
    check(check_structure(kJointCount, kTextureCount, clips_all, 5) == nullptr,
          "structure-accept-15-4-all-clips");
    check(check_structure(14, kTextureCount, clips_all, 5) != nullptr,
          "structure-reject-joints");
    check(check_structure(kJointCount, 3, clips_all, 5) != nullptr,
          "structure-reject-textures");
    const char* clips_missing[] = {"landing", "wait", "flick"};
    check(check_structure(kJointCount, kTextureCount, clips_missing, 3) != nullptr,
          "structure-reject-missing-clip");
    check(check_structure(kJointCount, kTextureCount, nullptr, 0) != nullptr,
          "structure-reject-null-clips");

    ExpectedHashes exp;
    make_hash(exp.profile, kRecordedProfilePrefix, 'a');
    make_hash(exp.mesh, kRecordedMeshPrefix, 'b');
    make_hash(exp.slot, kRecordedSlotPrefix, 'c');
    char profile[65], mesh[65], slot[65];
    std::memcpy(profile, exp.profile, 65);
    std::memcpy(mesh, exp.mesh, 65);
    std::memcpy(slot, exp.slot, 65);
    check(check_hashes(profile, mesh, slot, &exp) == nullptr, "hash-accept");
    mesh[0] = (mesh[0] == 'x' ? 'y' : 'x');
    check(check_hashes(profile, mesh, slot, &exp) != nullptr, "hash-reject-tampered");
    check(check_hashes(profile, mesh, slot, nullptr) != nullptr, "hash-reject-no-expected");
    ExpectedHashes bad = exp;
    bad.profile[0] = 'z';
    bad.profile[1] = 'z';
    check(check_hashes(profile, mesh, slot, &bad) != nullptr, "hash-reject-prefix");
    ExpectedHashes malformed;
    std::memset(&malformed, 0, sizeof(malformed));
    check(check_hashes(profile, mesh, slot, &malformed) != nullptr, "hash-reject-malformed");

    SlotBinding bound = bind_slot(&exp);
    check(bound.slot == 312004 && bound.enemy == 56, "slot-binding-identity");
    check(bound.hash_gated, "slot-binding-hash-gated");
    check(std::strcmp(bound.profile_name, "damagumo-family.json") == 0, "slot-binding-profile");
    check(std::strcmp(bound.mesh_path, "Demon/enemy.bmd") == 0, "slot-binding-mesh");
    SlotBinding open = bind_slot(nullptr);
    check(!open.hash_gated, "slot-binding-open-marks-ungated");

    check(!captain_down(false, false, 100.0f), "guard-pass-healthy");
    check(captain_down(true, false, 100.0f), "guard-down-orima");
    check(captain_down(false, true, 100.0f), "guard-down-navi");
    check(captain_down(false, false, 1.0f), "guard-down-hp-boundary");
    check(captain_down(false, false, 0.0f), "guard-down-hp-zero");
    return failures;
}

}  // namespace

int main(int argc, char** argv) {
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--guard-negative") == 0) {
            require_captain(true, false, 0.0f, 0);
            std::printf("P2_DAMAGUMO_GUARD_NEGATIVE_ERROR guard did not stop\n");
            return 1;
        }
    }
    const int failed = run_self_check();
    std::printf("P2_DAMAGUMO_PROFILE_MESH_%s failures=%d\n",
                failed == 0 ? "PASS" : "FAIL", failed);
    return failed == 0 ? 0 : 1;
}
