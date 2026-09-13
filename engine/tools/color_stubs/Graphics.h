#pragma once
#include "Camera.h"
struct Graphics {Camera* mCamera=nullptr;int clears=0;void useMaterial(void*){++clears;}};
