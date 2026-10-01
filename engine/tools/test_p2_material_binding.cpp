#include "pc_p2_material_binding.h"
#include "Shape.h"
#include <cassert>
#include <fstream>
#include <iostream>
using namespace p2material;
int main(int argc,char** argv){
 assert(argc==2);std::ifstream input(argv[1]);Bank bank=read(input);
 bank.tracks[0].curves[0]={{0,2,0,0},{10,4,0,0}};
 bank.tracks[0].curves[2]={{0,0,0,0}};
 bank.tracks.push_back(bank.tracks[0]);bank.tracks[1].material="second";
 bank.tracks[1].curves[0]={{0,5,0,0}};
 Material materials[3];PVWTextureData textures[3];PVWTexGenData generators[3];
 for(int i=0;i<3;++i){materials[i].mTextureInfo.mTextureData=&textures[i];materials[i].mTextureInfo.mTexGenData=&generators[i];textures[i].mAnimatedTexMtx.mMtx[0][0]=9;}
 Shape shape;shape.mMaterialList=materials;shape.mMaterialCount=3;shape.expected=2;shape.expectedSecond=5;
 Camera camera;Graphics gfx;gfx.mCamera=&camera;
 Binding binding;std::vector<Target> targets={{"material",0,0},{"second",0,1},{"material",0,2}};
 assert(binding.bind(bank,shape,targets,1));assert(binding.ready());
 assert(binding.draw(bank,shape,gfx,0,1)&&shape.draws==1&&gfx.clears==2);
 for(const auto& t:textures)assert(t.mAnimatedTexMtx.mMtx[0][0]==9&&t.mAnimationFactor==255);
 shape.expected=4;assert(binding.draw(bank,shape,gfx,10,1)&&shape.draws==2&&gfx.clears==4);
 shape.expected=3;assert(binding.draw(bank,shape,gfx,5,1)&&shape.draws==3&&gfx.clears==6);
 // An independently bound second actor uses the shared shape at its own phase.
 Binding actor;assert(actor.bind(bank,shape,targets,2));shape.expected=2;assert(actor.draw(bank,shape,gfx,0,2));
 assert(textures[0].mAnimatedTexMtx.mMtx[0][0]==9);
 int draws=shape.draws,clears=gfx.clears;
 assert(!binding.draw(bank,shape,gfx,0,2));assert(!binding.draw(bank,shape,gfx,11,1));
 Bank otherBank=bank;assert(!binding.draw(otherBank,shape,gfx,0,1));
 Shape otherShape=shape;assert(!binding.draw(bank,otherShape,gfx,0,1));
 --shape.mMaterialCount;assert(!binding.draw(bank,shape,gfx,0,1));++shape.mMaterialCount;
 auto* saved=shape.mMaterialList;shape.mMaterialList=nullptr;assert(!binding.draw(bank,shape,gfx,0,1));shape.mMaterialList=saved;
 PVWTextureData replacement;materials[1].mTextureInfo.mTextureData=&replacement;assert(!binding.draw(bank,shape,gfx,0,1));materials[1].mTextureInfo.mTextureData=&textures[1];
 // Later target failure rolls back the first already-applied scope, without draw.
 generators[1].mTexGenSrc=1;assert(!binding.draw(bank,shape,gfx,0,1));generators[1].mTexGenSrc=4;
 assert(textures[0].mAnimatedTexMtx.mMtx[0][0]==9&&generators[0].mMatrixType==10&&textures[0].mAnimationFactor==255);
 assert(shape.draws==draws&&gfx.clears==clears);
 // Draw exceptions restore both scoped values and the material cache.
 shape.throwOnDraw=true;bool caught=false;try{binding.draw(bank,shape,gfx,0,1);}catch(int){caught=true;}shape.throwOnDraw=false;
 assert(caught&&gfx.clears==clears+2&&textures[0].mAnimatedTexMtx.mMtx[0][0]==9);
 binding.reset();assert(!binding.ready()&&!binding.draw(bank,shape,gfx,0,1));
 for(const auto& bad:std::vector<std::vector<Target>>{{},{ {"material",0,0} },{{"material",0,0},{"second",0,0}},{{"material",1,0},{"second",0,1}},{{"absent",0,0},{"second",0,1}},{{"material",0,99},{"second",0,1}}}){
  assert(binding.bind(bank,shape,targets,1));assert(!binding.bind(bank,shape,bad,1)&&!binding.ready());
 }
 assert(!binding.bind(bank,shape,targets,0));
 materials[2].mTextureInfo.mTextureData=&textures[0];
 assert(!binding.bind(bank,shape,targets,1));
 const std::vector<Target> partial={{"material",0,0},{"second",0,1}};
 assert(!binding.bind(bank,shape,partial,1)); // unbound alias
 materials[2].mTextureInfo.mTextureData=&textures[2];materials[2].mTextureInfo.mTexGenData=&generators[0];
 assert(!binding.bind(bank,shape,targets,1));materials[2].mTextureInfo.mTexGenData=&generators[2];
 std::vector<Target> tooMany(129,targets[0]);assert(!binding.bind(bank,shape,tooMany,1));
 std::cout<<"PASS transactional material bindings, actor phases, alias guards and lifecycle\n";
}
