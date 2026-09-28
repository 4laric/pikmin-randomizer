// p2_muse_bombsarai_fixture.cpp — muse-bombsarai gate1 probe (l59, #499).
//
// SCOPE: additive gate1 (identity_spawn) probe for BombSarai 58. It asserts
// the SAME generator id across the generated-placement resolve, the source
// resolve (EnemyID 58), and the lane-27 actor binding markers
// (P2_BOMBSARAI_TEKI_READY / SUPPLY). A P1 Napkid birth without a matching
// source-58 placement resolve never correlates.
//
// STATUS: STUB — BLOCKED on muse-placement (#492) and muse-packaging (#493)
// dependency-ready records. This translation unit is engine-free, NOT wired
// into CMakeLists.txt, and never linked into production. It compiles
// standalone for contract review:
//
//   g++ -std=gnu++17 -Wall -Wextra -Werror -DP2_MUSE_BOMBSARAI_STANDALONE_TEST
//       tools/p2_muse_bombsarai_fixture.cpp -o p2_muse_bombsarai_gate1_probe
//   ./p2_muse_bombsarai_gate1_probe   (exits 0 on contract self-check)
//
// Legacy lane-27 claim, family projectile/FSM, and shared placement files
// are read-only to this lane; no shared semantics are touched here.

#include <cstdio>
#include <cstring>

namespace {

// Decomp source resolve: EnemyID_BombSarai = 58 (enemyInfo.h), generator
// name in genEnemy.cpp, payload EnemyID_Bomb with mChildNum = 2.
const unsigned kBombSaraiSourceId = 58;
// P1 vehicle type the generated carrier binds (TEKI_Napkid).
const int kNapkidVehicleType = 11;
// Reviewed muse-placement #492 candidate profile: accepted generated slot
// uid for source 58 (must equal MUSE_ACCEPTED_SLOT[58] in
// experimental/pikmin2_muse_placement.py).
const unsigned kAcceptedSlotUid58 = 1787125272;

struct CorrelatedBirth {
    bool actor_bound = false;
    bool supplied = false;
    bool source_agree = false;
    bool placement_agree = false;
};

// Engine-free correlation core: mirrors
// experimental/pikmin2_muse_bombsarai.py::validate_correlated_birth.
// ready_gen < 0 means no READY marker seen; placement_seen distinguishes
// "pending" from "unparseable".
const char *check_correlated_birth(int ready_gen, int supply_gen,
                                   bool placement_seen, unsigned placement_source,
                                   int placement_gen, CorrelatedBirth *out) {
    CorrelatedBirth legs;
    if (ready_gen >= 0) {
        legs.actor_bound = true;
        if (supply_gen == ready_gen) {
            legs.supplied = true;
        }
    }
    if (placement_seen) {
        legs.source_agree = (placement_source == kBombSaraiSourceId);
        legs.placement_agree =
            (ready_gen >= 0 && placement_gen == ready_gen);
    }
    if (out) {
        *out = legs;
    }
    if (ready_gen < 0) {
        return "no-ready";
    }
    if (!placement_seen) {
        return "placement-pending";
    }
    if (!legs.source_agree) {
        return "source-mismatch";
    }
    if (!legs.placement_agree) {
        return "generator-mismatch";
    }
    if (!legs.supplied) {
        return "supply-missing";
    }
    return "correlated";
}

const char *p2_muse_bombsarai_gate1_contract() {
    return "muse-bombsarai-gate1-v2";
}

// Generation-2 core: mirrors
// experimental/pikmin2_muse_bombsarai.py::validate_generated_birth over the
// real marker contract. resolved_uid/bound_uid come from P2_SEED_RESOLVE and
// the P2_GENERATED_PLACEMENT bound marker; bound_flag is the marker's
// bound bit; bind_gen is its generator field; ready_gen/supplied mirror the
// teki READY generator and same-generator SUPPLY presence. Uids use -1 for
// "marker absent".
const char *check_generated_birth(int resolved_uid, int bound_uid,
                                  bool bound_flag, int bind_gen,
                                  int ready_gen, bool supplied) {
    if (ready_gen < 0) {
        return "no-ready";
    }
    if (resolved_uid < 0) {
        return "seed-unresolved";
    }
    if (!bound_flag) {
        return "placement-refused";
    }
    if (resolved_uid != bound_uid ||
        bound_uid != (int)kAcceptedSlotUid58) {
        return "slot-mismatch";
    }
    if (bind_gen != ready_gen) {
        return "generator-mismatch";
    }
    if (!supplied) {
        return "supply-missing";
    }
    return "correlated";
}

}  // namespace

#ifdef P2_MUSE_BOMBSARAI_STANDALONE_TEST
int main() {
    int failures = 0;
    CorrelatedBirth legs;
    // Correlated: READY+SUPPLY on 270001 with matching source-58 placement.
    if (std::strcmp(check_correlated_birth(270001, 270001, true, 58, 270001,
                                           &legs),
                    "correlated") != 0 ||
        !(legs.actor_bound && legs.supplied && legs.source_agree &&
          legs.placement_agree)) {
        std::puts("FAIL correlated");
        ++failures;
    }
    // Napkid birth without placement never correlates.
    if (std::strcmp(check_correlated_birth(270001, 270001, false, 0, -1,
                                           nullptr),
                    "placement-pending") != 0) {
        std::puts("FAIL placement-pending");
        ++failures;
    }
    // Generator mismatch between binding and placement.
    if (std::strcmp(check_correlated_birth(270001, 270001, true, 58, 270002,
                                           nullptr),
                    "generator-mismatch") != 0) {
        std::puts("FAIL generator-mismatch");
        ++failures;
    }
    // Wrong source id (e.g. Kurage 57) rejected.
    if (std::strcmp(check_correlated_birth(270001, 270001, true, 57, 270001,
                                           nullptr),
                    "source-mismatch") != 0) {
        std::puts("FAIL source-mismatch");
        ++failures;
    }
    // READY without SUPPLY.
    if (std::strcmp(check_correlated_birth(270001, -1, true, 58, 270001,
                                           nullptr),
                    "supply-mismatch") == 0) {
        // Defensive: "supply-mismatch" is not a valid reason token.
        std::puts("FAIL invalid-token");
        ++failures;
    }
    if (std::strcmp(check_correlated_birth(270001, -1, true, 58, 270001,
                                           nullptr),
                    "supply-missing") != 0) {
        std::puts("FAIL supply-missing");
        ++failures;
    }
    // Generation-2 real-marker cases (accepted slot 1787125272).
    if (std::strcmp(check_generated_birth(1787125272, 1787125272, true,
                                          270001, 270001, true),
                    "correlated") != 0) {
        std::puts("FAIL gen2-correlated");
        ++failures;
    }
    if (std::strcmp(check_generated_birth(1787125272, 1787125272, false,
                                          270001, 270001, true),
                    "placement-refused") != 0) {
        std::puts("FAIL gen2-refused");
        ++failures;
    }
    if (std::strcmp(check_generated_birth(12345, 12345, true,
                                          270001, 270001, true),
                    "slot-mismatch") != 0) {
        std::puts("FAIL gen2-slot");
        ++failures;
    }
    if (std::strcmp(check_generated_birth(1787125272, 1787125272, true,
                                          270002, 270001, true),
                    "generator-mismatch") != 0) {
        std::puts("FAIL gen2-generator");
        ++failures;
    }
    if (std::strcmp(check_generated_birth(-1, -1, false,
                                          -1, 270001, true),
                    "seed-unresolved") != 0) {
        std::puts("FAIL gen2-seed");
        ++failures;
    }
    std::printf("contract=%s vehicle=%d failures=%d\n",
                p2_muse_bombsarai_gate1_contract(), kNapkidVehicleType,
                failures);
    return failures == 0 ? 0 : 1;
}
#endif
