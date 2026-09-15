#include "pc_p2_specular_layer.h"
#include "Shape.h"
#include <iostream>
#include <limits>
int main(){
 Material mat;Texture textures[2];TexAttr attrs[2];for(int i=0;i<2;++i)attrs[i].mTexture=&textures[i];
 PVWTextureData data;data.mTexture=&textures[0];PVWTexGenData gen;PVWTevStage stage;PVWTevInfo tev;tev.mTevStages=&stage;
 mat.mTextureInfo.mTextureData=&data;mat.mTextureInfo.mTexGenData=&gen;mat.mTevInfo=&tev;
 u8 display=1;mat.mDisplayListPtr=&display;mat.mLightingInfo.mCtrlFlag=123;
 Shape shape;shape.mMaterialList=&mat;shape.mMaterialCount=1;shape.mTexAttrList=attrs;shape.mTexAttrCount=2;shape.specularFixture=true;
 Camera camera;Graphics gfx;gfx.mCamera=&camera;p2material::Sample sample;sample.sx=-.5;
 auto restored=[&](){assert(mat.mTextureInfo.mTextureData==&data&&mat.mTextureInfo.mTexGenData==&gen&&mat.mTextureInfo.mTextureDataCount==1);
  assert(mat.mTevInfo==&tev&&mat.mDisplayListPtr==&display&&mat.mLightingInfo.mCtrlFlag==123&&stage.mTevColorCombiner.mScale==0);};
 assert(p2material::drawSpecular(shape,gfx,0,1,sample));restored();
 shape.specularExpected=false;assert(p2material::drawSpecular(shape,gfx,0,1,sample,false));restored();
 shape.throwOnDraw=true;bool caught=false;try{p2material::drawSpecular(shape,gfx,0,1,sample,false);}catch(int){caught=true;}assert(caught);restored();
 assert(gfx.clears==6);
 assert(!p2material::drawSpecular(shape,gfx,1,1,sample));assert(!p2material::drawSpecular(shape,gfx,0,2,sample));
 sample.rotation=1;assert(!p2material::drawSpecular(shape,gfx,0,1,sample));sample.rotation=0;
 stage.mTevColorCombiner.mInArgA=8;assert(!p2material::drawSpecular(shape,gfx,0,1,sample));stage.mTevColorCombiner.mInArgA=15;
 sample.sx=std::numeric_limits<double>::infinity();assert(!p2material::drawSpecular(shape,gfx,0,1,sample));restored();
 std::cout<<"PASS specular combiner, diffuse control, rejection and exception restoration\n";
}
