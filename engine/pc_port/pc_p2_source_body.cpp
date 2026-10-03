#include "pc_p2_source_body.h"
namespace {
PcP2SourceOnyonReader* onyonReader=nullptr;
bool equalRoot(const PcP2SourceOnyonRoot& a,const PcP2SourceOnyonRoot& b){
 return a.campaign==b.campaign&&a.session==b.session&&a.sourceSha==b.sourceSha&&a.sourceKey==b.sourceKey&&a.uid==b.uid&&a.species==b.species&&a.birthIncarnation==b.birthIncarnation;
}
bool digest(const std::string& s){return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
bool validRoot(const PcP2SourceOnyonRoot& r,const OriginalPikiBodyState& s){
 return digest(r.campaign)&&digest(r.session)&&digest(r.sourceSha)&&!r.sourceKey.empty()&&r.sourceKey.size()<=256
 &&r.sourceKey.find_first_of(" \t\r\n")==std::string::npos&&r.sourceKey.find(char(0))==std::string::npos&&r.species<=4&&s.species==r.species&&r.birthIncarnation!=0;
}
}
PcP2SourceBodyKind pc_p2_source_body_query(const Piki* p,PcP2SourceBody& out){
 if(!p)return PcP2SourceBodyKind::None;
 OriginalPikiBody gen;p2budorigin::Record bud;
 const bool hasGen=pc_p2_original_piki_body_query(p,gen);
 const bool hasBud=p2budorigin::registry().body(p,bud);
 const bool hasOnyon=onyonReader&&onyonReader->owned(p);
 OriginalPikiOrigin legacy;const bool legacyOnly=!hasGen&&pc_p2_original_piki_origin_query(p,legacy);
 if(legacyOnly)return PcP2SourceBodyKind::Unavailable;
 if(unsigned(hasGen)+unsigned(hasBud)+unsigned(hasOnyon)>1)return PcP2SourceBodyKind::Unavailable;
 PcP2SourceBody next;
 if(hasGen){next.kind=PcP2SourceBodyKind::GenPiki;next.state=gen.state;next.genPiki=std::move(gen);}
 else if(hasBud){next.kind=PcP2SourceBodyKind::BudConversion;next.state={static_cast<std::uint8_t>(bud.species),false,false};next.conversion=std::move(bud);}
 else if(hasOnyon){
  next.kind=PcP2SourceBodyKind::OnyonEmission;next.nativeBody=p;
  if(!onyonReader->lifetime(p,next.nativeLifetime)||!next.nativeLifetime
     ||!onyonReader->query(p,next.nativeLifetime,next.onyon,next.state)
     ||!validRoot(next.onyon,next.state))return PcP2SourceBodyKind::Unavailable;
 }
 else {OriginalPikiOrigin legacy;if(pc_p2_original_piki_origin_query(p,legacy))return PcP2SourceBodyKind::Unavailable;return PcP2SourceBodyKind::None;}
 out=std::move(next);return out.kind;
}
bool pc_p2_source_body_admitted(const PcP2SourceBody& body,const std::string& campaign,const std::string& catalog,std::string& e){
 if(body.kind==PcP2SourceBodyKind::GenPiki)return body.genPiki.origin.catalogFingerprint==catalog;
 if(body.kind==PcP2SourceBodyKind::BudConversion){
  if(body.conversion.identity.floor.campaign!=campaign){e="converted source body campaign mismatch";return false;}
  return p2budorigin::registry().admitted(body.conversion,e);
 }
 if(body.kind==PcP2SourceBodyKind::OnyonEmission){
  PcP2SourceBody current;
  if(!body.nativeBody||pc_p2_source_body_query(body.nativeBody,current)!=PcP2SourceBodyKind::OnyonEmission
     ||current.nativeLifetime!=body.nativeLifetime||!equalRoot(current.onyon,body.onyon)
     ||current.state.species!=body.state.species||current.state.wild!=body.state.wild||current.state.wasWild!=body.state.wasWild){e="Onyon body lifetime/state changed";return false;}
  if(body.onyon.campaign!=campaign){e="Onyon body campaign mismatch";return false;}
  return onyonReader->admitted(body.nativeBody,body.nativeLifetime,body.onyon,campaign,e);
 }
 e="source body discriminator unavailable";return false;
}
bool pc_p2_source_body_recruited(Piki* p){PcP2SourceBody body;const auto kind=pc_p2_source_body_query(p,body);
 if(kind==PcP2SourceBodyKind::GenPiki)return pc_p2_original_piki_body_recruited(p);
 if(kind==PcP2SourceBodyKind::OnyonEmission)return onyonReader->recruited(p,body.nativeLifetime);
 // Retail FakePiki::onInit clears flags; a converted, plucked body is not wild.
 return kind==PcP2SourceBodyKind::BudConversion&&!body.state.wild;
}

bool pc_p2_source_body_install_onyon_reader(PcP2SourceOnyonReader& reader)noexcept{
 if(onyonReader&&onyonReader!=&reader)return false;
 onyonReader=&reader;return true;
}
void pc_p2_source_body_forget_external(Piki* p)noexcept{if(onyonReader&&p)onyonReader->forget(p);}
void pc_p2_source_body_scene_exit_external()noexcept{if(onyonReader)onyonReader->sceneExit();}
