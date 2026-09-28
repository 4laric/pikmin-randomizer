#pragma once
#include <cmath>

struct P2DemonMatrix { float m[3][4]{}; };
struct P2DemonAttachmentPose {
    bool valid=false;
    P2DemonMatrix matrix;
    float position[3]{};
};
// Creature::updateStick non-OniKurage mouth path: jointWorld * local Rz(pi/2).
// Position is the joint center; no invented hand offset or scale normalization.
inline P2DemonAttachmentPose p2_demon_attachment_pose(const P2DemonMatrix& world) {
    P2DemonAttachmentPose out;
    for(const auto& row:world.m) for(float x:row)
        if(!std::isfinite(x)||std::fabs(x)>1.0e6f) return out;
    out.valid=true;
    for(int row=0;row<3;++row) {
        out.matrix.m[row][0]=world.m[row][1];
        out.matrix.m[row][1]=-world.m[row][0];
        out.matrix.m[row][2]=world.m[row][2];
        out.matrix.m[row][3]=world.m[row][3];
        out.position[row]=world.m[row][3];
    }
    return out;
}
