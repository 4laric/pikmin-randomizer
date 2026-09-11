#include "pc_randomizer.h"
#include <chrono>
#include <cstdio>
#include <thread>
#include <cstring>
#undef NDEBUG
#include <cassert>
int main(int argc, char** argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    if (!pc_randomizer_init(argc, argv)) {
        if (pc_randomizer_enabled() || pc_randomizer_goal() || pc_randomizer_next_day(29) != 30) return 4;
        std::puts("standalone adapter inert"); return 0;
    }
    for (int i = 0; i < 100; ++i) {
        pc_randomizer_update();
        if (pc_randomizer_ready()) {
            bool collectionProbe = false;
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--collection-probe")) collectionProbe = true;
            if (collectionProbe) {
                assert(pc_randomizer_collection_checks());
                assert(pc_randomizer_field_capacity() == 20);
                pc_randomizer_observe_population(100, true);
                pc_randomizer_observe_total_population(500, false);
                pc_randomizer_observe_total_population(-1, true);
                assert(!pc_randomizer_checked("Population: 20 total Pikmin"));
                pc_randomizer_observe_total_population(149, true);
                assert(pc_randomizer_checked("Population: 100 total Pikmin"));
                assert(!pc_randomizer_checked("Population: 150 total Pikmin"));
                pc_randomizer_observe_total_population(500, true);
                assert(pc_randomizer_checked("Population: 500 total Pikmin"));
                assert(pc_randomizer_field_capacity() == 20);
                const int types[] = {3, 4, 18, 19, 20, 15, 30, 33};
                const char* names[] = {"Dwarf Bulborb", "Spotty Bulborb", "Female Sheargrub", "Male Sheargrub", "Shearwig", "Fiery Blowhog", "Water Dumple", "Wollywog"};
                for (int n = 0; n < 8; ++n) {
                    char name[100]; std::snprintf(name, sizeof(name), "Bestiary: Deliver %s", names[n]);
                    pc_randomizer_enemy_defeated(types[n], 1, true, true);
                    pc_randomizer_corpse_delivered(types[n], 1, false);
                    pc_randomizer_corpse_delivered(types[n], 4, true);
                    assert(!pc_randomizer_checked(name));
                    pc_randomizer_corpse_delivered(types[n], 1, true);
                    pc_randomizer_corpse_delivered(types[n], 1, true);
                    assert(pc_randomizer_checked(name));
                }
                pc_randomizer_corpse_delivered(6, 1, true);
                std::puts("COLLECTION_PASS"); return 0;
            }
            bool enemyProbe = false;
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--enemy-probe")) enemyProbe = true;
            if (enemyProbe) {
                for (int type = 0; type < 35; ++type) {
                    const int target = pc_randomizer_enemy_type(type, false);
                    assert(pc_randomizer_enemy_type(type, true) == type);
                    assert(pc_randomizer_enemy_type(target, false) == type);
                    std::printf("ENEMY_MAP %d %d\n", type, target);
                }
                return 0;
            }
            bool areaProbe = false;
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--area-probe")) areaProbe = true;
            if (areaProbe) {
                const char* areas[] = {"Pikmin: Impact Site Access", "Pikmin: Forest of Hope Access", "Pikmin: Forest Navel Access", "Pikmin: Distant Spring Access", "Pikmin: Final Trial Access"};
                const char* colors[] = {"Blue Onion", "Red Onion", "Yellow Onion"};
                const char* lands[] = {"Explore: The Impact Site - Land", "Explore: The Forest of Hope - Land", "Explore: The Forest Navel - Land", "Explore: The Distant Spring - Land", "Explore: The Final Trial - Land"};
                for (int area = 0; area < 5; ++area) {
                    assert(pc_randomizer_has(areas[area]) == (area == pc_randomizer_start_stage()));
                    pc_randomizer_observe_exploration(area, 0, 0, true, true);
                    assert(pc_randomizer_checked(lands[area]) == (area == pc_randomizer_start_stage()));
                }
                for (int color = 0; color < 3; ++color) assert(pc_randomizer_has(colors[color]) == (color == pc_randomizer_start_color()));
                if (pc_randomizer_start_stage() == 0) {
                    pc_randomizer_observe_exploration(0, 600, 0, true, true);
                    pc_randomizer_check("Pikmin: Positron Generator");
                }
                std::puts("ALL_AREA_INITIAL_PASS"); return 0;
            }
            if (pc_randomizer_expanded()) {
                assert(pc_randomizer_field_capacity() == 20);
                pc_randomizer_observe_population(19, true);
                pc_randomizer_observe_population(20, false);
                assert(!pc_randomizer_checked("Population: 20 Pikmin in the field"));
                pc_randomizer_observe_population(20, true);
                pc_randomizer_observe_population(30, true);
                assert(!pc_randomizer_checked("Population: 30 Pikmin in the field"));
                pc_randomizer_enemy_defeated(3, 1, false, true);
                pc_randomizer_enemy_defeated(3, 1, true, false);
                assert(!pc_randomizer_checked("Bestiary: Dwarf Bulborb"));
                pc_randomizer_enemy_defeated(3, 1, true, true);
                pc_randomizer_enemy_defeated(3, 1, true, true);
                pc_randomizer_enemy_defeated(6, 1, true, true); // Honeywisp is not in this catalog.
                pc_randomizer_observe_exploration(4, 800, 0, true, true); // locked area
                assert(!pc_randomizer_checked("Explore: The Final Trial - Land"));
                pc_randomizer_observe_exploration(1, 800, 0, false, true);
                pc_randomizer_observe_exploration(1, 800, 0, true, false);
                assert(!pc_randomizer_checked("Explore: The Forest of Hope - Land"));
                pc_randomizer_observe_exploration(1, 599, 0, true, true);
                assert(!pc_randomizer_checked("Explore: The Forest of Hope - Scout"));
                pc_randomizer_observe_exploration(1, 600, 0, true, true);
                std::puts("EXPANDED_INITIAL");
                for (int step = 0; step < 100; ++step) {
                    pc_randomizer_update();
                    if (pc_randomizer_field_capacity() == 100) {
                        assert(!pc_randomizer_checked("Population: 100 Pikmin in the field"));
                        pc_randomizer_observe_population(99, true);
                        assert(!pc_randomizer_checked("Population: 100 Pikmin in the field"));
                        pc_randomizer_observe_population(100, true);
                        pc_randomizer_observe_exploration(4, 600, 0, true, true);
                        assert(pc_randomizer_checked("Explore: The Final Trial - Scout"));
                        std::puts("EXPANDED_COMPLETE"); return 0;
                    }
                    std::this_thread::sleep_for(std::chrono::milliseconds(50));
                }
                return 6;
            }
            pc_randomizer_check("Pikmin: Eternal Fuel Dynamo");
            pc_randomizer_check("Pikmin: Eternal Fuel Dynamo");
            if (pc_randomizer_next_day(29) != 29 || pc_randomizer_has("Zora Tunic")) return 5;
            std::puts("standalone ready; duplicate delivery tested"); return 0;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    std::fprintf(stderr, "standalone handshake timed out\n"); return 3;
}
