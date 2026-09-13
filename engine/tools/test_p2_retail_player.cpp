#include "pc_p2_retail_player.h"
#include <fstream>
#include <iostream>
#include <stdexcept>
using namespace p2retail;
static int checks=0;
static void check(bool ok){++checks;if(!ok)throw std::runtime_error("retail player check "+std::to_string(checks));}
int main(int argc,char** argv){
 Player player;std::vector<int> ids;
 auto receive=[&](const Event& e){ids.push_back(e.type);};
 Motion motion{"test.bca","",10,2,{{0,0},{3,2},{4,1},{8,3},{9,4}}};
 check(player.start(motion));check(player.advance(0,receive)==Update::Ok);check(ids.empty());
 player.advance(.999f,receive);check(ids.empty());player.advance(.0011f,receive);check(ids==std::vector<int>{0});
 player.advance(8,receive);check(ids==std::vector<int>({0,2,1}));check(player.frame()==0); // Discard huge overshoot.
 ids.clear();check(player.advance(10,[&](const Event& e){receive(e);if(e.type==1)player.finishMotion();})==Update::Ok);
 check(ids==std::vector<int>({0,2,1,3,4,1000}));check(player.frame()==9&&player.completed());
 player.advance(10,receive);check(ids.size()==6); // END once.
 auto old=player.generation();auto invalid=motion;invalid.events={{0,1}};
 check(!player.start(invalid)&&player.generation()==old);
 check(player.start(motion));ids.clear();
 check(player.advance(10,[&](const Event& e){receive(e);player.cancel();})==Update::Replaced);
 check(ids==std::vector<int>{0});check(player.advance(1,receive)==Update::Inactive);
 check(player.start(motion));ids.clear();
 check(player.advance(10,[&](const Event& e){receive(e);check(player.start(motion));})==Update::Replaced);
 check(ids==std::vector<int>{0}&&player.frame()==0);
 ids.clear();check(player.advance(1,[&](const Event& e){receive(e);check(player.advance(1,receive)==Update::Reentrant);})==Update::Ok);
 check(ids==std::vector<int>{0});
 check(player.advance(-1,receive)==Update::Invalid);
 check(player.advance(std::numeric_limits<float>::infinity(),receive)==Update::Invalid);
 check(player.advance(1000001,receive)==Update::Invalid);
 unsigned clips=0;
 for(int arg=1;arg<argc;++arg){std::ifstream file(argv[arg]);auto table=read(file);
  for(const auto& clip:table.motions){
   check(player.start(clip));player.finishMotion();std::vector<Event> events;
   check(player.advance(float(clip.duration),[&](const Event& e){events.push_back(e);})==Update::Ok);
   check(events.size()==clip.events.size()+1);
   for(std::size_t i=0;i<clip.events.size();++i)check(events[i].frame==clip.events[i].frame&&events[i].type==clip.events[i].type);
   check(events.back().type==1000&&events.back().frame==clip.duration&&player.completed());++clips;
  }
 }
 std::cout<<"PASS retail player: "<<checks<<" checks, "<<clips<<" real clips\n";
}
