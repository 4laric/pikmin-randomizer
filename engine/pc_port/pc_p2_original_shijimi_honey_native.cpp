#include "pc_p2_original_shijimi_honey.h"
#include "pc_p2_original_honey_native.h"

namespace p2original { namespace shijimi {
bool birthHoney(const Child& child,const Position& position,const Position& velocity,
 p2originalresource::honey::Manager& manager,p2originalresource::Engine& rng,
 Creature*& out,std::string& error){
 out=nullptr;
 p2originalresource::ChildOutcome outcome;
 if(!honeyOutcome(child,position,velocity,outcome,error))return false;
 const auto kind=child.color==Color::Yellow?p2originalresource::HoneyKind::Nectar:
                 child.color==Color::Red?p2originalresource::HoneyKind::Spicy:
                                        p2originalresource::HoneyKind::Bitter;
 return manager.birth(kind,outcome,rng,out,error);
}
} }
