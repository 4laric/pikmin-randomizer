#pragma once
#include "pc_p2_kochappy_policy.h"
namespace p2original {namespace snow {
inline bool bank(std::istream& in,std::vector<p2animation::Clip>& out){
 std::string magic;if(!(in>>magic)||magic!="P2_SNOW_BANK_1")return false;
 std::ostringstream normalized;normalized<<"P2_KOCHAPPY_BANK_2 "<<in.rdbuf();std::istringstream parsed(normalized.str());
 return p2kochappy::originalBank(parsed,out);
}
}}
