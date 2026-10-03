#pragma once
#include "pc_p2_original_catfish.h"
#include <memory>
class BTeki;
namespace p2original { namespace catfish {
class Native {
public:
 Native();~Native();
 Native(const Native&)=delete;Native& operator=(const Native&)=delete;
 Provider& provider();
 void retired(Creature*);
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }
void pc_p2_original_catfish_forget(BTeki*);
bool pc_p2_original_catfish_admitted();
