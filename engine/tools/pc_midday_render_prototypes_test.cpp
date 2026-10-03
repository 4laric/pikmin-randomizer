// Actual native headers/source bridge; loader and physical fence are explicit
// stubs. This is source inventory evidence, not live scene/engine acceptance.
#include "pc_midday_render_prototypes.h"
#include "Shape.h"
#include <cstdio>
BaseShape::BaseShape(){}
void BaseShape::read(RandomAccessStream&){}
RouteGroup::RouteGroup():EditNode("test routes"){}
RoutePoint::RoutePoint(){}
void RouteGroup::render2d(Graphics&,int&){}
void Material::read(RandomAccessStream&){}
void Material::attach(){}
namespace pc_midday {
AudioConstructionFence::~AudioConstructionFence()=default;
ConstructorFence::~ConstructorFence()=default;
bool ConstructorFence::begin(std::string&){held_=true;return true;}
bool ConstructorFence::finish(bool,std::string&){held_=false;return true;}
}
using namespace pc_midday;
namespace {int checks=0,failures=0;void check(bool b,const char* s){++checks;if(!b){++failures;std::printf("FAIL %s\n",s);}}}
int main(){
 BaseShape model;Material materials[2];PVWTevInfo tevs[3];PVWTextureData textures[2];
 model.mMaterialCount=2;model.mMaterialList=materials;model.mTevInfoCount=3;model.mTevInfoList=tevs;
 for(int i=0;i<2;++i){auto& m=materials[i];m.mIndex=i;m.mFlags=MATFLAG_PVW;m.mTevInfoIndex=i*2;m.mTevInfo=&tevs[i*2];m.mColourInfo.mColourInfo.mAnimInfo.mSize=0;m.mColourInfo.mAlphaInfo.mAnimInfo.mSize=0;m.mTextureInfo.mTextureDataCount=2;m.mTextureInfo.mTextureData=textures;m.mTextureInfo.mTexGenDataCount=0;m.mTextureInfo.mTevStageCount=0;}
 for(auto& t:tevs){t.mTevStageCount=0;for(auto& c:t.mTevColRegs){c.mColorAnimData.mInfo.mSize=0;c.mAlphaAnimData.mInfo.mSize=0;}}
 for(auto& t:textures){t.mScaleInfo.mInfo.mSize=0;t.mRotationInfo.mInfo.mSize=0;t.mTranslationInfo.mInfo.mSize=0;}
 PrototypeShapeBinding source{1,&model,10,110,20,120,{{0,30,130},{1,30,130}}};
 ConstructorFence held,idle;std::string e;held.begin(e);PrototypeRenderCensus out;
 check(observePrototypeRender(7,{source},held,out,e)&&out.observations.size()==3,"actual model original allocations observed without clone or init");
 check(out.generation==7,"source census carries exact snapshot generation for composition");
 check(out.required==std::set<u64>{10,20,30}&&out.observations[0].count==3&&out.observations[0].contentRoot,"whole TEV allocation includes unused initialized middle entry");
 check(out.observations[2].address==reinterpret_cast<uintptr_t>(textures)&&out.observations[2].count==2,"shared original texture allocation appears once");
 check(!observePrototypeRender(0,{source},held,out,e)&&out.required.size()==3&&out.generation==7,"zero epoch refusal preserves outputs");
 check(!observePrototypeRender(7,{source},idle,out,e),"physical fence absence refuses before native observation");
 auto bad=source;bad.model=nullptr;check(!observePrototypeRender(7,{bad},held,out,e),"null source model refused");
 bad=source;bad.content=0;check(!observePrototypeRender(7,{bad},held,out,e),"missing source content identity refused");
 check(!observePrototypeRender(7,{source,source},held,out,e),"duplicate loaded model inventory refused");
 bad=source;bad.materials=20;check(!observePrototypeRender(7,{bad},held,out,e),"different original allocations cannot share logical identity");
 bad=source;bad.textures.pop_back();check(!observePrototypeRender(7,{bad},held,out,e),"nonempty texture source binding cannot be omitted");
 bad=source;bad.textures[1].id=31;check(!observePrototypeRender(7,{bad},held,out,e),"same physical alias cannot acquire a second identity");
 bad=source;bad.textures[1].factory=131;check(!observePrototypeRender(7,{bad},held,out,e),"same physical alias cannot acquire foreign factory provenance");
 bad=source;bad.textures[1].materialSlot=0;check(!observePrototypeRender(7,{bad},held,out,e),"duplicated material texture binding refused");
 bad=source;bad.textures[1].materialSlot=2;check(!observePrototypeRender(7,{bad},held,out,e),"one past original material slot refused");
 materials[1].mTevInfo=&tevs[1];check(!observePrototypeRender(7,{source},held,out,e),"valid in-range foreign TEV element refuses index agreement");materials[1].mTevInfo=&tevs[2];
 materials[1].mTevInfoIndex=3;check(!observePrototypeRender(7,{source},held,out,e),"one-past source TEV index refused");materials[1].mTevInfoIndex=2;
 materials[1].mTextureInfo.mTextureDataCount=1;check(!observePrototypeRender(7,{source},held,out,e),"physical shared texture allocation count drift refused");materials[1].mTextureInfo.mTextureDataCount=2;
 tevs[1].mTevStageCount=17;check(!observePrototypeRender(7,{source},held,out,e),"unused initialized TEV still subject to native backing bounds");tevs[1].mTevStageCount=0;
 BaseShape alias;alias.mMaterialCount=2;alias.mMaterialList=materials;alias.mTevInfoCount=3;alias.mTevInfoList=tevs;bad=source;bad.content=2;bad.model=&alias;
 check(observePrototypeRender(8,{source,bad},held,out,e)&&out.observations.size()==3,"distinct source models may explicitly share exact canonical allocations");
 bad.tevs=21;check(!observePrototypeRender(8,{source,bad},held,out,e),"cross-model original TEV alias cannot be relabeled");
 BaseShape empty;empty.mMaterialCount=0;empty.mTevInfoCount=0;PrototypeShapeBinding emptyBinding;emptyBinding.content=3;emptyBinding.model=&empty;
 check(observePrototypeRender(9,{emptyBinding},held,out,e)&&out.observations.empty(),"empty initialized model avoids uninitialized backing pointer reads");
 emptyBinding.tevs=40;check(!observePrototypeRender(9,{emptyBinding},held,out,e),"empty model cannot fabricate TEV allocation");emptyBinding.tevs=0;
 empty.mTevInfoCount=3;empty.mTevInfoList=tevs;emptyBinding.tevs=20;emptyBinding.tevFactory=120;
 check(observePrototypeRender(10,{emptyBinding},held,out,e)&&out.observations.size()==1&&out.observations[0].count==3,"complete loaded TEV array retained even with no material consumers");
 auto* originalTextures=materials[1].mTextureInfo.mTextureData;materials[1].mTextureInfo.mTextureData=reinterpret_cast<PVWTextureData*>(reinterpret_cast<char*>(materials)+1);auto overlap=source;overlap.textures[1]={1,31,131};check(!observePrototypeRender(7,{overlap},held,out,e),"texture allocation overlap rejected before descriptor backing dereference");materials[1].mTextureInfo.mTextureData=originalTextures;
 auto* originalMaterials=model.mMaterialList;model.mMaterialList=reinterpret_cast<Material*>(tevs);check(!observePrototypeRender(7,{source},held,out,e),"overlapping model root allocations rejected before material interpretation");model.mMaterialList=originalMaterials;
 model.mMaterialCount=-1;check(!observePrototypeRender(7,{source},held,out,e),"invalid initialized model count refused");model.mMaterialCount=2;
 check(observePrototypeRender(11,{source},held,out,e)&&out.observations.size()==3,"correct model remains accepted after all refusal paths");
 held.finish(false,e);std::printf("%d checks, %d failures\n",checks,failures);return failures?1:0;
}
