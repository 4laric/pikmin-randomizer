// P2 small Breadbug appearance on an opted-in P1 Collec. P1 gameplay remains authoritative.
#include "pc_p2_breadbug_actor.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <SDL.h>
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <cmath>
#include <cstdlib>
#include <cstdio>
namespace {
struct Motion {int duration=0;std::vector<int> frames;std::vector<Shape*> shapes;};
struct BreadbugProxyActor {unsigned id;unsigned started;int lastMotion=-1;bool logged=false;};
std::map<BTeki*,BreadbugProxyActor> actors;Motion motions[2];
void fail(){std::fputs("P2_BREADBUG_ACTOR invalid P1 proxy profile\n",stderr);std::abort();}
Shape* load(const std::string& name){
 std::ifstream in("assets/dataDir/courses/pikmin2room/"+name,std::ios::binary|std::ios::ate);if(!in)fail();auto size=in.tellg();if(size<=0||size>16*1024*1024)fail();in.seekg(0);
 std::vector<unsigned char> bytes(size_t(size),0),resources;if(!in.read(reinterpret_cast<char*>(bytes.data()),size)||!p2animation::resources(bytes,resources))fail();
 Shape* shape=gameflow.loadShape(("courses/pikmin2room/"+name).c_str(),true);if(!shape)fail();
 for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();return shape;
}
}
void pc_p2_breadbug_actor_reset(){actors.clear();for(auto& motion:motions)motion=Motion{};}
void pc_p2_breadbug_actor_forget(BTeki* actor){actors.erase(actor);}
void pc_p2_breadbug_actor_setup(){
 pc_p2_breadbug_actor_reset();if(!pc_pikipelago_room_preview())return;std::ifstream in("p2-breadbug-actor.txt");if(!in)return;
 std::string word;if(!(in>>word)||word!="P2_BREADBUG_ACTOR_PROXY_1"||!tekiMgr)fail();
 for(int k=0;k<2;++k){int count;auto& motion=motions[k];if(!(in>>word>>motion.duration>>count)||word!=(k?"move":"wait")||motion.duration<2||motion.duration>10000||count<2||count>12)fail();
  for(int i=0;i<count;++i){int frame;if(!(in>>frame)||frame<0||frame>=motion.duration||(i&&frame<=motion.frames.back()))fail();motion.frames.push_back(frame);}
  if(motion.frames.front()!=0||motion.frames.back()!=motion.duration-1)fail();
 }
 int count;if(!(in>>count)||count<1||count>8)fail();std::set<unsigned> wanted;
 for(int i=0;i<count;++i){unsigned long long id;int kind;if(!(in>>id>>kind)||id>0xffffffffULL||kind!=TEKI_Collec||!wanted.insert(unsigned(id)).second)fail();}
 if(in>>word)fail();std::set<unsigned> found;
 Iterator it(tekiMgr);CI_LOOP(it){Teki* actor=static_cast<Teki*>(*it);if(!actor||!actor->mGenerator)continue;unsigned id=actor->mGenerator->_70;if(!wanted.count(id))continue;
  if(actor->mTekiType!=TEKI_Collec||!found.insert(id).second)fail();actors.emplace(actor,BreadbugProxyActor{id,SDL_GetTicks()});
  std::printf("P2_BREADBUG_ACTOR_READY generator=%u native_type=8 xyz=%.6f,%.6f,%.6f behavior=P1_Collec_proxy\n",id,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);
 }
 if(found!=wanted)fail();
 for(int k=0;k<2;++k)for(size_t i=0;i<motions[k].frames.size();++i){char name[80];std::snprintf(name,sizeof(name),"breadbug_actor_%s_%02u.mod",k?"move":"wait",unsigned(i));motions[k].shapes.push_back(load(name));}
}
bool pc_p2_breadbug_actor_draw(BTeki* actor,Graphics& gfx,const Matrix4f& view){
 auto found=actors.find(actor);if(found==actors.end()||!actor->isAlive()||!gfx.mCamera)return false;
 auto& state=found->second;const int kind=actor->mVelocity.x*actor->mVelocity.x+actor->mVelocity.z*actor->mVelocity.z>1.f?1:0;
 if(kind!=state.lastMotion){state.lastMotion=kind;state.started=SDL_GetTicks();}
 auto& motion=motions[kind];const float frame=std::fmod(float(SDL_GetTicks()-state.started)*.03f,float(motion.duration));size_t best=0;
 for(size_t i=1;i<motion.frames.size();++i)if(std::fabs(float(motion.frames[i])-frame)<std::fabs(float(motion.frames[best])-frame))best=i;
 Shape* shape=motion.shapes[best];shape->updateAnim(gfx,view,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);
 if(!state.logged){std::printf("P2_BREADBUG_ACTOR_DRAW generator=%u visual_proxy no_P2_FSM\n",state.id);state.logged=true;}return true;
}
