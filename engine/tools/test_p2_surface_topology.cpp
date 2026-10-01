#include "pc_p2_surface_topology_policy.h"
#include <cassert>
#include <limits>
#include <cstdio>
using namespace p2surface;
struct Point {float x,y,z;};
static Face make(std::array<unsigned,3> ids,unsigned code,const std::vector<Point>& points){
    const Point& a=points[ids[0]];const Point& b=points[ids[1]];const Point& c=points[ids[2]];
    Point u{b.x-a.x,b.y-a.y,b.z-a.z},v{c.x-a.x,c.y-a.y,c.z-a.z};
    Point n{v.y*u.z-v.z*u.y,v.z*u.x-v.x*u.z,v.x*u.y-v.y*u.x};
    float length=std::sqrt(n.x*n.x+n.y*n.y+n.z*n.z);n={n.x/length,n.y/length,n.z/length};
    Face f{ids,{n.x,n.y,n.z,n.x*a.x+n.y*a.y+n.z*a.z},{},code};
    for(int e=0;e<3;++e){const Point& p=points[ids[e]];const Point& q=points[ids[(e+1)%3]];
        Point d{q.x-p.x,q.y-p.y,q.z-p.z};Point m{d.y*n.z-d.z*n.y,d.z*n.x-d.x*n.z,d.x*n.y-d.y*n.x};
        f.edges[e]={m.x,m.y,m.z,m.x*p.x+m.y*p.y+m.z*p.z};}
    return f;
}
int main(){
    std::vector<Point> points{{0,0,0},{0,0,10},{10,0,0},{10,0,10},{10,10,10}};
    Face a=make({0,2,1},65,points),b=make({1,2,3},65,points),wall=make({1,2,4},103,points);
    Topology t;assert(t.build({a,b}));auto crossing=t.continuation(0,1,8,8);
    assert(crossing.kind==Kind::Unique&&crossing.face==1);
    assert(t.continuation(0,1,-1,-1).kind==Kind::Boundary);
    assert(t.continuation(0,0,8,8).kind==Kind::Boundary);
    // Retail tutorial673/4914 and727/4915 are coincident same-winding
    // overlays with distinct source slip codes103/65; never collapse them.
    Face duplicate=b;duplicate.mapcode=103;
    assert(t.build({a,b,duplicate}));assert(t.multiEdges()==1);
    assert(t.incidents(0,1)->size()==3);
    assert(t.continuation(0,1,8,8).kind==Kind::Ambiguous);
    // Distinct slopes sharing the same edge also remain ambiguous where both
    // projected triangles contain the point; neither angle nor ID chooses one.
    assert(t.build({a,b,wall}));assert(t.continuation(0,1,5,6).kind==Kind::Ambiguous);
    t.clear();assert(t.size()==0&&t.incidents(0,1)==nullptr);
    assert(t.continuation(0,1,8,8).kind==Kind::Invalid);
    assert(t.build({a,b}));assert(t.continuation(0,1,std::numeric_limits<float>::quiet_NaN(),8).kind==Kind::Invalid);
    Face invalid=a;invalid.plane.x=std::numeric_limits<float>::infinity();assert(!t.build({invalid}));assert(t.size()==0);
    std::puts("PASS P2_SURFACE_TOPOLOGY_POLICY unique ambiguous duplicate_slip boundary finite reset");
}
