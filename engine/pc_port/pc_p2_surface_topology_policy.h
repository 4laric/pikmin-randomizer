#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <map>
#include <vector>

// P2 sphere sweeps keep all faces. This adapter never fabricates a unique
// continuation when distinct incident faces satisfy the geometric query.
namespace p2surface {
struct Plane { float x, y, z, d; };
struct Face { std::array<unsigned,3> vertices; Plane plane; std::array<Plane,3> edges; unsigned mapcode; };
struct Incident { int face, edge; };
enum class Kind { Boundary, Unique, Ambiguous, Invalid };
struct Crossing { Kind kind; int face; };
class Topology {
    std::vector<Face> faces;
    std::map<std::pair<unsigned,unsigned>,std::vector<Incident>> edges;
public:
    void clear() { faces.clear(); edges.clear(); }
    bool build(const std::vector<Face>& input) {
        clear();
        if (input.empty() || input.size()>32767) return false;
        for (const Face& f:input) {
            if (!std::isfinite(f.plane.x)||!std::isfinite(f.plane.y)||!std::isfinite(f.plane.z)||!std::isfinite(f.plane.d)) return false;
            for (int e=0;e<3;++e) if(f.vertices[e]==f.vertices[(e+1)%3]) return false;
            for (const Plane& p:f.edges) if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||!std::isfinite(p.d)) return false;
        }
        faces=input;
        for (int i=0;i<int(faces.size());++i) for(int e=0;e<3;++e) {
            unsigned a=faces[i].vertices[e],b=faces[i].vertices[(e+1)%3];
            edges[{std::min(a,b),std::max(a,b)}].push_back({i,e});
        }
        return true;
    }
    int size() const { return int(faces.size()); }
    const std::vector<Incident>* incidents(int face,int edge) const {
        if(face<0||face>=size()||edge<0||edge>=3) return nullptr;
        unsigned a=faces[face].vertices[edge],b=faces[face].vertices[(edge+1)%3];
        auto it=edges.find({std::min(a,b),std::max(a,b)});
        return it==edges.end()?nullptr:&it->second;
    }
    int multiEdges() const { int n=0;for(const auto& e:edges)if(e.second.size()>2)++n;return n; }
    Crossing continuation(int face,int edge,float x,float z) const {
        auto list=incidents(face,edge);
        if(!list||!std::isfinite(x)||!std::isfinite(z))return {Kind::Invalid,-1};
        const Face& from=faces[face];
        unsigned a=from.vertices[edge],b=from.vertices[(edge+1)%3];
        int found=-1;
        for(const Incident& i:*list) {
            if(i.face==face)continue;
            const Face& next=faces[i.face];
            if(next.vertices[i.edge]!=b||next.vertices[(i.edge+1)%3]!=a||next.plane.y<=0.01f)continue;
            bool coincident=true;
            for(unsigned v:next.vertices) if(v!=from.vertices[0]&&v!=from.vertices[1]&&v!=from.vertices[2])coincident=false;
            if(coincident)continue;
            float y=(next.plane.d-next.plane.x*x-next.plane.z*z)/next.plane.y;
            if(!std::isfinite(y))continue;
            bool inside=true;
            for(const Plane& p:next.edges)if(p.x*x+p.y*y+p.z*z-p.d < -0.001f)inside=false;
            if(!inside)continue;
            if(found>=0)return {Kind::Ambiguous,-1};
            found=i.face;
        }
        return found<0?Crossing{Kind::Boundary,-1}:Crossing{Kind::Unique,found};
    }
};
}
