#pragma once
#include "pc_p2_original_barrel.h"
#include "Generator.h"
class Piki;
bool pc_p2_original_barrel_install(const std::vector<p2original::BarrelRecord>&,std::string&);
void pc_p2_original_barrel_unload();
// Post ItemMgr node iteration: retire completed barrels without skipping siblings.
void pc_p2_original_barrel_finish_updates();
// After course cache save, before destroying the stage heap/managers. Handles
// dying bodies which native killAll skips because they are already not alive.
void pc_p2_original_barrel_before_teardown();
void pc_p2_original_barrel_register();
bool pc_p2_original_barrel_preflight(const std::vector<Generator*>&,std::string&);
bool pc_p2_original_barrel_owned(const Creature*);
float pc_p2_original_barrel_work_damage(Piki*);
bool pc_p2_original_barrel_snapshot(const Creature*,p2original::BarrelState&,std::string&);
bool pc_p2_original_barrel_generator_init(Generator*,bool& handled,std::string&);
bool pc_p2_original_barrel_generator_load(Generator*,RandomAccessStream&,bool& handled,std::string&);
struct GenObjectOriginalBarrel final:GenObject {
 GenObjectOriginalBarrel();
 void doRead(RandomAccessStream&)override;
 void doWrite(RandomAccessStream&)override;
 void ramLoadParameters(RandomAccessStream&)override;
 void ramSaveParameters(RandomAccessStream&)override;
 void updateUseList(Generator*,int)override;
 Creature* birth(BirthInfo&)override;
 unsigned uid=0;
};
