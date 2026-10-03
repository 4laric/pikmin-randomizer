#include "pc_p2_original_gas_save.h"
#include "pc_p2_original_gas_clock.h"
#include <cassert>
#include <limits>
#include <cstdio>
using namespace p2original::gas;
int main(){
 std::string bytes,e;Snapshot s;s.identity={std::string(64,'a'),1389546882u,0,0,1};s.health=150;s.position={1.2345678f,-12,99};
 assert(encodeSnapshot(s,bytes,e));Snapshot out;assert(decodeSnapshot(bytes,out,e));assert(out.identity==s.identity&&out.position.x==s.position.x);
 s.state=State::Attack;s.motion=1;s.sourceFrame=4;assert(!encodeSnapshot(s,bytes,e));s.sourceFrame=3.9f;s.health=0;s.finishMotion=true;s.checkLinks=false;s.bridge=std::string(64,'b')+":bridge#7";
 assert(encodeSnapshot(s,bytes,e)&&decodeSnapshot(bytes,out,e));assert(out.health==0&&out.finishMotion&&out.bridge==s.bridge); // zero HP pending END is alive state
 const auto good=bytes;const auto saved=out;
 for(auto bad:{std::string("P2OG2")+good.substr(5),good+" tail",good.substr(0,good.size()-1),std::string(8193,'x'),good+"\n"}){assert(!decodeSnapshot(bad,out,e));assert(out.identity==saved.identity&&out.bridge==saved.bridge);}
 auto invalid=s;invalid.identity.activation=0;assert(!encodeSnapshot(invalid,bytes,e)&&bytes==good);invalid=s;invalid.health=std::numeric_limits<float>::infinity();assert(!encodeSnapshot(invalid,bytes,e));
 invalid=s;invalid.gate="gate";assert(!encodeSnapshot(invalid,bytes,e));invalid=s;invalid.state=State::Dead;invalid.motion=0;invalid.sourceFrame=0;invalid.finishMotion=false;invalid.generatorDeathCommitted=true;assert(encodeSnapshot(invalid,bytes,e)&&decodeSnapshot(bytes,out,e));
 // Source strict loop event: 3.9 does not reach int(timer)>3. Loop resets to
 // zero on 4, discarding overshoot. Finishing instead clamps3 and emits END.
 float frame=3;assert(!advanceAttack(frame,.03f,false)&&frame>3&&frame<4);assert(!advanceAttack(frame,.1f,false)&&frame==0);
 frame=3;assert(advanceAttack(frame,1.0f/30,true)&&frame==3);frame=0;assert(!advanceAttack(frame,.1f,true));
 std::puts("P2_ORIGINAL_GAS_SAVE_POLICY_PASS: bounded atomic codec and retail loop clock; no physical resume claim");
}
