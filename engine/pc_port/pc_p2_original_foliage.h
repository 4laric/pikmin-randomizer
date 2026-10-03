#pragma once
#include "pc_p2_original_group.h"
#include <memory>
namespace p2original { namespace foliage {
// Literal Plants::Obj sources. Additional variants require their own resource
// admission; specialised touched() behaviour is never flattened into this set.
bool supported(unsigned);
bool decode(const CatalogRow&,std::string&);
// Authentication of a genuine cave TekiInfo association, never GenEnemy.
bool caveDecode(const CatalogRow&,std::string&);
struct Resources { bool model=false,clip=false,collider=false; float health=0; unsigned duration=0; bool sentinelFactory=false; };
struct Host {
 Creature* creature=nullptr; Generator* generator=nullptr; CatalogRow row;
 Position position; unsigned ordinal=0,token=0; float frame=0; bool active=false,touched=false;
};
class Engine {
public:
 virtual ~Engine()=default;
 virtual bool resources(unsigned,Resources&,std::string&)=0;
 virtual bool reserve(unsigned,std::string&)=0;
 virtual bool allocate(Host&,const Position&,float,std::string&)=0;
 virtual bool cleanup(Host&,std::string&)=0;
 virtual bool touchSound(Host&,Creature*,std::string&)=0;
 // Retail virtual touched(), after motion reset and before becoming active.
 // Quake has no contact collider. Plain admitted species require no effect.
 virtual bool touched(Host&,Creature*,std::string&){return true;}
};
class Provider final:public GroupProvider {
public:
 explicit Provider(Engine& e):mEngine(e){}
 bool preflight(const std::vector<CatalogRow>&,std::string&) override;
 bool reserve(const std::vector<CatalogRow>&,std::string&) override;
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*&,std::string&) override;
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&) override;
 bool release(Creature*,unsigned,std::string&) override;
 // Caller owns the cave registry/generator association and retires it after
 // release. The association Generator is never attached to the native actor.
 bool cavePrepare(const std::vector<CatalogRow>&,std::string&);
 bool caveReserve(const std::vector<CatalogRow>&,std::string&);
 bool caveBirth(const CatalogRow&,Generator* associationGenerator,unsigned,const Position&,float,Creature*&,std::string&);
 Host* lookup(Creature*);
 const Host* lookup(const Creature*)const;
 bool tick(Creature*,float,bool visible,std::string&);
 bool collision(Creature*,Creature* collider,bool isNavi,bool isTeki,float y,float vx,float vz,bool visible,std::string&);
 bool earthquake(Creature*,std::string&);
 std::size_t size()const{return mHosts.size();}
private:
 bool prepare(const std::vector<CatalogRow>&,bool cave,std::string&);
 bool reserveMode(const std::vector<CatalogRow>&,bool cave,std::string&);
 bool birthMode(const CatalogRow&,Generator*,unsigned,const Position&,float,bool cave,Creature*&,std::string&);
 bool activate(Host&,Creature*,std::string&);
 Engine& mEngine; bool mPrepared=false,mReserved=false,mCave=false;
 std::map<unsigned,CatalogRow> mAdmitted;
 std::map<unsigned,unsigned> mRemaining;
 std::map<unsigned,Resources> mResources;
 std::map<Creature*,std::unique_ptr<Host>> mHosts;
 std::set<std::pair<unsigned,unsigned>> mUsedCaveOrdinals;
 std::set<unsigned> mUsedCaveTokens;
};
} }

