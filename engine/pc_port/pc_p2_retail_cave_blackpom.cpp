#include "pc_p2_retail_cave_blackpom.h"
#include "Pom.h"
namespace p2retail {
bool verifyBlackPomBirth(const Snapshot& floor,const FloorIdentityAuthority& authority,
                         const Pom* actor,unsigned token,const p2original::InstanceIdentity& supplied,
                         BirthIdentity& out,std::string& error){
 auto fail=[&](const char* reason){error=reason;return false;};
 auto* native=p2original::blackpom::Native::owner(actor);
 if(!native||!native->owns(actor)||!token||!floor.inCave)return fail("retail bud is not an actual owned source root");
 auto& registry=p2original::originalActors();unsigned source=0,actualToken=0;p2original::InstanceIdentity actual;
 if(!registry.query(actor,source,actualToken,&actual)||source!=6||actualToken!=token||!(actual==supplied)||
    actual.catalog!=floor.scene.layoutSha256||registry.fingerprint()!=floor.scene.layoutSha256)
  return fail("retail bud actual source association differs");
 const auto* row=registry.find(actual.generator);const auto* cave=descriptor(floor.cave);
 if(!row||!cave||row->sourceForm!=p2original::SourceForm::CaveTekiInfo||row->enemy.source!=6||
    row->course!=floor.cave||row->member!=floor.source||row->caveSourceSha256!=floor.sourceSha256||
    row->caveFloor!=floor.floor||floor.source!=cave->source||floor.sourceSha256!=cave->sourceSha256||
    floor.catalogSha256!=cave->catalogSha256||floor.maxFloor!=cave->maxFloor)
  return fail("retail bud selected descriptor differs");
 const auto* definitionRow=definition(*cave,floor.floor);
 if(!definitionRow||row->caveRow>=definitionRow->rows.size())return fail("retail bud definition row differs");
 BirthIdentity expected;
 if(!authority.expectedBirth(*cave,floor.floor,floor.scene,row->caveRow,actual.ordinal,expected,error))return false;
 if(expected.row!=row->caveRow||expected.ordinal!=actual.ordinal||expected.epoch!=actual.epoch||
    expected.activation!=actual.activation||
    expected.instance!=instanceKey(*cave,floor.floor,definitionRow->rows[row->caveRow],actual.ordinal))return fail("retail bud independent selected birth differs");
 out=std::move(expected);error.clear();return true;
}
bool bindBlackPom(NativeFloor& floor,p2original::blackpom::Native& native,
                  BlackPomPopulation population,BlackPomConsumer consumer,std::string& error){
 if(!population||!consumer){error="retail BlackPom actual population/consumer unavailable";return false;}
 FamilyOps ops;
 ops.prepare=[&native](const std::vector<p2original::CatalogRow>& rows,std::string& e){
  unsigned count=0;for(const auto& row:rows)count+=row.enemy.count;return native.prepare(count,e);
 };
 ops.birth=[&native,population](const p2original::CatalogRow& row,const Snapshot& floor,
          Generator* generator,unsigned,const Vector3f& p,float yaw,Creature*& actor,bool& suppressed,std::string& e){
  p2original::blackpom::BirthContext context;
  if(!population(floor,context,e))return false;
  if(!context.section||context.inCave!=floor.inCave||context.story!=floor.story||context.cave!=floor.cave||
     context.floorIndex!=floor.floor-1||row.caveFloor!=floor.floor){
   e="retail BlackPom physical population scene differs";return false;
  }
  Pom* pom=nullptr;bool born=native.birth(generator,p,yaw,context,pom,suppressed,e);actor=pom;return born;
 };
 ops.bind=[&native](const p2original::CatalogRow&,Creature* actor,unsigned token,std::string& e){
  return native.bind(static_cast<Pom*>(actor),token,e);
 };
 ops.release=[&native](Creature* actor,unsigned,std::string& e){return native.release(static_cast<Pom*>(actor),e);};
 ops.cancel=[&native](std::string& e){return native.cancel(e);};ops.retireBeforeRelease=true;
 // Natural beforeKill already calls floor retirement then leaf nativeRetired.
 // Explicit Native.release takes its own cleanup path and bypasses onDeath.
 ops.retired=[](Creature*,std::string& e){e.clear();return true;};
 if(!floor.family(6,std::move(ops),error))return false;
 native.onDeath([&floor](Pom* actor,std::string& e){return floor.retired(actor,e);});
 native.onBind(std::move(consumer));return true;
}
}
