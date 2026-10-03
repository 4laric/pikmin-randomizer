#pragma once
#include <string>
class BTeki;
namespace p2hana {
bool resources(std::string&);
bool birth(BTeki*,unsigned uid,unsigned ordinal,std::string&);
bool registry(BTeki*,unsigned,std::string&);
bool has(const BTeki*);
bool active();
bool update(BTeki*);
bool clip(const BTeki*,const char*&,float&);
void forget(BTeki*);
}
