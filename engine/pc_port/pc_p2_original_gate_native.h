#pragma once
#include "pc_p2_original_gate.h"
#include "Generator.h"
struct BuildingItem;
struct Piki;
bool pc_p2_original_gate_install(const std::vector<p2original::GateRecord>&,std::string&);
void pc_p2_original_gate_unload(); // after stage heap disposal
void pc_p2_original_gate_register();
bool pc_p2_original_gate_preflight(const std::vector<Generator*>&,std::string&);
bool pc_p2_original_gate_generator_init(Generator*,bool& handled,std::string&);
bool pc_p2_original_gate_generator_load(Generator*,RandomAccessStream&,bool& handled,std::string&);
bool pc_p2_original_gate_owned(const Creature*);
float pc_p2_original_gate_work_damage(Piki*);
bool pc_p2_original_gate_damage(BuildingItem*,float,bool& handled);
bool pc_p2_original_gate_save(BuildingItem*,RandomAccessStream&,bool& handled,std::string&);
bool pc_p2_original_gate_load(BuildingItem*,RandomAccessStream&,bool& handled,std::string&);
bool pc_p2_original_gate_forget(BuildingItem*); // unlinks only owned node-list bodies
bool pc_p2_original_gate_snapshot(const Creature*,p2original::GateState&,std::string& identity);
struct PcOriginalGateLink {
 std::string identity;
 std::array<float,3> position{};
 bool alive=false;
};
// Actual active source gates in physical birth order. No P1/AP items.
std::vector<PcOriginalGateLink> pc_p2_original_gate_links();
bool pc_p2_original_gate_alive(const std::string& identity,bool& alive);
struct GenObjectOriginalGate final:GenObject {
 GenObjectOriginalGate();
 void doRead(RandomAccessStream&)override;
 void doWrite(RandomAccessStream&)override;
 void ramLoadParameters(RandomAccessStream&)override;
 void ramSaveParameters(RandomAccessStream&)override;
 void updateUseList(Generator*,int)override;
 Creature* birth(BirthInfo&)override;
 unsigned uid=0;
};
