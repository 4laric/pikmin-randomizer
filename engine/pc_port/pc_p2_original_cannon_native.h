#pragma once
#include "pc_p2_original_cannon.h"
#include <memory>
class BTeki;
namespace p2original { namespace cannon {
// The shared original corpse owner verifies a real source-specific profile
// and the native death hook before this family is admitted. Null refuses.
using CorpseResources=bool(*)(unsigned source,std::string& error);
class Native {
public:
 explicit Native(CorpseResources=nullptr);~Native();
 Native(const Native&)=delete;Native& operator=(const Native&)=delete;
 Provider& provider();
 void retired(Creature*);
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
void pc_p2_original_cannon_forget(BTeki*);
bool pc_p2_original_cannon_admitted();
