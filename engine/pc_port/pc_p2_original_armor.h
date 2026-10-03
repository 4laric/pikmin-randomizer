#pragma once
#include "pc_p2_original_group.h"
#include <set>
namespace p2original { namespace armor {
// Retail Armor inherits EnemyGeneratorBase's ????/empty payload.
// This first adapter admits ordinary ground births. Size remains the common
// pair-separation spacing consumed by planSpawns (genEnemy.cpp:130-136).
bool admits(const CatalogRow&,std::string&);
struct Host { CatalogRow row; Generator* generator=nullptr; Creature* actor=nullptr; unsigned ordinal=0,token=0; };
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool resources(const std::set<unsigned>&,std::string&)=0;
 virtual bool commonResources(const CatalogRow&,std::string&)=0;
 virtual bool reserve(const std::vector<CatalogRow>&,unsigned,std::string&)=0;
 virtual bool allocate(Host&,const Position&,float,std::string&)=0;
 virtual bool bind(Host&,std::string&)=0;
 virtual bool cleanup(Host&,std::string&)=0;
};
class Provider final:public GroupProvider {
public:
 explicit Provider(Engine& engine):mEngine(engine){}
 bool preflight(const std::vector<CatalogRow>&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,std::string&) override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&) override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&) override;
 bool release(Creature*,unsigned,std::string&) override;
 void retired(Creature*);
 bool owns(Creature* p)const{return mHosts.count(p)!=0;}
 bool prepared()const{return mPrepared;}
 std::size_t size()const{return mHosts.size();}
private:
 Engine& mEngine;std::map<unsigned,CatalogRow> mRows;
 std::map<unsigned,std::set<unsigned>> mBorn;
 std::map<unsigned,unsigned> mRemaining;std::map<Creature*,Host> mHosts;
 bool mPrepared=false,mReserved=false;
};
} }
