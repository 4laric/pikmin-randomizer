#include "pc_midday_actor_archive.h"
#include <cstring>
#include <cmath>
#include <limits>
namespace pc_midday {
namespace {
constexpr size_t Limit=4*1024*1024, MaxFields=65536;
size_t width(ScalarKind k) {
    switch(k) {
    case ScalarKind::U8: case ScalarKind::S8: case ScalarKind::Bool:return 1;
    case ScalarKind::U16: case ScalarKind::S16:return 2;
    case ScalarKind::U32: case ScalarKind::S32: case ScalarKind::F32:return 4;
    case ScalarKind::U64: case ScalarKind::S64: case ScalarKind::F64:return 8;
    } return 0;
}
bool valid_scalar(ScalarKind k,u64 bits) {
    auto n=width(k); if(!n || (n<8 && bits>>(n*8))) return false;
    if(k==ScalarKind::Bool) return bits<=1;
    if(k==ScalarKind::F32) {u32 b=static_cast<u32>(bits);float f;std::memcpy(&f,&b,4);return std::isfinite(f);}
    if(k==ScalarKind::F64) {double f;std::memcpy(&f,&bits,8);return std::isfinite(f);}
    return true;
}
bool absent(const LogicalRef& r) {return !r.owner && !r.resource && !r.slot;}
bool valid_key(const std::string& s) {
    if(s.empty()||s.size()>512) return false;
    for(unsigned char c:s) if(!(c>='a'&&c<='z') && !(c>='A'&&c<='Z') && !(c>='0'&&c<='9') && c!='_'&&c!='.'&&c!='-') return false;
    return true;
}
bool reject(std::string& e,const char* s) {if(e.empty()) e=s;return false;}
void put(ActorBytes& b,u64 v,size_t n) {while(n--) {b.push_back(static_cast<u8>(v));v>>=8;}}
struct Reader {
    const ActorBytes& b;size_t p=0;
    bool get(u64& v,size_t n) {if(n>b.size()-p)return false;v=0;for(size_t i=0;i<n;++i)v|=u64(b[p++])<<(8*i);return true;}
};
u64 scalar_bits(ScalarKind k,const void* p) {
    switch(width(k)) {
    case 1:{u8 v=0;std::memcpy(&v,p,1);return v;}
    case 2:{u16 v=0;std::memcpy(&v,p,2);return v;}
    case 4:{u32 v=0;std::memcpy(&v,p,4);return v;}
    case 8:{u64 v=0;std::memcpy(&v,p,8);return v;}
    }return 0;
}
void scalar_value(ScalarKind k,u64 bits,void* p) {
    switch(width(k)) {
    case 1:{u8 v=static_cast<u8>(bits);std::memcpy(p,&v,1);break;}
    case 2:{u16 v=static_cast<u16>(bits);std::memcpy(p,&v,2);break;}
    case 4:{u32 v=static_cast<u32>(bits);std::memcpy(p,&v,4);break;}
    case 8:std::memcpy(p,&bits,8);break;
    }
}
}
bool encode_actor_fields(const ActorFields& fields,ActorBytes& output,std::string& error) {
    if(fields.size()>MaxFields)return reject(error,"too many actor fields");
    ActorBytes b={'A','S','T','1'};put(b,fields.size(),4);
    for(const auto& pair:fields) {
        const auto& key=pair.first;const auto& f=pair.second;
        if(!valid_key(key))return reject(error,"invalid actor field key");
        put(b,key.size(),2);b.insert(b.end(),key.begin(),key.end());put(b,static_cast<u8>(f.category),1);
        if(f.category==FieldCategory::Scalar) {
            if(!valid_scalar(f.scalar,f.bits))return reject(error,"invalid actor scalar");
            put(b,static_cast<u8>(f.scalar),1);put(b,f.bits,width(f.scalar));
        } else if(f.category==FieldCategory::Reference || f.category==FieldCategory::Handle || f.category==FieldCategory::Token64) {
            if(static_cast<unsigned>(f.reference)>=static_cast<unsigned>(RefKind::Count))return reject(error,"invalid reference kind");
            put(b,static_cast<u8>(f.reference),1);put(b,f.target.owner,8);put(b,f.target.resource,8);put(b,f.target.slot,4);
        } else return reject(error,"invalid field category");
        if(b.size()>Limit)return reject(error,"actor payload exceeds bound");
    }
    output.swap(b);return true;
}
bool decode_actor_fields(const ActorBytes& bytes,ActorFields& output,std::string& error) {
    if(bytes.size()<8 || bytes.size()>Limit || std::memcmp(bytes.data(),"AST1",4))return reject(error,"invalid actor payload header");
    Reader r{bytes,4};u64 count=0;if(!r.get(count,4)||count>MaxFields)return reject(error,"invalid actor field count");
    ActorFields fields;
    while(count--) {
        u64 length=0,category=0,kind=0;
        if(!r.get(length,2)||length>512||length>bytes.size()-r.p)return reject(error,"invalid actor key length");
        std::string key(bytes.begin()+r.p,bytes.begin()+r.p+length);r.p+=length;
        if(!valid_key(key)||fields.count(key)||!r.get(category,1)||!r.get(kind,1))return reject(error,"invalid duplicate/truncated actor field");
        ActorField f;f.category=static_cast<FieldCategory>(category);
        if(f.category==FieldCategory::Scalar) {
            if(kind>static_cast<u8>(ScalarKind::Bool))return reject(error,"unknown scalar kind");
            f.scalar=static_cast<ScalarKind>(kind);
            if(!r.get(f.bits,width(f.scalar))||!valid_scalar(f.scalar,f.bits))return reject(error,"invalid scalar payload");
        } else if(f.category==FieldCategory::Reference||f.category==FieldCategory::Handle||f.category==FieldCategory::Token64) {
            if(kind>=static_cast<u8>(RefKind::Count))return reject(error,"unknown reference kind");
            f.reference=static_cast<RefKind>(kind);u64 slot=0;
            if(!r.get(f.target.owner,8)||!r.get(f.target.resource,8)||!r.get(slot,4))return reject(error,"truncated logical reference");
            f.target.slot=static_cast<u32>(slot);
        } else return reject(error,"unknown field category");
        fields.emplace(key,f);
    }
    if(r.p!=bytes.size())return reject(error,"trailing actor payload");
    output.swap(fields);return true;
}
bool validate_actor_fields(const ActorFields& fields,const std::vector<FieldSchema>& schema,const LogicalResolver& resolver,std::string& error) {
    if(fields.size()!=schema.size())return reject(error,"actor schema field count mismatch");
    std::set<std::string> seen;
    for(const auto& s:schema) {
        if(!seen.insert(s.key).second)return reject(error,"duplicate schema field");
        auto it=fields.find(s.key);if(it==fields.end())return reject(error,"missing actor field");
        const auto& f=it->second;
        if(s.strength!=ReferenceStrength::Weak &&
           (s.strength!=ReferenceStrength::StrongCreature || s.category!=FieldCategory::Reference || s.reference!=RefKind::Creature))
            return reject(error,"invalid reference strength contract");
        if(f.category!=s.category)return reject(error,"actor field category mismatch");
        if(f.category==FieldCategory::Scalar) {
            if(f.scalar!=s.scalar||!valid_scalar(f.scalar,f.bits))return reject(error,"actor scalar schema mismatch");
        } else {
            if(s.targetType.empty())return reject(error,"missing concrete reference contract");
            switch(s.ownership) {
            case ReferenceOwnership::AnyLive: case ReferenceOwnership::Self:
            case ReferenceOwnership::ActorSubobject: case ReferenceOwnership::Content:
            case ReferenceOwnership::ResourceSubobject: case ReferenceOwnership::ResourceSelf:break;
            default:return reject(error,"unknown reference ownership contract");
            }
            if(f.reference!=s.reference)return reject(error,"actor reference role mismatch");
            if(absent(f.target)) {if(!s.nullable)return reject(error,"required actor reference absent");}
            else {
                if((s.ownership==ReferenceOwnership::ResourceSelf || s.ownership==ReferenceOwnership::ResourceSubobject) &&
                   (f.target.owner || !f.target.resource))return reject(error,"resource subject reference encoding mismatch");
                if(!s.ownerLink.empty()) {
                    auto owner=fields.find(s.ownerLink);
                    if(s.ownership!=ReferenceOwnership::ActorSubobject || owner==fields.end() ||
                       owner->second.category!=FieldCategory::Reference || owner->second.reference!=RefKind::Creature ||
                       !owner->second.target.owner || owner->second.target.resource ||
                       f.target.owner!=owner->second.target.owner || f.target.resource)
                        return reject(error,"actor subobject owner link mismatch");
                }
            }
            // Nullability does not waive the compiled type, ownership, subject
            // context or declared owner-link contract supplied to the resolver.
            if(!resolver.validateTyped(s,f.target,error))return false;
        }
    }
    return true;
}
bool actor_i32(const ActorFields& f,const char* key,int& value,std::string& error) {
    auto it=f.find(key);if(it==f.end()||it->second.category!=FieldCategory::Scalar||it->second.scalar!=ScalarKind::S32)
        return reject(error,"missing signed discriminator");
    u32 v=static_cast<u32>(it->second.bits);s32 signedValue;std::memcpy(&signedValue,&v,4);value=signedValue;return true;
}
bool actor_u32(const ActorFields& f,const char* key,u32& value,std::string& error) {
    auto it=f.find(key);if(it==f.end()||it->second.category!=FieldCategory::Scalar||it->second.scalar!=ScalarKind::U32)
        return reject(error,"missing unsigned discriminator");
    value=static_cast<u32>(it->second.bits);return true;
}
bool FieldArchive::entry(const char* key,FieldCategory c,ScalarKind s,RefKind r,ActorField*& result) {
    if(!valid_key(key)||!visited.insert(key).second)return fail("invalid or repeated visitor key");
    if(operation==Mode::Capture) {
        if(fields.count(key))return fail("capture requires fresh fields");
        ActorField f;f.category=c;f.scalar=s;f.reference=r;result=&fields.emplace(key,f).first->second;return true;
    }
    auto it=fields.find(key);
    if(it==fields.end()||it->second.category!=c || (c==FieldCategory::Scalar ? it->second.scalar!=s : it->second.reference!=r))return fail("visitor schema mismatch");
    result=&it->second;return true;
}
bool FieldArchive::scalar(const char* key,ScalarKind k,void* value) {
    ActorField* f;
    if(!entry(key,FieldCategory::Scalar,k,RefKind::Creature,f))return false;
    if(operation==Mode::Capture)f->bits=scalar_bits(k,value);
    if(!valid_scalar(k,f->bits))return fail("invalid scalar value");
    if(operation!=Mode::Capture)scalar_value(k,f->bits,value);
    return true;
}
bool FieldArchive::reference(const char* key,RefKind k,void*& value) {
    ActorField* f;if(!entry(key,FieldCategory::Reference,ScalarKind::U8,k,f))return false;
    if(operation==Mode::Capture) {
        if(!value) {f->target={};return true;}
        return resolver.identify(key,k,value,f->target,error);
    }
    if(absent(f->target)){value=nullptr;return true;}
    if(!resolver.validate(key,k,f->target,error))return false;
    if(operation==Mode::Apply)return resolver.resolve(key,k,f->target,value,error);
    value=nullptr;return true;
}
bool FieldArchive::handle(const char* key,RefKind k,u32& value) {
    ActorField* f;if(!entry(key,FieldCategory::Handle,ScalarKind::U32,k,f))return false;
    if(operation==Mode::Capture)return resolver.identifyHandle(key,k,value,f->target,error);
    if(!absent(f->target)&&!resolver.validate(key,k,f->target,error))return false;
    if(operation==Mode::Apply)return resolver.resolveHandle(key,k,f->target,value,error);
    value=0;return true;
}
bool FieldArchive::finish() {return visited.size()==fields.size() || fail("unvisited actor fields");}
bool FieldArchive::token64(const char* key,RefKind k,u64& value) {
    ActorField* f;if(!entry(key,FieldCategory::Token64,ScalarKind::U64,k,f))return false;
    if(operation==Mode::Capture)return resolver.identifyToken(key,k,value,f->target,error);
    if(!absent(f->target)&&!resolver.validate(key,k,f->target,error))return false;
    if(operation==Mode::Apply)return resolver.resolveToken(key,k,f->target,value,error);
    value=0;return true;
}
}
