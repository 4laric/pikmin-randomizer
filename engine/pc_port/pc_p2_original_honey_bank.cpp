#include "pc_p2_original_honey_bank.h"
#include "pc_p2_original_honey_bank_validation.h"
#include "sysNew.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "pc_p2_motion_events.h"
#include "pc_p2_attachments.h"
#include "netplay/pc_netplay_sha256.h"
#include "Matrix4f.h"
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace p2originalresource { namespace honey {
namespace {
struct AppHeap {int previous;AppHeap():previous(gsys->setHeap(SYSHEAP_App)){}~AppHeap(){gsys->setHeap(previous);}};
const char* names[]={"born","airwait","fall","swing","wait","touch","dead"};
const int durations[]={30,20,8,40,40,60,50};
bool fail(std::string& e,const char* why){e=why;return false;}
std::string hash(const std::string& bytes){unsigned char h[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),h);std::string s;const char* x="0123456789abcdef";for(auto b:h){s+=x[b>>4];s+=x[b&15];}return s;}
bool read(const std::string& name,std::string& out){std::ifstream f(name,std::ios::binary);if(!f)return false;out.assign(std::istreambuf_iterator<char>(f),{});return !f.bad()&&out.size()<=4194304;}
ReceiverClip clock(const p2retail::Motion& motion){ReceiverClip c;c.duration=float(motion.duration);for(auto key:motion.events){c.keys.push_back({float(key.frame),key.type});if(key.type==0)c.loopStart=float(key.frame);if(key.type==1)c.loopEnd=float(key.frame);}return c;}
struct Track {unsigned motion=0;ReceiverClock clock;p2pose::Track pose;p2attach::Instance joints;p2attach::Token token=0;std::uint64_t tick=0;};
}
struct SourceBank::Impl {
 p2posefamily::Bank bank{"ORIGINAL_HONEY"};p2poseload::Shared shared;
 std::shared_ptr<const p2attach::Bank> joints;
 std::array<ReceiverClip,7> clocks;Resources resource;std::string fingerprint;
 std::map<const Actor*,std::unique_ptr<Track>> tracks;bool loaded=false;
 bool load(std::string& e){
  if(loaded)return true;
  if(!gsys)return fail(e,"Honey actual native system missing");
  AppHeap heap;
  std::string metadata,events,attach,receivers;
  if(!read("p2-original-honey-bank.txt",metadata)||!read("p2-original-honey-events.txt",events)||!read("p2-original-honey-attach.txt",attach)||!read("p2-honey-receiver-events.txt",receivers))return fail(e,"Honey actual source bank/event/attachment/receiver file missing");
  std::istringstream in(metadata);in.imbue(std::locale::classic());std::string magic,receipt,eventHash,jointHash,receiverHash;
  if(!(in>>magic>>receipt>>eventHash>>jointHash>>receiverHash)||magic!="P2_ORIGINAL_HONEY_BANK_1"||!p2retail::hash(receipt)||eventHash!=hash(events)||jointHash!=hash(attach)||receiverHash!=hash(receivers))return fail(e,"Honey source closure hash invalid");
  p2retail::Table table,receiverTable;try{std::istringstream a(events),b(receivers);table=p2retail::read(a);receiverTable=p2retail::read(b);}catch(...){return fail(e,"Honey actual source event grammar invalid");}
  std::istringstream attachment(attach);joints=p2attach::read(attachment);
  if(!joints||joints->joints.size()!=1||joints->joint("all")!=0||joints->clips.size()!=7||table.motions.size()!=7||receiverTable.motions.size()!=3)return fail(e,"Honey source rig/clip/receiver topology invalid");
  bank.reset();shared={};std::size_t total=0;std::string closure=metadata+events+attach+receivers;
  for(unsigned k=0;k<7;++k){std::string name,stem,word;int count,duration;if(!(in>>word>>name>>count>>duration>>stem)||word!="clip"||name!=names[k]||stem!="original_honey_"+name||count<1||count>64||duration!=durations[k])return fail(e,"Honey source pose index invalid");
   std::vector<int> frames;for(int i=0;i<count;++i){int frame;if(!(in>>frame))return fail(e,"Honey pose frames truncated");frames.push_back(frame);}
   if(!p2posefamily::Bank::validFrames(frames,count,duration)||table.motions[k].name!=name+".bca"||table.motions[k].duration!=duration||joints->clips[k].name!=name||joints->clips[k].duration!=duration)return fail(e,"Honey pose/event/attachment clip mismatch");
   clocks[k]=clock(table.motions[k]);if(!clocks[k].valid())return fail(e,"Honey source clock invalid");
   std::vector<Shape*> shapes;if(!p2posefamily::loadFamilyClip(bank,name,stem,count,duration,frames,shared,total,shapes,e))return false;
   for(int i=0;i<count;++i){char suffix[16];std::snprintf(suffix,sizeof(suffix),"_%02d.mod",i);std::string expected,bytes;if(!(in>>expected)||!p2retail::hash(expected)||!read(p2poseload::stemPath(true,stem,i),bytes)||hash(bytes)!=expected)return fail(e,"Honey sampled geometry hash differs from source receipt");closure+=expected;}
  }
  std::string word;if(!(in>>word>>resource.gravity)||word!="gravity"||resource.gravity!=560.0f||(in>>word))return fail(e,"Honey actual source gravity invalid");
  if(!bank.owner()||!bank.basePose()||!p2original::pelplant::Geometry::admits(*bank.owner()))return fail(e,"Honey actual private flattened geometry missing");
  const char* receiverNames[]={"mizunomi.bca","grow_up1.bca","grow_up2.bca"};
  for(unsigned i=0;i<3;++i){const p2retail::Motion* found=nullptr;for(const auto& c:receiverTable.motions)if(c.name==receiverNames[i])found=&c;if(!found)return fail(e,"Honey source receiver clip missing");resource.receiverClips[i]=clock(*found);if(!resource.receiverClips[i].valid())return fail(e,"Honey source receiver clock invalid");}
  // NaviMgr and FakePiki share the proven original source animMgr/arc.
  resource.receiverClips[3]=resource.receiverClips[0];resource.sourceShape=bank.owner();resource.collider=true;for(auto& clip:resource.clips)clip=true;
  fingerprint=hash(closure);loaded=true;e.clear();return true;
 }
 bool present(Track& t,Shape& shape,float dt,std::string& e){AppHeap heap;auto* clip=bank.clip(names[t.motion]);if(!clip)return fail(e,"Honey actual pose clip lost");t.pose.shape=&shape;if(t.pose.view.scratch.positions.empty())t.pose.size(*bank.basePose());t.pose.advance(dt);float frame=std::min(t.clock.frame,float(clip->duration-1));if(!p2pose::present(t.pose,names[t.motion],clip->poses.size(),[&](std::size_t n)->const p2pose::Pose&{return clip->poses[n];},clip->frames,frame,p2motion::tunables(),clip->seamContinuous).ok)return fail(e,"Honey private source pose write failed");return true;}
 bool sample(const Actor& actor,Track& track,std::string& e){Matrix4f root;if(!actorWorld(actor,root,e))return false;p2attach::Affine world;for(int r=0;r<3;++r)for(int c=0;c<4;++c)world.m[r][c]=root.mMtx[r][c];float frame=std::min(track.clock.frame,float(durations[track.motion]-1));if(!track.joints.sample(track.token,int(track.motion),frame,world,++track.tick))return fail(e,"Honey actual source joint sample invalid");return true;}
};
SourceBank::SourceBank():m(std::make_unique<Impl>()){}
SourceBank::~SourceBank()=default;
const std::string& SourceBank::fingerprint()const{return m->fingerprint;}
bool SourceBank::resources(Resources& out,std::string& e){if(!m->load(e))return false;AppHeap heap;out=m->resource;e.clear();return true;}
bool SourceBank::motion(Actor& actor,unsigned motion,std::string& e){if(!m->loaded||motion>6||motion!=sourceMotion(phase(actor)))return fail(e,"Honey motion lacks actual source phase/bank");AppHeap heap;auto& slot=m->tracks[&actor];if(!slot){slot=std::make_unique<Track>();slot->token=slot->joints.bind(m->joints);if(!slot->token)return fail(e,"Honey actual joint binding failed");}slot->motion=motion;slot->clock.reset();return m->sample(actor,*slot,e)&&m->present(*slot,shape(actor),0,e);}
bool SourceBank::advance(Actor& actor,Shape& shape,float dt,std::vector<int>& events,std::string& e){auto i=m->tracks.find(&actor);if(i==m->tracks.end()||!std::isfinite(dt)||dt<0)return fail(e,"Honey advance outside actual source animation");auto& t=*i->second;bool finishing=false;std::vector<int> next;if(!t.clock.advance(m->clocks[t.motion],dt*30,finishing,[&](int key){next.push_back(key);return true;}))return fail(e,"Honey source event advance invalid");if(!m->sample(actor,t,e))return false;
 if(!m->present(t,shape,dt,e))return false;events=std::move(next);e.clear();return true;}
bool SourceBank::collisionCentre(const Actor& actor,P2EggVec3& out,std::string& e){auto i=m->tracks.find(&actor);if(i==m->tracks.end()||!m->sample(actor,*i->second,e))return false;p2attach::Affine joint;if(!i->second->joints.socket(i->second->token,0,joint))return fail(e,"Honey actual source collider socket missing");out={joint.m[0][3],joint.m[1][3],joint.m[2][3]};e.clear();return true;}
bool SourceBank::captureAnimation(const Actor& actor,std::string& out,std::string& e)const{auto i=m->tracks.find(&actor);if(i==m->tracks.end())return fail(e,"Honey snapshot outside source animation");const auto& t=*i->second;std::ostringstream s;s.imbue(std::locale::classic());s<<std::setprecision(std::numeric_limits<float>::max_digits10)<<"P2OHA1 "<<m->fingerprint<<' '<<t.motion<<' '<<t.clock.frame<<' '<<t.clock.next<<' '<<t.clock.complete;out=s.str();e.clear();return true;}
bool SourceBank::restoreAnimation(Actor& actor,const std::string& bytes,std::string& e){if(!m->loaded)return fail(e,"Honey source animation bank absent");unsigned motion;ReceiverClock clock;if(!animationSnapshot(bytes,m->fingerprint,phase(actor),m->clocks,motion,clock,e))return false;AppHeap heap;auto& slot=m->tracks[&actor];if(!slot){slot=std::make_unique<Track>();slot->token=slot->joints.bind(m->joints);if(!slot->token)return fail(e,"Honey actual joint binding failed");}slot->motion=motion;slot->clock=clock;return m->sample(actor,*slot,e)&&m->present(*slot,shape(actor),0,e);}
bool SourceBank::validateAnimation(Phase phase,const std::string& bytes,std::string& e)const{if(!m->loaded)return fail(e,"Honey source animation bank absent");unsigned motion;ReceiverClock clock;return animationSnapshot(bytes,m->fingerprint,phase,m->clocks,motion,clock,e);}
bool SourceBank::sourceClocks(std::array<ReceiverClip,7>& out,std::string& e)const{if(!m->loaded)return fail(e,"Honey source animation bank absent");out=m->clocks;e.clear();return true;}
void SourceBank::forget(Actor& actor){m->tracks.erase(&actor);}
} }
