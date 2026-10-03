#include "pc_p2_original_bridge.h"
#include <cassert>
#include <cmath>
#include <cstdio>
int main(){
 using namespace p2original;
 BridgeRecord r;r.uid=1377679251;r.sourceKey="tutorial/initgen.txt#11";r.sourceSha=std::string(64,'a');r.type=2;
 std::string e;assert(validateBridge(r,e));assert(bridgeStageCount(0)==6&&bridgeStageCount(1)==6&&bridgeStageCount(2)==15);
 auto s=bridgeInitial(r);assert(bridgeAttack(r,s,3000));assert(s.stage==0&&s.extensionTicks==40&&s.health[0]==0);
 assert(bridgeAttack(r,s,500));assert(s.health[0]==0); // pending extension ignores extra hits
 for(int i=0;i<39;++i)assert(!bridgeTick(r,s));assert(s.stage==0&&s.extensionTicks==1);
 std::vector<std::uint8_t> b;assert(bridgeExport(r,s,b,e));auto restored=bridgeInitial(r);assert(bridgeImport(r,b,restored,e));assert(restored.extensionTicks==1);assert(bridgeTick(r,restored)&&restored.stage==1);
 auto wrong=r;wrong.sourceSha[0]='b';auto unchanged=restored;assert(!bridgeImport(wrong,b,restored,e));assert(restored.stage==unchanged.stage);
 b[90]^=1;assert(!bridgeImport(r,b,restored,e));assert(restored.stage==unchanged.stage);
 assert(!bridgeBreak(r,restored,1000));assert(restored.stage==1&&restored.health[0]==1000);assert(bridgeExport(r,restored,b,e));assert(bridgeImport(r,b,s,e));
 assert(!bridgeBreak(r,restored,2000));assert(restored.stage==0&&restored.health[0]==3000);
 auto interrupted=bridgeInitial(r);for(int stage=0;stage<2;++stage){bridgeAttack(r,interrupted,3000);for(int i=0;i<40;++i)bridgeTick(r,interrupted);}bridgeAttack(r,interrupted,200);assert(!bridgeBreak(r,interrupted,3000));assert(interrupted.stage==1&&interrupted.health[2]==2800);assert(bridgeExport(r,interrupted,b,e));assert(bridgeImport(r,b,s,e)&&s.health[2]==2800&&s.stage==1);
 for(int stage=0;stage<15;++stage){assert(bridgeAttack(r,restored,3001));for(int i=0;i<40;++i)bridgeTick(r,restored);assert(restored.stage==stage+1);}
 assert(!bridgeAttack(r,restored,10));assert(bridgeExport(r,restored,b,e));assert(bridgeImport(r,b,s,e)&&s.stage==15);
 r.type=1;r.position={10,20,30};r.rotation[1]=90;auto p=bridgeStagePosition(r,3);assert(std::fabs(p[0]-52.5f)<0.001f&&p[1]==36&&std::fabs(p[2]-30)<0.001f);
 std::puts("P2_ORIGINAL_BRIDGE_STATE_PASS pending-extension source-cache break-rebuild sloped-placement");
}
