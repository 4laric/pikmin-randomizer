#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <utility>
#include <vector>

namespace p2pose {
constexpr std::size_t MaxVectors = 65536;
struct Vec { float x, y, z; };
struct Pose { std::vector<Vec> positions, normals; };
struct Interval { std::size_t left = 0, right = 0; float weight = 0; };

// The authoritative player owns looping and events. This only clamps a frame.
inline bool bracket(const std::vector<int>& frames, float frame, Interval& out) {
    if (frames.empty() || frames.size() > 256 || !std::isfinite(frame)) return false;
    for (std::size_t i=0; i<frames.size(); ++i)
        if (frames[i]<0 || frames[i]>10000 || (i && frames[i]<=frames[i-1])) return false;
    Interval next;
    if (frame <= frames.front()) next = {0,0,0};
    else if (frame >= frames.back()) next = {frames.size()-1,frames.size()-1,0};
    else {
        auto hi = std::lower_bound(frames.begin(),frames.end(),frame);
        const auto right = std::size_t(hi-frames.begin());
        if (frame == *hi) next = {right,right,0};
        else next = {right-1,right,(frame-frames[right-1])/float(frames[right]-frames[right-1])};
    }
    out = next;
    return true;
}
inline bool valid(Vec v) {
    return std::isfinite(v.x) && std::isfinite(v.y) && std::isfinite(v.z)
        && std::fabs(v.x)<=1000000 && std::fabs(v.y)<=1000000 && std::fabs(v.z)<=1000000;
}
inline bool unit(Vec v, Vec& out) {
    if (!valid(v)) return false;
    const double length = std::sqrt(double(v.x)*v.x+double(v.y)*v.y+double(v.z)*v.z);
    if (length < 1e-12) return false;
    out = {float(v.x/length),float(v.y/length),float(v.z/length)};
    return true;
}
inline Vec mix(Vec a, Vec b, float t) {
    return {float((1.-t)*a.x+t*b.x),float((1.-t)*a.y+t*b.y),float((1.-t)*a.z+t*b.z)};
}
// Compatibility (including vertex ordering) is the caller's precondition.
// Allocation is bounded, all validation precedes the sole output replacement.
inline bool blend(const Pose& a, const Pose& b, float t, Pose& out) {
    if (!std::isfinite(t) || t<0 || t>1 || a.positions.empty() || a.normals.empty()
        || a.positions.size()>MaxVectors || a.normals.size()>MaxVectors
        || a.positions.size()!=b.positions.size() || a.normals.size()!=b.normals.size()) return false;
    Pose next;
    next.positions.reserve(a.positions.size()); next.normals.reserve(a.normals.size());
    for (std::size_t i=0; i<a.positions.size(); ++i) {
        if (!valid(a.positions[i]) || !valid(b.positions[i])) return false;
        next.positions.push_back(mix(a.positions[i],b.positions[i],t));
    }
    for (std::size_t i=0; i<a.normals.size(); ++i) {
        Vec x,y,n;
        if (!unit(a.normals[i],x) || !unit(b.normals[i],y)) return false;
        if (!unit(mix(x,y,t),n)) n = t<=.5f ? x : y;
        next.normals.push_back(n);
    }
    out = std::move(next);
    return true;
}
}
