#include "pc_p2_material_scope.h"
#include "Shape.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
using namespace p2material;
static bool near(double a,double b){return std::abs(a-b)<1e-6;}
int main(int argc,char** argv){
 assert(argc==2);std::ifstream input(argv[1]);Bank b=read(input);assert(valid(b));
 Sample s;assert(sample(b,0,5,s));assert(near(s.sx,2.75));assert(s.sy==1&&s.rotation==34);
 assert(sample(b,0,0,s)&&s.sx==1);assert(sample(b,0,10,s)&&s.sx==3);
 const auto before=s;assert(!sample(b,0,-1,s)&&s.sx==before.sx);
 assert(!sample(b,1,0,s));assert(!sample(b,0,11,s));assert(!sample(b,0,std::numeric_limits<double>::quiet_NaN(),s));
 b.tracks[0].curves[2]={{0,-1.9,0,0}};assert(sample(b,0,3,s)&&s.rotation==-2);
 b.shift=15;b.tracks[0].curves[2]={{0,3.9,0,0}};assert(sample(b,0,3,s)&&s.rotation==-32768);
 b.tracks.push_back(b.tracks[0]);assert(!valid(b));b.tracks.pop_back();
 b.tracks[0].curves[0][1].frame=0;assert(!valid(b));
 for(const char* bad:{"", "P2_MATERIAL_SRT_1 abc 10 2 1 1", "P2_MATERIAL_SRT_1 abc 10 2 1 9999999"}){
  bool rejected=false;try{std::istringstream in(bad);read(in);}catch(const std::runtime_error&){rejected=true;}assert(rejected);
 }
 s=Sample{};s.sx=2;s.sy=3;s.tx=.25;s.ty=-.25;s.cx=.5;s.cy=.5;
 double m[2][3];assert(matrix(s,m)&&near(m[0][2],-.25)&&near(m[1][2],-1.25));
 s.rotation=31;assert(matrix(s,m)&&m[0][1]==0);s.rotation=16384;
 assert(matrix(s,m)&&near(m[0][0],0)&&near(m[0][1],-2)&&near(m[1][0],3));
 s.rotation=0;
 PVWTextureData data;PVWTexGenData gen;Material material;material.mTextureInfo.mTextureData=&data;material.mTextureInfo.mTexGenData=&gen;
 data.mAnimatedTexMtx.mMtx[0][0]=7;data.mAnimatedTexMtx.mMtx[0][3]=9;
 {
  ScopedSrt first(material,s);assert(first.applied());assert(data.mAnimatedTexMtx.mMtx[0][0]==2);
  assert(data.mAnimatedTexMtx.mMtx[0][2]==0&&data.mAnimatedTexMtx.mMtx[0][3]==-.25f);
  assert(gen.mMatrixType==0&&data.mAnimationFactor==0);
  Sample other=s;other.sx=4;
  try{ScopedSrt second(material,other);assert(second.applied()&&data.mAnimatedTexMtx.mMtx[0][0]==4);throw 1;}catch(int){}
  assert(data.mAnimatedTexMtx.mMtx[0][0]==2);
 }
 assert(data.mAnimatedTexMtx.mMtx[0][0]==7&&data.mAnimatedTexMtx.mMtx[0][3]==9&&data.mAnimationFactor==255&&gen.mMatrixType==10);
 for(int i=0;i<2;++i){Sample actor=s;actor.sx=3+i;ScopedSrt scope(material,actor);assert(scope.applied()&&data.mAnimatedTexMtx.mMtx[0][0]==3+i);}
 assert(data.mAnimatedTexMtx.mMtx[0][0]==7);
 material.mFlags=0;{ScopedSrt rejected(material,s);assert(!rejected.applied());}material.mFlags=MATFLAG_PVW;
 gen.mTexCoordID=1;{ScopedSrt rejected(material,s);assert(!rejected.applied());}gen.mTexCoordID=0;
 material.mTextureInfo.mTexGenDataCount=2;{ScopedSrt rejected(material,s);assert(!rejected.applied());}material.mTextureInfo.mTexGenDataCount=1;
 gen.mTexGenSrc=1;{ScopedSrt rejected(material,s);assert(!rejected.applied());}
 data._UNUSED10=0xE6;data.mAnimationFactor=0;
 {ScopedSrt env(material,s);assert(env.applied()&&data.mScaleX==2&&data.mTranslationX==.25f&&gen.mMatrixType==0);}
 assert(data.mScaleX==1&&data.mTranslationX==0&&gen.mMatrixType==10);
 data.mRotationZ=1;{ScopedSrt rejected(material,s);assert(!rejected.applied());}data.mRotationZ=0;
 s.rotation=32;{ScopedSrt rejected(material,s);assert(!rejected.applied());}s.rotation=0;
 data._UNUSED10=0;gen.mTexGenSrc=4;
 Camera camera;Graphics gfx;gfx.mCamera=&camera;Shape shape;shape.mMaterialList=&material;shape.mMaterialCount=1;shape.expected=2;
 assert(draw(shape,gfx,0,s)&&shape.draws==1&&gfx.clears==2&&data.mAnimatedTexMtx.mMtx[0][0]==7);
 assert(!draw(shape,gfx,1,s)&&shape.draws==1);gfx.mCamera=nullptr;assert(!draw(shape,gfx,0,s));
 s.sx=std::numeric_limits<double>::infinity();{ScopedSrt rejected(material,s);assert(!rejected.applied());}
 std::cout<<"PASS material sampling, scope isolation and draw cache invalidation\n";
}
