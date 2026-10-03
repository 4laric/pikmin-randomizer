#pragma once
#include <string>
class BTeki;
namespace p2original {struct CatalogRow;}
bool pc_p2_original_drop_resources(const p2original::CatalogRow&,std::string& error);
// Returns false only for an ordinary/AP actor. An original physical failure is
// fatal and may never fall through to P1 personality drops or nectar rolls.
bool pc_p2_original_spawn_items(BTeki*);
