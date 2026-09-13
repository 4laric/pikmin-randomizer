#pragma once
// Source-local TRS samples, shared immutable banks, caller-owned animation clock.
// No Creature pointers: owners/receivers supply generation identities explicitly.
#include "pc_p2_pose_blend.h"
#include <array>
#include <atomic>
#include <cstdint>
#include <istream>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <vector>

namespace p2attach {
using Vec=p2pose::Vec;
constexpr size_t MaxJoints=128,MaxClips=64,MaxSamples=32768,MaxContacts=64,MaxBytes=4*1024*1024;
struct Quat { float x=0,y=0,z=0,w=1; };
struct TRS { Vec translation{0,0,0};Quat rotation;Vec scale{1,1,1}; };
struct Affine { float m[3][4]={{1,0,0,0},{0,1,0,0},{0,0,1,0}}; };
inline bool valid(const Affine& a){for(auto& row:a.m)for(float v:row)if(!std::isfinite(v)||std::fabs(v)>1e9f)return false;return true;}
inline Vec point(const Affine& a,Vec p){return {
    a.m[0][0]*p.x+a.m[0][1]*p.y+a.m[0][2]*p.z+a.m[0][3],
    a.m[1][0]*p.x+a.m[1][1]*p.y+a.m[1][2]*p.z+a.m[1][3],
    a.m[2][0]*p.x+a.m[2][1]*p.y+a.m[2][2]*p.z+a.m[2][3]};}
inline Affine compose(const Affine& a,const Affine& b){Affine out;
    for(int r=0;r<3;++r)for(int c=0;c<4;++c){out.m[r][c]=c==3?a.m[r][3]:0;
        for(int k=0;k<3;++k)out.m[r][c]+=a.m[r][k]*b.m[k][c];}return out;}
inline bool normalize(Quat& q){
    const double n=double(q.x)*q.x+double(q.y)*q.y+double(q.z)*q.z+double(q.w)*q.w;
    if(!std::isfinite(n)||std::fabs(n-1)>0.002)return false;
    const float length=float(std::sqrt(n));q.x/=length;q.y/=length;q.z/=length;q.w/=length;return true;
}
inline Quat slerp(Quat a,Quat b,float t){
    float d=a.x*b.x+a.y*b.y+a.z*b.z+a.w*b.w;
    if(d<0){b={-b.x,-b.y,-b.z,-b.w};d=-d;}
    d=std::min(1.f,d);float left=1-t,right=t;
    if(d<.9995f){const float angle=std::acos(d),den=std::sin(angle);left=std::sin((1-t)*angle)/den;right=std::sin(t*angle)/den;}
    Quat q{left*a.x+right*b.x,left*a.y+right*b.y,left*a.z+right*b.z,left*a.w+right*b.w};
    const float n=std::sqrt(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w);q.x/=n;q.y/=n;q.z/=n;q.w/=n;return q;
}
inline Affine matrix(const TRS& t){
    const auto q=t.rotation;const float x=q.x,y=q.y,z=q.z,w=q.w;
    Affine a{{{(1-2*y*y-2*z*z)*t.scale.x,(2*x*y-2*z*w)*t.scale.y,(2*x*z+2*y*w)*t.scale.z,t.translation.x},
              {(2*x*y+2*z*w)*t.scale.x,(1-2*x*x-2*z*z)*t.scale.y,(2*y*z-2*x*w)*t.scale.z,t.translation.y},
              {(2*x*z-2*y*w)*t.scale.x,(2*y*z+2*x*w)*t.scale.y,(1-2*x*x-2*y*y)*t.scale.z,t.translation.z}}};return a;
}
struct Joint { std::string name;int parent=-1; };
struct Clip { std::string name;int duration=0;std::vector<int> frames;std::vector<TRS> samples; };
struct Bank {
    std::vector<Joint> joints;std::vector<Clip> clips;
    int joint(const std::string& name)const{for(size_t i=0;i<joints.size();++i)if(joints[i].name==name)return int(i);return -1;}
    int clip(const std::string& name)const{for(size_t i=0;i<clips.size();++i)if(clips[i].name==name)return int(i);return -1;}
};
inline bool name(const std::string& s){if(s.empty()||s.size()>63)return false;for(char c:s)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'))return false;return true;}
// Bounded byte buffer also bounds hostile numeric/name tokens before parsing.
inline std::shared_ptr<const Bank> read(std::istream& source){
    std::string bytes;char ch;while(source.get(ch)){if(bytes.size()>=MaxBytes)return {};bytes.push_back(ch);}
    if(!source.eof())return {};
    std::istringstream in(bytes);std::string magic,extra;size_t nj,nc,total=0;
    if(!(in>>magic>>nj>>nc)||magic!="P2_ATTACHMENTS_1"||nj<1||nj>MaxJoints||nc<1||nc>MaxClips)return {};
    auto bank=std::make_shared<Bank>();std::set<std::string> names;
    for(size_t i=0;i<nj;++i){Joint j;if(!(in>>j.name>>j.parent)||!name(j.name)||!names.insert(j.name).second||j.parent<-1||j.parent>=int(i))return {};bank->joints.push_back(j);}
    names.clear();
    for(size_t c=0;c<nc;++c){Clip clip;size_t count;
        if(!(in>>clip.name>>clip.duration>>count)||!name(clip.name)||!names.insert(clip.name).second||clip.duration<1||clip.duration>10000||count<1||count>256||count*nj>MaxSamples-total)return {};
        total+=count*nj;
        for(size_t i=0;i<count;++i){int frame;if(!(in>>frame)||frame<0||frame>=clip.duration||(i&&frame<=clip.frames.back()))return {};clip.frames.push_back(frame);}
        if(clip.frames.front()!=0||clip.frames.back()!=clip.duration-1)return {};
        for(size_t i=0;i<count*nj;++i){TRS t;auto& p=t.translation;auto& q=t.rotation;auto& s=t.scale;
            if(!(in>>p.x>>p.y>>p.z>>q.x>>q.y>>q.z>>q.w>>s.x>>s.y>>s.z)||!p2pose::valid(p)||!normalize(q)||!p2pose::valid(s)||s.x<1e-6f||s.y<1e-6f||s.z<1e-6f||s.x>1000||s.y>1000||s.z>1000)return {};
            clip.samples.push_back(t);}
        bank->clips.push_back(std::move(clip));}
    if(in>>extra)return {};
    return bank;
}
using Token=uint64_t;
inline bool checked(const Bank& bank){
    if(bank.joints.empty()||bank.joints.size()>MaxJoints||bank.clips.empty()||bank.clips.size()>MaxClips)return false;
    std::set<std::string> names;size_t total=0;
    for(size_t i=0;i<bank.joints.size();++i){const auto& j=bank.joints[i];if(!name(j.name)||!names.insert(j.name).second||j.parent<-1||j.parent>=int(i))return false;}
    names.clear();
    for(const auto& c:bank.clips){p2pose::Interval span;
        if(!name(c.name)||!names.insert(c.name).second||c.duration<1||c.duration>10000||!p2pose::bracket(c.frames,0,span)||c.frames.front()!=0||c.frames.back()!=c.duration-1||c.samples.size()!=c.frames.size()*bank.joints.size()||c.samples.size()>MaxSamples-total)return false;
        total+=c.samples.size();
        for(const auto& t:c.samples){auto q=t.rotation;const auto s=t.scale;
            if(!p2pose::valid(t.translation)||!normalize(q)||!p2pose::valid(s)||s.x<1e-6f||s.y<1e-6f||s.z<1e-6f||s.x>1000||s.y>1000||s.z>1000)return false;}}
    return true;
}
class Instance {
    std::shared_ptr<const Bank> bank_;
    std::array<Affine,MaxJoints> world_{};
    Token token_=0;uint64_t tick_=0;bool sampled_=false,ready_=false,paused_=false,dead_=false;
    int clip_=-1;float frame_=0;
    static Token fresh(){static std::atomic<Token> next{1};Token n=next.load();
        do{if(n==UINT64_MAX)return 0;}while(!next.compare_exchange_weak(n,n+1));return n;}
public:
    Instance()=default;Instance(const Instance&)=delete;Instance& operator=(const Instance&)=delete;
    void reset(){token_=0;bank_.reset();sampled_=ready_=paused_=dead_=false;clip_=-1;}
    Token bind(std::shared_ptr<const Bank> bank){reset();if(!bank||!checked(*bank))return 0;bank_=std::move(bank);token_=fresh();return token_;}
    bool sample(Token token,int clip,float frame,const Affine& owner,uint64_t tick,bool paused=false,bool dead=false){
        if(!token||token!=token_)return false;
        if(dead){dead_=true;ready_=false;return true;}
        if(dead_ || (sampled_&&tick<tick_)){ready_=false;return false;}
        if(paused){paused_=true;return ready_;}
        if(clip<0||size_t(clip)>=bank_->clips.size()||!std::isfinite(frame)||!valid(owner)){ready_=false;return false;}
        const auto& c=bank_->clips[clip];p2pose::Interval span;
        if(frame<0||frame>c.duration-1||!p2pose::bracket(c.frames,frame,span)){ready_=false;return false;}
        std::array<Affine,MaxJoints> next;
        for(size_t j=0;j<bank_->joints.size();++j){const auto& a=c.samples[span.left*bank_->joints.size()+j];const auto& b=c.samples[span.right*bank_->joints.size()+j];
            TRS blended{p2pose::mix(a.translation,b.translation,span.weight),slerp(a.rotation,b.rotation,span.weight),p2pose::mix(a.scale,b.scale,span.weight)};
            const int parent=bank_->joints[j].parent;next[j]=compose(parent<0?owner:next[parent],matrix(blended));
            if(!valid(next[j])){ready_=false;return false;}}
        world_=next;tick_=tick;sampled_=ready_=true;paused_=false;clip_=clip;frame_=frame;return true;
    }
    bool socket(Token token,int joint,Affine& out)const{if(!token||token!=token_||!ready_||joint<0||size_t(joint)>=bank_->joints.size())return false;out=world_[joint];return true;}
    bool active(Token token)const{return token&&token==token_&&ready_&&!paused_&&!dead_;}
    int clip()const{return clip_;}float frame()const{return frame_;}
};
// World-unit spherical volume, attached to an affine-transformed local offset.
// No sweep or native damage policy: caller dispatches its receiver on true.
class DamageVolume {
    Token owner_=0;uint64_t cycle_=0;size_t count_=0;std::array<Token,MaxContacts> hit_{};
public:
    bool contact(const Instance& instance,Token owner,uint64_t cycle,int clip,int joint,Vec offset,float radius,
                 float start,float end,Token receiver,Vec target,float targetRadius=0){
        if(!instance.active(owner)||!cycle||!receiver||!p2pose::valid(offset)||!p2pose::valid(target)||!std::isfinite(radius)||radius<=0||radius>1000000||!std::isfinite(targetRadius)||targetRadius<0||targetRadius>1000000||!std::isfinite(start)||!std::isfinite(end)||start<0||end<=start)return false;
        if(owner!=owner_){owner_=owner;cycle_=0;count_=0;}
        if(cycle<cycle_)return false;
        if(cycle>cycle_){cycle_=cycle;count_=0;}
        if(instance.clip()!=clip||instance.frame()<start||instance.frame()>=end)return false;
        Affine jointWorld;if(!instance.socket(owner,joint,jointWorld))return false;
        const Vec p=point(jointWorld,offset);if(!p2pose::valid(p))return false;
        const double x=double(p.x)-target.x,y=double(p.y)-target.y,z=double(p.z)-target.z,r=double(radius)+targetRadius;
        if(x*x+y*y+z*z>r*r)return false;
        for(size_t i=0;i<count_;++i)if(hit_[i]==receiver)return false;
        if(count_==MaxContacts)return false;
        hit_[count_++]=receiver;return true;
    }
};
}
