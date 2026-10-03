#include "pc_p2_original_sprout_native.h"
#include "pc_p2_source_body.h"
#include "pc_randomizer.h"
namespace {
bool same(const PcP2SourceOnyonRoot& a,const PcP2SourceOnyonRoot& b){
 return a.campaign==b.campaign&&a.session==b.session&&a.sourceSha==b.sourceSha&&a.sourceKey==b.sourceKey&&a.uid==b.uid&&a.species==b.species&&a.birthIncarnation==b.birthIncarnation;
}
class Reader final:public PcP2SourceOnyonReader {
public:
 bool owned(const Piki* p)const noexcept override{return pc_p2_original_sprout_body_owned(p);}
 bool lifetime(const Piki* p,std::uint64_t& out)const noexcept override{return pc_p2_original_sprout_body_lifetime(p,out);}
 bool query(const Piki* p,std::uint64_t lifetime,PcP2SourceOnyonRoot& out,OriginalPikiBodyState& state)const override{
  p2originalonyon::MemberRecord r;std::uint64_t h=0;std::string e;
  if(pc_p2_original_sprout_body_query(p,r,h,e)!=p2originalonyon::QueryResult::Present||h!=lifetime)return false;
  // The full authored-or-emitted variant, member serial, reward cause, and
  // lifetime remain in Lineage. This common read-view never replaces them.
  const auto* emission=std::get_if<p2originalonyon::OnyonEmission>(&r.origin);
  if(!emission&&!r.hasReceiver)return false;
  const auto& root=emission?emission->root:r.receiverRoot;
  PcP2SourceOnyonRoot projected;projected.campaign=pc_p2_original_sprout_campaign();
  projected.session=r.sessionFingerprint;projected.sourceSha=root.sourceSha;projected.sourceKey=root.sourceKey;
  projected.uid=root.sourceUid;projected.species=r.state.species;projected.birthIncarnation=root.incarnation;
  out=std::move(projected);state={r.state.species,r.state.wild,r.state.wasWild};return true;
 }
 bool admitted(const Piki* p,std::uint64_t lifetime,const PcP2SourceOnyonRoot& selected,const std::string& campaign,std::string& e)const override{
  PcP2SourceOnyonRoot observed;OriginalPikiBodyState state;
  if(!query(p,lifetime,observed,state)||!same(selected,observed)||campaign!=observed.campaign
     ||!pc_randomizer_original_session()||observed.session!=pc_randomizer_session_fingerprint()){
   e="source Onion continuation admission/lifetime changed";return false;
  }
  e.clear();return true;
 }
 bool recruited(Piki* p,std::uint64_t lifetime)override{return pc_p2_original_sprout_body_recruited(p,lifetime);}
 void forget(Piki* p)noexcept override{pc_p2_original_sprout_body_forget(p);}
 void sceneExit()noexcept override{pc_p2_original_sprout_scene_exit();}
};
Reader reader;
}
bool pc_p2_original_sprout_install_reader()noexcept{return pc_p2_source_body_install_onyon_reader(reader);}
