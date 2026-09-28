#include "pc_p2_demon_attachment.h"
#include <cassert>
#include <cstdio>
#include <limits>
int main() {
    P2DemonMatrix world{{{1,0,0,10},{0,1,0,20},{0,0,1,30}}};
    auto p=p2_demon_attachment_pose(world);
    assert(p.valid&&p.position[0]==10&&p.position[1]==20&&p.position[2]==30);
    assert(p.matrix.m[0][0]==0&&p.matrix.m[0][1]==-1&&p.matrix.m[1][0]==1&&p.matrix.m[1][1]==0);
    world={{{0,0,4,-3},{0,3,0,7},{-2,0,0,9}}};
    p=p2_demon_attachment_pose(world);
    assert(p.valid&&p.matrix.m[0][2]==4&&p.matrix.m[1][0]==3&&p.matrix.m[2][1]==2);
    assert(p.position[0]==-3&&p.position[1]==7&&p.position[2]==9);
    world.m[2][2]=std::numeric_limits<float>::infinity();
    assert(!p2_demon_attachment_pose(world).valid);
    puts("p2_demon_attachment_test PASS");
}
