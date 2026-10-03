#pragma once
#include "pc_p2_original_tank.h"
#include <memory>
class BTeki;
namespace p2original { namespace tank {
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
void pc_p2_original_tank_forget(BTeki*);
bool pc_p2_original_tank_admitted();
