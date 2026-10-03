#pragma once
#include <string>
class Generator;
class Creature;
namespace p2original { class GroupCourse; }
p2original::GroupCourse& pc_p2_original_groups();
// handled is false for every ordinary/AP generator. A handled false return is
// a fatal original-course construction error; it must never fall back to P1.
bool pc_p2_original_generator_init(Generator*,bool& handled,std::string& error);
bool pc_p2_original_generator_death(Generator*,Creature*,bool& handled,std::string& error);

void pc_p2_original_native_retired(Creature*);
