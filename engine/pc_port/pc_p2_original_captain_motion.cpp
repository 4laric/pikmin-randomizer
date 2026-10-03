#include "pc_p2_original_captain_motion.h"
#include "pc_randomizer.h"
#include "pc_p2_original_captain_rig.h"
#include "pc_p2_original_captain_mod.h"
#include "pc_p2_pose_bank.h"
#include "pc_p2_pose_loader.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "netplay/pc_netplay_sha256.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Graphics.h"
#include "Camera.h"
#include "Stream.h"
#include "sysNew.h"
#include "Texture.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <map>
#include <regex>
#include <sstream>
#include <locale>
#include <stdexcept>
#include <cstring>
namespace p2original { namespace captain {
namespace {
bool fail(std::string& e,const char* why){e=why;return false;}
std::string hash(const std::string& b){unsigned char h[32];pc_netplay_sha::sha256(b.data(),b.size(),h);std::string s;const char* x="0123456789abcdef";for(auto v:h){s+=x[v>>4];s+=x[v&15];}return s;}
bool get(const std::string& role,std::string& b,std::string& e){return pc_randomizer_original_input("p2-original/captains/"+role,b,e)&&b.size()<=4*1024*1024;}
unsigned be16(const std::string& b,std::size_t at){return (unsigned char)b[at]*256+(unsigned char)b[at+1];}
struct Heap {int previous;Heap():previous(gsys->setHeap(SYSHEAP_App)){}~Heap(){gsys->setHeap(previous);}};
struct Key {int frame,type;bool operator==(const Key& b)const{return frame==b.frame&&type==b.type;}};
struct Clip {std::string sourceSha;int duration=0;std::vector<Key> keys;std::vector<int> frames;std::vector<p2pose::Pose> poses;};
const unsigned ids20[]={0,1,3,4,10,11,13,14,22,23,28,29,30,31,32,33,34,50,54,1000};
const char* names20[]={"akubi","asibumi","chatting","damage","fue","furimuku","gattu","getup","jhit","jkoke","nigeru","run2","walk","wait","kizuku","throw","trwwait","jump","sagasu2","down"};
const unsigned ids26[]={0,1,3,4,5,10,11,13,14,22,23,28,29,30,31,32,33,34,42,43,50,54,64,65,66,1000};
const char* names26[]={"akubi","asibumi","chatting","damage","dead","fue","furimuku","gattu","getup","jhit","jkoke","nigeru","run2","walk","wait","kizuku","throw","trwwait","nuku","nuku3","jump","sagasu2","punch","punch2","punch3","down"};
const char* models[]={"orima1","orima3","syatyou"};
bool locomotion(Motion m){return m==Motion::Walk||m==Motion::Run2||m==Motion::Nigeru;}
struct Model {std::string sourceSha;rig::Model rig;Shape* shape=nullptr;std::map<unsigned,Clip> clips;std::string first;std::vector<unsigned char> topology;};
// Native Shapes do not destroy their nested arrays/textures. One fixed cache
// owns all three models (including partial failure) until process shutdown.
// Sys-heap texture registrations survive ordinary App-heap resets. No Shape
// destructor runs after the graphics system has gone away.
struct NativeModels {
 enum class Phase {Empty,Initializing,Ready,Failed};Phase phase=Phase::Empty;
 const void* system=nullptr;std::string closure;std::array<Shape*,3> shapes{};
 std::array<std::string,3> names;
};
NativeModels nativeModels;
class CheckedRam final:public RamStream {
public:explicit CheckedRam(const std::string& bytes):RamStream(const_cast<char*>(bytes.data()),int(bytes.size())){}
 void read(void* dest,int size)override{if(size<0||mPosition<0||mPosition>mLength||size>mLength-mPosition)throw std::runtime_error("source captain native MOD overread");RamStream::read(dest,size);}
 void setPosition(int pos)override{if(pos<0||pos>mLength)throw std::runtime_error("source captain native MOD seek");mPosition=pos;}
 void setLength(int len)override{if(len!=mLength)throw std::runtime_error("source captain native MOD length mutation");}
 void write(immut void*,int)override{throw std::runtime_error("source captain native MOD write");}
};
struct NativeScope {
 int heap;Shape* previous;NativeScope():heap(gsys->setHeap(SYSHEAP_Sys)),previous(gsys->mCurrentShape){}
 ~NativeScope(){gsys->mCurrentShape=previous;gsys->setHeap(heap);}
};
struct Actor {Model* model=nullptr;std::unique_ptr<pelplant::Geometry> geometry;std::array<MotionState,2> state;std::array<Listener,2> listener{};std::array<std::size_t,2> next{};std::array<bool,2> advancing{};bool down=false;int boundLock=-1;float downFrame=0;};
std::vector<std::vector<std::string>> registry(const std::string& b){std::string clean;bool comment=false;for(char c:b){if(c=='#')comment=true;if(c=='\n')comment=false;if(!comment)clean+=c;}std::istringstream in(clean);in.imbue(std::locale::classic());int count;std::string word;std::vector<std::vector<std::string>> out;if(!(in>>count)||count!=67)return out;for(int i=0;i<count;++i){if(!(in>>word)||word!="{")return {};std::vector<std::string> row;while(in>>word&&word!="}")row.push_back(word);if(word!="}"||row.size()<3||row.back()!="-1")return {};out.push_back(std::move(row));}if(in>>word)return {};return out;}
bool number(const std::string& b,const char* key,float& out){std::regex pattern(std::string("\\{")+key+"\\}\\s+4\\s+([-+0-9.eE]+)");auto begin=std::sregex_iterator(b.begin(),b.end(),pattern);if(begin==std::sregex_iterator())return false;auto match=*begin;if(++begin!=std::sregex_iterator())return false;std::istringstream in(match[1].str());in.imbue(std::locale::classic());std::string extra;return bool(in>>out)&&!(in>>extra)&&std::isfinite(out);}
}
struct SourceBank::Impl {
 bool prepared=false,bound=false;std::uint64_t selectionRevision=0;std::uint64_t generation=0;std::string fingerprint;std::array<std::string,5> sources;SourceParameters parameters;
 std::array<Model,3> model;std::map<unsigned,rig::Clip> joints;std::map<const Navi*,Actor> actors;
 bool sample(Actor& a,std::string& e){if(!a.geometry)return fail(e,"source captain native geometry absent");unsigned self=a.down?1000:unsigned(a.state[0].motion),bound=a.down?1000:unsigned(a.state[1].motion);auto sc=joints.find(self),bc=joints.find(bound);if(sc==joints.end()||bc==joints.end())return fail(e,"source captain joint clips absent");std::array<rig::Matrix,11> matrices;p2pose::Pose pose;if(!rig::joints(a.model->rig,sc->second,a.down?a.downFrame:a.state[0].frame,bc->second,a.down?a.downFrame:a.state[1].frame,a.down,matrices)||!rig::pose(a.model->rig,matrices,pose)||!p2pose::write(a.geometry->shape,pose))return fail(e,"source captain actual joint pose failed");e.clear();return true;}

};
SourceBank::SourceBank():m(new Impl){}SourceBank::~SourceBank()=default;
bool SourceBank::prepare(std::string& e){
 if(m->prepared)return true;if(!pc_randomizer_original_session()||!gsys)return fail(e,"source captain bank requires actual selected session/system");
 auto next=std::make_unique<Impl>();next->selectionRevision=pc_randomizer_original_selection_revision();if(!next->selectionRevision)return fail(e,"source captain authenticated selection revision absent");const char* sourceRoles[]={"naviParms.txt","animmgr.txt","navicoll.txt","down/demo.stb","down/s03_dead1.bck"};for(unsigned i=0;i<5;++i)if(!get(sourceRoles[i],next->sources[i],e))return false;
 if(!number(next->sources[0],"p050",next->parameters.maximumHealth)||!number(next->sources[0],"p004",next->parameters.moveSpeed)||!number(next->sources[0],"p043",next->parameters.neutralStick)||!number(next->sources[0],"p044",next->parameters.cursorStick)||next->parameters.maximumHealth<=0||next->parameters.moveSpeed<=0||next->parameters.neutralStick<0||next->parameters.cursorStick<=next->parameters.neutralStick||next->parameters.cursorStick>1)return fail(e,"source captain parameters invalid");next->parameters.rawSourceSha=hash(next->sources[0]);
 auto rows=registry(next->sources[1]);if(rows.size()!=67)return fail(e,"source captain registry malformed");
 std::string bytes;if(!get("bank.txt",bytes,e))return false;std::string closure=bytes;for(const auto& b:next->sources)closure+=hash(b);std::istringstream in(bytes);in.imbue(std::locale::classic());std::string word,registrySha;int nmodel,nclip;if(!(in>>word>>registrySha>>nmodel>>nclip)||word!="P2_SOURCE_CAPTAIN_BANK_1"||registrySha!=hash(next->sources[1])||nmodel!=3||(nclip!=20&&nclip!=26))return fail(e,"source captain bank header invalid");
 const unsigned* ids=nclip==20?ids20:ids26;const char* const* names=nclip==20?names20:names26;
 std::size_t total=0;
 for(unsigned j=0;j<3;++j){auto& model=next->model[j];std::string name,expected,raw;if(!(in>>word>>name>>expected)||word!="model"||name!=models[j]||!get("models/"+name+".bmd",raw,e)||hash(raw)!=expected)return fail(e,"source captain model source mismatch");closure+=expected;model.sourceSha=expected;
  for(unsigned k=0;k<unsigned(nclip);++k){unsigned id;int duration,count;std::string clipName,sourceSha;if(!(in>>word>>id>>clipName>>duration>>sourceSha>>count)||word!="clip"||id!=ids[k]||clipName!=names[k]||duration<1||duration>10000||count<0||count>4096)return fail(e,"source captain clip index invalid");Clip clip;clip.duration=duration;clip.sourceSha=sourceSha;for(int v=0;v<count;++v){Key key;if(!(in>>key.frame>>key.type)||key.frame<0||key.frame>=duration||key.type<0||key.type>=1000||(!clip.keys.empty()&&key.frame<clip.keys.back().frame))return fail(e,"source captain event invalid");clip.keys.push_back(key);}
   if(id==1000){raw=next->sources[4];if(!clip.keys.empty()||raw.size()<72||raw.compare(0,8,"J3D1bck1")||raw.compare(32,4,"ANK1"))return fail(e,"source captain Down BCK invalid");}
   else {if(!get("motion/"+clipName+".bca",raw,e)||raw.size()<72||raw.compare(0,8,"J3D1bca1")||raw.compare(32,4,"ANF1"))return fail(e,"source captain BCA invalid");const auto& row=rows[id];if(row[1]!=clipName+".bca"||(row.size()-3)%2)return fail(e,"source captain source registry identity mismatch");std::vector<Key> keys;try{for(std::size_t at=2;at+1<row.size();at+=2){std::size_t x,y;int f=std::stoi(row[at],&x),t=std::stoi(row[at+1],&y);if(x!=row[at].size()||y!=row[at+1].size())return fail(e,"source captain source key malformed");keys.push_back({f,t});}}catch(...){return fail(e,"source captain source key malformed");}std::stable_sort(keys.begin(),keys.end(),[](Key a,Key b){return a.frame<b.frame;});if(keys!=clip.keys)return fail(e,"source captain source keys mismatch");}
   if(hash(raw)!=sourceSha||be16(raw,42)!=unsigned(duration)||be16(raw,44)!=11)return fail(e,"source captain animation source mismatch");closure+=sourceSha;
   int poses;if(!(in>>poses)||poses<1||poses>64)return fail(e,"source captain pose count invalid");for(int v=0;v<poses;++v){int frame;if(!(in>>frame)||frame<0||frame>=duration||(!clip.frames.empty()&&frame<=clip.frames.back()))return fail(e,"source captain pose frame invalid");clip.frames.push_back(frame);}if(clip.frames.front()!=0||clip.frames.back()!=duration-1)return fail(e,"source captain pose endpoints invalid");
   for(int v=0;v<poses;++v){char suffix[16];std::snprintf(suffix,sizeof(suffix),"_%02d.mod",v);std::string poseRole="poses/"+name+"_"+clipName+suffix;if(!(in>>expected)||!get(poseRole,raw,e)||hash(raw)!=expected)return fail(e,"source captain exact pose bytes mismatch");total+=raw.size();if(total>96*1024*1024)return fail(e,"source captain bank byte bound exceeded");closure+=expected;std::vector<unsigned char> b(raw.begin(),raw.end());p2pose::Baked baked;if(!sourceCaptainMod(raw)||!p2pose::decodeBaked(b,baked))return fail(e,"source captain flattened pose malformed");if(model.first.empty()){model.first=raw;model.topology=baked.topology;}else if(model.topology!=baked.topology)return fail(e,"source captain pose topology/resources mismatch");clip.poses.push_back(std::move(baked.pose));}
   model.clips.emplace(id,std::move(clip));
  }
 }
 if(in>>word)return fail(e,"source captain bank trailing data");
 std::string rigBytes,jointBytes,rigRegistry;std::array<rig::Model,3> rigs;if(!get("rig.txt",rigBytes,e)||!get("joint-clips.txt",jointBytes,e))return false;std::istringstream ri(rigBytes),ji(jointBytes);ri.imbue(std::locale::classic());ji.imbue(std::locale::classic());if(!rig::models(ri,rigs)||!rig::clips(ji,rigRegistry,next->joints)||rigRegistry!=registrySha)return fail(e,"source captain joint rig grammar/registry mismatch");closure+=hash(rigBytes)+hash(jointBytes);
 for(unsigned j=0;j<3;++j){auto& model=next->model[j];if(rigs[j].sourceSha!=model.sourceSha)return fail(e,"source captain joint rig model source mismatch");model.rig=std::move(rigs[j]);for(auto& c:model.clips){auto joint=next->joints.find(c.first);if(joint==next->joints.end()||joint->second.sourceSha!=c.second.sourceSha||joint->second.frames.size()!=unsigned(c.second.duration))return fail(e,"source captain joint animation source mismatch");for(unsigned f=0;f<c.second.frames.size();++f){std::array<rig::Matrix,11> matrices;p2pose::Pose pose;if(!rig::joints(model.rig,joint->second,float(c.second.frames[f]),joint->second,float(c.second.frames[f]),false,matrices)||!rig::pose(model.rig,matrices,pose))return fail(e,"source captain joint reconstruction failed");const auto& expected=c.second.poses[f];auto matches=[](const auto& a,const auto& b){if(a.size()!=b.size())return false;for(unsigned i=0;i<a.size();++i)if(std::fabs(a[i].x-b[i].x)>.001f||std::fabs(a[i].y-b[i].y)>.001f||std::fabs(a[i].z-b[i].z)>.001f)return false;return true;};if(!matches(pose.positions,expected.positions)||!matches(pose.normals,expected.normals))return fail(e,"source captain joint/baked geometry mismatch");}c.second.poses.clear();c.second.poses.shrink_to_fit();}}
 // Native geometry installation is deliberately deferred until the actual
 // independent self/bound clocks and root4 joint composition are implemented.
 // Retained verified source buffers do not grant runtime readiness.
 next->fingerprint=hash(closure);next->prepared=true;m=std::move(next);e.clear();return true;
}
bool SourceBank::prepareNativeModels(std::string& e){
 if(!m->prepared||!gsys||!m->selectionRevision||m->selectionRevision!=pc_randomizer_original_selection_revision())return fail(e,"source captain native models require current prepared selection/system");
 auto& cache=nativeModels;
 if(cache.phase==NativeModels::Phase::Ready){if(cache.system!=gsys||cache.closure!=m->fingerprint)return fail(e,"source captain native model cache belongs to another closure/system");for(unsigned j=0;j<3;++j)m->model[j].shape=cache.shapes[j];e.clear();return true;}
 if(cache.phase!=NativeModels::Phase::Empty)return fail(e,"source captain native model initialization failed or reentered");
 for(const auto& model:m->model)if(!sourceCaptainMod(model.first))return fail(e,"source captain native model retained bytes invalid");
 cache.phase=NativeModels::Phase::Initializing;cache.system=gsys;cache.closure=m->fingerprint;
 try{NativeScope scope;for(unsigned j=0;j<3;++j){cache.names[j]="p2-source-captain-"+std::string(models[j])+"-"+cache.closure;cache.shapes[j]=new Shape;auto* shape=cache.shapes[j];shape->mName=cache.names[j].c_str();gsys->mCurrentShape=shape;CheckedRam stream(m->model[j].first);shape->read(stream);if(stream.getPending()!=0)throw std::runtime_error("source captain native MOD trailing bytes");
 // Every texture is embedded and prevalidated. resolveTextureNames would
 // borrow ambient/path-cache textures whose App ownership is unsuitable.
 shape->initialise();shape->initIni(false);shape->optimize();if(!pelplant::Geometry::admits(*shape))throw std::runtime_error("source captain native static model unsupported");}}
 catch(const std::exception& ex){cache.phase=NativeModels::Phase::Failed;e=ex.what();return false;}catch(...){cache.phase=NativeModels::Phase::Failed;return fail(e,"source captain native model initialization exception");}
 cache.phase=NativeModels::Phase::Ready;for(unsigned j=0;j<3;++j)m->model[j].shape=cache.shapes[j];e.clear();return true;
}
bool SourceBank::parameters(SourceParameters& out,std::string& e)const{if(!m->prepared)return fail(e,"source captain parameters not prepared");out=m->parameters;e.clear();return true;}
bool SourceBank::sourceBytes(SourceResource r,std::string& out,std::string& e)const{unsigned i=unsigned(r);if(!m->prepared||i>=m->sources.size())return fail(e,"source captain retained source unavailable");out=m->sources[i];e.clear();return true;}
bool SourceBank::bindRoster(Navi*,Navi*,std::string& e){return fail(e,"source captain dual-clock joint geometry not installed");}
bool SourceBank::startMotion(Navi* n,Motion self,Motion bound,Listener sl,Listener bl,std::string& e){auto it=m->actors.find(n);if(unsigned(self)==1000||unsigned(bound)==1000||!m->bound||it==m->actors.end()||!it->second.model->clips.count(unsigned(self))||!it->second.model->clips.count(unsigned(bound))||m->generation>UINT64_MAX-2||(sl!=Listener::None&&sl!=Listener::SourceActor&&sl!=Listener::SourceState)||(bl!=Listener::None&&bl!=Listener::SourceActor&&bl!=Listener::SourceState))return fail(e,"source captain motion pair/roster invalid");auto& a=it->second;a.state[0]={self,0,++m->generation,false,false};a.state[1]={bound,0,++m->generation,false,false};a.listener={sl,bl};a.next={0,0};a.boundLock=-1;a.down=false;return m->sample(a,e);}
bool SourceBank::start(Navi* n,Motion motion,std::string& e){return startMotion(n,motion,motion,Listener::SourceActor,Listener::None,e);}
bool SourceBank::startAnimator(Navi* n,Animator channel,Motion motion,bool preserve,Listener listener,std::string& e){unsigned c=unsigned(channel);auto it=m->actors.find(n);if(unsigned(motion)==1000||c>1||!m->bound||it==m->actors.end()||!it->second.model->clips.count(unsigned(motion))||m->generation==UINT64_MAX||(listener!=Listener::None&&listener!=Listener::SourceActor&&listener!=Listener::SourceState))return fail(e,"source captain animator/clip invalid");auto& a=it->second;auto old=a.state[c];if(preserve&&(!locomotion(old.motion)||!locomotion(motion)||old.complete||a.down||old.frame>=a.model->clips.at(unsigned(motion)).duration))return fail(e,"source captain preservation requires actual live locomotion frame");a.state[c]={motion,preserve?old.frame:0,++m->generation,false,false};a.listener[c]=listener;a.next[c]=0;const auto& keys=a.model->clips.at(unsigned(motion)).keys;while(a.next[c]<keys.size()&&keys[a.next[c]].frame<a.state[c].frame)++a.next[c];a.down=false;return m->sample(a,e);}
bool SourceBank::startPreservingFrame(Navi* n,Motion motion,std::string& e){auto it=m->actors.find(n);if(it==m->actors.end())return fail(e,"source captain preservation roster absent");return startAnimator(n,Animator::Bound,motion,true,it->second.listener[1],e);}
bool SourceBank::enableMotionBlend(Navi* n,std::string& e){auto it=m->actors.find(n);if(it==m->actors.end())return fail(e,"source captain blend roster absent");int old=unsigned(it->second.state[1].motion);if(!startAnimator(n,Animator::Bound,Motion::Nigeru,false,Listener::SourceActor,e))return false;auto& a=it->second;a.boundLock=old;a.state[1].frame=10;a.next[1]=0;const auto& keys=a.model->clips.at(28).keys;while(a.next[1]<keys.size()&&keys[a.next[1]].frame<10)++a.next[1];return m->sample(a,e);}
bool SourceBank::boundMotionLock(const Navi* n,int& source,std::string& e)const{auto it=m->actors.find(n);if(it==m->actors.end())return fail(e,"source captain bound lock roster absent");source=it->second.boundLock;e.clear();return true;}
bool SourceBank::advanceAnimator(Navi* n,Animator channel,float amount,const std::function<bool(int)>& emit,std::string& e){unsigned c=unsigned(channel);auto it=m->actors.find(n);if(c>1||it==m->actors.end()||!std::isfinite(amount)||amount<0||(it->second.listener[c]!=Listener::None&&!emit))return fail(e,"source captain animator advance invalid");auto& a=it->second;if(a.advancing[0]||a.advancing[1])return fail(e,"source captain recursive clock advance refused");a.advancing[c]=true;struct Advancing {Impl& impl;Navi* actor;unsigned channel;~Advancing(){auto it=impl.actors.find(actor);if(it!=impl.actors.end())it->second.advancing[channel]=false;}} guard{*m,n,c};if(a.down)return fail(e,"source captain Down clock belongs to Studio");if(a.state[c].complete){e.clear();return true;}const auto generation=a.state[c].generation;float frame=a.state[c].frame+amount;auto next=a.next[c];const auto& clip=a.model->clips.at(unsigned(a.state[c].motion));if(!std::isfinite(frame)||frame>1000000)return fail(e,"source captain clock outside bound");while(next<clip.keys.size()&&clip.keys[next].frame<int(frame)){const auto key=clip.keys[next++];a.state[c].frame=frame;a.next[c]=next;bool keep=a.listener[c]==Listener::None||emit(key.type);auto live=m->actors.find(n);if(live==m->actors.end()||live->second.state[c].generation!=generation){e.clear();return true;}if(!keep)return m->sample(a,e);if(key.type==1&&!a.state[c].finishing){auto loop=std::find_if(clip.keys.rbegin(),clip.keys.rend(),[&](Key k){return k.type==0&&k.frame<key.frame;});if(loop==clip.keys.rend())return fail(e,"source captain loop start absent");frame=float(loop->frame);next=0;while(next<clip.keys.size()&&clip.keys[next].frame<frame)++next;a.state[c].frame=frame;a.next[c]=next;return m->sample(a,e);}}
 a.state[c].frame=frame;a.next[c]=next;if(frame>=clip.duration){a.state[c].frame=float(clip.duration-1);a.state[c].complete=true;if(a.listener[c]!=Listener::None)emit(1000);auto live=m->actors.find(n);if(live==m->actors.end()||live->second.state[c].generation!=generation){e.clear();return true;}}return m->sample(a,e);}
bool SourceBank::advance(Navi* n,float amount,const std::function<bool(int)>& emit,std::string& e){auto it=m->actors.find(n);if(it==m->actors.end())return fail(e,"source captain advance roster absent");if(it->second.listener[1]!=Listener::None)return fail(e,"source captain Bound listener requires explicit animator advancement");auto generation=it->second.state[1].generation;if(!advanceAnimator(n,Animator::Self,amount,emit,e))return false;it=m->actors.find(n);if(it==m->actors.end()||it->second.state[1].generation!=generation){e.clear();return true;}return advanceAnimator(n,Animator::Bound,amount,{},e);}

bool SourceBank::supports(Navi* n,Motion motion,std::string& e)const{auto it=m->actors.find(n);if(!m->bound||it==m->actors.end()||!it->second.model->clips.count(unsigned(motion))||unsigned(motion)==1000)return fail(e,"source captain selected clip/roster unavailable");e.clear();return true;}
bool SourceBank::finish(Navi* n,std::string& e){auto it=m->actors.find(n);if(it==m->actors.end())return fail(e,"source captain finish roster absent");it->second.state[0].finishing=it->second.state[1].finishing=true;e.clear();return true;}
bool SourceBank::listenerAnimator(const Navi* n,Animator channel,Listener& out,std::string& e)const{unsigned c=unsigned(channel);auto it=m->actors.find(n);if(c>1||it==m->actors.end())return fail(e,"source captain animator listener absent");out=it->second.listener[c];e.clear();return true;}
bool SourceBank::stateAnimator(const Navi* n,Animator channel,MotionState& out,std::string& e)const{unsigned c=unsigned(channel);auto it=m->actors.find(n);if(c>1||it==m->actors.end())return fail(e,"source captain animator state absent");out=it->second.state[c];e.clear();return true;}
bool SourceBank::state(const Navi* n,MotionState& out,std::string& e)const{return stateAnimator(n,Animator::Self,out,e);}

bool SourceBank::startDownMovie(Navi* n,std::string& e){auto it=m->actors.find(n);if(it==m->actors.end())return fail(e,"source captain Down roster absent");if(m->generation>UINT64_MAX-2)return fail(e,"source captain generation exhausted");it->second.state[0].generation=++m->generation;it->second.state[1].generation=++m->generation;it->second.down=true;it->second.downFrame=0;return m->sample(it->second,e);}
bool SourceBank::updateDownMovie(Navi* n,float frame,std::string& e){auto it=m->actors.find(n);if(it==m->actors.end()||!it->second.down||!std::isfinite(frame)||frame<0||frame>207||std::floor(frame)!=frame||frame<it->second.downFrame)return fail(e,"source captain Studio frame invalid");it->second.downFrame=frame;return m->sample(it->second,e);}
bool SourceBank::refresh(Navi* n,Graphics& gfx,std::string& e){auto it=m->actors.find(n);if(it==m->actors.end()||!gfx.mCamera)return fail(e,"source captain draw context absent");auto& a=it->second;if(!m->sample(a,e))return false;Matrix4f world,view;world.makeSRT(Vector3f(1,1,1),n->mSRT.r,n->mSRT.t);gfx.mCamera->mLookAtMtx.multiplyTo(world,view);a.geometry->shape.updateAnim(gfx,view,nullptr,n);a.geometry->shape.drawshape(gfx,*gfx.mCamera,nullptr);return true;}
void SourceBank::forget(Navi* n){m->actors.erase(n);m->bound=m->actors.size()==2;}
bool SourceBank::ready()const{return m->prepared&&m->bound&&m->actors.size()==2;}
const std::string& SourceBank::fingerprint()const{return m->fingerprint;}
} }
