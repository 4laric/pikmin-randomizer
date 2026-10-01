#include "pc_p2_envmap.h"
#include <iostream>
#include <limits>
#include <stdexcept>
int main(){
 int checks=0;auto check=[&](bool ok){++checks;if(!ok)throw std::runtime_error("envmap check "+std::to_string(checks));};
 float view[3][4]={{1,0,0,120},{0,1,0,-70},{0,0,1,900}};
 float srt[2][3]={{1,0,0},{0,1,0}},out[3][4]{};
 check(p2envmap::matrix(view,srt,out));check(out[0][0]==.5f&&out[1][1]==-.5f&&out[0][3]==.5f&&out[1][3]==.5f);
 // Independent full matrix multiply, including source center/SRT and yaw rotations.
 for(float yaw:{0.f,.6f,1.57f})for(float sx:{.78125f,.869140625f}){
  view[0][0]=std::cos(yaw);view[0][2]=std::sin(yaw);view[2][0]=-std::sin(yaw);view[2][2]=std::cos(yaw);
  srt[0][0]=sx;srt[1][1]=sx;srt[0][2]=.5f-.5f*sx;srt[1][2]=.5f-.5f*sx+.0537109375f;
  check(p2envmap::matrix(view,srt,out));
  float a[4][4]={{sx,0,0,srt[0][2]},{0,sx,0,srt[1][2]},{0,0,1,0},{0,0,0,1}};
  float q[4][4]={{.5f,0,0,.5f},{0,-.5f,0,.5f},{0,0,1,0},{0,0,0,1}},v[4][4]{};
  for(int i=0;i<3;++i)for(int j=0;j<3;++j)v[i][j]=view[i][j];
  v[3][3]=1;
  float aq[4][4]{},expected[4][4]{};
  for(int i=0;i<4;++i)for(int j=0;j<4;++j)for(int k=0;k<4;++k)aq[i][j]+=a[i][k]*q[k][j];
  for(int i=0;i<4;++i)for(int j=0;j<4;++j)for(int k=0;k<4;++k)expected[i][j]+=aq[i][k]*v[k][j];
  for(int i=0;i<3;++i)for(int j=0;j<4;++j)check(std::fabs(out[i][j]-expected[i][j])<1e-6f);
 }
 float old=out[0][0];view[0][0]=std::numeric_limits<float>::infinity();check(!p2envmap::matrix(view,srt,out)&&out[0][0]==old);
 std::cout<<"PASS P2 envmap: "<<checks<<" checks\n";
}
