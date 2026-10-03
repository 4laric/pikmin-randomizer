#include "pc_p2_original_shijimi_honey.h"
#include <cmath>
namespace p2original { namespace shijimi {
namespace {
bool reject(std::string& e,const char* message){e=message;return false;}
bool finite(const Position& p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
}
bool honeyOutcome(const Child& child,const Position& position,const Position& velocity,
 p2originalresource::ChildOutcome& out,std::string& e){
 using namespace p2originalresource;
 const auto& id=child.identity;
 if(!child.born||!child.initialized||child.retired||!child.dropAttempted||child.dropComplete||!finite(position)||!finite(velocity)
   ||id.emission||id.child>=5||unsigned(child.color)>2)return reject(e,"Spectralid Honey requires an actual pending source drop");
 ChildOutcome result;
 result.identity={{id.plant.catalog,id.plant.generator,id.plant.ordinal,id.plant.epoch,id.plant.activation},0,
                  {{EmitterKind::PlantSpectralid,0,id.child}}};
 if(!validChildIdentity(result.identity))return reject(e,"invalid canonical Spectralid Honey ancestry");
 result.kind=child.color==Color::Yellow?ChildKind::Nectar:child.color==Color::Red?ChildKind::Spicy:ChildKind::Bitter;
 result.position={position.x,position.y,position.z};result.velocity={velocity.x,velocity.y,velocity.z};
 // Source genItem sets position/velocity only; it does not transfer the
 // Spectralid's birth facing into the newly initialized Honey actor.
 result.attempted=true;
 out=std::move(result);e.clear();return true;
}
bool honeyOwner(const p2originalresource::ChildIdentity& child,Identity& out,std::string& e){
 using namespace p2originalresource;
 if(!validChildIdentity(child)||child.slot||child.ancestry.size()!=1
   ||child.ancestry[0].kind!=EmitterKind::PlantSpectralid||child.ancestry[0].emissionOrdinal||child.ancestry[0].member>=5)return reject(e,"Honey does not belong to a source77 plant child");
 Identity result;
 result.plant={child.source.fingerprint,child.source.uid,child.source.ordinal,child.source.epoch,child.source.activation};
 result.emission=0;result.child=child.ancestry[0].member;out=std::move(result);e.clear();return true;
}
} }
