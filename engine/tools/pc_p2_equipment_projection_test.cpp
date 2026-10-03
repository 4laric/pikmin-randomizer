#include "pc_p2_equipment.h"
#include "gameflow.h"
#include <cassert>
#include <set>
#include <string>
EquipmentGameflow gameflow;
static bool original=false;
static std::set<std::string> accepted;
bool pc_randomizer_original_session() { return original; }
bool pc_p2_campaign_treasure_seen(const char* id) { return accepted.count(id); }
int main() {
    using namespace p2equipment;
    // Asset/fixture/AP receipts cannot turn on original campaign equipment.
    accepted={"map01","map02","key","suit_powerup","dashboots","fue_wide"};
    assert(!pc_p2_equipment_has(SphericalAtlas));
    assert(pc_p2_equipment_courses()==0);
    assert(pc_p2_equipment_damage(12)==12&&pc_p2_equipment_speed(160)==160&&pc_p2_equipment_whistle(100)==100);
    pc_p2_equipment_reconcile_courses();assert(gameflow.mPlayState.opened==1);
    original=true;
    assert(pc_p2_equipment_courses()==7);
    pc_p2_equipment_reconcile_courses();assert(gameflow.mPlayState.opened==7);
    pc_p2_equipment_reconcile_courses();assert(gameflow.mPlayState.opened==7);
    assert(!pc_p2_equipment_has(TheKey));
    assert(pc_p2_equipment_damage(12)==6&&pc_p2_equipment_speed(160)==240&&pc_p2_equipment_whistle(100)==200);
    // Actual selected-card restore replaces receipt authority. Queries must
    // immediately reflect rollback; no cached acquired bits or event replay.
    accepted.clear();gameflow.mPlayState.opened=1;
    assert(pc_p2_equipment_courses()==1);
    pc_p2_equipment_reconcile_courses();assert(gameflow.mPlayState.opened==1);
    assert(!pc_p2_equipment_has(JusticeAlloy)&&pc_p2_equipment_damage(12)==12);
    accepted={"map02","fue_b","suit_fire","fue_pullout"};
    assert(pc_p2_equipment_courses()==5);
    assert(pc_p2_equipment_has(DreamMaterial)&&pc_p2_equipment_has(ForgedCourage)&&pc_p2_equipment_has(ProfessionalNoisemaker));
    pc_p2_equipment_reconcile_courses();assert(gameflow.mPlayState.opened==5);
}
