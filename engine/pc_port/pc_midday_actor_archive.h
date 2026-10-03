#pragma once
#include "pc_midday_actor_states.h"
#include <vector>
#include <map>
#include <set>
namespace pc_midday {
using ActorBytes = std::vector<u8>;
enum class FieldCategory : u8 { Scalar, Reference, Handle, Token64 };
// Content means a registered content-bound resource identity; mutable resource
// payloads are still required. It does not assert immutable state.
enum class ReferenceOwnership { AnyLive, Self, ActorSubobject, Content,
    ResourceSubobject, ResourceSelf };
// Compiled native storage semantics, never inferred from the pointer target or
// serialized into the wire payload. Raw Creature pointers remain Weak.
enum class ReferenceStrength { Weak, StrongCreature };
struct FieldSchema {
    std::string key;
    FieldCategory category;
    ScalarKind scalar;
    RefKind reference;
    bool nullable;
    // Compiled declared target type, never a serialized RTTI name. An empty
    // contract is invalid for every reference, including nullable references.
    std::string targetType;
    ReferenceOwnership ownership=ReferenceOwnership::AnyLive;
    // Absolute payload key of the owning actor reference. Empty means the
    // subject actor for ActorSubobject; populated links are checked prebegin.
    std::string ownerLink;
    ReferenceStrength strength=ReferenceStrength::Weak;
    static FieldSchema value(const char* k, ScalarKind s) { return {k,FieldCategory::Scalar,s,RefKind::Creature,false,"",ReferenceOwnership::AnyLive}; }
    static FieldSchema ref(const char* k, RefKind r, bool n=false, const char* t="", ReferenceOwnership o=ReferenceOwnership::AnyLive, const char* owner="", ReferenceStrength strength=ReferenceStrength::Weak) { return {k,FieldCategory::Reference,ScalarKind::U8,r,n,t,o,owner,strength}; }
    static FieldSchema handle(const char* k, RefKind r, bool n=false, const char* t="", ReferenceOwnership o=ReferenceOwnership::AnyLive) { return {k,FieldCategory::Handle,ScalarKind::U32,r,n,t,o}; }
    static FieldSchema token64(const char* k, RefKind r, bool n=false, const char* t="", ReferenceOwnership o=ReferenceOwnership::AnyLive) { return {k,FieldCategory::Token64,ScalarKind::U64,r,n,t,o}; }
};
// owner is a checkpoint actor incarnation, resource is a content-bound resource
// identity, slot identifies a named/indexed subobject of that owner/resource.
// All-zero is absent; no process address or recycled runtime handle is permitted.
// ResourceSelf/ResourceSubobject use owner=0, resource=current canonical resource
// ID, slot=registered adjusted interface/owned subobject. The resolver carries
// explicit actor or resource subject context and verifies exact membership.
struct LogicalRef { u64 owner=0, resource=0; u32 slot=0; };
struct ActorField {
    FieldCategory category=FieldCategory::Scalar;
    ScalarKind scalar=ScalarKind::U8;
    RefKind reference=RefKind::Creature;
    u64 bits=0;
    LogicalRef target;
};
using ActorFields = std::map<std::string,ActorField>;
// Each callback receives the schema key. Implementations MUST enforce the
// concrete destination type and ownership role for that key (not merely the
// broad RefKind), before begin. resolve returns that adjusted concrete pointer.
class LogicalResolver {
public:
    virtual ~LogicalResolver()=default;
    virtual bool identify(const char*,RefKind,const void*,LogicalRef&,std::string&)=0;
    virtual bool validate(const char*,RefKind,const LogicalRef&,std::string&) const=0;
    // Validate the exact compiled type/owner contract before scene allocation,
    // including for nullable all-zero references. Null cannot bypass subject
    // context or owner-link metadata validation.
    // resolve(key,...) must use this same record's descriptors to produce the
    // correctly adjusted destination pointer, including multiple inheritance.
    virtual bool validateTyped(const FieldSchema&,const LogicalRef&,std::string& error) const {
        error="typed logical reference validation unavailable"; return false;
    }
    virtual bool resolve(const char*,RefKind,const LogicalRef&,void*&,std::string&)=0;
    virtual bool identifyHandle(const char*,RefKind,u32,LogicalRef&,std::string&)=0;
    virtual bool resolveHandle(const char*,RefKind,const LogicalRef&,u32&,std::string&)=0;
    virtual bool identifyToken(const char*,RefKind,u64,LogicalRef&,std::string& error) {
        error="64-bit logical token capture unavailable"; return false;
    }
    virtual bool resolveToken(const char*,RefKind,const LogicalRef&,u64&,std::string& error) {
        error="64-bit logical token restore unavailable"; return false;
    }
};
bool encode_actor_fields(const ActorFields&,ActorBytes&,std::string&);
bool decode_actor_fields(const ActorBytes&,ActorFields&,std::string&);
bool validate_actor_fields(const ActorFields&,const std::vector<FieldSchema>&,const LogicalResolver&,std::string&);
bool actor_i32(const ActorFields&,const char*,int&,std::string&);
bool actor_u32(const ActorFields&,const char*,u32&,std::string&);
class FieldArchive final : public ActorArchive {
    Mode operation;
    double clockInstant;
    ActorFields& fields;
    LogicalResolver& resolver;
    std::string& error;
    std::set<std::string> visited;
    bool entry(const char*,FieldCategory,ScalarKind,RefKind,ActorField*&);
public:
    FieldArchive(Mode m,ActorFields& f,LogicalResolver& r,std::string& e,double now) : operation(m),clockInstant(now),fields(f),resolver(r),error(e) {}
    Mode mode() const override { return operation; }
    double clock_now() const override { return clockInstant; }
    bool scalar(const char*,ScalarKind,void*) override;
    bool reference(const char*,RefKind,void*&) override;
    bool handle(const char*,RefKind,u32&) override;
    bool token64(const char*,RefKind,u64&) override;
    bool fail(const char* reason) override { if(error.empty()) error=reason; return false; }
    bool finish();
};
// Schema functions are pure and may run before RestoreBackend::begin.
bool capture_navi(Navi&,LogicalResolver&,double now,ActorBytes&,std::string&);
bool validate_navi(const ActorBytes&,const LogicalResolver&,std::string&);
bool allocate_navi_subobjects(Navi&,const ActorBytes&,LogicalResolver&,double now,std::string&);
bool bind_navi(Navi&,const ActorBytes&,LogicalResolver&,double now,std::string&);
bool navi_runtime_schema(const ActorFields&,std::vector<FieldSchema>&,std::string&);
void animation_schema(const std::string&,std::vector<FieldSchema>&);
bool navi_schema(const ActorFields&,std::vector<FieldSchema>&,std::string&);
bool piki_state_schema(int,std::vector<FieldSchema>&);
bool piki_action_schema(int,std::vector<FieldSchema>&);
void piki_runtime_schema(std::vector<FieldSchema>&);
// Piki adapter: pure validation is required before scene allocation/publication.
bool piki_schema(const ActorFields&,std::vector<FieldSchema>&,std::string&);
bool capture_piki(Piki&,LogicalResolver&,double now,ActorBytes&,std::string&);
bool validate_piki(const ActorBytes&,const LogicalResolver&,std::string&);
bool bind_piki(Piki&,const ActorBytes&,LogicalResolver&,double now,std::string&);
}
