#include "pc_p2_original_calendar_state.h"
#include <cassert>
#include <cstdio>
int main(){
 using namespace p2original;std::string e,b;const std::string campaign(64,'a');CalendarLedger state;
 assert(!state.encode(b,e));assert(state.initialize(campaign,29,e));
 CalendarMember member;member.name="nonloop/source.txt";CalendarMember loop;loop.name="loop/source.txt";
 assert(state.commit("tutorial",{{&member,35,3,63},{&loop,40,4,0}},e));CalendarState view;
 assert(state.state("tutorial",view,e)&&view.visited&&view.nonloopLoaded==(std::uint64_t(1)<<63)&&view.loopLoaded==1);
 assert(state.state("forest",view,e)&&!view.visited&&!view.nonloopLoaded&&!view.loopLoaded);
 assert(state.encode(b,e)&&b.size()==CalendarLedger::Bytes);const auto unchanged=b;
 assert(!state.commit("tutorial",{{&member,35,3,64}},e));assert(state.encode(b,e)&&b==unchanged);
 assert(!state.commit("tutorial",{{&member,35,3,1},{&member,35,3,2}},e));assert(state.encode(b,e)&&b==unchanged);
 CalendarLedger restored;assert(restored.decode(campaign,29,b,e));assert(restored.encode(b,e)&&b==unchanged);
 unsigned checks=12;for(std::size_t i=0;i<b.size();++i){auto broken=b;broken[i]^=1;assert(!restored.decode(campaign,29,broken,e));std::string retained;assert(restored.encode(retained,e)&&retained==unchanged);checks+=2;}
 assert(!restored.decode(std::string(64,'b'),29,b,e));assert(!restored.decode(campaign,30,b,e));
 assert(!restored.advance(31,e));assert(restored.advance(30,e));assert(restored.state("tutorial",view,e)&&view.visited&&view.nonloopLoaded==(std::uint64_t(1)<<63)&&!view.loopLoaded);
 assert(!restored.initialize(campaign,29,e));assert(restored.initialize(campaign,30,e));
 std::printf("PASS original calendar ledger %u checks; successful loads, day30 reset, atomic checkpoint refusals\n",checks+8);
}
