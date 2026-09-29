// p2_dweevil_death_clip_test (wf7 dweevil-impl, #871): dead Dweevil plays its
// death clip then holds the dead pose, never attack1, for all four species
// (59-62). Engine-free: exercises pc_p2_dweevil_clip.h choose() directly.
//
// NOTE: checks use an always-evaluated CHECK macro, never bare assert():
// release build types define NDEBUG, which would compile assert() out.
#include "pc_p2_dweevil_clip.h"

#include <cstdio>
#include <string>

static int failures = 0;

#define CHECK(cond)                                                                  \
    do {                                                                             \
        if (!(cond)) {                                                               \
            std::printf("P2_DWEEVIL_DEATH_CLIP_TEST_FAIL line=%d check=%s\n", __LINE__, #cond); \
            ++failures;                                                              \
        }                                                                            \
    } while (0)

int main() {
    const std::string keys[4] = {
        "dweevil|FireOtakara", "dweevil|WaterOtakara",
        "dweevil|GasOtakara", "dweevil|ElecOtakara",
    };
    // Non-dweevil keys are untouched by the helper.
    CHECK(p2dweevilclip::choose("ground|Sokkuri", true, true, false, "", true, true).empty());
    CHECK(!p2dweevilclip::isDweevilKey("ground|Sokkuri"));
    for (const auto& key : keys) {
        CHECK(p2dweevilclip::isDweevilKey(key));
        // Dead live path forces dead, even with an attack motion fallback
        // pending and no forced clip (post-forget corpse retention).
        CHECK(p2dweevilclip::choose(key, false, true, false, "", true, true) == "dead");
        // Corpse path forces dead from the first dead frame.
        CHECK(p2dweevilclip::choose(key, true, true, false, "", true, true) == "dead");
        CHECK(p2dweevilclip::choose(key, true, false, false, "", true, true) == "dead");
        // Alive flick follows the Otakara forced attack1 (single source).
        CHECK(p2dweevilclip::choose(key, false, false, true, "attack1", true, true) == "attack1");
        // Alive wait/move follow forced clips.
        CHECK(p2dweevilclip::choose(key, false, false, true, "wait1", true, true) == "wait1");
        CHECK(p2dweevilclip::choose(key, false, false, true, "dead", true, true) == "dead");
        // Alive without forced never picks attack (no second animation layer).
        CHECK(p2dweevilclip::choose(key, false, false, false, "", true, true).empty());
        // Dead never returns attack, even if forced said attack (stale).
        CHECK(p2dweevilclip::choose(key, false, true, true, "attack1", true, true) == "dead");
        CHECK(p2dweevilclip::choose(key, true, true, true, "attack1", true, true) == "dead");
    }

    if (failures == 0) {
        std::printf("P2_DWEEVIL_DEATH_CLIP_TEST_PASS species=59..62 dead=dead attack_never_after_death=1\n");
        return 0;
    }
    std::printf("P2_DWEEVIL_DEATH_CLIP_TEST_FAIL failures=%d\n", failures);
    return 1;
}
