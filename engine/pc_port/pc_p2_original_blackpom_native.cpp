#include "pc_p2_original_blackpom_native.h"
#include "pc_p2_pose_family.h"
#include "Pom.h"
#include "Generator.h"
#include "Graphics.h"
#include "Camera.h"
#include "Stickers.h"
#include "sysNew.h"
#include <array>
#include <cmath>
#include <fstream>
#include <map>
#include <set>
#include <cstdio>
#include <cstdlib>
extern Matrix4f invCamMat;
// Exact Purple owner API (#1281). Definitions arrive from its published core
// pin; these declarations introduce no alternate state or conversion authority.
bool pc_p2_original_pom_intake(Pom*,Piki*,CollPart*);
void pc_p2_original_pom_touch(Pom*,Creature*);
bool pc_p2_original_pom_preflight(std::string&);
bool pc_p2_original_pom_bind(Pom*,const p2original::InstanceIdentity&,unsigned,std::string&);
bool pc_p2_original_pom_start(Pom*,std::string&);
bool pc_p2_original_pom_release(Pom*,std::string&);
bool pc_p2_original_pom_pose(const Pom*,unsigned&,float&);
namespace p2original { namespace blackpom {
namespace {
const char* clips[]={"wait","dead","type1","type2","type3","type4"};
const int durations[]={1,40,30,30,40,20};
bool refuse(std::string& e,const char* s){e=s;return false;}
struct AppHeap {int previous;AppHeap():previous(gsys->setHeap(SYSHEAP_App)){}~AppHeap(){gsys->setHeap(previous);}};
std::set<Native*>& owners(){static std::set<Native*> all;return all;}
void require(bool result,const std::string& e){if(!result){std::fprintf(stderr,"Original BlackPom: %s\n",e.c_str());std::abort();}}
class Core final:public Mechanic {
 bool preflight(std::string& e)override{return pc_p2_original_pom_preflight(e);}
 bool bind(Pom* p,const InstanceIdentity& i,unsigned t,std::string& e)override{return pc_p2_original_pom_bind(p,i,t,e);}
 bool start(Pom* p,std::string& e)override{return pc_p2_original_pom_start(p,e);}
 bool release(Pom* p,std::string& e)override{return pc_p2_original_pom_release(p,e);}
 bool pose(const Pom* p,unsigned& motion,float& frame)const override{return pc_p2_original_pom_pose(p,motion,frame);}
};
}
std::unique_ptr<Mechanic> coreMechanic(){return std::make_unique<Core>();}
struct Native::Impl {
 Mechanic& mechanic;p2posefamily::Bank bank{"ORIGINAL_BLACKPOM"};
 p2poseload::Shared shared;std::array<std::vector<Shape*>,6> shapes;
 struct Sphere {int joint;Vector3f offset;float radius;};
 std::array<Sphere,7> spheres;
 std::array<std::vector<std::array<Matrix4f,6>>,6> jointFrames;
 struct Tree {
  std::array<ObjCollInfo,7> nodes;
  std::array<CollPart,7> parts;
  std::array<u32,7> ids{};
  CollInfo own{7,parts.data(),ids.data()};
  CollInfo* previous=nullptr;
  std::array<CollPart*,7> resolved{};
 };
 std::map<Pom*,std::unique_ptr<Tree>> trees;
 std::map<Pom*,unsigned> actors;unsigned reserved=0;bool loaded=false;
 std::set<const Pom*> started;
 std::set<const Pom*> releasing;
 std::function<bool(Pom*,std::string&)> death;
 std::function<bool(Pom*,const InstanceIdentity&,unsigned,std::string&)> bound;
 int petal=0;
 explicit Impl(Mechanic& core):mechanic(core){}
 bool load(std::string& e){
  if(loaded)return true;
  std::ifstream in("p2-original-blackpom-bank.txt");std::string magic,name,stem,word,extra;
  unsigned source;int count,duration;
  if(!(in>>magic>>source)||magic!="P2_ORIGINAL_BLACKPOM_BANK_1"||source!=6)
   return refuse(e,"actual BlackPom resource index absent");
  std::size_t total=0;
  for(unsigned i=0;i<6;++i){
   if(!(in>>word>>name>>count>>duration>>stem)||word!="clip"||name!=clips[i]
      ||duration!=durations[i]||count<1||count>64||stem!="flora_BlackPom_"+name)
    return refuse(e,"actual BlackPom clip identity mismatch");
   std::vector<int> frames;
   if(!(in>>word)||word!="frames")return refuse(e,"BlackPom source frame list absent");
   for(int j=0;j<count;++j){int frame;if(!(in>>frame))return refuse(e,"BlackPom source frame list truncated");frames.push_back(frame);}
   if(!p2posefamily::Bank::validFrames(frames,count,duration))return refuse(e,"BlackPom source frames invalid");
   if(!p2posefamily::loadFamilyClip(bank,name,stem,count,duration,frames,shared,total,shapes[i],e))return false;
   // Approximate materials are an explicit presentation limit. Missing poses
   // cannot silently select the inherited P1 flower or Chappy model.
   if(shapes[i].empty())return refuse(e,"BlackPom physical poses missing");
  }
  int r,g,b,a;
  if(!(in>>word>>petal>>r>>g>>b>>a)||word!="petal"||petal!=0||r!=28||g!=0||b!=52||a!=255)
   return refuse(e,"BlackPom source Violet petal mapping missing");
  for(const auto& clip:shapes)for(auto* shape:clip)if(!shape||shape->mMaterialCount<=petal)
   return refuse(e,"BlackPom source Violet petal material unresolved");
  if(in>>extra)return refuse(e,"BlackPom resource index trailing data");
  std::ifstream joints("p2-original-blackpom-joints.txt");
  if(!(joints>>magic)||magic!="P2_ORIGINAL_BLACKPOM_JOINTS_1")return refuse(e,"BlackPom actual collision joint bank absent");
  for(unsigned i=0;i<7;++i){
   unsigned part;int joint,parent;std::string id,code;float x,y,z,radius;
   if(!(joints>>word>>part>>joint>>parent>>id>>code>>x>>y>>z>>radius)||word!="collider"||part!=i
     ||joint!=(i<2?0:int((i-1)*2))||parent!=(i?0:-1)||id!=(i==1?"slot":"none")
     ||code!=(i==1?"st__":"____")||radius!=(i==0?45.f:i==1?30.f:10.f)
     ||x!=(i==0?5.f:i==1?-7.5f:7.5f)||y!=(i<2?0.f:5.f)||z!=0.f)
    return refuse(e,"BlackPom original collider topology mismatch");
   spheres[i]={joint,Vector3f(x,y,z),radius};
  }
  for(unsigned motion=0;motion<6;++motion){
   jointFrames[motion].resize(durations[motion]);
   for(int frame=0;frame<durations[motion];++frame)for(unsigned joint=0;joint<6;++joint){
    int actualFrame,actualJoint;
    if(!(joints>>word>>name>>actualFrame>>actualJoint)||word!="joint"||name!=clips[motion]
       ||actualFrame!=frame||actualJoint!=int(joint*2))return refuse(e,"BlackPom source collision joint sequence incomplete");
    auto& matrix=jointFrames[motion][frame][joint];matrix.makeIdentity();
    for(int r=0;r<3;++r)for(int c=0;c<4;++c){float v;
     if(!(joints>>v)||!std::isfinite(v))return refuse(e,"BlackPom source collision joint matrix invalid");
     matrix.mMtx[r][c]=v;
    }
   }
  }
  if(joints>>extra)return refuse(e,"BlackPom source joint bank trailing data");
  loaded=true;return true;
 }
};
Native::Native(Mechanic& core):m(std::make_unique<Impl>(core)){owners().insert(this);}
Native::~Native(){if(!m->actors.empty()){std::fputs("BlackPom owner destroyed before actual root release\n",stderr);std::abort();}owners().erase(this);}
bool Native::prepare(unsigned count,std::string& e){
 if(!count||count>10||!gsys||!bossMgr)return refuse(e,"BlackPom managers/count unavailable");
 if(!m->actors.empty()||m->reserved)return refuse(e,"BlackPom factory already reserved");
 AppHeap heap;
 if(!m->load(e)||!m->mechanic.preflight(e))return false;
 if(bossMgr->pcOriginalPomCapacity()<int(count))return refuse(e,"BlackPom native Pom pool capacity insufficient");
 m->reserved=count;e.clear();return true;
}
bool Native::birth(Generator* gen,const Vector3f& p,float yaw,const BirthContext& context,
                   Pom*& out,bool& wasSuppressed,std::string& e){
 out=nullptr;wasSuppressed=false;
 if(!m->loaded||!m->reserved||!bossMgr||!gen||!std::isfinite(p.x)||!std::isfinite(p.y)
    ||!std::isfinite(p.z)||!std::isfinite(yaw))return refuse(e,"BlackPom birth lacks prepared physical slot");
 const auto* row=originalActors().find(gen->_70);
 if(!row||row->enemy.source!=6)return refuse(e,"BlackPom generator UID is not admitted original source6");
 if(suppressed(context)){wasSuppressed=true;--m->reserved;e.clear();return true;}
 AppHeap heap;BirthInfo info;info.set(p,Vector3f(0,yaw,0),Vector3f(1,1,1),gen);
 Boss* root=bossMgr->pcAllocateOriginalPom(info);
 if(!root)return refuse(e,"BlackPom actual Pom manager allocation failed");
 out=static_cast<Pom*>(root);m->actors.emplace(out,0);--m->reserved;e.clear();return true;
}
bool Native::bind(Pom* body,unsigned token,std::string& e){
 auto it=m->actors.find(body);if(it==m->actors.end()||it->second||!token)return refuse(e,"BlackPom binding lacks new owned root");
 unsigned source=0,actualToken=0;InstanceIdentity identity;
 if(!originalActors().query(body,source,actualToken,&identity)||source!=6||token!=actualToken
    ||identity.catalog.empty()||!identity.generator||!identity.epoch||!identity.activation)
  return refuse(e,"BlackPom root lacks actual original source identity");
 // Mark ownership before callback: a failed partial bind still needs release.
 it->second=token;
 if(!m->mechanic.bind(body,identity,token,e))return false;
 if(m->bound&&!m->bound(body,identity,token,e))return false;
 {
  AppHeap heap;
  auto tree=std::make_unique<Impl::Tree>();
  for(unsigned i=0;i<7;++i){
   auto& node=tree->nodes[i];const auto& sphere=m->spheres[i];
   // The six anonymous retail ids repeat. Give them internal lookup ids only;
   // source slot id/code remain literal slot/st__ for ordinary press contacts.
   const u32 id=i==1?0x736c6f74u:0x62703030u+i;
   node.mId.setID(id);node.mCode.setID(i==1?0x73745f5fu:0x5f5f5f5fu);
   node.mRadius=sphere.radius;node.mCentrePosition=sphere.offset;node.mJointIndex=-1;
   if(i)tree->nodes[0].add(&node);
  }
  tree->own.initInfoTree(&tree->nodes[0]);
  for(unsigned i=0;i<7;++i){
   tree->resolved[i]=tree->own.getSphere(tree->nodes[i].mId.mId);
   if(!tree->resolved[i])return refuse(e,"BlackPom actual slot collision tree unresolved");
   tree->resolved[i]->mIsUpdateActive=false;tree->resolved[i]->mJointMatrix.makeIdentity();
  }
  tree->previous=body->mCollInfo;body->mCollInfo=&tree->own;m->trees.emplace(body,std::move(tree));
 }
 if(!m->mechanic.start(body,e))return false;
 m->started.insert(body);
 if(!follow(body,e))return false;
 e.clear();return true;
}
bool Native::release(Pom* body,std::string& e){
 auto it=m->actors.find(body);if(it==m->actors.end())return refuse(e,"BlackPom release does not own root");
 if(it->second){if(!m->mechanic.release(body,e))return false;it->second=0;}
 m->started.erase(body);
 auto tree=m->trees.find(body);
 if(tree!=m->trees.end()){
  Stickers attached(body);Iterator sticker(&attached);
  CI_LOOP(sticker){if(*sticker)return refuse(e,"BlackPom collider release still has attached references");}
  body->mCollInfo=tree->second->previous;m->trees.erase(tree);
 }
 // Floor owner retires its original registry handle before freeing manager slot.
 unsigned source=0,token=0;if(originalActors().query(body,source,token))return refuse(e,"BlackPom registry authority must retire before pool reuse");
 // Keep source dispatch through Creature::kill cleanup and Pom::doKill. An
 // unstarted source root never initialized the inherited P1 effect callbacks.
 m->releasing.insert(body);body->kill(false);m->releasing.erase(body);
 m->actors.erase(it);e.clear();return true;
}
bool Native::nativeRetired(Pom* body,std::string& e){
 auto it=m->actors.find(body);if(it==m->actors.end())return refuse(e,"BlackPom native retirement does not own root");
 unsigned source=0,token=0;
 if(originalActors().query(body,source,token))return refuse(e,"BlackPom native retirement still has original registry authority");
 if(it->second&&!m->mechanic.release(body,e))return false;
 m->started.erase(body);
 auto tree=m->trees.find(body);
 if(tree!=m->trees.end()){
  Stickers attached(body);Iterator sticker(&attached);
  CI_LOOP(sticker){if(*sticker)return refuse(e,"BlackPom retired collider still has attached references");}
  body->mCollInfo=tree->second->previous;m->trees.erase(tree);
 }
 m->actors.erase(it);e.clear();return true;
}
bool Native::cancel(std::string& e){
 if(!m->actors.empty())return refuse(e,"BlackPom cancel requires partial roots released");
 m->reserved=0;e.clear();return true;
}
bool Native::owns(const Creature* body)const{return m->actors.count(const_cast<Pom*>(dynamic_cast<const Pom*>(body)))!=0;}
bool Native::active(const Pom* body)const{
 auto it=m->actors.find(const_cast<Pom*>(body));if(it==m->actors.end()||!it->second||!m->started.count(body))return false;
 unsigned source=0,token=0;return originalActors().query(body,source,token)&&source==6&&token==it->second;
}
Native* Native::owner(const Creature* body){for(auto* n:owners())if(n->owns(body))return n;return nullptr;}
void Native::onDeath(std::function<bool(Pom*,std::string&)> callback){m->death=std::move(callback);}
void Native::onBind(std::function<bool(Pom*,const InstanceIdentity&,unsigned,std::string&)> callback){m->bound=std::move(callback);}
bool Native::beforeKill(Pom* body,std::string& e){
 auto it=m->actors.find(body);if(it==m->actors.end())return refuse(e,"BlackPom actual death lacks owning root");
 if(m->releasing.count(body)){e.clear();return true;}
 if(!m->death)return refuse(e,"BlackPom actual death lacks source floor retirement callback");
 if(!m->death(body,e))return false;
 return nativeRetired(body,e);
}
bool Native::press(Pom* body,Piki* donor,CollPart* part,bool descending){
 if(!active(body))return false;
 auto tree=m->trees.find(body);if(tree==m->trees.end()||part!=tree->second->resolved[1]||!descending)return false;
 return pc_p2_original_pom_intake(body,donor,part);
}
bool Native::collider(const Pom* body,unsigned part,Vector3f& center,float& radius)const{
 auto it=m->actors.find(const_cast<Pom*>(body));if(it==m->actors.end()||!it->second||part>=7)return false;
 unsigned source=0,token=0;
 if(!originalActors().query(body,source,token)||source!=6||token!=it->second)return false;
 unsigned motion;float frame;
 if(!m->mechanic.pose(body,motion,frame)||motion>=6||!std::isfinite(frame)||frame<0)return false;
 const auto& sphere=m->spheres[part];
 const int sourceFrame=std::min(durations[motion]-1,int(std::min(frame,float(durations[motion]-1))));
 const auto& local=m->jointFrames[motion][sourceFrame][sphere.joint/2];
 Matrix4f root,world;root.makeSRT(Vector3f(1,1,1),Vector3f(0,body->mFaceDirection,0),body->mSRT.t);root.multiplyTo(local,world);
 const auto& p=sphere.offset;
 center.set(world.mMtx[0][3]+world.mMtx[0][0]*p.x+world.mMtx[0][1]*p.y+world.mMtx[0][2]*p.z,
            world.mMtx[1][3]+world.mMtx[1][0]*p.x+world.mMtx[1][1]*p.y+world.mMtx[1][2]*p.z,
            world.mMtx[2][3]+world.mMtx[2][0]*p.x+world.mMtx[2][1]*p.y+world.mMtx[2][2]*p.z);
 radius=sphere.radius;return true;
}
bool Native::follow(Pom* body,std::string& e){
 auto tree=m->trees.find(body);if(tree==m->trees.end())return refuse(e,"BlackPom follow lacks actual collider tree");
 unsigned motion;float frame;
 if(!m->mechanic.pose(body,motion,frame)||motion>=6||!std::isfinite(frame)||frame<0)return refuse(e,"BlackPom follow lacks original motion");
 const int sourceFrame=int(std::min(frame,float(durations[motion]-1)));
 for(unsigned i=0;i<7;++i){Vector3f center;float radius;
  if(!collider(body,i,center,radius))return refuse(e,"BlackPom collider lost qualified mechanic/source identity");
  auto* part=tree->second->resolved[i];part->mCentre=center;part->mRadius=radius;
  Matrix4f root,world,cameraRotation;
  root.makeSRT(Vector3f(1,1,1),Vector3f(0,body->mFaceDirection,0),Vector3f(0,0,0));
  root.multiplyTo(m->jointFrames[motion][sourceFrame][m->spheres[i].joint/2],world);
  world.mMtx[0][3]=world.mMtx[1][3]=world.mMtx[2][3]=0;
  cameraRotation.makeIdentity();
  for(int r=0;r<3;++r)for(int c=0;c<3;++c)cameraRotation.mMtx[r][c]=invCamMat.mMtx[c][r];
  // Native CollPart::getMatrix multiplies invCamMat again. Cancel its camera
  // rotation so attached actors follow source world joints during simulation.
  cameraRotation.multiplyTo(world,part->mJointMatrix);
 }
 e.clear();return true;
}
bool Native::draw(Pom* body,Graphics& gfx){
 auto it=m->actors.find(body);if(it==m->actors.end())return false;
 if(!it->second||!gfx.mCamera)return true;
 unsigned source=0,token=0;
 if(!originalActors().query(body,source,token)||source!=6||token!=it->second)return true;
 unsigned motion;float frame;if(!m->mechanic.pose(body,motion,frame)||motion>=6||!std::isfinite(frame)||frame<0)return true;
 auto* clip=m->bank.clip(clips[motion]);const auto& shapes=m->shapes[motion];
 std::size_t index=0;
 if(clip){for(std::size_t i=1;i<clip->frames.size();++i)if(std::fabs(float(clip->frames[i])-frame)<std::fabs(float(clip->frames[index])-frame))index=i;}
 else index=std::min(shapes.size()-1,std::size_t(frame*shapes.size()/durations[motion]));
 Matrix4f root,view;root.makeSRT(Vector3f(1,1,1),Vector3f(0,body->mFaceDirection,0),body->mSRT.t);gfx.mCamera->mLookAtMtx.multiplyTo(root,view);
 auto* shape=shapes[index];Colour saved;shape->mMaterialList[m->petal].getColour(saved);
 shape->mMaterialList[m->petal].setColour(Colour(28,0,52,255));
 gfx.useMatrix(Matrix4f::ident,0);shape->updateAnim(gfx,view,nullptr,body);shape->drawshape(gfx,*gfx.mCamera,nullptr);
 shape->mMaterialList[m->petal].setColour(saved);return true;
}
} }
PcOriginalBlackPomPress pc_p2_original_blackpom_flying_press(Creature* body,Piki* piki,CollPart* part,bool descending){
 auto* owner=p2original::blackpom::Native::owner(body);if(!owner)return {};
 return {true,owner->press(static_cast<Pom*>(body),piki,part,descending)};
}
bool pc_p2_original_blackpom_update(Pom* body){
 auto* owner=p2original::blackpom::Native::owner(body);if(!owner)return false;
 if(!owner->active(body))return true; // Partial/unbound roots never execute P1 AI.
 // Core's PomAi entry executes actual source states/keys. No P1 animation
 // update, source tick injection or draw-driven clock is used here.
 body->doAI();
 // Completed source death may have retired this leaf during doAI.
 if(owner->owns(body)){std::string e;p2original::blackpom::require(owner->follow(body,e),e);}
 return true;
}
bool pc_p2_original_blackpom_refresh(Pom* body,Graphics& gfx){
 auto* owner=p2original::blackpom::Native::owner(body);return owner&&owner->draw(body,gfx);
}
bool pc_p2_original_blackpom_collision(Pom* body,Creature* collider){
 auto* owner=p2original::blackpom::Native::owner(body);if(!owner)return false;
 if(owner->active(body))pc_p2_original_pom_touch(body,collider);return true;
}
bool pc_p2_original_blackpom_before_kill(Pom* body){
 auto* owner=p2original::blackpom::Native::owner(body);if(!owner)return false;
 std::string e;p2original::blackpom::require(owner->beforeKill(body,e),e);return true;
}
