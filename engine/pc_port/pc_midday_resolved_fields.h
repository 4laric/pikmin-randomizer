#pragma once
#include "pc_midday_actor_archive.h"
namespace pc_midday {
// Ephemeral pointers only. Never serialized. The schema is validated completely,
// then each reference is resolved once before any native stage writes.
class ResolvedFields final:public LogicalResolver {
 ActorFields fields_;std::map<std::string,void*> pointers_;
 bool matches(const char*,RefKind,const LogicalRef&)const;
public:
 bool prepare(const ActorFields&,const std::vector<FieldSchema>&,LogicalResolver&,
              const std::map<std::string,const void*>& exactOwned,std::string&);
 bool identify(const char*,RefKind,const void*,LogicalRef&,std::string&)override;
 bool validate(const char*,RefKind,const LogicalRef&,std::string&)const override;
 bool resolve(const char*,RefKind,const LogicalRef&,void*&,std::string&)override;
 bool identifyHandle(const char*,RefKind,u32,LogicalRef&,std::string&)override;
 bool resolveHandle(const char*,RefKind,const LogicalRef&,u32&,std::string&)override;
};
}
