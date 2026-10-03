#include "pc_p2_original_barrel.h"
#include <cassert>
#include <cstdio>
using namespace p2original;
int main(){
 BarrelRecord r;r.uid=1379523090;r.sourceKey="tutorial/initgen.txt#10";r.sourceSha="ed81e18e4883c9dfc9a400db600e4a7a979592368797eedf4437eb5fb46bbb04";r.position={800,0,1380};r.rotation={0,135,0};
 std::string e;assert(validateBarrel(r,e));BarrelState s;
 assert(barrelDamage(s,4000));assert(s.health==0 && s.phase==BarrelPhase::Normal);
 assert(!barrelAnimate(s,1,70));assert(barrelDamage(s,10));assert(s.phase==BarrelPhase::Dying);
 assert(!barrelDamage(s,100));assert(!barrelAnimate(s,1,70));assert(s.animationFrame==30);
 std::vector<std::uint8_t> bytes;assert(barrelExport(r,s,70,bytes,e));assert(bytes.size()==112);
 BarrelState restored;assert(barrelImport(r,bytes,70,restored,e));assert(restored.animationFrame==30);
 auto wrong=r;wrong.rotation[1]=0;assert(!barrelImport(wrong,bytes,70,restored,e));assert(restored.animationFrame==30);
 auto bad=bytes;bad[78]^=1;assert(!barrelImport(r,bad,70,restored,e));assert(restored.animationFrame==30);
 assert(barrelAnimate(s,2,70));assert(barrelAnimate(restored,2,70));assert(s.phase==BarrelPhase::Retired && s.animationFrame==70);
 assert(!barrelAnimate(s,1,70));assert(barrelExport(r,s,70,bytes,e));assert(barrelImport(r,bytes,70,restored,e));
 std::puts("PASS ORIGINAL_BARREL_STATE strict_negative_death=1 typed_resume=1 source_reject=1 natural_gameplay=0");
}
