#include "pc_midday_resolved_fields.h"
namespace pc_midday {
namespace {bool absent(const LogicalRef&r){return !r.owner&&!r.resource&&!r.slot;}bool same(const LogicalRef&a,const LogicalRef&b){return a.owner==b.owner&&a.resource==b.resource&&a.slot==b.slot;}}
bool ResolvedFields::prepare(const ActorFields& fields,const std::vector<FieldSchema>& schema,LogicalResolver& resolver,const std::map<std::string,const void*>& owned,std::string& e){
 if(!validate_actor_fields(fields,schema,resolver,e))return false;
 std::map<std::string,void*> pointers;
 for(const auto& entry:schema){if(entry.category==FieldCategory::Handle||entry.category==FieldCategory::Token64){e="pointer graph cannot cache handles/tokens";return false;}
  if(entry.category!=FieldCategory::Reference)continue;
  const auto& ref=fields.at(entry.key);void* address=nullptr;
  if(!absent(ref.target)&&(!resolver.resolve(entry.key.c_str(),entry.reference,ref.target,address,e)||!address)){if(e.empty())e="non-null typed reference resolved null";return false;}
  auto expected=owned.find(entry.key);if(expected!=owned.end()&&address!=expected->second){e="resolved reference does not match exact private allocation: "+entry.key;return false;}
  pointers.emplace(entry.key,address);
 }
 for(const auto& entry:owned)if(pointers.find(entry.first)==pointers.end()){e="owned allocation key absent from compiled schema";return false;}
 // Both potentially allocating copies complete before publishing either map.
 ActorFields copied=fields;fields_.swap(copied);pointers_.swap(pointers);e.clear();return true;
}
bool ResolvedFields::matches(const char*k,RefKind kind,const LogicalRef&r)const{auto it=fields_.find(k);return it!=fields_.end()&&it->second.category==FieldCategory::Reference&&it->second.reference==kind&&same(it->second.target,r)&&pointers_.count(k);}
bool ResolvedFields::validate(const char*k,RefKind kind,const LogicalRef&r,std::string&e)const{if(matches(k,kind,r))return true;e="cached reference key/kind/identity mismatch";return false;}
bool ResolvedFields::resolve(const char*k,RefKind kind,const LogicalRef&r,void*&out,std::string&e){if(!validate(k,kind,r,e))return false;out=pointers_.at(k);return true;}
bool ResolvedFields::identify(const char*,RefKind,const void*,LogicalRef&,std::string&e){e="resolved stage graph is apply-only";return false;}
bool ResolvedFields::identifyHandle(const char*,RefKind,u32,LogicalRef&,std::string&e){e="resolved stage graph has no handle capture";return false;}
bool ResolvedFields::resolveHandle(const char*,RefKind,const LogicalRef&,u32&,std::string&e){e="resolved stage graph has no handle mapping";return false;}
}
