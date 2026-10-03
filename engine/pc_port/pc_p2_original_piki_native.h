#pragma once
#include "Generator.h"
#include <map>
#include "pc_p2_original_piki_manifest.h"
// active UIDs come from the complete selected native calendar census. The
// immutable manifest includes inactive members and is never narrowed here.
bool pc_p2_original_piki_install(const p2original::PikiManifest&,const std::vector<unsigned>& active,std::string&,const std::map<unsigned,int>& effectiveExpiry={});
bool pc_p2_original_piki_preflight(const std::vector<Generator*>&,std::string&);
bool pc_p2_original_piki_generator_init(Generator*,bool& handled,std::string&);
void pc_p2_original_piki_unload();
void pc_p2_original_piki_register();
struct GenObjectOriginalPiki final:GenObject {
 GenObjectOriginalPiki();
 void doRead(RandomAccessStream&)override;
 void doWrite(RandomAccessStream&)override;
 void ramLoadParameters(RandomAccessStream&)override;
 void ramSaveParameters(RandomAccessStream&)override;
 Creature* birth(BirthInfo&)override;
 unsigned uid=0;
};
