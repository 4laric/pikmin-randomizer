#pragma once
#include "pc_p2_original_spawn_plan.h"
namespace p2original {
struct DropIO {
 std::function<bool(float&,std::string&)> draw;
 std::function<bool(int,std::string&)> treasure;
 // Null is an ordinary physical pool/birth failure. Only successful births
 // consume lateral velocity draws, matching EnemyBase::throwupItem.
 std::function<bool(unsigned,unsigned,void*&,std::string&)> number;
 std::function<bool(void*,const Position&,std::string&)> velocity;
};
bool validateOriginalDrop(const EnemyRecord&,std::string&);
bool throwOriginalItems(const EnemyRecord&,const DropIO&,std::string&);
}
