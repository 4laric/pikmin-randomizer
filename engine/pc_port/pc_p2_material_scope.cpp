#include "pc_p2_material_scope.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"

bool p2material::draw(Shape& shape,Graphics& gfx,unsigned materialIndex,const Sample& sample){
 if(!gfx.mCamera||!shape.mMaterialList||shape.mMaterialCount<=0||materialIndex>=static_cast<unsigned>(shape.mMaterialCount))return false;
 ScopedSrt scope(shape.mMaterialList[materialIndex],sample);
 if(!scope.applied())return false;
 // Material pointer caching must not hide this actor's scoped matrix update.
 gfx.useMaterial(nullptr);
 shape.drawshape(gfx,*gfx.mCamera,nullptr);
 gfx.useMaterial(nullptr);
 return true;
}
