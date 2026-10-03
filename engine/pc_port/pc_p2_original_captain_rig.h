#pragma once
#include "pc_p2_pose_blend.h"
#include <array>
#include <map>
#include <string>
#include <istream>
#include <set>
namespace p2original { namespace captain { namespace rig {
using Matrix=std::array<float,12>;
struct Vertex {unsigned joint; p2pose::Vec local;};
struct Model {std::string name,sourceSha;std::array<int,11> parent;std::array<std::string,11> names;std::vector<Vertex> positions,normals;};
struct Clip {unsigned id;std::string name,sourceSha;std::vector<std::array<Matrix,11>> frames;};
inline bool digest(const std::string& s){return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
inline bool models(std::istream& in,std::array<Model,3>& out){
 std::string word;int count;if(!(in>>word>>count)||word!="P2_SOURCE_CAPTAIN_RIG_1"||count!=3)return false;
 const char* models[]={"orima1","orima3","syatyou"};const char* jointNames[]={"kosinull","legcentre","llegjnt","rlegjnt","sebonjnt","headjnt","happajnt1","happajnt2","happajnt3","lhandjnt","rhandjnt"};const int parents[]={-1,0,1,1,0,4,5,6,7,4,4};std::array<Model,3> parsed;
 for(unsigned j=0;j<3;++j){auto& m=parsed[j];int joints;if(!(in>>word>>m.name>>m.sourceSha>>joints)||word!="model"||m.name!=models[j]||!digest(m.sourceSha)||joints!=11)return false;
  for(unsigned i=0;i<11;++i){unsigned id;if(!(in>>word>>id>>m.parent[i]>>m.names[i])||word!="joint"||id!=i||m.parent[i]!=parents[i]||m.names[i]!=jointNames[i])return false;}
  for(unsigned k=0;k<2;++k){unsigned n;if(!(in>>word>>n)||word!=(k?"normals":"positions")||n<1||n>p2pose::MaxVectors)return false;auto& v=k?m.normals:m.positions;v.reserve(n);for(unsigned i=0;i<n;++i){Vertex item;if(!(in>>item.joint>>item.local.x>>item.local.y>>item.local.z)||item.joint>=11||!p2pose::valid(item.local))return false;p2pose::Vec unit;if(k&&!p2pose::unit(item.local,unit))return false;v.push_back(item);}}
 }
 if(in>>word)return false;out=std::move(parsed);return true;
}
inline bool clips(std::istream& in,std::string& registry,std::map<unsigned,Clip>& out){
 std::string word,sha;unsigned count;if(!(in>>word>>sha>>count)||word!="P2_SOURCE_CAPTAIN_JOINT_CLIPS_1"||!digest(sha)||(count!=20&&count!=26))return false;
 const unsigned ids20[]={0,1,3,4,10,11,13,14,22,23,28,29,30,31,32,33,34,50,54,1000};const char* names20[]={"akubi","asibumi","chatting","damage","fue","furimuku","gattu","getup","jhit","jkoke","nigeru","run2","walk","wait","kizuku","throw","trwwait","jump","sagasu2","down"};const unsigned ids26[]={0,1,3,4,5,10,11,13,14,22,23,28,29,30,31,32,33,34,42,43,50,54,64,65,66,1000};const char* names26[]={"akubi","asibumi","chatting","damage","dead","fue","furimuku","gattu","getup","jhit","jkoke","nigeru","run2","walk","wait","kizuku","throw","trwwait","nuku","nuku3","jump","sagasu2","punch","punch2","punch3","down"};const unsigned* ids=count==20?ids20:ids26;const char* const* names=count==20?names20:names26;std::map<unsigned,Clip> parsed;std::size_t total=0;
 for(unsigned k=0;k<count;++k){Clip clip;unsigned frames,joints;if(!(in>>word>>clip.id>>clip.name>>frames>>clip.sourceSha>>joints)||word!="clip"||clip.id!=ids[k]||clip.name!=names[k]||frames<1||frames>10000||!digest(clip.sourceSha)||joints!=11)return false;total+=frames;if(total>20000)return false;clip.frames.resize(frames);for(auto& frame:clip.frames)for(auto& joint:frame)for(auto& value:joint)if(!(in>>value)||!std::isfinite(value)||std::fabs(value)>1000000)return false;parsed.emplace(clip.id,std::move(clip));}
 if(in>>word)return false;registry=sha;out=std::move(parsed);return true;
}
inline Matrix compose(const Matrix& a,const Matrix& b){Matrix out{};for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c){for(unsigned k=0;k<3;++k)out[r*4+c]+=a[r*4+k]*b[k*4+c];if(c==3)out[r*4+c]+=a[r*4+3];}return out;}
// Bound root0 applies through all ancestors. Self replaces local transforms at
// root4 and descendants, exactly FakePiki::setModelCalc(model,4).
inline bool joints(const Model& model,const Clip& self,float sf,const Clip& bound,float bf,bool movie,std::array<Matrix,11>& out){
 if(!std::isfinite(sf)||!std::isfinite(bf)||sf<0||bf<0||sf>1000000||bf>1000000||self.frames.empty()||bound.frames.empty())return false;if((self.id==1000&&std::floor(sf)!=sf)||(bound.id==1000&&std::floor(bf)!=bf))return false;auto at=[](const Clip& c,float f){return std::min(std::size_t(c.id==1000?f:f+.5f),c.frames.size()-1);};std::array<bool,11> upper{};
 for(unsigned i=0;i<11;++i){int parent=model.parent[i];if((i==0&&parent!=-1)||(i>0&&(parent<0||parent>=int(i))))return false;upper[i]=i==4||(parent>=0&&upper[parent]);const Matrix& local=!movie&&upper[i]?self.frames[at(self,sf)][i]:bound.frames[at(bound,bf)][i];out[i]=parent<0?local:compose(out[parent],local);for(float value:out[i])if(!std::isfinite(value)||std::fabs(value)>1000000)return false;}return true;
}
inline p2pose::Vec point(const Matrix& m,p2pose::Vec p){return {m[0]*p.x+m[1]*p.y+m[2]*p.z+m[3],m[4]*p.x+m[5]*p.y+m[6]*p.z+m[7],m[8]*p.x+m[9]*p.y+m[10]*p.z+m[11]};}
inline p2pose::Vec normal(const Matrix& m,p2pose::Vec p){float a=m[0],b=m[1],c=m[2],d=m[4],e=m[5],f=m[6],g=m[8],h=m[9],i=m[10];std::array<float,9> co={e*i-f*h,f*g-d*i,d*h-e*g,c*h-b*i,a*i-c*g,b*g-a*h,b*f-c*e,c*d-a*f,a*e-b*d};float det=a*co[0]+b*co[1]+c*co[2];p2pose::Vec v={co[0]*p.x+co[1]*p.y+co[2]*p.z,co[3]*p.x+co[4]*p.y+co[5]*p.z,co[6]*p.x+co[7]*p.y+co[8]*p.z};if(std::fabs(det)>=1e-12){v.x/=det;v.y/=det;v.z/=det;}p2pose::Vec unit{};p2pose::unit(v,unit);return unit;}
inline bool pose(const Model& model,const std::array<Matrix,11>& joints,p2pose::Pose& out){if(model.positions.empty()||model.normals.empty()||model.positions.size()>p2pose::MaxVectors||model.normals.size()>p2pose::MaxVectors)return false;p2pose::Pose p;for(auto v:model.positions){if(v.joint>=11||!p2pose::valid(v.local))return false;auto transformed=point(joints[v.joint],v.local);if(!p2pose::valid(transformed))return false;p.positions.push_back(transformed);}for(auto v:model.normals){if(v.joint>=11||!p2pose::valid(v.local))return false;auto transformed=normal(joints[v.joint],v.local);if(!p2pose::valid(transformed))return false;p.normals.push_back(transformed);}out=std::move(p);return true;}
} } }
