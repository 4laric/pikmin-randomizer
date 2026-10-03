#include "pc_p2_original_dispatch.h"
#include <iostream>
#include <stdexcept>
using namespace p2original;
unsigned checks=0;
void check(bool b){++checks;if(!b)throw std::runtime_error("dispatch control "+std::to_string(checks));}
struct Family:GroupProvider {
 unsigned source=0,preflights=0,reserves=0,births=0,binds=0,releases=0;
 bool resourceOK=true,capacityOK=true,birthOK=true,releaseOK=true;
 int storage=0;std::function<void(Creature*)> onRelease;
 bool preflight(const std::vector<CatalogRow>& rows,std::string&)override{++preflights;for(const auto& r:rows)check(r.enemy.source==source||(source==0&&r.enemy.source==1));return resourceOK;}
 bool reserve(const std::vector<CatalogRow>& rows,std::string&)override{++reserves;for(const auto& r:rows)check(r.enemy.source==source||(source==0&&r.enemy.source==1));return capacityOK;}
 bool birth(const CatalogRow&,Generator*,unsigned,const Position&,float,Creature*& out,std::string&)override{++births;out=reinterpret_cast<Creature*>(&storage);return birthOK;}
 bool bind(const CatalogRow&,Creature*,unsigned,std::string&)override{++binds;return true;}
 bool release(Creature* c,unsigned,std::string&)override{++releases;if(!releaseOK)return false;if(onRelease)onRelease(c);return true;}
};
CatalogRow row(unsigned source,unsigned index){CatalogRow r;r.course="tutorial";r.member="defaultgen.txt";r.index=index;r.sourceKey="tutorial/defaultgen.txt#"+std::to_string(index);r.enemy.uid=originalGeneratorUid(r.sourceKey);r.enemy.source=source;r.enemy.count=1;return r;}
int main(){
 std::string e;Dispatch d;Family a,b;b.source=21;
 auto capability=[](const CatalogRow& r,std::string&){return r.enemy.generatorTail.empty();};
 check(d.add(0,a,capability,e));check(!d.add(0,b,capability,e));check(d.add(1,a,capability,e));check(d.add(21,b,capability,e));
 auto x=row(0,0),y=row(21,1),unknown=row(99,2);std::vector<CatalogRow> rows{x,y};
 check(!d.preflight({x,unknown},e));check(e.find("99")!=std::string::npos);check(a.preflights==0&&b.preflights==0&&a.births==0);
 auto bad=y;bad.enemy.generatorTail={"unadmitted"};check(!d.preflight({x,bad},e));check(a.preflights==0&&b.preflights==0);
 bad=y;bad.enemy.uid=x.enemy.uid;check(!d.preflight({x,bad},e));check(a.preflights==0);
 b.resourceOK=false;check(!d.preflight(rows,e));check(a.reserves==0&&b.reserves==0);
 b.resourceOK=true;check(d.preflight(rows,e));check(!d.add(2,a,capability,e));
 bad=y;bad.enemy.position.x=1;check(!d.reserve({x,bad},e));check(a.reserves==0&&b.reserves==0);
 check(!d.reserve({x,x},e));check(!d.reserve({x},e));check(d.reserve({y,x},e));check(!d.reserve(rows,e));
 Creature* actor=nullptr;check(!d.birth(bad,nullptr,0,{},0,actor,e));check(actor==nullptr&&a.births==0&&b.births==0);
 check(d.birth(x,nullptr,0,{},0,actor,e));check(actor==reinterpret_cast<Creature*>(&a.storage)&&a.births==1&&b.births==0);
 check(!d.bind(y,actor,1,e));check(d.bind(x,actor,1,e));check(a.binds==1&&b.binds==0);
 check(!d.preflight(rows,e));a.releaseOK=false;check(!d.release(actor,1,e));check(!d.preflight(rows,e));
 a.releaseOK=true;a.onRelease=[&](Creature* c){d.retired(c);};check(d.release(actor,1,e));check(!d.release(actor,1,e));
 // A failed family birth returning an owned body remains releasable.
 b.birthOK=false;check(!d.birth(y,nullptr,0,{},0,actor,e));check(actor!=nullptr);check(d.release(actor,0,e));check(b.releases==1);
 check(d.preflight(rows,e));b.capacityOK=false;check(!d.reserve(rows,e));check(!d.birth(x,nullptr,0,{},0,actor,e));
 // Fresh admission resets prior partial resource reservations without births.
 b.capacityOK=true;check(d.preflight(rows,e));check(d.reserve(rows,e));check(d.birth(y,nullptr,0,{},0,actor,e)==false);check(d.release(actor,0,e));
 const unsigned beforeA=a.preflights,beforeR=a.reserves;auto variant=row(1,2);
 check(d.preflight({variant,y,x},e));check(a.preflights==beforeA+1);check(d.reserve({x,y,variant},e));check(a.reserves==beforeR+1);
 const unsigned emptyPreflights=a.preflights+b.preflights,emptyReserves=a.reserves+b.reserves;
 check(d.preflight({},e));check(!d.reserve({x},e));check(d.reserve({},e));check(!d.reserve({},e));
 check(!d.birth(x,nullptr,0,{},0,actor,e)&&actor==nullptr);
 check(a.preflights+b.preflights==emptyPreflights&&a.reserves+b.reserves==emptyReserves);
 check(d.preflight(rows,e)&&d.reserve(rows,e));
 std::cout<<"PASS original full-inventory dispatcher "<<checks<<" controls\n";
}
