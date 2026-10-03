#include "pc_p2_original_shijimi_bank.h"
#include "pc_p2_original_honey_policy.h"
#include "pc_p2_original_pelplant_geometry.h"
#include "pc_p2_pose_family.h"
#include "pc_p2_motion_events.h"
#include "netplay/pc_netplay_sha256.h"
#include <array>
#include <fstream>
#include <iomanip>
#include <limits>
#include <locale>
#include <sstream>
namespace p2original { namespace shijimi {
namespace {
using Clock=p2originalresource::honey::ReceiverClock;
using Clip=p2originalresource::honey::ReceiverClip;
const char* names[]={"carry","dead","move"};
constexpr int durations[]={40,61,8};
const char* sources[]={"0dfce9a247fa223efc536f0766c0feb1cef338f0873bfc72576b5d9be3c4366e",
 "f74878b24c8813b46a9d29b89624362e0b611e8a1548f1fe7e87b0b4bddd8a52",
 "45004202a8e74994f3cebc1f6a234a08f667f0de4432b7e0f8e388ef1f17f381"};
struct AppHeap{int previous;AppHeap():previous(gsys->setHeap(SYSHEAP_App)){}~AppHeap(){gsys->setHeap(previous);}};
bool fail(std::string& e,const char* message){e=message;return false;}
std::string hash(const std::string& bytes){unsigned char h[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),h);std::string out;const char* hex="0123456789abcdef";for(auto c:h){out+=hex[c>>4];out+=hex[c&15];}return out;}
bool read(const std::string& file,std::string& out){std::ifstream in(file,std::ios::binary);if(!in)return false;out.assign(std::istreambuf_iterator<char>(in),{});return !in.bad()&&out.size()<=4*1024*1024;}
struct Track{unsigned motion=2;Clock clock;p2pose::Track pose;};
}
struct SourceBank::Impl {
 p2posefamily::Bank bank{"ORIGINAL_SHIJIMI"};p2poseload::Shared shared;
 std::array<Clip,3> clips;std::array<std::vector<Matrix4f>,3> joints;
 std::map<const Creature*,std::unique_ptr<Track>> tracks;std::string fingerprint;bool ready=false;
 bool load(std::string& e){
  if(ready)return true;if(!gsys)return fail(e,"source77 bank requires native system");AppHeap heap;
  std::string metadata,events,jointBytes;
  if(!read("p2-original-shijimi-bank.txt",metadata)||!read("p2-original-shijimi-events.txt",events)||!read("p2-original-shijimi-joint0.txt",jointBytes))return fail(e,"source77 genuine geometry/events/joint bank missing");
  std::istringstream in(metadata),jointIn(jointBytes);in.imbue(std::locale::classic());jointIn.imbue(std::locale::classic());
  std::string magic,receipt,eventHash,jointHash;
  if(!(in>>magic>>receipt>>eventHash>>jointHash)||magic!="P2_ORIGINAL_SHIJIMI_BANK_1"||!p2retail::hash(receipt)||eventHash!=hash(events)||jointHash!=hash(jointBytes))return fail(e,"source77 bank closure hash mismatch");
  p2retail::Table table;try{std::istringstream eventIn(events);table=p2retail::read(eventIn);}catch(const std::exception&){return fail(e,"source77 motion event table invalid");}
  unsigned count;if(table.registrySha!="15c77627bfd0646f5dfc104492867c53cc021af940f3135394b0d25519f48806"||table.motions.size()!=3
   ||!(jointIn>>magic>>count)||magic!="P2_ORIGINAL_SHIJIMI_JOINT0_1"||count!=3)return fail(e,"source77 original animation registry/joint topology changed");
  bank.reset();shared={};std::size_t total=0;std::string closure=metadata+events+jointBytes;
  for(unsigned n=0;n<3;++n){
   const auto& motion=table.motions[n];
   if(motion.name!=std::string(names[n])+".bca"||motion.duration!=durations[n]||motion.attribute!=2||motion.sha!=sources[n])return fail(e,"source77 literal motion changed");
   auto& clip=clips[n];clip={};clip.duration=float(durations[n]);
   for(auto key:motion.events){clip.keys.push_back({float(key.frame),key.type});if(key.type==0)clip.loopStart=float(key.frame);if(key.type==1)clip.loopEnd=float(key.frame);}
   if(!clip.valid()||clip.keys.size()!=(n==1?0:2)||clip.loopStart!=(n==0?10.f:n==2?0.f:-1.f)||clip.loopEnd!=(n==0?29.f:n==2?7.f:-1.f))return fail(e,"source77 authored loop keys changed");
   std::string word,name,stem;int poses,duration;
   if(!(in>>word>>name>>poses>>duration>>stem)||word!="clip"||name!=names[n]||stem!="fly_ShijimiChou_"+name||poses<2||poses>64||duration!=durations[n])return fail(e,"source77 pose index changed");
   std::vector<int> frames;for(int p=0;p<poses;++p){int frame;if(!(in>>frame))return fail(e,"source77 pose frames truncated");frames.push_back(frame);}
   if(!p2posefamily::Bank::validFrames(frames,poses,duration))return fail(e,"source77 pose sample indices invalid");
   // Authenticate converted resources before the engine loads any Shape.
   for(int p=0;p<poses;++p){std::string expected,bytes;if(!(in>>expected)||!p2retail::hash(expected)||!read(p2poseload::stemPath(true,stem,p),bytes)||hash(bytes)!=expected)return fail(e,"source77 geometry differs from source closure");closure+=expected;}
   if(!(jointIn>>name>>duration)||name!=names[n]||duration!=durations[n])return fail(e,"source77 joint motion index changed");
   joints[n].clear();for(int f=0;f<duration;++f){Matrix4f local;local.makeIdentity();for(int r=0;r<3;++r)for(int c=0;c<4;++c)if(!(jointIn>>local.mMtx[r][c])||!std::isfinite(local.mMtx[r][c]))return fail(e,"source77 mechanical joint sample invalid");joints[n].push_back(local);}
   std::vector<Shape*> shapes;if(!p2posefamily::loadFamilyClip(bank,name,stem,poses,duration,frames,shared,total,shapes,e))return false;
  }
  if((in>>magic)||(jointIn>>magic)||!bank.ready()||!bank.basePose()||!pelplant::Geometry::admits(*bank.owner()))return fail(e,"source77 private flattened bank incomplete/trailing");
  fingerprint=hash(closure);ready=true;e.clear();return true;
 }
 bool present(Track& t,Shape& shape,float dt,std::string& e){
  const auto* clip=bank.clip(names[t.motion]);if(!clip)return fail(e,"source77 pose clip missing");
  t.pose.shape=&shape;if(t.pose.view.scratch.positions.empty())t.pose.size(*bank.basePose());t.pose.advance(dt);
  auto tune=p2motion::tunables();tune.crossfadeSeconds=0;
  if(!p2pose::present(t.pose,names[t.motion],clip->poses.size(),[clip](std::size_t n)->const p2pose::Pose&{return clip->poses[n];},clip->frames,std::min(t.clock.frame,float(durations[t.motion]-1)),tune,clip->seamContinuous).ok)return fail(e,"source77 private geometry pose write failed");
  return true;
 }
 bool parse(const std::string& bytes,unsigned& motion,Clock& clock,std::string& e)const{
  if(!ready||bytes.size()>512)return fail(e,"source77 cold clock needs actual prepared bank");
  std::istringstream in(bytes);in.imbue(std::locale::classic());std::string magic,source,extra;unsigned complete;
  if(!(in>>magic>>source>>motion>>clock.frame>>clock.next>>complete)||magic!="P2OS77A1"||source!=fingerprint||motion>2||complete>1
   ||!std::isfinite(clock.frame)||clock.frame<0||clock.frame>float(durations[motion])||clock.next>clips[motion].keys.size()||(in>>extra))return fail(e,"invalid source77 saved mechanical clock");
  clock.complete=complete!=0;if(clock.complete&&clock.frame!=float(durations[motion]-1))return fail(e,"source77 completed clock frame changed");
  std::size_t expected=0;while(expected<clips[motion].keys.size()&&clips[motion].keys[expected].frame<std::floor(clock.frame))++expected;
  if(clock.next!=expected)return fail(e,"source77 saved key frontier differs from its mechanical frame");
  e.clear();return true;
 }
};
SourceBank::SourceBank():m(std::make_unique<Impl>()){}
SourceBank::~SourceBank()=default;
bool SourceBank::prepare(Shape*& out,std::string& e){out=nullptr;if(!m->load(e))return false;out=m->bank.owner();e.clear();return true;}
bool SourceBank::motion(const Creature* actor,unsigned motion,float frame,Shape& shape,std::string& e){
 if(!m->ready||!actor||motion>2||!std::isfinite(frame)||frame<0||frame>durations[motion])return fail(e,"source77 motion lacks prepared actual body/bank");AppHeap heap;
 auto& track=m->tracks[actor];if(!track)track=std::make_unique<Track>();track->motion=motion;track->clock.reset();track->clock.frame=frame;
 // getLowestAnimKey compares against int(timer), including fractional births.
 while(track->clock.next<m->clips[motion].keys.size()&&m->clips[motion].keys[track->clock.next].frame<std::floor(frame))++track->clock.next;
 return m->present(*track,shape,0,e);
}
bool SourceBank::advance(const Creature* actor,Shape& shape,float seconds,std::vector<int>& keys,std::string& e){
 auto i=m->tracks.find(actor);if(i==m->tracks.end()||!std::isfinite(seconds)||seconds<0||seconds>2)return fail(e,"source77 advance outside actual animation");AppHeap heap;
 std::vector<int> prospective;auto& t=*i->second;bool finishing=false;
 if(!t.clock.advance(m->clips[t.motion],seconds*30,finishing,[&](int key){prospective.push_back(key);return true;})||!m->present(t,shape,seconds,e))return fail(e,"source77 mechanical clock/presentation failed");
 keys=std::move(prospective);e.clear();return true;
}
bool SourceBank::joint0(const Creature* actor,const Matrix4f& root,Matrix4f& out,std::string& e)const{
 auto i=m->tracks.find(actor);if(i==m->tracks.end())return fail(e,"source77 joint request outside actual animation");const auto& t=*i->second;
 // J3DAnmTransformFull uses integer BCA samples, not the render interpolation.
 const unsigned frame=unsigned(std::min(std::floor(t.clock.frame),float(durations[t.motion]-1)));
 Matrix4f copy=root;copy.multiplyTo(m->joints[t.motion][frame],out);e.clear();return true;
}
bool SourceBank::capture(const Creature* actor,std::string& bytes,std::string& e)const{
 auto i=m->tracks.find(actor);if(i==m->tracks.end())return fail(e,"source77 capture outside actual animation");const auto& t=*i->second;std::ostringstream out;out.imbue(std::locale::classic());
 out<<std::setprecision(std::numeric_limits<float>::max_digits10)<<"P2OS77A1 "<<m->fingerprint<<' '<<t.motion<<' '<<t.clock.frame<<' '<<t.clock.next<<' '<<t.clock.complete;bytes=out.str();e.clear();return true;
}
bool SourceBank::validate(const std::string& bytes,std::string& e)const{unsigned motion;Clock clock;return m->parse(bytes,motion,clock,e);}
bool SourceBank::restore(const Creature* actor,Shape& shape,const std::string& bytes,std::string& e){
 unsigned motion;Clock clock;if(!actor||!m->parse(bytes,motion,clock,e))return false;AppHeap heap;auto& slot=m->tracks[actor];if(!slot)slot=std::make_unique<Track>();slot->motion=motion;slot->clock=clock;return m->present(*slot,shape,0,e);
}
void SourceBank::forget(const Creature* actor){m->tracks.erase(actor);}
const std::string& SourceBank::fingerprint()const{return m->fingerprint;}
} }
