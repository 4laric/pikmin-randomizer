#pragma once
#include "pc_p2_original_group.h"
#include <map>
#include <set>
namespace p2original { namespace catfish {
// Retail genEnemy.cpp creates EnemyGeneratorBase for IDs 24/25;
// gameGenerator.h gives it version '????', an empty tail and null initArg.
bool decode(const CatalogRow&,std::string&);
const char* species(unsigned source);
int nativeType(unsigned source);
struct Host { CatalogRow row; Generator* generator=nullptr; Creature* actor=nullptr; unsigned ordinal=0,token=0; };
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool resources(const CatalogRow&,std::string&)=0;
 virtual bool reserve(const std::vector<CatalogRow>&,unsigned,std::string&)=0;
 virtual bool allocate(Host&,const Position&,float,std::string&)=0;
 virtual bool bind(Host&,std::string&)=0;
 virtual bool cleanup(Host&,std::string&)=0;
};
class Provider final:public GroupProvider {
public:
 explicit Provider(Engine& engine):mEngine(engine){}
 ~Provider()override;
 bool preflight(const std::vector<CatalogRow>&,std::string&)override;
 bool reserve(const std::vector<CatalogRow>&,std::string&)override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&)override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&)override;
 bool release(Creature*,unsigned,std::string&)override;
 // Called by the native forget funnel before address reuse, without killing.
 void retired(Creature* actor){mHosts.erase(actor);}
 Host* lookup(Creature* actor){auto i=mHosts.find(actor);return i==mHosts.end()?nullptr:&i->second;}
 bool prepared()const{return mPrepared;}
private:
 Engine& mEngine;std::map<unsigned,CatalogRow> mRows;
 std::map<unsigned,unsigned> mRemaining;std::map<Creature*,Host> mHosts;
 std::map<unsigned,std::set<unsigned>> mAttempts;
 bool mPrepared=false,mReserved=false;
};
} }
