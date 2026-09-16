#include "pc_p2_native_counter.h"
#include "pc_p2_tank_phase.h"
#include <iostream>
#include <stdexcept>
using namespace p2source;
static int checks=0;
static void check(bool ok){++checks;if(!ok)throw std::runtime_error("check "+std::to_string(checks));}
static void ids(const Batch& batch,std::initializer_list<unsigned> wanted){
 check(bool(batch));check(batch.events.size()==wanted.size());std::size_t i=0;
 for(auto id:wanted)check(batch.events[i++].id==id);
}
int main(){
 NativeCounter cursor;
 Clip one{61,false,0,0,{{0,1},{20,2},{60,3}}};
 check(cursor.observe(1,0).error==Error::Inactive);
 check(!cursor.bind(one,30,0));check(!cursor.bind(one,0,1));check(cursor.bind(one,30,1));
 ids(cursor.observe(1,0),{});ids(cursor.observe(1,15),{1,2});
 float mapped=0;check(p2tankvisual::frame(15,31,61,mapped));check(cursor.frame()==mapped);
 ids(cursor.observe(1,15),{}); // Paused native motion does not progress.
 check(cursor.observe(1,14).error==Error::InvalidAdvance);
 check(cursor.observe(2,20).error==Error::InvalidAdvance);
 check(cursor.observe(1,31).error==Error::InvalidAdvance);
 check(cursor.observe(1,20,1).error==Error::InvalidAdvance);
 check(cursor.frame()==30);
 ids(cursor.observe(1,30),{3});check(!cursor.finished());
 ids(cursor.finish(1),{});check(cursor.finished()&&cursor.poseFrame()==60);
 ids(cursor.finish(1),{});ids(cursor.observe(1,30),{});
 check(cursor.observe(1,29).error==Error::InvalidAdvance);
 check(!cursor.bind(one,30,1));check(cursor.bind(one,30,2));
 auto prior=cursor.observe(2,15);check(cursor.current(prior));
 check(!cursor.seek(2,5));check(cursor.seek(3,5));check(!cursor.current(prior));
 check(cursor.observe(2,15).error==Error::InvalidAdvance);ids(cursor.observe(3,15),{2});
 prior=cursor.observe(3,15);cursor.cancel();check(!cursor.current(prior));
 check(cursor.bind(one,30,4));check(!cursor.current(prior));ids(cursor.finish(4),{1,2,3});

 Clip loop{10,true,4,8,{{0,1},{4,2},{7,3}}};
 check(cursor.bind(loop,9,5));ids(cursor.observe(5,7),{1,2,3});
 check(cursor.observe(5,4).error==Error::InvalidAdvance);
 auto wrap=cursor.observe(5,4,1);ids(wrap,{2});check(wrap.events[0].cycle==1);
 auto skipped=cursor.observe(5,5,3);ids(skipped,{3,2,3,2});
 check(skipped.events.back().cycle==3);check(cursor.frame()==5);
 check(cursor.observe(5,5,2).error==Error::InvalidAdvance);
 check(cursor.observe(5,3,4).error==Error::InvalidAdvance);
 check(cursor.observe(5,8,3).error==Error::InvalidAdvance);
 check(cursor.observe(5,5,1000).error==Error::Budget);check(cursor.frame()==5);
 ids(cursor.observe(5,7,3),{3});check(cursor.finish(5).error==Error::InvalidAdvance);
 check(cursor.seek(6,4));ids(cursor.observe(6,7,0),{3});
 check(cursor.observe(5,7,3).error==Error::InvalidAdvance);

 Clip crowded{2,true,0,2,{}};crowded.events.resize(Clock::MaxEvents,{0,8});
 check(cursor.bind(crowded,1,7));auto fail=cursor.observe(7,0,1);
 check(fail.error==Error::Budget&&fail.events.empty()&&cursor.frame()==0);
 auto retry=cursor.observe(7,1,0);check(bool(retry)&&retry.events.size()==Clock::MaxEvents);
 check(cursor.observe(7,std::numeric_limits<double>::quiet_NaN()).error==Error::InvalidAdvance);
 check(!cursor.seek(8,2));check(cursor.observe(7,1).error==Error::None);
 std::cout<<"PASS native_counter clock: "<<checks<<" checks\n";
}
