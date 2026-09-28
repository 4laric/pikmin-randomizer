#include "pc_p2_display_clock.h"
#include "pc_p2_bulblax_visual_policy.h"
#include <iostream>
#include <stdexcept>
static int checks=0;
static void check(bool ok){++checks;if(!ok)throw std::runtime_error("check "+std::to_string(checks));}
int main(){
 p2display::Clock clock;using p2display::Advance;
 check(clock.update(1)==Advance::Invalid);check(!clock.start(0,0));
 check(clock.start(30,100));check(clock.update(100)==Advance::Ok);check(clock.frame()==0);
 p2bulblax::Clip clip;clip.duration=30;clip.frames={0,15,29};
 for(unsigned ms=1;ms<=10000;++ms){
  check(clock.update(100+ms)==Advance::Ok);
  // Exact ties can differ from old float multiplication rounding; compare
  // representative integer-source frames, and continuous phase within tolerance.
  double expected=std::fmod(double(ms)*.03,30.);
  double difference=std::fabs(clock.frame()-expected);
  check(difference<1e-8||std::fabs(difference-30)<1e-8);
  if(ms%100==0)check(clip.index(float(clock.frame()))==clip.index(float(expected)));
 }
 check(clock.update(10100)==Advance::Ok);
 check(clock.start(30,0xfffffff0u));check(clock.update(0x10u)==Advance::Ok);
 check(std::fabs(clock.frame()-.96)<1e-10);
 check(clock.start(1,0));check(clock.update(1000000)==Advance::RecoveredGap);check(clock.frame()==0);
 check(clock.update(1000001)==Advance::Ok);check(std::fabs(clock.frame()-.03)<1e-10);
 clock.reset();check(clock.update(1000002)==Advance::Invalid);
 check(clock.start(30,555));check(clock.frame()==0);
 check(clock.update(1555)==Advance::Ok);check(clock.frame()==0);
 std::cout<<"PASS display clock: "<<checks<<" checks\n";
}
