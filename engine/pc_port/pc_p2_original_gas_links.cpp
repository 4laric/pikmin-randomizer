#include "pc_p2_original_gas_links.h"
#include <cmath>
#include <set>
namespace p2original { namespace gas { namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool valid(const std::vector<SourceStructureLink>& rows,std::string& e){
 std::set<std::string> identities;
 for(const auto& r:rows)if(r.identity.empty()||!identities.insert(r.identity).second||!std::isfinite(r.position.x)||!std::isfinite(r.position.y)||!std::isfinite(r.position.z))return fail(e,"GasHiba actual source structure registry identity/position invalid");
 return true;
}
}
bool Links::linksReady(std::string& e){
 if(!mReaders.surfaceStory||!mReaders.bridges||!mReaders.gates||!mReaders.bridgeStage||!mReaders.gateAlive)return fail(e,"GasHiba actual original Bridge/Gate producer callbacks missing");
 std::vector<SourceStructureLink> bridges,gates;
 if(!mReaders.bridges(bridges,e)||!valid(bridges,e)||!mReaders.gates(gates,e)||!valid(gates,e))return false;
 e.clear();return true;
}
bool Links::surfaceStory()const{return mReaders.surfaceStory&&mReaders.surfaceStory();}
bool Links::livingLinks(Position pipe,void*& bridge,void*& gate,std::string& e){
 bridge=gate=nullptr;if(!surfaceStory()){e.clear();return true;}
 if(!mReaders.bridges||!mReaders.gates)return fail(e,"GasHiba source structure readers unavailable");
 std::vector<SourceStructureLink> rows;
 if(!mReaders.bridges(rows,e)||!valid(rows,e))return false;
 for(const auto& row:rows)if(nearbyLink(pipe,row.position)){auto key=std::make_pair(true,row.identity);auto i=mRefs.emplace(key,Ref{row.identity,true}).first;bridge=&i->second;e.clear();return true;}
 rows.clear();if(!mReaders.gates(rows,e)||!valid(rows,e))return false;
 for(const auto& row:rows)if(nearbyLink(pipe,row.position)){auto key=std::make_pair(false,row.identity);auto i=mRefs.emplace(key,Ref{row.identity,false}).first;gate=&i->second;e.clear();return true;}
 e.clear();return true;
}
Links::Ref* Links::lookup(void* handle){for(auto& entry:mRefs)if(&entry.second==handle)return &entry.second;return nullptr;}
bool Links::bridgeStage(void* handle,int& stage,std::string& e){auto* ref=lookup(handle);if(!ref||!ref->bridge||!mReaders.bridgeStage)return fail(e,"GasHiba Bridge reference is not an actual source binding");return mReaders.bridgeStage(ref->identity,stage,e);}
bool Links::gateAlive(void* handle,bool& alive,std::string& e){auto* ref=lookup(handle);if(!ref||ref->bridge||!mReaders.gateAlive)return fail(e,"GasHiba Gate reference is not an actual source binding");return mReaders.gateAlive(ref->identity,alive,e);}
bool Links::identity(void* handle,std::string& out,bool& bridge)const{for(const auto& entry:mRefs)if(&entry.second==handle){out=entry.second.identity;bridge=entry.second.bridge;return true;}return false;}
bool Links::resolveLink(const std::string& id,bool bridge,void*& out,std::string& e){
 out=nullptr;if(id.empty())return fail(e,"GasHiba saved structure identity empty");
 if(bridge){int stage;if(!mReaders.bridgeStage||!mReaders.bridgeStage(id,stage,e))return false;}
 else {bool alive;if(!mReaders.gateAlive||!mReaders.gateAlive(id,alive,e))return false;}
 auto i=mRefs.emplace(std::make_pair(bridge,id),Ref{id,bridge}).first;out=&i->second;e.clear();return true;
}
} }
