#include "pc_p2_original_drop.h"
#include <cmath>
namespace p2original {namespace {
bool fail(std::string& e,const char* s){e=s;return false;}
bool draw(const DropIO& io,float& out,std::string& e){
 if(!io.draw(out,e))return false;
 return (std::isfinite(out)&&out>=0&&out<=1)?true:fail(e,"original drop unit RNG invalid");
}
}
bool validateOriginalDrop(const EnemyRecord& r,std::string& e){
 if(!validateOriginalRecord(r,e))return false;
 if(r.pelletColor>3||(r.pelletSize!=1&&r.pelletSize!=5&&r.pelletSize!=10&&r.pelletSize!=20))return fail(e,"original number pellet color/size unsupported");
 e.clear();return true;
}
bool throwOriginalItems(const EnemyRecord& r,const DropIO& io,std::string& e){
 if(!validateOriginalDrop(r,e)||!io.draw||!io.number||!io.velocity||(r.treasureCode&&!io.treasure))return fail(e,"original drop record/physical callback missing");
 // Source treasure-first branch performs no common number-drop RNG draws.
 if(r.treasureCode&&!io.treasure(r.treasureCode,e))return false;
 float chance=0;if(!draw(io,chance,e))return false;
 if(!(chance<r.pelletProbability)){e.clear();return true;}
 float countDraw=0;if(!draw(io,countDraw,e))return false;
 float range=(float(r.pelletMaximum)-float(r.pelletMinimum))*countDraw;
 range=range>=0?range+0.5f:range-0.5f;
 const int amount=int(r.pelletMinimum)+int(range);
 const float speed=r.pelletSize==1?150.0f:r.pelletSize==5?200.0f:250.0f;
 for(int i=0;i<amount;++i){
  unsigned color=r.pelletColor;
  if(color==3){float colorDraw=0;if(!draw(io,colorDraw,e))return false;color=unsigned(colorDraw*3.0f);}
  void* pellet=nullptr;if(!io.number(r.pelletSize,color,pellet,e))return false;
  if(!pellet)continue;
  // Explicit port order X then Z avoids C++ argument-evaluation differences.
  // Binary-level MW axis evaluation has not been claimed by this source port.
  float x=0,z=0;if(!draw(io,x,e)||!draw(io,z,e))return false;
  if(!io.velocity(pellet,{speed*(x-0.5f),speed,speed*(z-0.5f)},e))return false;
 }
 e.clear();return true;
}
}
