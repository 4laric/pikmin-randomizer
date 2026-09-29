#include "pc_p2_frog_flight.h"
#include "pc_p2_frog_policy.h"
#include <cassert>
#include <cstdio>

int main(){
    assert(!p2frog::readyToFall(1.4f,0.8f,1.0f,1.0f)); // finish before first loop
    assert(p2frog::readyToFall(1.6f,1.0f,1.0f,1.0f));
    assert(!p2frog::readyToFall(2.1f,1.5f,2.0f,1.0f)); // late finish plays tail
    assert(p2frog::readyToFall(2.4f,1.8f,2.0f,1.0f));
    for(int kind=0;kind<2;++kind)for(float dt:{1.0f/30.0f,1.0f/60.0f}){
        const auto& p=p2frog::params(kind);
        auto f=p2frog::launchFlight(0,10,0,100,0,p.airTime,p.jumpSpeed);
        float previous=f.y,hoverY=0;int hoverFrames=0;
        while(f.elapsed<p.airTime+11.0f/30.0f){
            p2frog::advanceFlying(f,100,0,p.airTime,dt);
            assert(f.y>=previous); // no descent at all in Jump or JumpWait
            if(f.vy==0){if(!hoverFrames)hoverY=f.y;assert(f.y==hoverY);++hoverFrames;}
            previous=f.y;
        }
        assert(hoverFrames*dt>0.6f);
        assert(hoverY>95.0f); // old low sine hop peaks at ~61 / ~71 including ground
        assert(std::fabs(f.x-100.0f)<1.0f && f.z==0);
        const float landingX=f.x;
        p2frog::startFall(f,p.fallSpeed);
        assert(f.vy==-p.fallSpeed);
        int fallFrames=0;
        while(!p2frog::advanceFalling(f,25.0f,dt)){assert(f.y>25);assert(++fallFrames<60);}
        assert(f.y==25 && f.x==landingX && f.z==0);
        assert(fallFrames*dt<0.4f);
        std::printf("frog=%d dt=%.5f hover_y=%.2f hover_s=%.2f fall_s=%.2f destination_y=%.2f PASS\n",kind,dt,hoverY,hoverFrames*dt,fallFrames*dt,f.y);
    }
}
