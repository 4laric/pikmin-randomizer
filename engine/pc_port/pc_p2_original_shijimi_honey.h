#pragma once
#include "pc_p2_original_shijimi_group.h"
#include "pc_p2_original_resource_contents.h"
class Creature;
namespace p2originalresource { namespace honey { class Manager; } }

namespace p2original { namespace shijimi {
// Shared Honey provenance is the actual plant incarnation plus a typed emitted
// source77 member. Neither the plant ordinal nor generator UID is repurposed.
bool honeyOutcome(const Child&,const Position&,const Position&,
                  p2originalresource::ChildOutcome&,std::string&);
bool honeyOwner(const p2originalresource::ChildIdentity&,Identity&,std::string&);
// Calls the real typed Honey manager: successful ItemHoney init(nullptr) draws
// from this same course RNG before the source color overwrites its random kind.
// A true/null result is the original pool-full failure, never a P1 nectar alias.
bool birthHoney(const Child&,const Position&,const Position&,
                p2originalresource::honey::Manager&,p2originalresource::Engine&,
                Creature*&,std::string&);
} }
