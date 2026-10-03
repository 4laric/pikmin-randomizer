#include "pc_p2_original_spawn_plan.h"
#include <cmath>
#include <utility>
namespace p2original {
namespace {
bool finite(Position p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
bool reject(std::string& e,const char* message){e=message;return false;}
}
bool validateOriginalRecord(const EnemyRecord& r,std::string& e){
 if(!r.uid||r.source>65535||r.birthType>255||r.count>10||r.deathCount>r.count||r.spawnType>255
  ||!finite(r.position)||!finite(r.offset)||!std::isfinite(r.directionDegrees)||!std::isfinite(r.appearRadius)||!std::isfinite(r.enemySize)
  ||r.treasureCode<-32768||r.treasureCode>32767||r.pelletColor>255||r.pelletSize>255||r.pelletMinimum>255||r.pelletMaximum>255
  ||!std::isfinite(r.pelletProbability)||r.generatorVersion.size()!=4||r.generatorTail.size()>4096)
  return reject(e,"original enemy common field or ten-slot source limit invalid");
 for(const auto& value:r.generatorTail)if(value.size()>4096)return reject(e,"original species tail token exceeds bound");
 if(!finite({r.position.x+r.offset.x,r.position.y+r.offset.y,r.position.z+r.offset.z}))return reject(e,"original center overflow");
 e.clear();return true;
}
bool planSpawns(const EnemyRecord& r,const Math& math,SpawnPlan& out,std::string& e){
 if(!validateOriginalRecord(r,e))return false;
 const unsigned count=r.count-r.deathCount;
 if((count>1&&!math.squareRoot)||(count&&((math.mapAvailable&&!math.floor)||(r.spawnType!=1&&(!math.draw||!math.sinCos)))))return reject(e,"source-qualified original placement math adapter missing");
 const Position center{r.position.x+r.offset.x,r.position.y+r.offset.y,r.position.z+r.offset.z};
 if(!finite(center))return reject(e,"original center overflow");
 SpawnPlan next;next.source=r;next.positions.resize(count);
 constexpr float tau=6.28318530717958647692f;
 for(auto& p:next.positions){
  p=center;if(r.spawnType==1)continue;
  float angleDraw=0,radiusDraw=0,sine=0,cosine=0;
  if(!math.draw(angleDraw,e)||!math.draw(radiusDraw,e))return false;
  if(!std::isfinite(angleDraw)||!std::isfinite(radiusDraw)||angleDraw<0||angleDraw>1||radiusDraw<0||radiusDraw>1)return reject(e,"original placement RNG adapter returned invalid unit draw");
  const float angle=tau*angleDraw,radius=r.appearRadius*radiusDraw;
  if(!math.sinCos(angle,sine,cosine,e))return false;
  if(!std::isfinite(sine)||!std::isfinite(cosine)||!std::isfinite(radius))return reject(e,"original placement trig/radius invalid");
  p={center.x+radius*sine,center.y,center.z+radius*cosine};
  if(!finite(p))return reject(e,"original randomized position overflow");
 }
 const float territory=r.enemySize>0?r.enemySize:35.0f;
 std::vector<Position> corrections(count);
 for(unsigned iteration=0;iteration<5;++iteration){
  for(auto& p:corrections)p={};
  for(unsigned i=0;i<count;++i)for(unsigned j=i+1;j<count;++j){
   float dx=next.positions[i].x-next.positions[j].x,dy=next.positions[i].y-next.positions[j].y,dz=next.positions[i].z-next.positions[j].z;
   const float squared=dx*dx+dy*dy+dz*dz;float distance=0;
   if(!std::isfinite(squared)||!math.squareRoot(squared,distance,e))return reject(e,"original separation distance calculation failed");
   if(!std::isfinite(distance)||distance<0)return reject(e,"original root adapter returned invalid distance");
   if(distance<territory){
    // Retail calculates the root again inside the correction branch.
    float again=0;if(!math.squareRoot(squared,again,e))return false;
    if(!std::isfinite(again)||again<0)return reject(e,"original correction root adapter invalid");
    if(again>0){const float inverse=1.0f/again;dx*=inverse;dy*=inverse;dz*=inverse;}
    const float scale=(territory-distance)*0.5f;dx*=scale;dy*=scale;dz*=scale;
    corrections[i].x+=dx;corrections[i].y+=dy;corrections[i].z+=dz;
    corrections[j].x-=dx;corrections[j].y-=dy;corrections[j].z-=dz;
   }
  }
  for(unsigned i=0;i<count;++i){auto& p=next.positions[i];p.x+=corrections[i].x;p.y+=corrections[i].y;p.z+=corrections[i].z;if(!finite(p))return reject(e,"original pair separation overflow");}
 }
 // Retail projects each surviving actor only after all five corrections.
 if(math.mapAvailable)for(auto& position:next.positions){float height=0;if(!math.floor(position,height,e))return false;if(!std::isfinite(height))return reject(e,"original terrain adapter returned invalid height");position.y=height;}
 // Facing conversion and family birth follow in the engine adapter. Raw facing,
 // drops and complete tail remain unchanged; no actor or singleton is written.
 out=std::move(next);e.clear();return true;
}
}
