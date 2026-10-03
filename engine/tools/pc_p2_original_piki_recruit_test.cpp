#include "pc_p2_original_piki_recruit.h"
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_original_source_uid.h"
#include "pc_p2_original_progress.h"
#include <cstdlib>
#include <iostream>
#include <thread>
class Piki {};
// Pure authority controls only: no native body, movie, whistle or SAVE fixture.
bool pc_p2_cave_campaign_party_associate_birth(Piki*,const char*,std::uint32_t,std::uint32_t,std::uint64_t,const char*){return true;}
bool pc_p2_cave_campaign_survivor_permit(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,std::uint64_t*,std::uint8_t[32]){return false;}
bool pc_p2_cave_campaign_survivor_body(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,OriginalPikiBodyState&,std::uint64_t*,std::uint8_t[32]){return false;}
unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){std::cerr<<"FAIL "<<checks<<" "<<#x<<"\n";std::exit(1);}}while(0)
int main(){
 std::string error;const std::string campaign(64,'c'),catalog(64,'a');
 const auto uid=[](const char* key){return p2original::originalSourceCatalogUid(key);};
 std::vector<OriginalPikiSource> rows={{"tutorial/initgen.txt#1",uid("tutorial/initgen.txt#1"),3,0},
  {"tutorial/defaultgen.txt#5",uid("tutorial/defaultgen.txt#5"),3,1},
  {"tutorial/initgen.txt#4",uid("tutorial/initgen.txt#4"),3,4}};
 CHECK(pc_p2_original_piki_origin_install(catalog,rows,error));
 CHECK(!pc_p2_original_piki_recruit_bind(campaign,catalog,error));
 CHECK(p2original::originalProgress().initialize(campaign,error));
 CHECK(!pc_p2_original_piki_recruit_bind(catalog,catalog,error));
 CHECK(!pc_p2_original_piki_recruit_bind(campaign,campaign,error));
 CHECK(pc_p2_original_piki_recruit_bind(campaign,catalog,error)); // Distinct hashes.
 Piki blue,red,white,ordinary,legacy;
 const auto original=[&](unsigned index){const auto& row=rows[index];return OriginalPikiBody{{row.sourceKey,row.uid,0,1,catalog},{row.species,true,true}};};
 CHECK(pc_p2_original_piki_body_associate_birth(&blue,original(0)));
 const auto initial=p2original::originalProgress().snapshot();
 CHECK(pc_p2_original_piki_recruit_allowed(&ordinary,1,true,false,error));
 CHECK(pc_p2_original_piki_recruit_accepted(&ordinary,1,true,false,error));
 CHECK(p2original::originalProgress().snapshot().met==initial.met);
 CHECK(!pc_p2_original_piki_recruit_allowed(nullptr,0,false,true,error));
 CHECK(!pc_p2_original_piki_recruit_allowed(&blue,1,false,true,error));
 CHECK(!pc_p2_original_piki_contact_owner_allowed(&blue,0,1,false,error));
 CHECK(!pc_p2_original_piki_recruit_accepted(&blue,0,true,true,error));
 CHECK(!pc_p2_original_piki_recruit_accepted(&blue,0,false,false,error));
 CHECK(pc_p2_original_piki_body_wild(&blue));CHECK(!p2original::originalProgress().met(0));
 bool foreign=true;std::thread t([&]{std::string e;foreign=pc_p2_original_piki_recruit_accepted(&blue,0,false,true,e);});t.join();CHECK(!foreign);
 CHECK(pc_p2_original_piki_recruit_allowed(&blue,0,false,true,error));
 CHECK(pc_p2_original_piki_recruit_accepted(&blue,0,false,true,error));
 OriginalPikiBody out;CHECK(pc_p2_original_piki_body_query(&blue,out));CHECK(!out.state.wild&&out.state.wasWild);
 CHECK(p2original::originalProgress().met(0));CHECK(p2original::originalProgress().booted(0));CHECK(p2original::originalProgress().container(0));
 CHECK(pc_p2_original_piki_recruit_accepted(&blue,0,false,true,error));
 CHECK(pc_p2_original_piki_body_associate_birth(&red,original(1)));
 CHECK(pc_p2_original_piki_recruit_accepted(&red,0,false,true,error));
 CHECK(!p2original::originalProgress().met(1));CHECK(p2original::originalProgress().booted(1));
 CHECK(pc_p2_original_progress_hello(1,error));CHECK(p2original::originalProgress().met(1));
 CHECK(pc_p2_original_piki_body_associate_birth(&white,original(2)));
 CHECK(!pc_p2_original_piki_recruit_accepted(&white,0,false,true,error));CHECK(pc_p2_original_piki_body_wild(&white));
 auto legacyOrigin=original(0).origin;legacyOrigin.attempt=1;
 CHECK(pc_p2_original_piki_origin_associate_birth(&legacy,legacyOrigin));
 CHECK(!pc_p2_original_piki_recruit_allowed(&legacy,0,false,true,error));
 pc_p2_original_piki_recruit_unbind();
 CHECK(!pc_p2_original_piki_recruit_allowed(&blue,0,false,true,error));
 CHECK(pc_p2_original_piki_recruit_allowed(&ordinary,0,false,true,error));
 CHECK(pc_p2_original_piki_recruit_bind(campaign,catalog,error));
 CHECK(pc_p2_original_progress_reunite(error));CHECK(pc_p2_original_piki_recruit_allowed(&blue,1,false,true,error));
 CHECK(pc_p2_original_piki_contact_owner_allowed(&blue,0,1,false,error)); // Source post-reunion Louie contact despite P1 ID0.
 CHECK(!pc_p2_original_piki_contact_owner_allowed(&ordinary,0,1,false,error));
 CHECK(!pc_p2_original_piki_contact_owner_allowed(&blue,0,1,true,error));
 CHECK(pc_p2_original_piki_contact_owner_allowed(&ordinary,-1,1,false,error));
 CHECK(pc_p2_original_piki_contact_owner_allowed(&ordinary,0,0,true,error));

 pc_p2_original_piki_origin_scene_exit();
 CHECK(pc_p2_original_piki_origin_install(std::string(64,'b'),rows,error));
 auto changed=original(0);changed.origin.catalogFingerprint=std::string(64,'b');
 CHECK(pc_p2_original_piki_body_associate_birth(&blue,changed));
 CHECK(!pc_p2_original_piki_recruit_allowed(&blue,0,false,true,error));
 CHECK(!pc_p2_original_piki_recruit_bind(campaign,std::string(64,'b'),error));
 CHECK(pc_p2_original_piki_body_wild(&blue));
 std::cout<<"PASS "<<checks<<" original Piki paired recruitment controls; no native event/SAVE proof\n";
}
