#include "pc_p2_color_binding.h"
#include "Shape.h"
#include <cassert>
#include <fstream>
#include <iostream>
using namespace p2color;
int main(int argc,char** argv){
 Bank bank;bank.source=std::string(64,'0');bank.duration=10;
 Track track;track.material="body";for(auto& c:track.curves)c={{0,0,0,0},{10,100,0,0}};bank.tracks={track};assert(valid(bank));
 Sample s;assert(sample(bank,0,5,s)&&s[0]==50);Sample sentinel{1,2,3,4};s=sentinel;assert(!sample(bank,0,NAN,s)&&s==sentinel);
 auto special=bank;for(auto& c:special.tracks[0].curves)c={{0,-2000,0,0},{10,2000,0,0}};
 assert(sample(special,0,0,s)&&s[0]==-1024&&sample(special,0,10,s)&&s[0]==1023);
 special.tracks[0].kind=1;assert(sample(special,0,0,s)&&s[0]==0&&sample(special,0,10,s)&&s[0]==255);
 special.tracks[0].curves[0]={{0,-1,0,0}};assert(sample(special,0,0,s)&&s[0]==255);special.tracks[0].kind=0;assert(sample(special,0,0,s)&&s[0]==-1);
 std::istringstream bad("P2_MATERIAL_COLOR_1 garbage");bool refused=false;try{read(bad);}catch(const std::runtime_error&){refused=true;}assert(refused);
 Material materials[2];PVWTevInfo values[2];materials[0].mTevInfo=&values[0];materials[1].mTevInfo=&values[1];
 Shape shape;shape.mMaterialList=materials;shape.mMaterialCount=2;Camera camera;Graphics gfx;gfx.mCamera=&camera;
 Binding b,other;std::vector<Target> targets={{"body",0,0,0,0}};assert(b.bind(bank,shape,targets,1)&&other.bind(bank,shape,targets,2));
 assert(b.draw(bank,shape,gfx,0,1)&&values[0].mTevColRegs[0].mAnimatedColor.r==9);shape.expected=100;assert(b.draw(bank,shape,gfx,10,1));shape.expected=50;assert(other.draw(bank,shape,gfx,5,2));
 assert(values[0].mTevColRegs[0].mAnimatedColor.r==9&&values[1].mTevColRegs[0].mAnimatedColor.r==9);
 int draws=shape.draws;assert(!b.draw(bank,shape,gfx,0,2)&&!b.draw(bank,shape,gfx,11,1));
 auto copy=bank;assert(!b.draw(copy,shape,gfx,0,1));materials[1].mTevInfo=&values[0];assert(!b.draw(bank,shape,gfx,0,1));assert(!other.bind(bank,shape,targets,2));materials[1].mTevInfo=&values[1];
 assert(shape.draws==draws);shape.throws=true;shape.expected=0;bool caught=false;try{b.draw(bank,shape,gfx,0,1);}catch(int){caught=true;}assert(caught&&values[0].mTevColRegs[0].mAnimatedColor.r==9);shape.throws=false;
 b.reset();assert(!b.draw(bank,shape,gfx,0,1));auto duplicate=targets;duplicate.push_back(targets[0]);assert(!b.bind(bank,shape,duplicate,1));targets[0].hostReg=3;assert(!b.bind(bank,shape,targets,1));
 auto mixed=bank;auto konst=track;konst.kind=1;konst.reg=1;konst.curves[0]={{0,-1,0,0}};mixed.tracks.push_back(konst);
 const std::vector<Target> mixedTargets={{"body",0,0,0,0},{"body",1,1,0,1}},partial={{"body",0,0,0,0}};
 assert(b.bind(mixed,shape,mixedTargets,3));shape.expected=50;shape.expectedK=255;assert(b.draw(mixed,shape,gfx,5,3));assert(values[0].mKonstColors[1].r==9&&values[0].mTevColRegs[0].mAnimatedColor.r==9);
 assert(!b.bind(mixed,shape,partial,3));
 if(argc==2){std::ifstream in(argv[1]);auto real=read(in);for(unsigned f=0;f<=real.duration;++f){assert(sample(real,0,f,s));std::cout<<f;for(auto v:s)std::cout<<' '<<v;std::cout<<'\n';}}
 std::cout<<"PASS material colors and scoped binding\n";
}
