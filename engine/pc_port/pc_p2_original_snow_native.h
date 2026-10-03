#pragma once
#include "pc_p2_original_snow.h"
#include <memory>
class BTeki;
namespace p2original { namespace snow {
class Native {
public:
 Native();~Native();
 Native(const Native&)=delete;Native& operator=(const Native&)=delete;
 Provider& provider();
 void retired(Creature*);
private:struct Impl;std::unique_ptr<Impl> m;
};
} }
void pc_p2_original_snow_forget(BTeki*);
bool pc_p2_original_snow_owned(const BTeki*);

struct Vector3f;
// Cave TekiInfo leaf. No surface GenEnemy version/tail is synthesized.
// The cave owner installs authenticated floor/source row identity separately.
bool pc_p2_snow_prepare_cave(std::string&);
bool pc_p2_snow_reserve_cave(unsigned count,std::string&);
bool pc_p2_snow_birth_cave(Generator*,const Vector3f&,float yaw,Creature*&,std::string&);
bool pc_p2_snow_bind_cave(Creature*,unsigned token,std::string&);
bool pc_p2_snow_release_cave(Creature*,unsigned token,std::string&);

void pc_p2_original_snow_resources_reset();
