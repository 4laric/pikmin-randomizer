#include "pc_coop_menu_layout.h"
#include <cassert>
#include <cmath>
#include <cstdio>
#include <limits>
using namespace pc_coop_menu;
static bool contains(Rect r,float x,float y){return x>=r.x0&&x<=r.x1&&y>=r.y0&&y<=r.y1;}
int main(){
    int cases=0;
    for(float aspect:{4.f/3.f,16.f/9.f,21.f/9.f,32.f/9.f,9.f/16.f})
    for(Mode mode:{Mode::Fullscreen,Mode::Vertical,Mode::Horizontal})
    for(int side:{0,1}){
        Rect r=panel(aspect,mode,side),v=view(mode,side),other=view(mode,1-side);
        assert(r.x0>=v.x0 && r.y0>=v.y0 && r.x1<=v.x1 && r.y1<=v.y1);
        assert(r.x1>r.x0 && r.y1>r.y0);
        assert(!contains(r,(other.x0+other.x1)/2,(other.y0+other.y1)/2));
        assert(!contains(r,.5f,.5f)); // each fullscreen peer/unified camera center
        Rect peer=panel(aspect,mode,1-side);
        assert(r.x1<=peer.x0 || peer.x1<=r.x0 || r.y1<=peer.y0 || peer.y1<=r.y0);
        assert(std::fabs((r.x1-r.x0)*aspect/(r.y1-r.y0)-4.f/3.f)<.00001f);
        ++cases;
    }
    for(float invalid:{0.f,-1.f,std::numeric_limits<float>::infinity(),std::numeric_limits<float>::quiet_NaN()}){
        Rect r=panel(invalid,Mode::Fullscreen,0);assert(std::isfinite(r.x1)&&!contains(r,.5f,.5f));++cases;
    }
    std::printf("PASS coop_menu_layout cases=%d containment=1 centers_clear=1 aspect43=1 side_swap=1\n",cases);
}
