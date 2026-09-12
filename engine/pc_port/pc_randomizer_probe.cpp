#include "pc_randomizer.h"
#include "pc_randomizer_catalog.h"
#include <chrono>
#include <cstdio>
#include <thread>
#include <cstring>
#include "pc_randomizer_spawn_catalog.h"
#include "pc_randomizer_campaign_catalog.h"
#undef NDEBUG
#include <cassert>
int main(int argc, char** argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    if (!pc_randomizer_init(argc, argv)) {
        if (pc_randomizer_enabled() || pc_randomizer_goal() || pc_randomizer_next_day(29) != 30) return 4;
        std::puts("standalone adapter inert"); return 0;
    }
    for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--campaign-probe")) {
        int objects[72] = {};
        for (int i=71; i>=0; --i) {
            const auto& row = randomizerCampaignSlots[i];
            pc_randomizer_set_generator_id(&objects[i], row.uid);
            std::printf("CAMPAIGN_PROBE %u %d\n", row.uid, pc_randomizer_enemy_for_generator(row.original, false, &objects[i]));
        }
        for (const auto& row : randomizerSpawnSlots) {
            bool eligible = false;
            for (const auto& candidate : randomizerCampaignSlots) if (candidate.uid == row.uid) eligible = true;
            if (eligible) continue;
            int object; pc_randomizer_set_generator_id(&object, row.uid);
            assert(pc_randomizer_enemy_for_generator(row.species, true, &object) == row.species);
        }
        return 0;
    }
    for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--capacity-probe")) {
        std::printf("CAPACITY_PROBE %d\n", pc_randomizer_field_capacity());
        return 0;
    }
    for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--group-probe")) {
        assert(pc_randomizer_group_slots());
        int objects[12] = {};
        for (int i=11; i>=0; --i) {
            pc_randomizer_set_generator_id(&objects[i], randomizerGroupSlots[i]);
            const int original = randomizerGroupOriginals[i];
            const int actual = pc_randomizer_enemy_for_generator(original, false, &objects[i]);
            assert(pc_randomizer_enemy_for_generator(original, true, &objects[i]) == original);
            std::printf("GROUP_PROBE %u %d\n", randomizerGroupSlots[i], actual);
        }
        return 0;
    }
    for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--slot-probe")) {
        assert(pc_randomizer_spawn_slots());
        int objects[15] = {}, restored[15] = {};
        for (int i = 14; i >= 0; --i) {
            const RandomizerSpawnSlot* source = nullptr;
            for (const auto& row : randomizerSpawnSlots) if (row.uid == randomizerAdultSlots[i]) source = &row;
            assert(source);
            pc_randomizer_bind_generator(&objects[i], source->stage, source->file, source->offset);
            assert(pc_randomizer_generator_id(&objects[i]) == source->uid);
            pc_randomizer_set_generator_id(&restored[i], pc_randomizer_generator_id(&objects[i]));
            const int actual = pc_randomizer_enemy_for_generator(source->species, false, &objects[i]);
            assert(pc_randomizer_enemy_for_generator(source->species, false, &restored[i]) == actual);
            assert(pc_randomizer_enemy_for_generator(3, false, &objects[i]) == 3);
            std::printf("SLOT_PROBE %u %d\n", source->uid, actual);
            pc_randomizer_set_generator_id(&objects[i], 0);
            assert(pc_randomizer_generator_id(&objects[i]) == 0);
        }
        return 0;
    }
    for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--stats-probe")) {
        for (int color = 0; color < 3; ++color)
            std::printf("STATS_PROBE %d %.0f %.0f %.0f %d\n", color,
                100 * pc_randomizer_color_multiplier(color, PC_PIKI_DAMAGE),
                100 * pc_randomizer_color_multiplier(color, PC_PIKI_MOVEMENT),
                100 * pc_randomizer_color_multiplier(color, PC_PIKI_ATTACK_RATE), pc_randomizer_carry_strength(color));
        return 0;
    }
    for (int i = 0; i < 100; ++i) {
        pc_randomizer_update();
        if (pc_randomizer_ready()) {
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--retired-stick-probe")) {
                for (const auto& obstacle : randomizerObstacles)
                    for (int dx = -1; dx <= 1; ++dx)
                        for (int dz = -1; dz <= 1; ++dz)
                            pc_randomizer_observe_obstacle(obstacle.stage, obstacle.kind, float(obstacle.x + dx), float(obstacle.z + dz), true, true);
                std::puts("RETIRED_STICK_PASS");
                return 0;
            }
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--emperor-probe")) {
                const bool unlocked = pc_randomizer_repairs() == 25;
                assert(pc_randomizer_emperor_available() == unlocked);
                pc_randomizer_emperor_defeated();
                assert(pc_randomizer_goal() == unlocked);
                std::puts("EMPEROR_PASS");
                return 0;
            }
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--benefit-probe")) {
                char saved[32768] = {};
                if (pc_randomizer_resumed()) {
                    assert(pc_randomizer_load_campaign(saved));
                    assert(saved[123] == 42);
                }
                int used = 0;
                for (int kind = 0; kind < 3; ++kind)
                    while (pc_randomizer_consume_benefit(static_cast<PcBenefit>(kind))) ++used;
                while (pc_randomizer_consume_benefit(PC_BENEFIT_BOMBS)) ++used;
                while (pc_randomizer_consume_benefit(PC_BENEFIT_BOMB_TRAP)) ++used;
                while (pc_randomizer_consume_benefit(PC_BENEFIT_PROGG)) ++used;
                assert(!pc_randomizer_consume_benefit(PC_BENEFIT_WHISTLE));
                std::printf("CAPTAIN_MOVE %.2f\n", pc_randomizer_captain_movement_multiplier());
                std::printf("BENEFIT_PROBE used=%d whistle=%.2f pluck=%.2f\n", used,
                    pc_randomizer_benefit_multiplier(PC_BENEFIT_WHISTLE), pc_randomizer_benefit_multiplier(PC_BENEFIT_PLUCK));
                for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--save-probe")) {
                    saved[123] = 42;
                    pc_randomizer_save_campaign(saved);
                }
                return 0;
            }
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--color-population-probe")) {
                const char* colors[] = {"Blue", "Red", "Yellow"};
                const char* onions[] = {"Blue Onion", "Red Onion", "Yellow Onion"};
                pc_randomizer_observe_total_population(1500, true);
                pc_randomizer_observe_population(100, true);
                pc_randomizer_observe_color_population(-1, 500, true);
                pc_randomizer_observe_color_population(3, 500, true);
                for (int color = 0; color < 3; ++color) {
                    char low[80], high[80];
                    std::snprintf(low, sizeof(low), "Population: 10 total %s Pikmin", colors[color]);
                    std::snprintf(high, sizeof(high), "Population: 100 total %s Pikmin", colors[color]);
                    pc_randomizer_observe_color_population(color, 500, false);
                    pc_randomizer_observe_color_population(color, -1, true);
                    pc_randomizer_observe_color_population(color, 9, true);
                    assert(!pc_randomizer_checked(low));
                    pc_randomizer_observe_color_population(color, 10, true);
                    assert(pc_randomizer_checked(low) == pc_randomizer_has(onions[color]));
                    assert(!pc_randomizer_checked(high));
                    pc_randomizer_observe_color_population(color, 500, true);
                    pc_randomizer_observe_color_population(color, 500, true);
                    assert(pc_randomizer_checked(high) == pc_randomizer_has(onions[color]));
                }
                std::puts("COLOR_POPULATION_PASS"); return 0;
            }
            bool modernProbe = false;
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--bestiary-probe")) modernProbe = true;
            if (modernProbe) {
                const int types[] = {3, 4, 18, 19, 20, 15, 30, 33};
                const char* names[] = {"Dwarf Bulborb", "Spotty Bulborb", "Female Sheargrub", "Male Sheargrub", "Shearwig", "Fiery Blowhog", "Water Dumple", "Wollywog"};
                for (int n = 0; n < 8; ++n) {
                    char name[100]; std::snprintf(name, sizeof(name), "Bestiary: Deliver %s", names[n]);
                    pc_randomizer_corpse_delivered(types[n], 1, true);
                    pc_randomizer_corpse_delivered(types[n], 1, true);
                    assert(pc_randomizer_checked(name));
                }
                // In shifted catalogs the old index incorrectly awarded this.
                assert(!pc_randomizer_checked("Bestiary: Deliver Wogpole"));
                for (const auto& entry : randomizerNewBestiary) {
                    pc_randomizer_corpse_delivered(entry.type, 1, false);
                    pc_randomizer_corpse_delivered(entry.type, 4, true);
                    pc_randomizer_enemy_defeated(entry.type, 1, false, true);
                    pc_randomizer_enemy_defeated(entry.type, 1, true, false);
                    assert(!pc_randomizer_checked(entry.name));
                    if (entry.type == 16) {
                        pc_randomizer_corpse_delivered(entry.type, 1, true);
                        assert(!pc_randomizer_checked(entry.name));
                        pc_randomizer_enemy_defeated(entry.type, 1, true, true);
                    } else {
                        pc_randomizer_enemy_defeated(entry.type, 1, true, true);
                        assert(!pc_randomizer_checked(entry.name));
                        pc_randomizer_corpse_delivered(entry.type, 1, true);
                        pc_randomizer_corpse_delivered(entry.type, 1, true);
                    }
                    assert(pc_randomizer_checked(entry.name));
                }
                pc_randomizer_observe_exploration(1, 9999, 9999, true, true);
                assert(!pc_randomizer_checked("Explore: The Forest of Hope - Land"));
                assert(!pc_randomizer_checked("Explore: The Forest of Hope - Scout"));
                std::puts("BESTIARY_PASS"); return 0;
            }
            bool permanentProbe = false;
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--permanent-probe")) permanentProbe = true;
            if (permanentProbe) {
                assert(pc_randomizer_checked("Population: 450 total Pikmin")); // restored index above 63
                pc_randomizer_observe_total_population(500, false);
                assert(!pc_randomizer_checked("Population: 350 total Pikmin"));
                pc_randomizer_observe_total_population(500, true);
                for (int value : randomizerFinePopulation) {
                    char name[80]; std::snprintf(name, sizeof(name), "Population: %d total Pikmin", value);
                    assert(pc_randomizer_checked(name));
                }
                for (const auto& o : randomizerObstacles) {
                    assert(!pc_randomizer_checked(o.name));
                    pc_randomizer_observe_obstacle(o.stage, o.kind, o.x, o.z, false, true);
                    pc_randomizer_observe_obstacle(o.stage, o.kind, o.x, o.z, true, false);
                    pc_randomizer_observe_obstacle(o.stage, o.kind, o.x+20, o.z, true, true);
                    assert(!pc_randomizer_checked(o.name));
                    pc_randomizer_observe_obstacle(o.stage, o.kind, o.x, o.z, true, true);
                    assert(pc_randomizer_checked(o.name));
                    pc_randomizer_observe_obstacle(o.stage, o.kind, o.x, o.z, true, true);
                }
                std::puts("PERMANENT_PASS"); return 0;
            }
            bool upgradeProbe = false;
            for (int arg = 1; arg < argc; ++arg) if (!std::strcmp(argv[arg], "--upgrade-probe")) upgradeProbe = true;
            if (upgradeProbe) {
                for (int color = 0; color < 3; ++color)
                    std::printf("LIVE_STATS %d %.0f %.0f %.0f %d\n", color,
                        100 * pc_randomizer_color_multiplier(color, PC_PIKI_DAMAGE),
                        100 * pc_randomizer_color_multiplier(color, PC_PIKI_MOVEMENT),
                        100 * pc_randomizer_color_multiplier(color, PC_PIKI_ATTACK_RATE), pc_randomizer_carry_strength(color));
                if (pc_randomizer_goal()) return 0;
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }
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
