#pragma once
#include "pc_p2_original_gas_native.h"
#include <functional>
namespace p2original { namespace gas {
struct SourceStructureLink {std::string identity;Position position;};
// Readers enumerate actual source-owned bodies in retail manager order. Gate
// identity is the published original gate fullsourceSha:sourceKey. Bridge
// identity likewise belongs to its source producer, never a P1/AP obstacle ID.
// Empty lists are valid ONLY after a real producer census says zero active
// bodies. Absence of a producer is a missing callback, an admission refusal.
struct StructureReaders {
 std::function<bool()> surfaceStory;
 std::function<bool(std::vector<SourceStructureLink>&,std::string&)> bridges,gates;
 std::function<bool(const std::string&,int&,std::string&)> bridgeStage;
 std::function<bool(const std::string&,bool&,std::string&)> gateAlive;
};
class Links:public Services {
public:
 explicit Links(StructureReaders readers):mReaders(std::move(readers)){}
 bool linksReady(std::string&)override;
 bool surfaceStory()const override;
 bool livingLinks(Position,void*&,void*&,std::string&)override;
 bool bridgeStage(void*,int&,std::string&)override;
 bool gateAlive(void*,bool&,std::string&)override;
 // Stable source identity for typed checkpoint payloads. Handle is transient.
 bool identity(void*,std::string&,bool& isBridge)const;
 bool linkIdentity(void* h,std::string& id,bool& bridge)const override{return identity(h,id,bridge);}
 bool resolveLink(const std::string&,bool,void*&,std::string&)override;
private:
 struct Ref {std::string identity;bool bridge=false;};
 StructureReaders mReaders;
 std::map<std::pair<bool,std::string>,Ref> mRefs;
 Ref* lookup(void*);
};
} }
