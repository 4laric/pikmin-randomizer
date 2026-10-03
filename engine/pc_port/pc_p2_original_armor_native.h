#pragma once
#include "pc_p2_original_armor.h"
class BTeki;
namespace p2original { namespace armor {
class Native final:public Engine {
public:
 Native();~Native();
 Native(const Native&)=delete;Native& operator=(const Native&)=delete;
 Provider& provider(){return mProvider;}
 bool resources(const std::set<unsigned>&,std::string&) override;
 bool commonResources(const CatalogRow&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,unsigned,std::string&) override;
 bool allocate(Host&,const Position&,float,std::string&) override;
 bool bind(Host&,std::string&) override;
 bool cleanup(Host&,std::string&) override;
 void retired(Creature* p){mProvider.retired(p);}
private:
 Provider mProvider;
};
} }
void pc_p2_original_armor_retired(BTeki*);

bool pc_p2_original_armor_admitted();
