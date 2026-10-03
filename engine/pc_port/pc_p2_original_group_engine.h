#pragma once
#include <string>
#include "pc_p2_original_group.h"
class Generator;
class Creature;
namespace p2original { class GroupCourse; }
const p2original::GroupCourse& pc_p2_original_groups();
bool pc_p2_original_course_install(const std::vector<p2original::GroupBinding>&,p2original::GroupProvider&,std::string& error);
bool pc_p2_original_course_unload(std::string& error);
// handled is false for every ordinary/AP generator. A handled false return is
// a fatal original-course construction error; it must never fall back to P1.
bool pc_p2_original_generator_init(Generator*,bool& handled,std::string& error);
bool pc_p2_original_generator_death(Generator*,Creature*,bool& handled,std::string& error);

void pc_p2_original_native_retired(Creature*);
