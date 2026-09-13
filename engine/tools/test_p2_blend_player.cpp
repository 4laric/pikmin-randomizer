#include "pc_p2_blend_player.h"
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace p2retail;
int main(){
 int checks=0;auto check=[&](bool ok){++checks;if(!ok)throw std::runtime_error("check "+std::to_string(checks));};
 BlendPlayer b;Motion m{"test.bca","",10,0,{{0,2},{2,3},{5,4}}};
 std::vector<int> events;int ends=0;float ending=0;
 auto event=[&](unsigned track,const Event& e){events.push_back(int(track)*10000+e.type);};
 auto end=[&](float duration){++ends;ending=duration;};
 check(b.advance(1,1,1,event,end)==Update::Inactive);
 check(b.startTrack(0,m));check(!b.startBlend(2));
 check(b.startTrack(1,m));check(!b.startTrack(2,m));
 check(b.advance(1,1,4,event,end)==Update::Ok);
 check(events==std::vector<int>{2}&&b.frame(0)==1&&b.frame(1)==0);
 check(!b.startBlend(0)&&!b.startBlend(-1)&&!b.startBlend(std::numeric_limits<float>::infinity()));
 check(b.startBlend(2.5f));events.clear();
 check(b.advance(1,2,1,event,end)==Update::Ok);
 check(events==std::vector<int>({3,10002}));check(b.progress()==.4f&&ends==0);
 check(b.advance(2,0,0,event,end)==Update::Ok);
 check(b.completed()&&b.enabled()&&b.progress()==1&&ends==1&&ending==2.5f);
 b.advance(1,0,0,event,end);check(ends==1);
 check(b.endBlend()&&!b.enabled()&&!b.completed());
 const auto secondary=b.frame(1);b.advance(1,1,1,event,end);check(b.frame(1)==secondary);
 check(b.startBlend(1));auto primary=b.frame(0);
 check(b.advance(1,1,-1,event,end)==Update::Invalid&&b.frame(0)==primary&&b.progress()==0);
 check(b.seekTrack(0,0));events.clear();
 check(b.advance(10,10,10,[&](unsigned t,const Event& e){event(t,e);check(b.endBlend());},end)==Update::Replaced);
 check(events==std::vector<int>{2}&&b.frame(1)==secondary); // No stale later keys or second-track update.
 check(b.seekTrack(0,0)&&b.startBlend(1));events.clear();
 check(b.advance(10,10,10,[&](unsigned t,const Event& e){event(t,e);b.cancel();},end)==Update::Replaced);
 check(events.size()==1&&b.advance(1,1,1,event,end)==Update::Inactive);
 check(b.startTrack(0,m)&&b.startTrack(1,m)&&b.startBlend(1));events.clear();
 check(b.advance(1,1,1,[&](unsigned t,const Event& e){event(t,e);check(b.advance(1,1,1,event,end)==Update::Reentrant);},end)==Update::Ok);
 check(events==std::vector<int>({2,10002}));
 check(b.startBlend(1));
 check(b.advance(1,0,0,event,[&](float){check(b.startBlend(4));})==Update::Replaced);
 check(!b.completed()&&b.progress()==0);
 Motion loop{"loop.bca","",10,2,{{0,0},{2,1},{9,3}}};
 check(b.startTrack(0,loop)&&b.startTrack(1,m)&&b.startBlend(10));events.clear();
 b.advance(1,8,4,event,end);check(b.frame(0)==0&&b.frame(1)==4);
 check(events==std::vector<int>({0,1,10002,10003}));
 check(b.finishTrack(0));events.clear();b.advance(1,10,0,event,end);
 check(events==std::vector<int>({0,1,3,1000}));
 std::cout<<"PASS blend player: "<<checks<<" checks\n";
}
