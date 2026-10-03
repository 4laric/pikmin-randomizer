#pragma once
#include "pc_p2_original_cave.h"
#include "Generator.h"
class Graphics;
bool pc_p2_original_cave_install(const std::vector<p2original::CaveRecord>&,std::string&);
void pc_p2_original_cave_register();
bool pc_p2_original_cave_preflight(const std::vector<Generator*>&,std::string&);
bool pc_p2_original_cave_generator_init(Generator*,bool& handled,std::string&);
bool pc_p2_original_cave_generator_load(Generator*,RandomAccessStream&,bool& handled,std::string&);
void pc_p2_original_cave_draw(Graphics&);
void pc_p2_original_cave_unload(); // clear bindings AFTER stage heap disposal
bool pc_p2_original_cave_identity(const Creature*,p2original::CaveRecord&);
// Presentation/cache only. Activation requires the distinct retail SAVE seam.
struct GenObjectOriginalCave final:GenObject {
    GenObjectOriginalCave();
    void doRead(RandomAccessStream&)override;
    void doWrite(RandomAccessStream&)override;
    void ramLoadParameters(RandomAccessStream&)override;
    void ramSaveParameters(RandomAccessStream&)override;
    void updateUseList(Generator*,int)override {}
    Creature* birth(BirthInfo&)override;
    unsigned uid=0;
};
