#include "pc_p2_original_cave_native.h"
#include "Creature.h"
#include "Graphics.h"
#include "Camera.h"
#include "MapMgr.h"
#include "Stream.h"
#include "sysNew.h"
#include <map>
#include <set>
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
constexpr unsigned type=0x70326376u,version=0x43563031u; // p2cv / CV01
std::map<unsigned,p2original::CaveRecord> records;
std::map<const Generator*,unsigned> generators;
std::map<const Creature*,unsigned> actors;
bool admitted=false;
[[noreturn]] void fail(const char* e){std::fprintf(stderr,"P2_ORIGINAL_CAVE_FAIL %s\n",e);std::abort();}
const p2original::CaveRecord& row(unsigned uid){auto i=records.find(uid);if(i==records.end())fail("unknown Cave UID in installed source inventory");return i->second;}
void writeCache(unsigned uid,RandomAccessStream& s){std::string e;std::vector<std::uint8_t> b;
    if(!p2original::caveCache(row(uid),b,e)||s.getPending()<int(b.size()))fail("Cave cache write bound/source invalid");
    for(auto v:b)s.writeByte(v);
}
bool readCache(unsigned uid,RandomAccessStream& s,std::string& e){
    if(s.getPending()<104){e="truncated original Cave cache";return false;}
    std::vector<std::uint8_t> b(104);for(auto& v:b)v=s.readByte();return p2original::caveRestore(row(uid),b,e);
}
class CaveBody final:public Creature {
public:
    explicit CaveBody(unsigned id):Creature(nullptr),uid(id){mObjType=OBJTYPE_NULL;mHealth=1;}
    bool isOrganic()override{return false;}
    bool isAtari()override{return false;}
    bool isFixed()override{return true;}
    bool needShadow()override{return false;}
    void update()override {} // sparse owner; no P1 proxy AI/physics
    void doSave(RandomAccessStream& s)override {writeCache(uid,s);}
    void doLoad(RandomAccessStream& s)override {std::string e;if(!readCache(uid,s,e))fail(e.c_str());}
    void refresh(Graphics& gfx)override {
        const auto& p=mSRT.t;
        const auto old=gfx.mPrimaryColour,aux=gfx.mAuxiliaryColour;
        const int blend=gfx.setCBlending(BLEND_Alpha),cull=gfx.setCullFront(2);
        const bool depth=gfx.setDepth(true),light=gfx.setLighting(false,nullptr);
        auto* texture=gfx.mActiveTexture[0];gfx.useMaterial(nullptr);gfx.useTexture(nullptr,0);
        gfx.useMatrix(gfx.mCamera->mLookAtMtx,0);
        auto point=[&](float t,float radius,float h){return Vector3f(p.x+std::cos(t)*radius,p.y+h,p.z+std::sin(t)*radius);};
        auto tri=[&](Vector3f a,Vector3f b,Vector3f c,Colour color){const Vector3f v[]={a,b,c};const Vector2f uv[]={Vector2f(0,0),Vector2f(0,0),Vector2f(0,0)};gfx.setColour(color,true);gfx.drawOneTri(v,nullptr,uv,3);};
        for(int i=0;i<24;++i){const float t=mFaceDirection+i*6.28318530718f/24,u=mFaceDirection+(i+1)*6.28318530718f/24;
            const auto a=point(t,30,4),b=point(u,30,4),c=point(t,52,14),d=point(u,52,14);
            tri(a,b,d,Colour(166,149,118,255));tri(a,d,c,Colour(139,123,99,255));
            tri(c,d,point(u,59,0),Colour(89,78,61,255));tri(c,point(u,59,0),point(t,59,0),Colour(89,78,61,255));
            tri(Vector3f(p.x,p.y+3,p.z),b,a,Colour(17,21,27,255));
        }
        gfx.setColour(old,true);gfx.mAuxiliaryColour=aux;gfx.setCBlending(blend);
        gfx.useTexture(texture,0);gfx.setLighting(light,nullptr);gfx.setDepth(depth);gfx.setCullFront(cull);
    }
protected:
    void doKill()override {actors.erase(this);}
private:unsigned uid;
};
std::vector<CaveBody*> allocations;
GenObject* make(){return new GenObjectOriginalCave;}
struct AppHeap {int previous;AppHeap():previous(gsys->setHeap(SYSHEAP_App)){}~AppHeap(){gsys->setHeap(previous);}};
}
bool pc_p2_original_cave_install(const std::vector<p2original::CaveRecord>& rows,std::string& e){
    if(!records.empty()||!generators.empty()||!actors.empty()||rows.empty()||rows.size()>4096){e="Cave inventory installed or invalid envelope";return false;}
    std::map<unsigned,p2original::CaveRecord> next;std::set<std::string> keys;
    for(const auto& r:rows){if(!p2original::validateCave(r,e))return false;if(!next.emplace(r.uid,r).second||!keys.insert(r.sourceKey).second){e="duplicate Cave source identity";return false;}}
    records.swap(next);e.clear();return true;
}
void pc_p2_original_cave_unload(){
    admitted=false;actors.clear();generators.clear();records.clear();
    // PC ordinary operator-new allocations are independent of App heap reset.
    // Retain killed bodies until disposal too, so each owned allocation frees once.
#if defined(PIKI_PC_PORT)
    for(auto* body:allocations)delete body;
#endif
    allocations.clear();
}
void pc_p2_original_cave_register(){auto* f=GenObjectFactory::factory;if(!f)fail("native factory absent");for(int i=0;i<f->mSpawnerCount;++i)if(f->mSpawnerInfo[i].mID==type)return;if(f->mSpawnerCount>=f->mMaxSpawners)fail("native factory capacity exhausted");f->registerMember(type,make,"original P2 Cave",version);}
GenObjectOriginalCave::GenObjectOriginalCave():GenObject(type,"original P2 Cave"){}
void GenObjectOriginalCave::doRead(RandomAccessStream& s){if(mVersion!=version)fail("Cave adapter version mismatch");if(Generator::ramMode)return;uid=unsigned(s.readInt());row(uid);}
void GenObjectOriginalCave::doWrite(RandomAccessStream& s){if(Generator::ramMode)return;row(uid);s.writeInt(int(uid));}
void GenObjectOriginalCave::ramSaveParameters(RandomAccessStream& s){writeCache(uid,s);}
void GenObjectOriginalCave::ramLoadParameters(RandomAccessStream& s){
    if(s.getPending()<104)fail("truncated Cave parameter cache");
    std::vector<std::uint8_t> b(104);for(auto& v:b)v=s.readByte();unsigned next=0;for(unsigned i=0;i<4;++i)next|=unsigned(b[68+i])<<(i*8);
    std::string e;if(!p2original::caveRestore(row(next),b,e))fail(e.c_str());uid=next;
}
bool pc_p2_original_cave_preflight(const std::vector<Generator*>& inventory,std::string& e){
    if(admitted||!gsys||!mapMgr||records.empty()||inventory.size()!=records.size()){e="Cave requires whole installed inventory and live stage";return false;}
    std::set<unsigned> seen;std::map<const Generator*,unsigned> next;
    for(auto* g:inventory){auto* o=g?dynamic_cast<GenObjectOriginalCave*>(g->mGenObject):nullptr;
        if(!o||!records.count(o->uid)||!seen.insert(o->uid).second||g->mLatestSpawnCreature){e="Cave generator missing/wrong/duplicate/already born";return false;}
        const auto& r=row(o->uid);if(g->mCarryOverFlags!=r.reserved||g->mRespawnInterval!=r.resurrectionDays||g->mDayLimit!=r.dayLimit){e="Cave generator common metadata mismatch";return false;}
        const std::array<float,3> position={g->mGenPosition.x,g->mGenPosition.y,g->mGenPosition.z},offset={g->mGenOffset.x,g->mGenOffset.y,g->mGenOffset.z};
        if(position!=r.position||offset!=r.offset){e="Cave generator/source transform mismatch";return false;}
        next.emplace(g,o->uid);
    }
    generators.swap(next);admitted=true;e.clear();return true;
}
Creature* GenObjectOriginalCave::birth(BirthInfo& info){
    if(!admitted||!gsys||!info.mGenerator||info.mGenerator->mGenObject!=this||!generators.count(info.mGenerator)||generators.at(info.mGenerator)!=uid||info.mGenerator->isExpired())fail("Cave birth lacks complete eligible source admission");
    for(const auto& a:actors)if(a.second==uid)fail("duplicate live Cave source body");
    const auto& r=row(uid);AppHeap heap;auto* body=new CaveBody(uid);allocations.push_back(body);
    body->init(Vector3f(r.position[0]+r.offset[0],r.position[1]+r.offset[1],r.position[2]+r.offset[2]));
    body->mSearchContext.exit(); // static sparse render owner has no search scheduling
    body->mSRT.r.set(r.rotation[0]*0.01745329252f,r.rotation[1]*0.01745329252f,r.rotation[2]*0.01745329252f);
    body->mFaceDirection=body->mSRT.r.y;body->mGenerator=info.mGenerator;info.mGenerator->_70=uid;
    actors.emplace(body,uid);std::printf("P2_ORIGINAL_CAVE_BIRTH uid=%u target=%s authored=1 activation=unavailable\n",uid,r.caveId.c_str());return body;
}
bool pc_p2_original_cave_generator_init(Generator* g,bool& handled,std::string& e){
    auto* o=g?dynamic_cast<GenObjectOriginalCave*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;
    if(!admitted||!generators.count(g)||generators.at(g)!=o->uid||g->mLatestSpawnCreature){e="Cave init without fresh admitted source generator";return false;}
    g->mAliveCount=0;if(!g->isExpired()){BirthInfo info;info.mGenerator=g;g->mLatestSpawnCreature=o->birth(info);g->mAliveCount=1;}e.clear();return true;
}
bool pc_p2_original_cave_generator_load(Generator* g,RandomAccessStream& s,bool& handled,std::string& e){
    auto* o=g?dynamic_cast<GenObjectOriginalCave*>(g->mGenObject):nullptr;handled=o!=nullptr;if(!handled)return true;
    if(!admitted||!generators.count(g)||generators.at(g)!=o->uid||g->mLatestSpawnCreature){e="Cave load without fresh admitted generator";return false;}
    if(!readCache(o->uid,s,e))return false;return pc_p2_original_cave_generator_init(g,handled,e);
}
bool pc_p2_original_cave_identity(const Creature* c,p2original::CaveRecord& out){auto i=actors.find(c);if(i==actors.end())return false;out=row(i->second);return true;}
void pc_p2_original_cave_draw(Graphics& gfx){if(!admitted||!gfx.mCamera)return;gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);for(const auto& a:actors)const_cast<Creature*>(a.first)->refresh(gfx);}
