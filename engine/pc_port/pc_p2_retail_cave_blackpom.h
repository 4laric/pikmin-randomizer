#pragma once
#include "pc_p2_retail_cave_native.h"
#include "pc_p2_original_blackpom_native.h"
namespace p2retail {
// Actual SAVE/party owner must query current physical and cached Purple counts
// against this independently selected floor. No inferred/default population.
using BlackPomPopulation=std::function<bool(const Snapshot&,p2original::blackpom::BirthContext&,std::string&)>;
using BlackPomConsumer=std::function<bool(Pom*,const p2original::InstanceIdentity&,unsigned,std::string&)>;
// Consumer installs actual donor snapshot/head provenance before source start.
// Narrow bud-side proof for the typed body's Authority::bud implementation.
// Selected floor authority must independently verify real card/session/scene.
// This returns no donor lineage, campaign proof or SAVE publication authority.
bool verifyBlackPomBirth(const Snapshot&,const FloorIdentityAuthority&,const Pom*,unsigned token,
                         const p2original::InstanceIdentity&,BirthIdentity&,std::string&);
bool bindBlackPom(NativeFloor&,p2original::blackpom::Native&,BlackPomPopulation,BlackPomConsumer,std::string&);
}
