#include "pc_p2_original_spawn_plan.h"
#include <cmath>
#include <cstdio>
#include <limits>
using namespace p2original;
namespace {unsigned checks=0,failures=0;void check(bool v,const char* message){++checks;if(!v){++failures;std::printf("FAIL %s\n",message);}}}
int main(){
 unsigned draws=0,roots=0;std::vector<float> values;size_t next=0;
 Math m;
 m.draw=[&](float& out,std::string& e){++draws;if(next==values.size()){e="draw exhaustion";return false;}out=values[next++];return true;};
 m.sinCos=[](float a,float& sine,float& cosine,std::string&){sine=std::sin(a);cosine=std::cos(a);return true;};
 m.squareRoot=[&](float v,float& out,std::string&){++roots;out=std::sqrt(v);return true;};
 EnemyRecord r;r.uid=0x52000001;r.source=33;r.count=3;r.deathCount=1;r.position={10,20,30};r.offset={1,2,3};r.directionDegrees=193.359375f;r.treasureCode=841;r.generatorVersion="0001";r.generatorTail={"3","1","2"};
 SpawnPlan out;std::string e;
 check(planSpawns(r,m,out,e)&&out.positions.size()==2,"count minus death count preserved");
 check(draws==0&&roots==10,"center spawn consumes no random and five pair-distance iterations");
 check(out.positions[0].x==11&&out.positions[0].y==22&&out.positions[0].z==33&&out.positions[1].x==11,"coincident center pair follows literal zero-delta source correction");
 check(out.source.directionDegrees==r.directionDegrees&&out.source.treasureCode==841&&out.source.generatorTail==r.generatorTail,"raw facing treasure and complete opaque tail preserved");
 const auto previous=out.positions;r.count=11;check(!planSpawns(r,m,out,e)&&out.positions.size()==previous.size(),"ten-slot overflow refused atomically");r.count=3;r.deathCount=4;check(!planSpawns(r,m,out,e),"negative survivor count refused");r.deathCount=3;
 check(planSpawns(r,{},out,e)&&out.positions.empty(),"zero survivors needs no math or RNG");
 r.deathCount=0;r.count=1;r.source=0;check(planSpawns(r,m,out,e)&&out.source.source==0,"Pelplant zero source identity preserved without admission inference");
 check(planSpawns(r,{},out,e),"single center survivor requires no unused math callbacks");
 r.source=26;r.spawnType=2;r.appearRadius=60;values={0.25f,0.5f};draws=0;next=0;
 check(planSpawns(r,m,out,e)&&draws==2&&std::abs(out.positions[0].x-41)<0.001f&&std::abs(out.positions[0].z-33)<0.001f,"source circle uses angle then linear radius and retains center y");
 check(out.positions[0].y==22,"terrain projection deferred explicitly");
 r.count=2;r.appearRadius=10;values={0,0,0,1};draws=0;next=0;roots=0;
 check(planSpawns(r,m,out,e)&&draws==4,"noncenter two draws for every survivor");
 check(std::abs(out.positions[0].z-20.5f)<0.001f&&std::abs(out.positions[1].z-55.5f)<0.001f,"five source corrections separate pair to default35");
 r.enemySize=50;next=0;check(planSpawns(r,m,out,e)&&std::abs(out.positions[1].z-out.positions[0].z-50)<0.001f,"positive source enemy size replaces territory");
 r.enemySize=-1;next=0;check(planSpawns(r,m,out,e)&&std::abs(out.positions[1].z-out.positions[0].z-35)<0.001f,"nonpositive enemy size uses original35");
 unsigned floors=0;m.mapAvailable=true;m.floor=[&](const Position& p,float& height,std::string&){++floors;height=p.x+p.z;return true;};next=0;
 check(planSpawns(r,m,out,e)&&floors==2&&out.positions[0].y==out.positions[0].x+out.positions[0].z,"source terrain queries once per survivor after group correction");
 const auto projected=out.positions;m.floor=[](const Position&,float&,std::string& e){e="floor unavailable";return false;};next=0;check(!planSpawns(r,m,out,e)&&out.positions[0].y==projected[0].y,"terrain failure keeps output atomic; external RNG rollback belongs caller");
 m.floor={};check(!planSpawns(r,m,out,e),"present map requires actual floor adapter");m.mapAvailable=false;
 const auto stable=out.positions;next=0;values={2,0};check(!planSpawns(r,m,out,e)&&out.positions[0].z==stable[0].z,"invalid RNG refuses without output publication");
 r.uid=0;check(!planSpawns(r,m,out,e),"absent original stable UID refused");r.uid=1;r.source=65536;check(!planSpawns(r,m,out,e),"source ushort bound enforced");r.source=33;r.generatorVersion="000";check(!planSpawns(r,m,out,e),"four-byte source version required");r.generatorVersion="????";r.position.x=std::numeric_limits<float>::infinity();check(!planSpawns(r,m,out,e),"nonfinite position refused");r.position.x=10;
 r.pelletMaximum=256;check(!planSpawns(r,m,out,e),"pellet byte boundary enforced");r.pelletMaximum=8;r.treasureCode=32768;check(!planSpawns(r,m,out,e),"treasure signed-short boundary enforced");r.treasureCode=0;
 r.generatorTail={std::string(4097,'a')};check(!planSpawns(r,m,out,e),"bounded opaque tail retained or refused without dropping");
 std::printf("checks=%u failures=%u\n",checks,failures);return failures?1:0;
}
