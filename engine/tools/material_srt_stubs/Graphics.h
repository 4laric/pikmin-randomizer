#pragma once
#include "Material.h"
#include "Camera.h"
class Graphics {
public:
 Camera* mCamera=nullptr;int clears=0;
 void useMaterial(Material*){++clears;}
};
