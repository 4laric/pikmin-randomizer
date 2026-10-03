#pragma once
#include "pc_p2_original_chappy.h"
class BTeki;
namespace p2original { namespace chappy {
class Native final:public Engine {
public:
 Native();~Native();
 Native(const Native&)=delete;Native& operator=(const Native&)=delete;
 Provider& provider(){return mProvider;}
 bool resources(const std::set<unsigned>&,std::string&) override;
 bool commonResources(const CatalogRow&,std::string&) override;
 bool reserve(unsigned,std::string&) override;
 bool allocate(Host&,const Position&,float,std::string&) override;
 bool bind(Host&,std::string&) override;
 bool cleanup(Host&,std::string&) override;
 void retired(Creature* p){mProvider.retired(p);}
private:
 Provider mProvider;
};
} }
void pc_p2_original_chappy_retired(BTeki*);
