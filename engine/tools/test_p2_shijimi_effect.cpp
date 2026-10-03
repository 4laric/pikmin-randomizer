#include "pc_p2_shijimi_effect.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace p2original::shijimi;
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)
int main(int argc,char** argv){try{
 CHECK(argc==2);std::string e;DownEffects fx;auto visible=[](std::uint64_t,p2original::Position,float r){CHECK(r==30);return false;};
 CHECK(!fx.create(1,{0,0,0},Color::Yellow,7,e));CHECK(!fx.load(std::string(argv[1])+"/absent",e));
 CHECK(fx.load(argv[1],e));CHECK(fx.create(1,{10,20,30},Color::Yellow,7,e));
 CHECK(fx.create(2,{10,20,30},Color::Red,8,e));CHECK(fx.create(3,{10,20,30},Color::Purple,9,e));
 CHECK(fx.emitters().at(1).resource==23&&fx.emitters().at(2).resource==22&&fx.emitters().at(3).resource==21);
 CHECK(fx.tick(1.f/60,visible,e));CHECK(fx.particles()==0);CHECK(fx.tick(1.f/60,visible,e));
 CHECK(fx.particles()==3);CHECK(fx.emitters().at(1).births==1);
 auto first=fx.emitters().at(1).particles[0];CHECK(first.age==0&&first.life>=31.25f&&first.life<=50);
 CHECK(first.scaleOut>=.625f&&first.scaleOut<=1.375f);CHECK(std::fabs(first.gravity.y+.03f)<1e-7f);
 CHECK(fx.follow(1,{1000,2000,3000},e));CHECK(fx.tick(1.f/30,visible,e));
 CHECK(fx.emitters().at(1).particles[0].position.x<11); // existing particle does not chase
 CHECK(fx.tick(1.f/30,visible,e));CHECK(fx.emitters().at(1).births==2);
 CHECK(fx.emitters().at(1).particles[0].position.x>999); // next birth does chase
 CHECK(!fx.load(argv[1],e));CHECK(!fx.tick(std::numeric_limits<float>::quiet_NaN(),visible,e));
 CHECK(fx.fade(1,e)&&fx.fade(2,e)&&fx.fade(3,e));
 CHECK(!fx.create(1,{0,0,0},Color::Yellow,7,e));
 CHECK(fx.create(5,{40,50,60},Color::Yellow,11,e)&&fx.tick(1.f/30,visible,e));
 CHECK(fx.emitters().at(5).births==1&&fx.fade(5,e));CHECK(fx.tick(2,visible,e));
 CHECK(fx.particles()==0&&fx.emitters().empty());CHECK(fx.load(argv[1],e));
 CHECK(fx.create(4,{0,0,0},Color::Yellow,10,e));
 auto hidden=[](std::uint64_t,p2original::Position,float r){CHECK(r==30);return true;};
 CHECK(fx.tick(1.f/30,hidden,e));CHECK(fx.emitters().at(4).births==1);
 CHECK(fx.tick(1.f/30,hidden,e)&&fx.tick(1.f/30,hidden,e));CHECK(fx.emitters().at(4).births==1);
 CHECK(fx.tick(1.f/30,visible,e)&&fx.tick(1.f/30,visible,e)&&fx.tick(1.f/30,visible,e));CHECK(fx.emitters().at(4).births==2);
 CHECK(fx.fade(4,e)&&fx.tick(2,visible,e));CHECK(fx.emitters().empty());
 std::cout<<"PASS genuine21/22/23 colors first/fractional emission 30Hz birth-only chase gravity fade/drain refusal; gameplay=0\n";
 return 0;
 }catch(const std::exception& ex){std::cerr<<ex.what()<<'\n';return 1;}}
