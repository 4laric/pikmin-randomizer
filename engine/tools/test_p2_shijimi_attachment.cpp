#include "pc_p2_shijimi_attachment.h"
#include "pc_p2_original_source_uid.h"
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace p2original;using namespace p2original::shijimi;
namespace {OriginalPikiOrigin selected;bool permit=false;OriginalPikiBodyState selectedState{0,true,true};}
bool pc_p2_cave_campaign_party_associate_birth(Piki*,const char*,std::uint32_t,std::uint32_t,std::uint64_t,const char*){return true;}
bool pc_p2_cave_campaign_survivor_permit(const std::string& k,std::uint32_t u,std::uint32_t a,std::uint64_t x,const std::string& f,std::uint64_t* g,std::uint8_t h[32]){
 if(!permit||k!=selected.sourceKey||u!=selected.recordUid||a!=selected.attempt||x!=selected.activation||f!=selected.catalogFingerprint)return false;
 *g=1;for(int i=0;i<32;++i)h[i]=7;return true;
}
bool pc_p2_cave_campaign_survivor_body(const std::string& k,std::uint32_t u,std::uint32_t a,std::uint64_t x,const std::string& f,OriginalPikiBodyState& s,std::uint64_t* g,std::uint8_t h[32]){
 if(!pc_p2_cave_campaign_survivor_permit(k,u,a,x,f,g,h))return false;
 s=selectedState;return true;
}
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
struct Authority final:AttachmentAuthority {
 OriginalPikiSource source;std::string fingerprint;bool available=true;
 mutable unsigned visits=0;unsigned forgetAt=0;Piki* forgetBody=nullptr;
 bool member(const OriginalPikiOrigin& o,std::string& e)const override{
  if(++visits==forgetAt)pc_p2_original_piki_origin_forget(forgetBody);
  if(!available||o.catalogFingerprint!=fingerprint||o.sourceKey!=source.sourceKey||o.recordUid!=source.uid||o.attempt>=source.count||o.activation!=1){e="actual selected member mismatch";return false;}return true;
 }
};
int main(){try{
 std::string e;Authority authority;authority.fingerprint=std::string(64,'a');authority.source={"tutorial/defaultgen.txt#5",originalSourceCatalogUid("tutorial/defaultgen.txt#5"),5,0};
 CHECK(pc_p2_original_piki_origin_install(authority.fingerprint,{authority.source},e));
 int storage=0;auto* p=reinterpret_cast<Piki*>(&storage);OriginalPikiBody body{{authority.source.sourceKey,authority.source.uid,2,1,authority.fingerprint},{0,true,true}};
 LiveGenPikiAttachment live;live.saved.local={99,99,99};CHECK(!captureAttachment(p,{1,2,3},authority,live,e));CHECK(live.saved.local.x==99);
 CHECK(pc_p2_original_piki_body_associate_birth(p,body));CHECK(captureAttachment(p,{1,2,3},authority,live,e));CHECK(currentAttachment(live));
 std::string bytes;CHECK(encodeAttachments({live.saved},authority,bytes,e));CHECK(bytes.find("nativeLifetime")==std::string::npos);
 std::vector<GenPikiAttachment> saved;CHECK(decodeAttachments(bytes,authority,saved,e));CHECK(saved.size()==1&&saved[0].body.attempt==2&&saved[0].local.y==2);
 auto before=saved;CHECK(!decodeAttachments(bytes+"extra",authority,saved,e));CHECK(saved.size()==before.size()&&saved[0].body.attempt==2);
 auto bad=live.saved;bad.body.attempt=5;CHECK(!encodeAttachments({bad},authority,bytes,e));CHECK(!encodeAttachments({live.saved,live.saved},authority,bytes,e));
 bad=live.saved;bad.local.x=std::numeric_limits<float>::infinity();CHECK(!encodeAttachments({bad},authority,bytes,e));
 authority.available=false;CHECK(!captureAttachment(p,{4,5,6},authority,live,e));CHECK(live.saved.local.x==1);authority.available=true;
 auto stale=live;pc_p2_original_piki_origin_forget(p);CHECK(!currentAttachment(stale));
 selected=body.origin;permit=true;CHECK(pc_p2_original_piki_body_restore_saved(p,body));LiveGenPikiAttachment fresh;CHECK(captureAttachment(p,{0,0,0},authority,fresh,e));
 CHECK(fresh.nativeLifetime!=stale.nativeLifetime&&currentAttachment(fresh)&&!currentAttachment(stale));
 std::vector<LiveGenPikiAttachment> resolved;CHECK(resolveAttachments(saved,{fresh},authority,resolved,e));CHECK(resolved.size()==1&&resolved[0].nativeLifetime==fresh.nativeLifetime&&resolved[0].saved.local.x==1);
 CHECK(!resolveAttachments(saved,{stale},authority,resolved,e));CHECK(resolved[0].nativeLifetime==fresh.nativeLifetime);
 CHECK(!resolveAttachments(saved,{fresh,fresh},authority,resolved,e));CHECK(!resolveAttachments(saved,{},authority,resolved,e));
 auto wrong=saved;wrong[0].body.attempt=3;CHECK(!resolveAttachments(wrong,{fresh},authority,resolved,e)); // same shared UID cannot alias another successful attempt
 authority.visits=0;authority.forgetAt=3;authority.forgetBody=p;
 CHECK(!resolveAttachments(saved,{fresh},authority,resolved,e));CHECK(!currentAttachment(fresh));CHECK(resolved[0].nativeLifetime==fresh.nativeLifetime); // last authority callback cannot publish a retired handle
 pc_p2_original_piki_origin_forget(p);std::cout<<"PASS released GenPiki SDK ancestry/lifetime capture, stale reuse, pointer-free attachment bytes and fresh-handle resolution; gameplay=0 cold_graph=0\n";return 0;
 }catch(const std::exception& ex){std::cerr<<ex.what()<<'\n';return 1;}}
