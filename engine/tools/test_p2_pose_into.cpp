#include "pc_p2_pose_blend.h"
#include <cassert>
#include <iostream>
int main(){
 using namespace p2pose;
 Pose a{{{0,0,0},{2,0,0}},{{2,0,0}}},b{{{2,4,0},{4,0,0}},{{0,3,0}}},out=a;
 auto* p=out.positions.data();auto* n=out.normals.data();
 assert(blendInto(a,b,0,out)&&out.positions[0].x==0&&out.normals[0].x==2);
 assert(blendInto(a,b,1,out)&&out.positions[0].y==4&&out.normals[0].y==3);
 for(int i=0;i<100;++i){assert(blendInto(a,b,.5f,out));assert(out.positions.data()==p&&out.normals.data()==n);}
 assert(out.positions[0].x==1&&out.positions[0].y==2&&std::fabs(out.normals[0].x-.70710678f)<1e-6f);
 const auto saved=out.positions[0];b.normals[0]={0,0,0};assert(!blendInto(a,b,.5f,out)&&out.positions[0].x==saved.x);
 b.normals[0]={-2,0,0};assert(blendInto(a,b,.5f,out)&&out.normals[0].x==1);
 assert(blendInto(a,b,.75f,out)&&out.normals[0].x==-1);
 assert(!blendInto(a,b,NAN,out)&&!blendInto(a,b,-1,out)&&!blendInto(a,b,2,out));
 b.positions[1].x=NAN;assert(!blendInto(a,b,.5f,out));b.positions[1].x=4;
 Pose empty;assert(!blendInto(a,b,0,empty));Pose wrong=out;wrong.positions.pop_back();assert(!blendInto(a,b,0,wrong));
 assert(a.positions[0].x==0&&a.normals[0].x==2);
 std::cout<<"PASS preallocated interpolation\n";
}
