#include "pc_p2_original_pom_clock.h"
#include <cstdio>
#include <limits>
int main(){
    using namespace p2original::pom;Clock c;Events e;int checks=0;
    auto require=[&](bool yes){++checks;if(!yes){std::fprintf(stderr,"clock check %d failed\n",checks);return false;}return true;};
    if(!require(c.reset(2)&&c.advance(24.f/30.f,e)&&!e.action&&!e.finished))return 1;
    if(!require(c.advance(1.f/30.f,e)&&e.action&&!e.finished))return 1;
    if(!require(c.advance(5.f/30.f,e)&&!e.action&&e.finished))return 1;
    if(!require(c.advance(10,e)&&!e.action&&!e.finished&&c.frame==30))return 1;
    if(!require(c.reset(4)&&c.advance(100,e)&&e.action&&e.finished&&c.frame==40))return 1;
    if(!require(c.reset(4)&&c.advance(20.f/30.f,e)&&e.action&&!e.finished))return 1;
    for(unsigned m:{0u,1u,3u,5u})if(!require(c.reset(m)&&c.advance(100,e)&&!e.action&&e.finished==(m!=0)))return 1;
    const auto before=c;
    if(!require(!c.reset(6)&&c.motion==before.motion))return 1;
    if(!require(!c.advance(-1,e)&&c.frame==before.frame))return 1;
    if(!require(!c.advance(std::numeric_limits<float>::quiet_NaN(),e)&&c.frame==before.frame))return 1;
    if(!require(c.reset(5)&&c.advance(0,e)&&!e.action&&!e.finished))return 1;
    std::printf("original Pom source-clock %d controls PASS\n",checks);
}
