#include "pc_p2_sheargrub.h"
#include "pc_p2_animation.h"
#include "pc_p2_uji_animation.h"
#include "Material.h"
#include "pc_bbft.h"
#include "pc_p2_preview.h"
#include "teki.h"
#include "Generator.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include <map>
#include <set>
#include <string>
#include <fstream>
#include <vector>
#include <cstdlib>
#include <cstdio>
namespace {
struct Entry { unsigned generator;int species; };
std::map<PelletView*,Entry> actors;
Shape* shapes[2][2]={{nullptr,nullptr},{nullptr,nullptr}};
const char* ids[]={"UjiA","UjiB"};
std::map<std::string,std::vector<Shape*>> animated[2];
std::map<std::string,p2animation::Clip> timing[2];
void loadAnimation(){
    std::ifstream input("p2-sheargrub-animation.txt");if(!input)return;
    std::vector<p2animation::Clip> banks[2];if(!p2uji::parse(input,banks))std::abort();
    size_t total=0;
    for(int kind=0;kind<2;++kind){std::vector<unsigned char> reference;
        for(const auto& clip:banks[kind]){size_t clipBytes=0;
            for(int i=0;i<clip.count;++i){char path[192];std::snprintf(path,sizeof(path),"assets/dataDir/courses/pikmin2room/uji_%s_%s_%02d.mod",ids[kind],clip.name.c_str(),i);
                std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)std::abort();auto size=file.tellg();
                if(size<=0||size>256*1024)std::abort();clipBytes+=size_t(size);total+=size_t(size);
                if(clipBytes>256*1024||total>2*1024*1024)std::abort();file.seekg(0);
                std::vector<unsigned char> bytes(size_t(size),0),resources;
                if(!file.read(reinterpret_cast<char*>(bytes.data()),size)||!p2animation::resources(bytes,resources))std::abort();
                if(!reference.empty()&&reference!=resources)std::abort();reference=resources;
            }
        }
    }
    for(int kind=0;kind<2;++kind){Shape* shared=nullptr;
        for(const auto& clip:banks[kind]){timing[kind][clip.name]=clip;
            for(int i=0;i<clip.count;++i){char path[160];std::snprintf(path,sizeof(path),"courses/pikmin2room/uji_%s_%s_%02d.mod",ids[kind],clip.name.c_str(),i);
                Shape* shape=gameflow.loadShape(path,true);if(!shape)std::abort();
                if(!shared){shared=shape;for(int t=0;t<shape->mTexAttrCount;++t)if(shape->mTexAttrList[t].mTexture)shape->mTexAttrList[t].mTexture->attach();}
                else{
                    if(shape->mMaterialCount!=shared->mMaterialCount||shape->mTexAttrCount!=shared->mTexAttrCount||shape->mTevInfoCount!=shared->mTevInfoCount)std::abort();
                    for(int j=0;j<shape->mTotalMatpolyCount;++j){auto* poly=shape->mMatpolyList[j];if(!poly||!poly->mMaterial)continue;int material=-1;
                        for(int m=0;m<shape->mMaterialCount;++m)if(poly->mMaterial==&shape->mMaterialList[m])material=m;
                        if(material<0)std::abort();poly->mMaterial=&shared->mMaterialList[material];}
                    shape->mMaterialList=shared->mMaterialList;shape->mTexAttrList=shared->mTexAttrList;shape->mTevInfoList=shared->mTevInfoList;
                }
                animated[kind][clip.name].push_back(shape);
            }
        }
    }
    std::printf("P2_UJI_ANIMATION_READY mod_bytes=%zu gameplay=P1_unchanged\n",total);
}
const char* motionClip(int motion,int kind){
    switch(motion){case TekiMotion::Dead:return "dead";case TekiMotion::Damage:return "dead_p";
    case TekiMotion::WaitAct1:return "appear";case TekiMotion::WaitAct2:return "dive";
    case TekiMotion::Move1:return "move";case TekiMotion::Attack:return "attack1";
    case TekiMotion::Type1:return kind?"attack2":nullptr;case TekiMotion::Type2:return kind?"eat":nullptr;default:return nullptr;}
}
}
void pc_p2_sheargrub_reset(){actors.clear();for(auto& bank:animated)bank.clear();for(auto& bank:timing)bank.clear();for(auto& pair:shapes)for(auto& shape:pair)shape=nullptr;}
void pc_p2_sheargrub_forget(BTeki* actor){actors.erase(static_cast<PelletView*>(actor));}
const char* pc_p2_sheargrub_name(PelletView* view){auto it=actors.find(view);return it==actors.end()?nullptr:ids[it->second.species];}
bool pc_p2_sheargrub_receipt(PelletView* view,unsigned& generator,int& value){auto it=actors.find(view);if(it==actors.end())return false;generator=it->second.generator;value=it->second.species+1;return true;}
void pc_p2_sheargrub_setup(){
    pc_p2_sheargrub_reset();if(!pc_pikipelago_room_preview())return;
    std::ifstream input("p2-sheargrub.txt");if(!input)return;
    std::string magic;int count;if(!(input>>magic>>count)||magic!="P2_SHEARGRUB_1"||count<1||count>100||!pc_p2_preview_goal())std::abort();
    std::map<unsigned,int> wanted;std::set<int> species;
    for(int i=0;i<count;++i){unsigned long long id;std::string name;int value;if(!(input>>id>>name>>value)||id>0xffffffffULL)std::abort();int kind=name=="UjiA"?0:name=="UjiB"?1:-1;if(kind<0||value!=kind+1||!wanted.emplace(unsigned(id),kind).second)std::abort();species.insert(kind);}
    if(input>>magic)std::abort();
    // Validate all four bounded model files before uploading source textures.
    for(int kind:species)for(int dead=0;dead<2;++dead){
        std::string path="assets/dataDir/courses/pikmin2room/uji_"+std::string(ids[kind])+(dead?"_dead.mod":"_live.mod");
        std::ifstream file(path,std::ios::binary|std::ios::ate);if(!file)std::abort();auto size=file.tellg();if(size<=0||size>16*1024*1024)std::abort();file.seekg(0);std::vector<unsigned char> bytes(size_t(size),0),resources;if(!file.read(reinterpret_cast<char*>(bytes.data()),size)||!p2animation::resources(bytes,resources))std::abort();
    }
    Iterator it(tekiMgr);CI_LOOP(it){Teki* teki=static_cast<Teki*>(*it);if(!teki||!teki->mGenerator)continue;auto found=wanted.find(teki->mGenerator->_70);if(found==wanted.end())continue;int kind=found->second;if(teki->mTekiType!=(kind?TEKI_KabekuiB:TEKI_KabekuiA))std::abort();actors[static_cast<PelletView*>(teki)]={found->first,kind};wanted.erase(found);std::printf("P2_UJI_READY species=%s generator=%u behavior=P1_proxy corpse_value=%d\n",ids[kind],teki->mGenerator->_70,kind+1);}
    if(!wanted.empty())std::abort();
    for(int kind:species)for(int dead=0;dead<2;++dead){std::string path="courses/pikmin2room/uji_"+std::string(ids[kind])+(dead?"_dead.mod":"_live.mod");Shape* shape=gameflow.loadShape(path.c_str(),true);if(!shape)std::abort();for(int i=0;i<shape->mTexAttrCount;++i)if(shape->mTexAttrList[i].mTexture)shape->mTexAttrList[i].mTexture->attach();shapes[kind][dead]=shape;}
    loadAnimation();
}
bool pc_p2_sheargrub_draw(BTeki* actor,Graphics& gfx,const Matrix4f& matrix,bool corpse){
    auto it=actors.find(static_cast<PelletView*>(actor));if(it==actors.end())return false;
    int kind=it->second.species;Shape* shape=shapes[kind][corpse?1:0];
    if(!animated[kind].empty()){
        const char* name=corpse?"dead":motionClip(actor->mTekiAnimator->getCurrentMotionIndex(),kind);
        if(name){int frames=actor->mTekiAnimator->getFrameCount();float phase=frames>1?actor->mTekiAnimator->getCounter()/(frames-1):0;
            if(!corpse&&actor->mStateID==1)phase=0;
            shape=animated[kind].at(name).at(timing[kind].at(name).index(phase,corpse));}
    }
    if(!shape)std::abort();shape->updateAnim(gfx,matrix,nullptr,actor);shape->drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
