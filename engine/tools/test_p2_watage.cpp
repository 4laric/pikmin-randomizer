#include "pc_p2_watage_effect.h"
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace p2watage;
#define CHECK(x) do{if(!(x))throw std::runtime_error(std::string("line ")+std::to_string(__LINE__)+": " #x);}while(0)
int main(int argc,char** argv){try{
 std::string e;Effect f;CHECK(!f.touch({},1,e));CHECK(!f.load("missing-watage-resource",e));
 // Independent field controls check additive type1, cycle and cap order.
 Particle p;p.age=1;p.velocity={1,2,3};std::uint32_t seed=1,old=seed;Effect::fields(p,seed,1);CHECK(std::fabs(p.drag-.985f)<1e-6&&p.velocity.x==1&&seed==old);
 p.drag=1;Effect::fields(p,seed,2);CHECK(seed==old&&p.velocity.y==2);p.age=4;Effect::fields(p,seed,2);CHECK(seed!=old&&p.velocity.y!=2);
 p.velocity={30,0,0};Effect::fields(p,seed,4);CHECK(std::fabs(std::sqrt(p.velocity.x*p.velocity.x+p.velocity.y*p.velocity.y)-9)<1e-5);
 CHECK(!f.tick(std::numeric_limits<float>::quiet_NaN(),e));CHECK(!f.tick(-1,e));CHECK(!f.tick(3,e));
 if(argc==2){
  CHECK(f.load(argv[1],e));CHECK(f.texture().size()==1088);CHECK(f.touch({10,20,30},1,e));CHECK(f.particles()>=3&&f.particles()<=5);CHECK(f.emissions()==1);
  for(const auto& p:f.bursts()[0].particles){CHECK(p.life>=125&&p.life<=200);CHECK(p.position.x==10&&p.position.y>=97&&p.position.y<=113);}
  CHECK(!f.load(argv[1],e)&&f.ready());auto n=f.particles();CHECK(f.tick(1.f/60,e)&&f.particles()==n);CHECK(f.tick(1.f/60,e));CHECK(f.bursts()[0].particles[0].age==0);
  for(int i=0;i<7;++i)CHECK(f.tick(1,e));CHECK(f.particles()==0&&f.bursts().empty());
  CHECK(f.touch({},2,e));CHECK(f.emissions()==2);f.clear();CHECK(f.particles()==0);CHECK(f.load(argv[1],e));
  for(int i=0;i<64;++i)CHECK(f.touch({},i,e));CHECK(!f.touch({},65,e));f.clear();
  // Changed legal data must refuse: isolated temporary copy, never source edits.
  auto dir=std::filesystem::temp_directory_path()/"p2-watage-refusal-control";CHECK(!std::filesystem::exists(dir));std::filesystem::create_directory(dir);
  for(auto name:{"watage-01e4.jpa","IP2_watage2_ia.tex1"})std::filesystem::copy_file(std::filesystem::path(argv[1])/name,dir/name);
  for(auto name:{"watage-01e4.jpa","IP2_watage2_ia.tex1"}){
   auto path=dir/name;{std::fstream out(path,std::ios::binary|std::ios::in|std::ios::out);out.put('\0');}CHECK(!f.load(dir.string(),e));std::filesystem::copy_file(std::filesystem::path(argv[1])/name,path,std::filesystem::copy_options::overwrite_existing);
  }
  std::filesystem::remove_all(dir);
 }
 std::cout<<"PASS WATAGE source_fields=3 finite_lifetime=1 raw_resource_controls="<<(argc==2)<<" gameplay=0\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
