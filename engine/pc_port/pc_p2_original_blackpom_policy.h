#pragma once
// #1281: PomMgr::birth, source EnemyID_BlackPom (6). Conversion belongs to
// the qualified Purple mechanic; this leaf only decides actual source birth.
#include <cstdint>
#include <string>
namespace p2original { namespace blackpom {
struct BirthContext {
 bool inCave=false,story=false,section=false;
 std::string cave;
 unsigned floorIndex=0; // actual zero-based BaseGameSection::getCurrFloor
 std::uint32_t allPurple=0,cachedPurple=0;
};
inline bool suppressed(const BirthContext& c) {
 // Retail t_01 is the authenticated tutorial_1 cave; the cave owner supplies
 // this canonical identity, never a caller-authored engineering cave alias.
 return c.inCave&&c.story&&c.section&&(c.floorIndex<2||c.cave=="tutorial_1")
     &&std::uint64_t(c.allPurple)+c.cachedPurple>=20;
}
} }
