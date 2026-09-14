#include "pc_p2_kurage_visual.h"
#include "Graphics.h"
#include "Shape.h"
#include "Texture.h"
#include "gameflow.h"
#include "sysNew.h"
#include "teki.h"
#include <filesystem>
namespace { Shape* sWait=nullptr; Shape* sAttack=nullptr; bool sReady=false;
Shape* load(const char* path){
    if(!std::filesystem::exists(std::filesystem::path("assets/dataDir")/path))return nullptr;
    const int heap=gsys->setHeap(SYSHEAP_App); Shape* shape=gameflow.loadShape(path,true);
    if(shape)for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();
    gsys->setHeap(heap); return shape;
}}
bool pc_p2_kurage_visual_setup(){if(sReady)return true;Shape* wait=load("courses/pikmin2room/kurage_wait.mod");Shape* attack=load("courses/pikmin2room/kurage_attack.mod");if(!wait||!attack)return false;sWait=wait;sAttack=attack;sReady=true;return true;}
void pc_p2_kurage_visual_reset(){sWait=nullptr;sAttack=nullptr;sReady=false;}
Shape* pc_p2_kurage_visual_wait_shape(){return sWait;}
Shape* pc_p2_kurage_visual_attack_shape(){return sAttack;}
bool pc_p2_kurage_visual_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){if(!sReady||!actor)return false;Shape* shape=corpse||actor->mTekiAnimator->getCurrentMotionIndex()!=TekiMotion::Attack?sWait:sAttack;if(!shape)return false;shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;}
