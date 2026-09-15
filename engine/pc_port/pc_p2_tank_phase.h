#pragma once
#include <cmath>
namespace p2tankvisual {
inline bool frame(float counter,int nativeDuration,int sourceDuration,float& result){
 if(!std::isfinite(counter)||nativeDuration<2||sourceDuration<2||sourceDuration>10000)return false;
 float phase=counter/float(nativeDuration-1);if(phase<0)phase=0;if(phase>1)phase=1;result=phase*float(sourceDuration-1);return true;
}
}
