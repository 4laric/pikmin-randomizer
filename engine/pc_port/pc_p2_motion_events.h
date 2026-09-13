#pragma once
#include <cmath>
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace p2retail {
struct Event { int frame, type; };
struct Motion { std::string name, sha; int duration, attribute; std::vector<Event> events; };
struct Table { std::string registrySha; std::vector<Motion> motions; };
inline bool hash(const std::string& s) {
    return s.size()==64 && s.find_first_not_of("0123456789abcdef")==std::string::npos;
}
// Exact positive-timer predicate from SysShape::Animator::animate. Metadata frame
// N triggers only once int(timer)>N; it is not a generic clock marker at N.
inline bool due(const Event& event, double timer) {
    return event.frame>=0 && std::isfinite(timer) && timer>=0 && double(event.frame)<std::floor(timer);
}
inline Table read(std::istream& in) {
    auto fail=[](){throw std::runtime_error("invalid retail motion event table");};
    Table result; std::string magic; int count;
    if(!(in>>magic>>result.registrySha>>count) || magic!="P2_RETAIL_EVENTS_1" ||
       !hash(result.registrySha) || count<1 || count>256) fail();
    std::set<std::string> names; unsigned total=0;
    for(int i=0;i<count;++i) {
        Motion m; int n;
        if(!(in>>m.name>>m.duration>>m.attribute>>m.sha>>n) || m.name.size()<5 || m.name.size()>68 ||
           m.name.substr(m.name.size()-4)!=".bca" ||
           m.name.substr(0,m.name.size()-4).find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789_")!=std::string::npos ||
           !names.insert(m.name).second || !hash(m.sha) || m.duration<1 || m.duration>10000 ||
           m.attribute<0 || m.attribute>4 || n<0 || n>4096) fail();
        total+=unsigned(n); if(total>65536) fail();
        int previous=-1, loopStart=-1;
        for(int j=0;j<n;++j) {
            Event e;
            if(!(in>>e.frame>>e.type) || e.frame<0 || e.frame<previous || e.frame>=m.duration ||
               e.type<0 || e.type>=1000) fail();
            if(e.type==0) loopStart=e.frame;
            if(e.type==1 && (loopStart<0 || e.frame<=loopStart)) fail();
            previous=e.frame; m.events.push_back(e);
        }
        result.motions.push_back(m);
    }
    if(in>>magic) fail();
    return result;
}
} // namespace p2retail
