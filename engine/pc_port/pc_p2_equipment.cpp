#include "pc_p2_equipment.h"
#include "gameflow.h"
#include <cstdio>

// #1232 provider validates the pinned catalog and selected campaign authority.
// Weak until that provider is linked; absence grants no equipment.
extern bool pc_p2_campaign_treasure_seen(const char*) __attribute__((weak));
extern bool pc_randomizer_original_session() __attribute__((weak));
namespace {
p2equipment::Kit kit() {
    return p2equipment::project([](const char* id) {
        return pc_randomizer_original_session && pc_randomizer_original_session()
            && pc_p2_campaign_treasure_seen && pc_p2_campaign_treasure_seen(id);
    });
}
}
bool pc_p2_equipment_has(p2equipment::Item item) { return kit().has(item); }
float pc_p2_equipment_damage(float original) { return kit().damage(original); }
float pc_p2_equipment_whistle(float original) { return kit().whistle(original); }
float pc_p2_equipment_speed(float original) { return kit().speed(original); }
unsigned pc_p2_equipment_courses() {
    return pc_randomizer_original_session && pc_randomizer_original_session() ? kit().courses() : 0;
}
void pc_p2_equipment_reconcile_courses() {
    const auto owned = kit();
    // Source openCourse(1)/(2). Wistful Wild belongs to debt/ending (#1232).
    if (owned.has(p2equipment::SphericalAtlas)) gameflow.mPlayState.openStage(1);
    if (owned.has(p2equipment::GeographicProjection)) gameflow.mPlayState.openStage(2);
}
