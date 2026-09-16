#pragma once
#include "pc_p2_pose_blend.h"
#include <cstdint>
#include <cstring>
#include <set>

namespace p2pose {
struct Baked { Pose pose; std::vector<unsigned char> topology; };
inline bool decodeBaked(const std::vector<unsigned char>& raw, Baked& out) {
    if (raw.empty() || raw.size()>1024*1024) return false;
    auto u32=[&](size_t p) { return uint32_t(raw[p])<<24|uint32_t(raw[p+1])<<16|uint32_t(raw[p+2])<<8|raw[p+3]; };
    auto f32=[&](size_t p) { auto bits=u32(p); float value; std::memcpy(&value,&bits,4); return value; };
    Baked next; std::set<uint32_t> tags; size_t at=0; uint32_t last=0;
    float bounds[6]={};
    while(at<raw.size()) {
        if(at%32 || raw.size()-at<8) return false;
        const auto tag=u32(at), bytes=u32(at+4);
        if(bytes>raw.size()-at-8 || !tags.insert(tag).second) return false;
        const size_t end=at+8+bytes, length=end-at;
        if(end%32 || (tag==65535 && end!=raw.size())) return false;
        if(tag==16 || tag==17) {
            if(length<32) return false;
            const auto count=u32(at+8);
            if(!count || count>MaxVectors || length!=((32+12*size_t(count)+31)/32)*32) return false;
            for(size_t p=at+12;p<at+32;++p) if(raw[p]) return false;
            for(size_t p=at+32+12*count;p<end;++p) if(raw[p]) return false;
            auto& vectors=tag==16?next.pose.positions:next.pose.normals;
            for(size_t i=0;i<count;++i) {
                const size_t p=at+32+12*i; Vec v={f32(p),f32(p+4),f32(p+8)};
                if(!valid(v) || (tag==17 && !unit(v,v))) return false;
                vectors.push_back(v);
            }
            next.topology.insert(next.topology.end(),raw.begin()+at,raw.begin()+at+32);
        } else {
            if(tag==64) {
                if(length!=64 || u32(at+8)!=1) return false;
                for(size_t p=at+12;p<end;++p) if(raw[p]) return false;
            }
            if(tag==96) {
                if(length<108 || u32(at+8)!=1 || u32(at+32)!=0xffffffff || u32(at+36)!=0) return false;
                for(size_t i=0;i<9;++i) if(f32(at+68+4*i)!=(i<3?1.f:0.f)) return false;
                for(size_t i=0;i<7;++i) if(!std::isfinite(f32(at+40+4*i))) return false;
                for(size_t i=0;i<6;++i) bounds[i]=f32(at+40+4*i);
                next.topology.insert(next.topology.end(),raw.begin()+at,raw.begin()+at+40);
                next.topology.insert(next.topology.end(),raw.begin()+at+68,raw.begin()+end);
            } else next.topology.insert(next.topology.end(),raw.begin()+at,raw.begin()+end);
        }
        last=tag; at=end;
    }
    if(last!=65535) return false;
    for(auto tag:{16u,17u,32u,34u,48u,64u,80u,96u}) if(!tags.count(tag)) return false;
    for(size_t i=0;i<3;++i) if(bounds[i]>bounds[i+3]) return false;
    for(auto v:next.pose.positions)
        if(v.x<bounds[0]-.001f || v.y<bounds[1]-.001f || v.z<bounds[2]-.001f ||
           v.x>bounds[3]+.001f || v.y>bounds[4]+.001f || v.z>bounds[5]+.001f) return false;
    out=std::move(next); return true;
}
}
