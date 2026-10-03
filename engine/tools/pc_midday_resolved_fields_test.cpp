#include "pc_midday_resolved_fields.h"
#include <cstdio>
using namespace pc_midday;
namespace {int checks=0,failed=0;void check(bool v,const char*s){++checks;if(!v){++failed;std::printf("FAIL %s\n",s);}}
struct Resolver:LogicalResolver {int storage=4,calls=0;bool deny=false,null=false;
 bool identify(const char*,RefKind,const void*,LogicalRef&,std::string&)override{return false;}
 bool validate(const char*,RefKind,const LogicalRef&,std::string&)const override{return true;}
 bool validateTyped(const FieldSchema&s,const LogicalRef&,std::string&)const override{return !deny&&s.targetType=="ExactType";}
 bool resolve(const char*,RefKind,const LogicalRef&,void*&p,std::string&)override{++calls;p=null?nullptr:&storage;return !deny;}
 bool identifyHandle(const char*,RefKind,u32,LogicalRef&,std::string&)override{return false;}
 bool resolveHandle(const char*,RefKind,const LogicalRef&,u32&,std::string&)override{return false;}
};}
int main(){Resolver r;ResolvedFields cached;ActorFields fields;ActorField ref;ref.category=FieldCategory::Reference;ref.reference=RefKind::Effect;ref.target={0,7,2};fields["root"]=ref;auto schema=std::vector<FieldSchema>{FieldSchema::ref("root",RefKind::Effect,false,"ExactType")};std::string error;void* p=nullptr;
 check(cached.prepare(fields,schema,r,{{"root",&r.storage}},error),"exact native storage accepted");check(r.calls==1,"one pre-write pointer resolution");r.deny=true;check(cached.resolve("root",RefKind::Effect,ref.target,p,error)&&p==&r.storage&&r.calls==1,"apply uses pinned pointer without resolving mutable provider twice");
 p=nullptr;check(!cached.resolve("foreign",RefKind::Effect,ref.target,p,error)&&!p,"foreign field key refused");check(!cached.resolve("root",RefKind::Creature,ref.target,p,error),"wrong role refused");auto wrong=ref.target;++wrong.slot;check(!cached.resolve("root",RefKind::Effect,wrong,p,error),"changed logical slot refused");++wrong.resource;check(!cached.resolve("root",RefKind::Effect,wrong,p,error),"changed resource refused");
 check(!cached.prepare(fields,schema,r,{},error),"typed provider refusal");check(cached.resolve("root",RefKind::Effect,ref.target,p,error)&&p==&r.storage,"failed prepare retains preceding complete graph");r.deny=false;r.null=true;check(!cached.prepare(fields,schema,r,{},error),"nonnull identity resolving null refused");r.null=false;int foreign=0;check(!cached.prepare(fields,schema,r,{{"root",&foreign}},error),"foreign adjusted native pointer refused");check(!cached.prepare(fields,schema,r,{{"missing",&foreign}},error),"owned key absent from schema refused");
 auto absent=fields;absent["root"].target={};schema[0].nullable=true;int before=r.calls;check(cached.prepare(absent,schema,r,{{"root",nullptr}},error)&&r.calls==before,"typed nullable reference pinned without unsafe resolution");p=&foreign;check(cached.resolve("root",RefKind::Effect,{},p,error)&&p==nullptr,"cached nullable resolves exactly null");r.deny=true;check(!cached.prepare(absent,schema,r,{},error),"null typed contract still validated");
 std::printf("%d checks, %d failures\n",checks,failed);return failed?1:0;}
