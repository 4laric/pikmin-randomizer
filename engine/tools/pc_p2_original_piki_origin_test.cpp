#include "pc_p2_original_piki_origin.h"
#include "pc_p2_original_source_uid.h"
#include <iostream>
namespace{unsigned checks=0;bool permitted=false,zeroHash=false,notificationOK=true;std::uint64_t selected=1;OriginalPikiOrigin ticket;OriginalPikiBodyState selectedState;bool bodyPermitted=false,callbackExposedNative=false,forgetDuringCallback=false;}
bool pc_p2_cave_campaign_survivor_permit(const std::string& k,std::uint32_t u,std::uint32_t a,std::uint64_t x,const std::string& f,std::uint64_t* g,std::uint8_t h[32]){if(!permitted||k!=ticket.sourceKey||u!=ticket.recordUid||a!=ticket.attempt||x!=ticket.activation||f!=ticket.catalogFingerprint)return false;*g=selected;for(int i=0;i<32;++i)h[i]=zeroHash?0:7;return true;}
bool pc_p2_cave_campaign_survivor_body(const std::string& k,std::uint32_t u,std::uint32_t a,std::uint64_t x,const std::string& f,OriginalPikiBodyState& state,std::uint64_t* g,std::uint8_t h[32]){if(!bodyPermitted)return false;if(!pc_p2_cave_campaign_survivor_permit(k,u,a,x,f,g,h))return false;state=selectedState;return true;}
bool pc_p2_cave_campaign_party_associate_birth(Piki* p,const char*,std::uint32_t,std::uint32_t,std::uint64_t,const char*){OriginalPikiBodyHandle h;callbackExposedNative|=pc_p2_original_piki_body_handle(p,h);if(forgetDuringCallback)pc_p2_original_piki_origin_forget(p);return notificationOK;}
#define CHECK(x) do{++checks;if(!(x)){std::cerr<<"FAIL "<<checks<<" "<<#x<<"\n";return 1;}}while(false)
int main(){std::string e,fp(64,'a');int slots[3]={};auto p=reinterpret_cast<Piki*>(&slots[0]),q=reinterpret_cast<Piki*>(&slots[1]);
 CHECK(p2original::originalSourceCatalogUid("tutorial/defaultgen.txt#5")==0x521c1cbeu);
 CHECK(p2original::originalSourceCatalogUid("tutorial/defaultgen.txt#0")==0x5204199eu);
 CHECK(p2original::originalSourceCatalogUid("tutorial/nonloop/day5.gen#41")==0x5244a665u);
 OriginalPikiSource row{"tutorial/defaultgen.txt#5",p2original::originalSourceCatalogUid("tutorial/defaultgen.txt#5"),5};
 OriginalPikiOrigin o{row.sourceKey,row.uid,2,1,fp},out{"unchanged",77,88,99,"sentinel"};
 CHECK(!pc_p2_original_piki_origin_query(p,out));CHECK(out.sourceKey=="unchanged"&&out.recordUid==77);
 CHECK(!pc_p2_original_piki_origin_install("bad",{row},e));CHECK(pc_p2_original_piki_origin_install(fp,{row},e));
 CHECK(!pc_p2_original_piki_origin_associate_birth(nullptr,o));auto bad=o;bad.attempt=5;CHECK(!pc_p2_original_piki_origin_associate_birth(p,bad));bad=o;bad.activation=0;CHECK(!pc_p2_original_piki_origin_associate_birth(p,bad));bad=o;bad.recordUid++;CHECK(!pc_p2_original_piki_origin_associate_birth(p,bad));bad=o;bad.catalogFingerprint[0]='b';CHECK(!pc_p2_original_piki_origin_associate_birth(p,bad));
 notificationOK=false;CHECK(!pc_p2_original_piki_origin_associate_birth(p,o));CHECK(!pc_p2_original_piki_origin_query(p,out));notificationOK=true;CHECK(pc_p2_original_piki_origin_associate_birth(p,o));CHECK(!pc_p2_original_piki_origin_associate_birth(q,o));CHECK(!pc_p2_original_piki_origin_associate_birth(p,o));CHECK(!pc_p2_original_piki_origin_install(fp,{row},e));CHECK(pc_p2_original_piki_origin_query(p,out));CHECK(out.attempt==2&&out.activation==1&&out.catalogFingerprint==fp);
 pc_p2_original_piki_origin_forget(p);CHECK(!pc_p2_original_piki_origin_query(p,out));CHECK(!pc_p2_original_piki_origin_restore_saved(q,o));
 ticket=o;permitted=true;selected=0;CHECK(!pc_p2_original_piki_origin_restore_saved(q,o));selected=1;zeroHash=true;CHECK(!pc_p2_original_piki_origin_restore_saved(q,o));zeroHash=false;CHECK(pc_p2_original_piki_origin_restore_saved(q,o));CHECK(!pc_p2_original_piki_origin_restore_saved(p,o));
 pc_p2_original_piki_origin_forget(q);permitted=false;CHECK(!pc_p2_original_piki_origin_restore_saved(q,o)); // ordinary death is not a permit
 permitted=true;CHECK(pc_p2_original_piki_origin_restore_saved(p,o)); // explicit selected older SAVE may restore its survivor
 pc_p2_original_piki_origin_forget(p);auto broken=row;broken.sourceKey="tutorial/../defaultgen.txt#5";broken.uid=p2original::originalSourceCatalogUid(broken.sourceKey);CHECK(!pc_p2_original_piki_origin_install(fp,{broken},e));broken=row;broken.sourceKey="tutorial/defaultgen.txt#05";broken.uid=p2original::originalSourceCatalogUid(broken.sourceKey);CHECK(!pc_p2_original_piki_origin_install(fp,{broken},e));CHECK(!pc_p2_original_piki_origin_install(fp,{row,row},e));CHECK(pc_p2_original_piki_origin_associate_birth(p,o));
 pc_p2_original_piki_origin_forget(p);CHECK(pc_p2_original_piki_origin_install(std::string(64,'b'),{row},e));CHECK(!pc_p2_original_piki_origin_restore_saved(p,o));

 CHECK(pc_p2_original_piki_origin_install(fp,{row},e));
 OriginalPikiBody body{o,{0,true,true}},bodyOut{{"sentinel",0,0,0,"old"},{5,false,false}};
 CHECK(!pc_p2_original_piki_body_query(p,bodyOut));CHECK(bodyOut.origin.sourceKey=="sentinel"&&bodyOut.state.species==5);
 auto invalid=body;invalid.state.species=6;CHECK(!pc_p2_original_piki_body_associate_birth(p,invalid));
 invalid=body;invalid.state.wasWild=false;CHECK(!pc_p2_original_piki_body_associate_birth(p,invalid));
 invalid=body;invalid.state.wild=false;CHECK(!pc_p2_original_piki_body_associate_birth(p,invalid));
 notificationOK=false;CHECK(!pc_p2_original_piki_body_associate_birth(p,body));CHECK(!pc_p2_original_piki_body_query(p,bodyOut));notificationOK=true;
 CHECK(pc_p2_original_piki_body_associate_birth(p,body));CHECK(pc_p2_original_piki_body_query(p,bodyOut));CHECK(bodyOut.state.wild&&bodyOut.state.wasWild&&bodyOut.state.species==0);
 CHECK(!pc_p2_original_piki_body_associate_birth(q,body));CHECK(pc_p2_original_piki_body_recruited(p));CHECK(pc_p2_original_piki_body_query(p,bodyOut));CHECK(!bodyOut.state.wild&&bodyOut.state.wasWild);CHECK(!pc_p2_original_piki_body_recruited(p));
 pc_p2_original_piki_origin_forget(p);CHECK(!pc_p2_original_piki_body_query(p,bodyOut));
 CHECK(!pc_p2_original_piki_body_birth_admit(body));CHECK(!pc_p2_original_piki_body_associate_birth(p,body));
 CHECK(pc_p2_original_piki_origin_install(fp,{row},e));CHECK(!pc_p2_original_piki_body_birth_admit(body));
 auto nextBirth=body;nextBirth.origin.activation++;CHECK(pc_p2_original_piki_body_birth_admit(nextBirth));
 body.state.species=3;CHECK(!pc_p2_original_piki_body_associate_birth(p,body));auto purple=row;purple.species=3;CHECK(!pc_p2_original_piki_origin_install(fp,{purple},e));
 CHECK(pc_p2_original_piki_origin_install(std::string(64,'b'),{purple},e));body.origin.catalogFingerprint=std::string(64,'b');CHECK(pc_p2_original_piki_body_associate_birth(p,body));CHECK(!pc_p2_original_piki_body_recruited(p));pc_p2_original_piki_origin_forget(p);
 CHECK(pc_p2_original_piki_origin_install(fp,{row},e));body.origin=o;body.state={0,false,true};selectedState=body.state;ticket=o;permitted=true;selected=2;zeroHash=false;
 CHECK(!pc_p2_original_piki_body_restore_saved(q,body)); // tuple-only ticket insufficient
 bodyPermitted=true;selectedState.wild=true;CHECK(!pc_p2_original_piki_body_restore_saved(q,body));
 selectedState=body.state;selectedState.species=1;CHECK(!pc_p2_original_piki_body_restore_saved(q,body));
 selectedState=body.state;selected=0;CHECK(!pc_p2_original_piki_body_restore_saved(q,body));selected=1;zeroHash=true;CHECK(!pc_p2_original_piki_body_restore_saved(q,body));zeroHash=false;
 CHECK(pc_p2_original_piki_body_restore_saved(q,body));CHECK(pc_p2_original_piki_body_query(q,bodyOut));CHECK(bodyOut.state.wasWild&&!bodyOut.state.wild);CHECK(!pc_p2_original_piki_body_restore_saved(p,body));
 CHECK(!pc_p2_original_piki_saved_color_held(q,0));
 {PcOriginalPikiSavedColorScope nullScope(nullptr);CHECK(!nullScope.valid());}
 bodyPermitted=false;{PcOriginalPikiSavedColorScope refused(q);CHECK(!refused.valid());}bodyPermitted=true;
 {PcOriginalPikiSavedColorScope selectedColor(q);CHECK(selectedColor.valid());
  CHECK(pc_p2_original_piki_saved_color_held(q,0));
  bodyPermitted=false;CHECK(!pc_p2_original_piki_saved_color_held(q,0));bodyPermitted=true;
  selected++;CHECK(!pc_p2_original_piki_saved_color_held(q,0));selected--;
  zeroHash=true;CHECK(!pc_p2_original_piki_saved_color_held(q,0));zeroHash=false;
  CHECK(pc_p2_original_piki_saved_color_held(q,0));CHECK(!pc_p2_original_piki_saved_color_held(q,1));CHECK(!pc_p2_original_piki_saved_color_held(p,0));
  PcOriginalPikiSavedColorScope nested(q);CHECK(!nested.valid());
  CHECK(pc_p2_original_piki_body_color_access(q,0));CHECK(!pc_p2_original_piki_body_color_access(q,2));
  pc_p2_original_piki_origin_forget(q);CHECK(!pc_p2_original_piki_saved_color_held(q,0));
 }
 CHECK(!pc_p2_original_piki_saved_color_held(q,0));
 CHECK(pc_p2_original_piki_body_restore_saved(q,body));
 pc_p2_original_piki_origin_forget(q);auto freshReplay=body;freshReplay.state={0,true,true};CHECK(!pc_p2_original_piki_body_birth_admit(freshReplay));bodyPermitted=false;CHECK(!pc_p2_original_piki_body_restore_saved(p,body));bodyPermitted=true;
 CHECK(pc_p2_original_piki_body_restore_saved(p,body)); // selected older SAVE remains legitimate
 pc_p2_original_piki_origin_forget(p);CHECK(pc_p2_original_piki_origin_associate_birth(p,o));CHECK(!pc_p2_original_piki_body_query(p,bodyOut));CHECK(!pc_p2_original_piki_body_recruited(p));pc_p2_original_piki_origin_forget(p);
 auto sceneBody=body;sceneBody.origin.activation=8;sceneBody.state={0,true,true};
 forgetDuringCallback=true;CHECK(!pc_p2_original_piki_body_associate_birth(p,sceneBody));forgetDuringCallback=false;
 CHECK(pc_p2_original_piki_body_birth_admit(sceneBody));
 CHECK(pc_p2_original_piki_body_associate_birth(p,sceneBody));
 CHECK(pc_p2_original_piki_body_wild(p));CHECK(pc_p2_original_piki_body_color_access(p,0));
 OriginalPikiBodyHandle liveHandle;CHECK(pc_p2_original_piki_body_handle(p,liveHandle));
 CHECK(liveHandle.nativeLifetime&&liveHandle.body.origin.attempt==sceneBody.origin.attempt&&liveHandle.body.origin.activation==sceneBody.origin.activation);
 CHECK(pc_p2_original_piki_body_current(p,liveHandle.nativeLifetime));CHECK(!callbackExposedNative);
 CHECK(!pc_p2_original_piki_body_current(p,0));CHECK(!pc_p2_original_piki_body_current(q,liveHandle.nativeLifetime));
 pc_p2_original_piki_origin_scene_exit();
 CHECK(!pc_p2_original_piki_origin_query(p,out));CHECK(!pc_p2_original_piki_body_query(p,bodyOut));
 CHECK(!pc_p2_original_piki_body_current(p,liveHandle.nativeLifetime));
 auto unchangedHandle=liveHandle;CHECK(!pc_p2_original_piki_body_handle(p,unchangedHandle));CHECK(unchangedHandle.nativeLifetime==liveHandle.nativeLifetime);
 CHECK(!pc_p2_original_piki_body_wild(p));CHECK(!pc_p2_original_piki_body_color_access(p,0));
 CHECK(pc_p2_original_piki_origin_install(fp,{row},e));
 CHECK(!pc_p2_original_piki_body_birth_admit(sceneBody));
 CHECK(!pc_p2_original_piki_body_associate_birth(q,sceneBody));
 // Scene teardown does not revoke an authenticated selected SAVE rollback.
 ticket=sceneBody.origin;selectedState=sceneBody.state;
 CHECK(pc_p2_original_piki_body_restore_saved(q,sceneBody));
 OriginalPikiBodyHandle restoredHandle;CHECK(pc_p2_original_piki_body_handle(q,restoredHandle));
 CHECK(restoredHandle.nativeLifetime>liveHandle.nativeLifetime&&restoredHandle.body.origin.attempt==liveHandle.body.origin.attempt);
 CHECK(!pc_p2_original_piki_body_current(q,liveHandle.nativeLifetime));
 pc_p2_original_piki_origin_forget(q);CHECK(pc_p2_original_piki_body_restore_saved(p,sceneBody));
 CHECK(pc_p2_original_piki_body_handle(p,restoredHandle)&&restoredHandle.nativeLifetime>liveHandle.nativeLifetime);
 CHECK(!pc_p2_original_piki_body_current(p,liveHandle.nativeLifetime));
 pc_p2_original_piki_origin_scene_exit();CHECK(!pc_p2_original_piki_body_query(q,bodyOut));
 std::cout<<"PASS "<<checks<<" original Piki origin controls; cave ticket mocked, no native birth\n";
}
