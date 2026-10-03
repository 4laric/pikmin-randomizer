#pragma once
#include "pc_p2_original_bridge.h"
#include "Generator.h"
class Bridge;
class WorkObject;
class Piki;
struct PcOriginalBridgeLink {
 std::string identity;
 std::array<float,3> position{};
 int stage=0; // Retail mCurrStageIdx; increments only after 40 update ticks.
};
std::vector<PcOriginalBridgeLink> pc_p2_original_bridge_links();
bool pc_p2_original_bridge_stage(const std::string&,int&);
bool pc_p2_original_bridge_snapshot(const Creature*,p2original::BridgeState&,std::string& identity);
bool pc_p2_original_bridge_owned(const Creature*);
float pc_p2_original_bridge_work_damage(Piki*);
bool pc_p2_original_bridge_stage_position(const Bridge*,int,Vector3f&);
bool pc_p2_original_bridge_stage_finished(const Bridge*,int,bool&);
bool pc_p2_original_bridge_install(const std::vector<p2original::BridgeRecord>&,std::string&);
void pc_p2_original_bridge_before_teardown(); // after course cache save, before managers/heaps reset
void pc_p2_original_bridge_unload(); // only after before_teardown and physical stage heap teardown
void pc_p2_original_bridge_register();
bool pc_p2_original_bridge_preflight(const std::vector<Generator*>&,std::string&);
bool pc_p2_original_bridge_generator_init(Generator*,bool& handled,std::string&);
bool pc_p2_original_bridge_generator_load(Generator*,RandomAccessStream&,bool& handled,std::string&);
struct GenObjectOriginalBridge final:GenObject {
 GenObjectOriginalBridge();
 void doRead(RandomAccessStream&)override;
 void doWrite(RandomAccessStream&)override;
 void ramLoadParameters(RandomAccessStream&)override;
 void ramSaveParameters(RandomAccessStream&)override;
 void updateUseList(Generator*,int)override;
 Creature* birth(BirthInfo&)override;
 unsigned uid=0;
};
