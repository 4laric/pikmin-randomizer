#pragma once
#include <cmath>
namespace p2envmap {
// J3D mode 6: Old-SRT * qMtx2 * view, with view translation removed.
// SRT rows are [xx, xy, translation], [yx, yy, translation].
inline bool matrix(const float view[3][4], const float srt[2][3], float out[3][4]) {
    for(unsigned i=0;i<3;++i)for(unsigned j=0;j<4;++j)if(!std::isfinite(view[i][j]))return false;
    for(unsigned i=0;i<2;++i)for(unsigned j=0;j<3;++j)if(!std::isfinite(srt[i][j]))return false;
    float result[3][4]{};
    for(unsigned i=0;i<2;++i){
        for(unsigned j=0;j<3;++j)result[i][j]=.5f*srt[i][0]*view[0][j]-.5f*srt[i][1]*view[1][j];
        result[i][3]=.5f*(srt[i][0]+srt[i][1])+srt[i][2];
    }
    for(unsigned j=0;j<3;++j)result[2][j]=view[2][j];
    for(unsigned i=0;i<3;++i)for(unsigned j=0;j<4;++j)if(!std::isfinite(result[i][j]))return false;
    for(unsigned i=0;i<3;++i)for(unsigned j=0;j<4;++j)out[i][j]=result[i][j];
    return true;
}
}
