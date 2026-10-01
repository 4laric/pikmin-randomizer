#include "pc_bbft.h"
#include "bbft/bbft_transport.h"
#undef NDEBUG
#include <cassert>
#include <cstring>
#include <cstdio>
#include <cstdlib>
// CMake links the real P2 proxy implementation. Without a proxy-tier
// handshake it returns -1; a local strong stub would duplicate its symbol.
static int ready, held, foreground = 1, access, warps, updates, checks, regions, pikminAccess, skipTutorial, progression, blue, yellow, shared, tunic, bombs;
extern "C" {
void bbft_transport_init(const char* game, void (*)(void), void (*)(char*)) { assert(!std::strcmp(game, "pikmin")); }
void bbft_transport_update() { ++updates; }
int bbft_state_ready() { return ready; }
int bbft_checked(const char*) { return 0; }
int bbft_warp_held() { return held; }
int bbft_is_foreground() { return foreground; }
int bbft_region_unlocks() { return regions; }
int bbft_shared_capabilities(void) { return shared; }
int bbft_pikmin_progression(void) { return progression; }
int bbft_pikmin_skip_tutorial() { return skipTutorial || progression; }
int bbft_has(const char* item) {
    if (!std::strcmp(item, "Zora Tunic")) return tunic;
    if (!std::strcmp(item, "Bomb Bag")) return bombs;
    if (!std::strcmp(item, "Blue Onion")) return blue;
    if (!std::strcmp(item, "Yellow Onion")) return yellow;
    if (!std::strcmp(item, "Pikmin Access")) return pikminAccess;
    assert(!std::strcmp(item, "Pikmin: Forest of Hope Access")); return access;
}
void bbft_warp_out() { ++warps; held = 1; }
void bbft_check(const char*) { ++checks; }
void bbft_logf(const char*, ...) {}
}
int main(int argc, char**) {
    assert(pc_bbft_focus_hold_policy(false, false) && !pc_bbft_focus_hold_policy(false, true));
    assert(!pc_bbft_focus_hold_policy(true, false) && !pc_bbft_focus_hold_policy(true, true));
    _putenv_s("PIKMIN_RANDOMIZER_TEST_VISIBLE", "1");
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "");
    assert(!pc_bbft_test_background() && !pc_bbft_test_visible());
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "1");
    assert(pc_bbft_test_background() && pc_bbft_test_visible());
    // Without background, visibility never applies (a WATCH_RUNS file may legitimately exist on the host).
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "");
    assert(!pc_bbft_test_visible());
    _putenv_s("PIKMIN_RANDOMIZER_TEST_BACKGROUND", "");
    const bool backgroundTest = argc > 1;
    if (backgroundTest) _putenv_s("PIKMIN_BBFT_TEST_BACKGROUND", "1");
    assert(!pc_bbft_enabled() && !pc_bbft_hold() && pc_bbft_forest_access());
    assert(!std::strcmp(pc_bbft_save_root(), "save"));
    pc_bbft_start_button(true); assert(pc_bbft_take_skip());
    pc_bbft_start_button(true); assert(!pc_bbft_take_skip());
    pc_bbft_start_button(false);
    // #1029: netplay derives the cutscene skip from the synced inputs. Local
    // Start is ignored; a rising edge on EITHER captain's pad requests one
    // skip for that frame only; a held Start does not repeat.
    pc_bbft_synced_start(true, false); assert(!pc_bbft_take_skip()); // inert until switched on
    pc_bbft_start_source_synced(true);
    pc_bbft_start_button(false); pc_bbft_start_button(true); assert(!pc_bbft_take_skip());
    pc_bbft_synced_start(false, false); assert(!pc_bbft_take_skip());
    pc_bbft_synced_start(true, false); assert(pc_bbft_take_skip());
    pc_bbft_synced_start(true, false); assert(!pc_bbft_take_skip());   // held: no new edge
    pc_bbft_synced_start(false, false);
    pc_bbft_synced_start(false, true); assert(pc_bbft_take_skip());    // the joiner's pad
    pc_bbft_synced_start(true, true); assert(pc_bbft_take_skip());     // host presses while joiner holds
    pc_bbft_synced_start(true, true); assert(!pc_bbft_take_skip());
    pc_bbft_synced_start(false, false);
    pc_bbft_synced_start(true, false);                                 // an unconsumed edge...
    pc_bbft_synced_start(true, false); assert(!pc_bbft_take_skip());   // ...does not outlive its frame
    pc_bbft_start_source_synced(false);
    pc_bbft_start_button(false); pc_bbft_start_button(true); assert(pc_bbft_take_skip()); // local path back
    pc_bbft_start_button(false);
    pc_bbft_update(); pc_bbft_warp(); pc_bbft_check("test");
    assert(!updates && !warps && !checks);
    char exe[] = "nectar", arg[] = "--bbft-port", port[] = "39000";
    char* argv[] = {exe, arg, port};
    pc_bbft_init(3, argv);
    if (backgroundTest) {
        foreground = 0; assert(pc_bbft_hold());
        ready = 1; assert(!pc_bbft_hold() && !pc_bbft_accept_input());
        pc_bbft_warp(); assert(!warps);
        pc_bbft_start_button(true); assert(!pc_bbft_take_skip());
        held = 1; assert(pc_bbft_hold());
        held = 0; regions = 1; assert(pc_bbft_hold());
        pikminAccess = 1; assert(!pc_bbft_hold());
        std::puts("BBFT background test mode retains input/state/warp/access gates");
        return 0;
    }
    assert(!std::strncmp(pc_bbft_save_root(), "save/bbft_sessions/", 19));
    const char* saveRoot = pc_bbft_save_root();
    assert(saveRoot == pc_bbft_save_root());
    assert(pc_bbft_enabled() && pc_bbft_hold());
    ready = 1;
    assert(!pc_bbft_hold() && !pc_bbft_forest_access());
    foreground = 0; pc_bbft_warp(); assert(pc_bbft_hold() && !warps);
    pc_bbft_update(); assert(updates == 1); // Network still pumps while held.
    foreground = 1; pc_bbft_warp(); assert(warps == 1 && pc_bbft_hold());
    held = 0; access = 1;
    assert(!pc_bbft_hold() && pc_bbft_forest_access());
    regions=1; assert(pc_bbft_hold());
    pikminAccess=1; assert(!pc_bbft_hold());
    access=0; assert(!pc_bbft_forest_access());
    skipTutorial=1; assert(pc_bbft_skip_tutorial() && pc_bbft_forest_access());
    skipTutorial=0; access=1;
    progression=1;
    assert(pc_bbft_skip_tutorial());
    assert(pc_bbft_color_access(1) && !pc_bbft_color_access(0) && !pc_bbft_color_access(2));
    blue=1; assert(pc_bbft_color_access(0) && !pc_bbft_color_access(2));
    yellow=1; assert(pc_bbft_color_access(2));
    pc_bbft_onion_site(2, 100, 200);
    assert(pc_bbft_near_onion_site(2, 102, 204, 10));
    assert(!pc_bbft_near_onion_site(2, 0, 0, 10));
    assert(!pc_bbft_near_onion_site(0, 100, 200, 10));
    assert(pc_bbft_bomb_rocks()); // Old seeds retain vanilla bomb rocks.
    shared=1; assert(!pc_bbft_color_access(0)); // Legacy Blue Onion cannot bypass tunic.
    tunic=1; assert(pc_bbft_color_access(0));
    assert(!pc_bbft_bomb_rocks());
    bombs=1; assert(pc_bbft_bomb_rocks());
    yellow=0; assert(!pc_bbft_bomb_rocks());
    yellow=1; bombs=0; assert(!pc_bbft_bomb_rocks());
    shared=0; assert(pc_bbft_bomb_rocks() && pc_bbft_color_access(0));
    progression=0; blue=yellow=0; assert(pc_bbft_color_access(0));
    pc_bbft_check("Pikmin: Main Engine"); assert(checks == 1);
    pc_bbft_start_button(true); assert(pc_bbft_take_skip());
    assert(!pc_bbft_take_skip());
    pc_bbft_start_button(true); assert(!pc_bbft_take_skip());
    pc_bbft_start_button(false); pc_bbft_start_button(true); assert(pc_bbft_take_skip());
    foreground = 0;
    pc_bbft_start_button(false); pc_bbft_start_button(true); assert(!pc_bbft_take_skip());
    std::puts("BBFT adapter state tests passed");
}
