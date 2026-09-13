#include "pc_p2_pose_bank.h"
#include <fstream>
#include <iostream>
#include <iterator>
int main(int argc,char** argv){
 if(argc!=3)return 2;
 p2pose::Baked pair[2];
 for(int i=0;i<2;++i){std::ifstream in(argv[i+1],std::ios::binary);std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(in)),{});
  if(!p2pose::decodeBaked(bytes,pair[i]))return 1;}
 if(pair[0].topology!=pair[1].topology)return 1;
 std::cout<<"PASS compatible "<<pair[0].pose.positions.size()<<" "<<pair[0].pose.normals.size()<<"\n";
}
