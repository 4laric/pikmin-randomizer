#include "pc_p2_pose_blend.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <cstdlib>
using namespace p2pose;
unsigned checks=0;
void require(bool v){++checks;if(!v){std::cerr<<"FAIL "<<checks<<'\n';std::exit(1);}}
bool near(float a,float b){return std::fabs(a-b)<1e-5f;}
int main(int argc,char** argv){
 Interval i{9,9,9};
 require(bracket({0,3,10},2,i)&&i.left==0&&i.right==1&&near(i.weight,2.f/3));
 require(bracket({0,3,10},3,i)&&i.left==1&&i.right==1);
 require(bracket({0,3,10},100,i)&&i.left==2&&i.right==2);
 require(bracket({0},-1,i)&&i.left==0&&i.right==0);
 i={9,9,9};require(!bracket({0,0},0,i)&&i.left==9);
 require(!bracket({},0,i));require(!bracket({0,1},std::numeric_limits<float>::infinity(),i));
 Pose a{{{0,2,4}},{{1,0,0}}},b{{{10,6,8}},{{0,1,0}}},out;
 require(blend(a,b,.25f,out)&&near(out.positions[0].x,2.5f));
 require(near(out.normals[0].x,3/std::sqrt(10.f)));
 require(blend(a,b,0,out)&&near(out.positions[0].y,2));
 require(blend(a,b,1,out)&&near(out.positions[0].z,8));
 b.normals[0]={-1,0,0};require(blend(a,b,.5f,out)&&out.normals[0].x==1);
 Pose saved=out;
 b.normals[0]={0,0,0};require(!blend(a,b,.5f,out)&&out.positions[0].x==saved.positions[0].x);
 b.normals[0]={1,0,0};b.positions.push_back({0,0,0});require(!blend(a,b,.5f,out));b.positions.pop_back();
 b.positions[0].z=std::numeric_limits<float>::quiet_NaN();require(!blend(a,b,0,out));b.positions[0].z=0;
 require(!blend(a,b,-.1f,out));require(!blend(a,b,1.1f,out));
 require(!blend(a,b,std::numeric_limits<float>::quiet_NaN(),out));
 Pose huge;huge.positions.resize(MaxVectors+1);huge.normals.push_back({1,0,0});require(!blend(huge,huge,.5f,out));
 require(blend(a,a,.5f,a)&&a.positions[0].y==2); // output alias is safe
 if(argc==2){
  std::ifstream in(argv[1]);std::size_t np,nn;require(bool(in>>np>>nn)&&np&&nn&&np<=MaxVectors&&nn<=MaxVectors);
  Pose p[2];for(auto& pose:p){pose.positions.resize(np);pose.normals.resize(nn);
   for(auto* list:{&pose.positions,&pose.normals})for(auto& v:*list)require(bool(in>>v.x>>v.y>>v.z));}
  std::string extra;require(!(in>>extra));
  for(float t:{0.f,.25f,.5f,.75f,1.f}){
   require(blend(p[0],p[1],t,out));
   for(std::size_t n=0;n<np;++n){const auto actual=out.positions[n];const auto x=p[0].positions[n],y=p[1].positions[n];
    require(std::fabs(actual.x-((1.-t)*x.x+t*y.x))<.001);require(std::fabs(actual.y-((1.-t)*x.y+t*y.y))<.001);require(std::fabs(actual.z-((1.-t)*x.z+t*y.z))<.001);}
   for(const auto& n:out.normals)require(std::fabs(n.x*n.x+n.y*n.y+n.z*n.z-1)<1e-5);
  }
  std::cout<<"REAL_PAIR positions="<<np<<" normals="<<nn<<" weights=5\n";
 }
 std::cout<<"PASS pose interpolation checks="<<checks<<'\n';
}
