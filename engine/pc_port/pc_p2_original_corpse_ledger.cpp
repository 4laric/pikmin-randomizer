#include "pc_p2_original_corpse_ledger.h"
#include <limits>
#include <set>

namespace p2original {
namespace {
constexpr std::size_t maxRecords=corpseSnapshotMaxRecords;
constexpr std::size_t headerSize=80, recordSize=33;
const std::uint8_t magic[8]={'P','2','C','O','R','P','S','E'};
bool fail(std::string& e,const char* text){e=text;return false;}
bool fingerprint(const std::string& s){if(s.size()!=64)return false;for(char c:s)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;return true;}
bool valid(const CorpseRecord& r,const std::string& catalog){
 return validCorpseIdentity(r.identity,catalog)&&r.sourceType<=65535&&r.sourceType!=55&&
 r.yield>0&&r.yield<=65535;
}
bool validate(const CorpseSnapshot& s,std::string& e){
 if(s.schema!=1||!fingerprint(s.catalog)||s.records.size()>maxRecords)return fail(e,"invalid corpse snapshot envelope");
 std::set<InstanceIdentity> ids;
 for(const auto& r:s.records)if(!valid(r,s.catalog)||!ids.insert(r.identity).second)return fail(e,"malformed or duplicate corpse record");
 return true;
}
void put(std::vector<std::uint8_t>& out,std::uint64_t v,unsigned n){for(unsigned i=0;i<n;++i){out.push_back(static_cast<std::uint8_t>(v));v>>=8;}}
std::uint64_t get(const std::vector<std::uint8_t>& in,std::size_t& p,unsigned n){std::uint64_t v=0;for(unsigned i=0;i<n;++i)v|=std::uint64_t(in[p++])<<(8*i);return v;}
}
bool validCorpseIdentity(const InstanceIdentity& id,const std::string& catalog){
 return fingerprint(catalog)&&id.catalog==catalog&&
  (id.generator&0xff000000u)==0x52000000u&&id.ordinal<10&&id.epoch&&id.activation;
}
bool encodeCorpseSnapshot(const CorpseSnapshot& s,std::vector<std::uint8_t>& out,std::string& e){
 if(!validate(s,e))return false;
 std::vector<std::uint8_t> candidate;candidate.reserve(headerSize+s.records.size()*recordSize);
 candidate.insert(candidate.end(),magic,magic+8);put(candidate,1,4);
 candidate.insert(candidate.end(),s.catalog.begin(),s.catalog.end());put(candidate,s.records.size(),4);
 for(const auto& r:s.records){put(candidate,r.identity.generator,4);put(candidate,r.identity.ordinal,4);put(candidate,r.identity.epoch,8);put(candidate,r.identity.activation,8);put(candidate,r.sourceType,4);put(candidate,r.yield,4);put(candidate,r.consumed?1:0,1);}
 out.swap(candidate);e.clear();return true;
}
bool decodeCorpseSnapshot(const std::vector<std::uint8_t>& in,CorpseSnapshot& out,std::string& e){
 if(in.size()<headerSize||in.size()>corpsePayloadMaxBytes)return fail(e,"invalid corpse payload size");
 for(unsigned i=0;i<8;++i)if(in[i]!=magic[i])return fail(e,"invalid corpse payload magic");
 std::size_t p=8;CorpseSnapshot candidate;candidate.schema=static_cast<unsigned>(get(in,p,4));
 candidate.catalog.assign(in.begin()+p,in.begin()+p+64);p+=64;
 const auto count=get(in,p,4);
 if(count>maxRecords||in.size()!=headerSize+count*recordSize)return fail(e,"invalid corpse payload count or trailing bytes");
 candidate.records.reserve(static_cast<std::size_t>(count));
 for(std::size_t i=0;i<count;++i){CorpseRecord r;r.identity.catalog=candidate.catalog;r.identity.generator=static_cast<unsigned>(get(in,p,4));r.identity.ordinal=static_cast<unsigned>(get(in,p,4));r.identity.epoch=get(in,p,8);r.identity.activation=get(in,p,8);r.sourceType=static_cast<unsigned>(get(in,p,4));r.yield=static_cast<unsigned>(get(in,p,4));const auto consumed=get(in,p,1);if(consumed>1)return fail(e,"invalid corpse consumed flag");r.consumed=consumed!=0;candidate.records.push_back(r);}
 if(!validate(candidate,e))return false;
 out=std::move(candidate);e.clear();return true;
}
bool CorpseLedger::bind(const void* pellet,const InstanceIdentity& id,std::uint64_t& handle,std::string& e){
 if(!pellet||mPellets.count(pellet)||mNextHandle==std::numeric_limits<std::uint64_t>::max())return fail(e,"invalid or already bound corpse pointer");
 for(const auto& p:mPellets)if(p.second.identity==id)return fail(e,"corpse identity already has a live pellet");
 const auto next=mNextHandle;mPellets.emplace(pellet,Binding{next,id});++mNextHandle;handle=next;e.clear();return true;
}
bool CorpseLedger::birth(const void* pellet,const InstanceIdentity& id,unsigned source,unsigned yield,std::uint64_t& handle,std::string& e){
 CorpseRecord r{id,source,yield,false};
 if(!valid(r,mCatalog)||mRecords.size()>=maxRecords||mRecords.count(id))return fail(e,"invalid or reused corpse identity/profile");
 auto added=mRecords.emplace(id,r);
 try{if(bind(pellet,id,handle,e))return true;}catch(...){mRecords.erase(added.first);throw;}
 mRecords.erase(added.first);return false;
}
bool CorpseLedger::rebind(const void* pellet,const InstanceIdentity& id,std::uint64_t& handle,std::string& e){
 auto r=mRecords.find(id);if(r==mRecords.end()||r->second.consumed)return fail(e,"unknown or consumed corpse cannot be rebound");
 return bind(pellet,id,handle,e);
}
bool CorpseLedger::lookup(const void* pellet,std::uint64_t handle,CorpseRecord& out)const{
 auto p=mPellets.find(pellet);if(p==mPellets.end()||!handle||p->second.handle!=handle)return false;
 auto r=mRecords.find(p->second.identity);if(r==mRecords.end())return false;out=r->second;return true;
}
bool CorpseLedger::deliver(const void* pellet,std::uint64_t handle,unsigned& grant,std::string& e){
 grant=0;auto p=mPellets.find(pellet);if(p==mPellets.end()||!handle||p->second.handle!=handle)return fail(e,"stale or unknown corpse suction binding");
 auto r=mRecords.find(p->second.identity);if(r==mRecords.end())return fail(e,"corpse suction record missing");
 if(!r->second.consumed){grant=r->second.yield;r->second.consumed=true;}
 e.clear();return true;
}
bool CorpseLedger::forgetPellet(const void* pellet,std::uint64_t handle){auto p=mPellets.find(pellet);if(p==mPellets.end()||!handle||p->second.handle!=handle)return false;mPellets.erase(p);return true;}
CorpseSnapshot CorpseLedger::snapshot()const{CorpseSnapshot s;s.catalog=mCatalog;for(const auto& r:mRecords)s.records.push_back(r.second);return s;}
bool CorpseLedger::restore(const CorpseSnapshot& s,const Validator& verifier,std::string& e){
 if(!mRecords.empty()||!mPellets.empty())return fail(e,"corpse restore requires fresh ledger");
 if(s.catalog!=mCatalog||!verifier)return fail(e,"corpse restore catalog mismatch or missing profile verifier");
 if(!validate(s,e))return false;
 std::map<InstanceIdentity,CorpseRecord> candidate;
 for(const auto& r:s.records){if(!verifier(r,e))return false;candidate.emplace(r.identity,r);}
 mRecords.swap(candidate);e.clear();return true;
}
}
