#include "pc_p2_shijimi_attachment.h"
#include "pc_p2_original_source_uid.h"
#include <cmath>
#include <iomanip>
#include <limits>
#include <locale>
#include <set>
#include <sstream>
#include <tuple>
namespace p2original { namespace shijimi {
namespace {
bool reject(std::string& e,const char* m){e=m;return false;}
using Key=std::tuple<std::string,std::string,std::uint32_t,std::uint32_t,std::uint64_t>;
Key key(const OriginalPikiOrigin& o){return {o.catalogFingerprint,o.sourceKey,o.recordUid,o.attempt,o.activation};}
bool valid(const GenPikiAttachment& a){const auto& o=a.body;
 if(o.catalogFingerprint.size()!=64||o.catalogFingerprint.find_first_not_of("0123456789abcdef")!=std::string::npos
  ||o.sourceKey.empty()||o.sourceKey.size()>256||!o.activation||o.recordUid!=originalSourceCatalogUid(o.sourceKey))return false;
 return std::isfinite(a.local.x)&&std::isfinite(a.local.y)&&std::isfinite(a.local.z);
}
bool validate(const std::vector<GenPikiAttachment>& saved,const AttachmentAuthority& authority,std::string& e){
 if(saved.size()>100)return reject(e,"source77 attachment census exceeds source party capacity");
 std::set<Key> members;
 for(const auto& a:saved)if(!valid(a)||!members.insert(key(a.body)).second||!authority.member(a.body,e))return reject(e,"source77 GenPiki attachment member is invalid or unauthenticated");
 return true;
}
}
bool captureAttachment(Piki* p,Position local,const AttachmentAuthority& authority,LiveGenPikiAttachment& out,std::string& e){
 OriginalPikiBodyHandle h;if(!pc_p2_original_piki_body_handle(p,h))return reject(e,"source77 attachment requires actual committed GenPiki body handle");
 LiveGenPikiAttachment next;next.saved={h.body.origin,local};next.body=p;next.nativeLifetime=h.nativeLifetime;
 if(!valid(next.saved)||!authority.member(next.saved.body,e)||!pc_p2_original_piki_body_current(p,h.nativeLifetime))return reject(e,"source77 attachment source/lifetime changed during capture");
 out=std::move(next);e.clear();return true;
}
bool currentAttachment(const LiveGenPikiAttachment& a)noexcept{
 if(!a.body||!pc_p2_original_piki_body_current(a.body,a.nativeLifetime))return false;
 try {OriginalPikiBodyHandle h;return pc_p2_original_piki_body_handle(a.body,h)&&h.nativeLifetime==a.nativeLifetime&&key(h.body.origin)==key(a.saved.body);}catch(...){return false;}
}
bool encodeAttachments(const std::vector<GenPikiAttachment>& saved,const AttachmentAuthority& authority,std::string& out,std::string& e){
 if(!validate(saved,authority,e))return false;
 std::ostringstream bytes;bytes.imbue(std::locale::classic());bytes<<"P2_SHIJIMI_GENPIKI_ATTACHMENTS_1 "<<saved.size()<<'\n';bytes<<std::setprecision(std::numeric_limits<float>::max_digits10);
 for(const auto& a:saved){const auto& o=a.body;bytes<<std::quoted(o.catalogFingerprint)<<' '<<std::quoted(o.sourceKey)<<' '<<o.recordUid<<' '<<o.attempt<<' '<<o.activation<<' '<<a.local.x<<' '<<a.local.y<<' '<<a.local.z<<'\n';}
 out=bytes.str();e.clear();return true;
}
bool decodeAttachments(const std::string& bytes,const AttachmentAuthority& authority,std::vector<GenPikiAttachment>& out,std::string& e){
 if(bytes.size()>65536)return reject(e,"source77 attachment bytes exceed bound");
 std::istringstream in(bytes);in.imbue(std::locale::classic());std::string magic,extra;unsigned n;
 if(!(in>>magic>>n)||magic!="P2_SHIJIMI_GENPIKI_ATTACHMENTS_1"||n>100)return reject(e,"source77 attachment header invalid");
 std::vector<GenPikiAttachment> next;
 for(unsigned i=0;i<n;++i){GenPikiAttachment a;auto& o=a.body;
  if(!(in>>std::quoted(o.catalogFingerprint)>>std::quoted(o.sourceKey)>>o.recordUid>>o.attempt>>o.activation>>a.local.x>>a.local.y>>a.local.z))return reject(e,"source77 attachment record malformed");
  next.push_back(std::move(a));}
 if(in>>extra)return reject(e,"source77 attachment trailing data");
 if(!validate(next,authority,e))return false;
 out=std::move(next);e.clear();return true;
}
bool resolveAttachments(const std::vector<GenPikiAttachment>& saved,const std::vector<LiveGenPikiAttachment>& party,const AttachmentAuthority& authority,std::vector<LiveGenPikiAttachment>& out,std::string& e){
 if(!validate(saved,authority,e))return false;
 if(party.size()>100)return reject(e,"source77 actual party mapping exceeds capacity");
 std::set<Key> members;std::set<const Piki*> bodies;
 for(const auto& live:party)if(!valid(live.saved)||!members.insert(key(live.saved.body)).second||!bodies.insert(live.body).second||!currentAttachment(live)||!authority.member(live.saved.body,e))return reject(e,"source77 actual party mapping stale/duplicate/unauthenticated");
 std::vector<LiveGenPikiAttachment> next;
 for(const auto& a:saved){const LiveGenPikiAttachment* found=nullptr;for(const auto& live:party)if(key(live.saved.body)==key(a.body)){found=&live;break;}
  if(!found)return reject(e,"source77 saved attachment absent from actual party mapping");
  auto resolved=*found;resolved.saved=a;next.push_back(std::move(resolved));}
 for(const auto& live:next)if(!authority.member(live.saved.body,e))return reject(e,"source77 party source changed during resolution");
 // An authority callback may retire any previously checked body. Check all
 // incarnations after the final callback, before publishing the resolved list.
 for(const auto& live:next)if(!currentAttachment(live))return reject(e,"source77 party lifetime changed during resolution");
 out=std::move(next);e.clear();return true;
}
} }
