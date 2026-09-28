// Optional P2 fire appearance on P1 Tank; water is a static noninteractive display.
#include "pc_p2_tank.h"
#include "pc_p2_tank_phase.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <vector>
#include <map>
#include <set>
#include <fstream>
#include <cmath>
#include <cstdlib>
#include <cstdio>
namespace {
const char* names[]={"dead","move1","flick","attack","waitact1","waitact2","type5"};
struct Clip{int duration;std::vector<int> frames;std::vector<Shape*> poses;};
Clip clips[7];std::map<BTeki*,unsigned> actors;std::set<BTeki*> logged;
Shape* water=nullptr;unsigned waterId=0;float xyz[3]={},yaw=0;bool waterLogged=false;size_t bytesTotal=0;
void fail(){std::fputs("P2_TANK_VISUAL invalid profile\n",stderr);std::abort();}
Shape* load(const std::string& name){
 std::ifstream file("assets/dataDir/courses/pikmin2room/"+name,std::ios::binary|std::ios::ate);if(!file)fail();auto size=file.tellg();if(size<=0||size>16*1024*1024||bytesTotal+size_t(size)>64*1024*1024)fail();bytesTotal+=size_t(size);file.seekg(0);
 std::vector<unsigned char> data(size_t(size),0),resources;if(!file.read(reinterpret_cast<char*>(data.data()),size)||!p2animation::resources(data,resources))fail();
 Shape* shape=gameflow.loadShape(("courses/pikmin2room/"+name).c_str(),true);if(!shape)fail();for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture)shape->mTexAttrList[t].mTexture->attach();return shape;
}
int motion(int native){switch(native){case TekiMotion::Move1:return 1;case TekiMotion::Flick:return 2;case TekiMotion::Attack:return 3;case TekiMotion::WaitAct1:return 4;case TekiMotion::WaitAct2:return 5;default:return -1;}}
}
void pc_p2_tank_reset(){actors.clear();logged.clear();for(auto& c:clips)c=Clip{};water=nullptr;waterLogged=false;bytesTotal=0;}
void pc_p2_tank_forget(BTeki* actor){actors.erase(actor);logged.erase(actor);}
void pc_p2_tank_setup(){
 pc_p2_tank_reset();if(!pc_pikipelago_room_preview())return;std::ifstream in("p2-tank-visual.txt");if(!in)return;std::string word;if(!(in>>word)||word!="P2_TANK_VISUAL_1"||!tekiMgr)fail();
 for(int k=0;k<7;++k){auto& c=clips[k];int count;if(!(in>>word>>c.duration>>count)||word!=names[k]||c.duration<2||c.duration>10000||count<2||count>40)fail();for(int i=0;i<count;++i){int frame;if(!(in>>frame)||frame<0||frame>=c.duration||(i&&frame<=c.frames.back()))fail();c.frames.push_back(frame);}if(c.frames.front()!=0||c.frames.back()!=c.duration-1)fail();}
 int count;if(!(in>>count)||count<1||count>8)fail();std::set<unsigned>wanted,found;
 for(int i=0;i<count;++i){unsigned long long id;int type;if(!(in>>id>>type)||id>0xffffffffULL||type!=TEKI_Tank||!wanted.insert(unsigned(id)).second)fail();}
 int display;if(!(in>>display)||display<0||display>1)fail();
 if(display){unsigned long long id;if(!(in>>id>>xyz[0]>>xyz[1]>>xyz[2]>>yaw)||id>0xffffffffULL||wanted.count(unsigned(id)))fail();waterId=unsigned(id);for(float v:xyz)if(!std::isfinite(v)||std::fabs(v)>100000)fail();if(!std::isfinite(yaw)||std::fabs(yaw)>360)fail();}
 if(in>>word)fail();Iterator it(tekiMgr);CI_LOOP(it){Teki* actor=static_cast<Teki*>(*it);if(!actor||!actor->mGenerator||!wanted.count(actor->mGenerator->_70))continue;unsigned id=actor->mGenerator->_70;if(actor->mTekiType!=TEKI_Tank||!found.insert(id).second)fail();actors.emplace(actor,id);}
 if(found!=wanted)fail();
 for(int k=0;k<7;++k)for(size_t i=0;i<clips[k].frames.size();++i){char file[96];std::snprintf(file,sizeof(file),"tank_fire_%s_%02u.mod",names[k],unsigned(i));clips[k].poses.push_back(load(file));}
 if(display){water=load("tank_water_static.mod");std::printf("P2_WTANK_DISPLAY_READY display=%u xyz=%.6f,%.6f,%.6f noninteractive_static_no_actor_no_collision_no_receiver\n",waterId,xyz[0],xyz[1],xyz[2]);}
 for(auto& entry:actors){auto* actor=entry.first;std::printf("P2_TANK_PROXY_READY generator=%u native_type=15 xyz=%.6f,%.6f,%.6f behavior=P1_fire_proxy\n",entry.second,actor->mSRT.t.x,actor->mSRT.t.y,actor->mSRT.t.z);}
}
bool pc_p2_tank_draw(BTeki* actor,Graphics& gfx,const Matrix4f& view){
 if(!actors.count(actor)||!actor->isAlive()||!gfx.mCamera||!actor->mTekiAnimator)return false;auto* anim=actor->mTekiAnimator;int k=motion(anim->getCurrentMotionIndex()),count=anim->getFrameCount();float counter=anim->getCounter();if(k<0||count<2||!std::isfinite(counter))return false;
 auto& c=clips[k];float frame;if(!p2tankvisual::frame(counter,count,c.duration,frame))return false;size_t best=0;for(size_t i=1;i<c.frames.size();++i)if(std::fabs(c.frames[i]-frame)<std::fabs(c.frames[best]-frame))best=i;
 Shape* shape=c.poses[best];shape->updateAnim(gfx,view,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);if(logged.insert(actor).second)std::printf("P2_TANK_PROXY_DRAW generator=%u source_clip=%s P1_gameplay_unchanged\n",actors[actor],names[k]);return true;
}
void pc_p2_tank_draw_water(Graphics& gfx){
 if(!water||!gfx.mCamera)return;gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);gfx.useMaterial(nullptr);gfx.setDepth(true);
 Matrix4f world,view;world.makeSRT(Vector3f(1,1,1),Vector3f(0,yaw*.0174532925199433f,0),Vector3f(xyz[0],xyz[1],xyz[2]));gfx.mCamera->mLookAtMtx.multiplyTo(world,view);water->updateAnim(gfx,view,nullptr,nullptr);water->drawshape(gfx,*gfx.mCamera,nullptr);
 if(!waterLogged){std::puts("P2_WTANK_DISPLAY_DRAW noninteractive_static_no_actor_no_collision_no_receiver");waterLogged=true;}
}
