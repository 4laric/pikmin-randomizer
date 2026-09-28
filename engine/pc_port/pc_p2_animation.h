#ifndef PC_P2_ANIMATION_H
#define PC_P2_ANIMATION_H
// Bounded baked-pose playback. P1 combat/event timing remains authoritative.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <istream>
#include <string>
#include <vector>
namespace p2animation {
constexpr size_t ClipBytes=512*1024, TotalBytes=2*1024*1024;
struct Clip {
    std::string name;
    int count=0, duration=0;
    std::vector<int> frames;
    size_t index(float phase,bool corpse=false) const {
        if(corpse)return count-1;
        if(!std::isfinite(phase))phase=0;
        phase=std::max(0.f,std::min(1.f,phase));
        if(frames.empty())return size_t(phase*(count-1)); // v1 compatibility
        const float source=phase*(duration-1);
        size_t best=0;
        for(size_t i=1;i<frames.size();++i)
            if(std::fabs(frames[i]-source)<std::fabs(frames[best]-source))best=i;
        return best;
    }
};
inline bool parse(std::istream& in,std::vector<Clip>& clips) {
    std::string word;
    if(!(in>>word) || (word!="P2_SNOW_1" && word!="P2_SNOW_2"))return false;
    const bool modern=word=="P2_SNOW_2";
    std::vector<Clip> parsed;
    for(const char* name:{"wait1","move1","attack","dead","flick"}) {
        Clip clip;
        if(!(in>>clip.name>>clip.count>>clip.duration) || clip.name!=name || clip.count<1 ||
           clip.count>(modern?24:12) || clip.duration<1 || clip.duration>10000)return false;
        if(modern) {
            for(int i=0;i<clip.count;++i) {
                int frame;
                if(!(in>>frame) || frame<0 || frame>=clip.duration || (i && frame<=clip.frames.back()))return false;
                clip.frames.push_back(frame);
            }
            if(clip.frames.front()!=0 || clip.frames.back()!=clip.duration-1)return false;
        }
        parsed.push_back(clip);
    }
    if(in>>word)return false;
    clips=parsed;
    return true;
}
inline uint32_t be32(const std::vector<unsigned char>& data,size_t at) {
    return uint32_t(data[at])<<24|uint32_t(data[at+1])<<16|uint32_t(data[at+2])<<8|data[at+3];
}
inline bool resources(const std::vector<unsigned char>& data,std::vector<unsigned char>& out) {
    std::vector<unsigned char> parts[3];
    size_t at=0;
    bool ended=false;
    while(at+8<=data.size()) {
        uint32_t tag=be32(data,at),size=be32(data,at+4);
        if(size>data.size()-at-8)return false;
        size_t end=at+8+size;
        int slot=tag==32?0:tag==34?1:tag==48?2:-1;
        if(slot>=0) {
            if(!parts[slot].empty())return false;
            parts[slot].assign(data.begin()+at,data.begin()+end);
        }
        at=end;
        if(tag==65535){ended=true;break;}
    }
    if(at!=data.size() || !ended)return false;
    out.clear();
    for(auto& part:parts) {
        if(part.empty())return false;
        out.insert(out.end(),part.begin(),part.end());
    }
    return true;
}
}
#endif
