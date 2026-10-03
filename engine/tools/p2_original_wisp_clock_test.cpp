#include "pc_p2_original_wisp_clock.h"
#include <cassert>
#include <cstdio>
using namespace p2original::wisp;
int main(){
 Clock c;c.start(false);const std::vector<Key> damage{{5,2}};
 assert(c.advance(5.0f/30,35,damage)==-1);
 assert(c.advance(.5f/30,35,damage)==-1);
 assert(c.advance(.5f/30,35,damage)==2); // int(timer)=6, source frame5 key
 assert(c.advance(1.0f/30,35,damage)==-1);
 assert(c.advance(28.0f/30,35,damage)==1000&&c.completed&&c.frame==34);
 assert(c.advance(1,35,damage)==-1); // source AnimCompleted guard
 c.start(true);assert(c.advance(100,30,{})==-1&&c.frame==0);
 c.start(false);assert(c.advance(1,30,{})==1000&&c.frame==29);
 c.start(false);const std::vector<Key> loop{{0,0},{9,1}};
 assert(c.advance(.5f/30,10,loop)==-1);assert(c.advance(.5f/30,10,loop)==0);
 assert(c.advance(20.0f/30,10,loop)==1&&c.frame==0&&!c.completed);
 assert(c.advance(1.0f/30,10,loop)==0); // loop start emitted again
 c.start(false);assert(c.advance(2,35,damage)==1000); // last event wins like retail listener
 std::puts("P2_ORIGINAL_WISP_CLOCK_PASS strict keys, loop overshoot, stop, END; no gameplay claim");
}
