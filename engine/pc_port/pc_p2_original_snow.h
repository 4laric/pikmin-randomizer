#pragma once
#include "pc_p2_original_group.h"
namespace p2original { namespace snow {
bool capability(const CatalogRow&,std::string&);
// Surface YellowKochappy inherits EnemyGeneratorBase: ???? and no species tail.
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool prepare(const std::vector<CatalogRow>&,std::string&)=0;
 virtual bool reserve(unsigned,std::string&)=0;
 virtual bool allocate(const CatalogRow&,Generator*,const Position&,float,Creature*&,std::string&)=0;
 virtual bool attach(const CatalogRow&,Creature*,unsigned ordinal,unsigned token,std::string&)=0;
 virtual bool destroy(Creature*,std::string&)=0;
};
class Provider final:public GroupProvider {
public:
 explicit Provider(Engine& engine):mEngine(engine){}
 bool preflight(const std::vector<CatalogRow>&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,std::string&) override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&) override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&) override;
 bool release(Creature*,unsigned,std::string&) override;
 void retired(Creature* actor){mHosts.erase(actor);}
 bool owns(Creature* actor)const{return mHosts.count(actor)!=0;}
 std::size_t size()const{return mHosts.size();}
private:
 struct Host {CatalogRow row;unsigned ordinal=0,token=0;};
 Engine& mEngine;std::map<unsigned,CatalogRow> mRows;
 std::map<unsigned,std::set<unsigned>> mBorn;
 std::map<Creature*,Host> mHosts;bool mPrepared=false,mReserved=false;
};
} }
