// Local source-oracle probe. Prints frames at eighth-frame intervals.
#include "pc_p2_material_srt.h"
#include <fstream>
#include <iomanip>
#include <iostream>
int main(int argc,char** argv){
 if(argc!=2)return 2;
 try{
  std::ifstream input(argv[1]);const auto bank=p2material::read(input);
  std::cout<<std::setprecision(17);
  for(std::size_t track=0;track<bank.tracks.size();++track){
   for(unsigned step=0;step<=bank.duration*8;++step){
    p2material::Sample s;double m[2][3];double frame=step/8.0;
    if(!p2material::sample(bank,track,frame,s)||!p2material::matrix(s,m))return 3;
    std::cout<<track<<' '<<frame<<' '<<s.sx<<' '<<s.sy<<' '<<s.rotation<<' '<<s.tx<<' '<<s.ty;
    for(const auto& row:m)for(double v:row)std::cout<<' '<<v;
    std::cout<<'\n';
   }
  }
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
}
