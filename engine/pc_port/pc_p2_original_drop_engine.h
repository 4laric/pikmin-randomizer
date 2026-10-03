#pragma once
#include <string>
#include <functional>
class BTeki;
struct Vector3f;
namespace p2original {struct CatalogRow;}
using PcOriginalDropGeometry=std::function<bool(BTeki*,Vector3f& position,Vector3f& treasureVelocity,std::string&)>;
bool pc_p2_original_drop_register_geometry(unsigned source,PcOriginalDropGeometry);
void pc_p2_original_drop_unregister_geometry(unsigned source);
bool pc_p2_original_drop_host_ready();
bool pc_p2_original_drop_resources(const p2original::CatalogRow&,std::string& error);
// Returns false only for an ordinary/AP actor. An original physical failure is
// fatal and may never fall through to P1 personality drops or nectar rolls.
bool pc_p2_original_spawn_items(BTeki*);
