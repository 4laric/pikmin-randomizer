#include "pc_p2_color_binding.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"
#include <optional>
namespace p2color {
namespace {
bool storage(const Material& m){return (m.mFlags&MATFLAG_PVW)&&m.mTevInfo;}
class Scope {
 PVWTevInfo& data_;unsigned kind_,reg_;Sample saved_;
 void put(const Sample& s){
  if(kind_){auto& c=data_.mKonstColors[reg_];c.r=static_cast<u8>(s[0]);c.g=static_cast<u8>(s[1]);c.b=static_cast<u8>(s[2]);c.a=static_cast<u8>(s[3]);}
  else{auto& c=data_.mTevColRegs[reg_].mAnimatedColor;c.r=s[0];c.g=s[1];c.b=s[2];c.a=s[3];}
 }
public:
 Scope(PVWTevInfo& data,unsigned kind,unsigned reg,const Sample& s):data_(data),kind_(kind),reg_(reg){
  if(kind){const auto& c=data.mKonstColors[reg];saved_={c.r,c.g,c.b,c.a};}
  else{const auto& c=data.mTevColRegs[reg].mAnimatedColor;saved_={c.r,c.g,c.b,c.a};}put(s);
 }
 ~Scope(){put(saved_);}Scope(const Scope&)=delete;Scope& operator=(const Scope&)=delete;
};
struct CacheScope {Graphics& gfx;explicit CacheScope(Graphics& g):gfx(g){gfx.useMaterial(nullptr);}~CacheScope(){gfx.useMaterial(nullptr);}};
}
bool Binding::bind(const Bank& bank,Shape& shape,const std::vector<Target>& targets,std::uint64_t generation){
 reset();if(!generation||!valid(bank)||targets.empty()||targets.size()>128||!shape.mMaterialList||shape.mMaterialCount<1)return false;
 std::vector<Entry> next;std::set<std::tuple<unsigned,unsigned,unsigned>> destinations;std::set<size_t> covered;
 for(const auto& t:targets){
  if(t.kind>1||t.hostReg>(t.kind?3u:2u)||t.hostMaterial>=unsigned(shape.mMaterialCount)||!destinations.insert({t.hostMaterial,t.kind,t.hostReg}).second)return false;
  size_t index=0;for(;index<bank.tracks.size();++index){const auto& source=bank.tracks[index];if(source.material==t.material&&source.kind==t.kind&&source.reg==t.reg)break;}
  if(index==bank.tracks.size())return false;
  auto& m=shape.mMaterialList[t.hostMaterial];if(!storage(m))return false;
  for(int j=0;j<shape.mMaterialCount;++j)if(unsigned(j)!=t.hostMaterial&&storage(shape.mMaterialList[j])&&shape.mMaterialList[j].mTevInfo==m.mTevInfo)return false;
  next.push_back({index,t.hostMaterial,t.hostReg,m.mTevInfo});covered.insert(index);
 }
 if(covered.size()!=bank.tracks.size())return false;
 bank_=&bank;shape_=&shape;materials_=shape.mMaterialList;count_=shape.mMaterialCount;generation_=generation;entries_=std::move(next);return true;
}
bool Binding::draw(const Bank& bank,Shape& shape,Graphics& gfx,double frame,std::uint64_t generation)const{
 if(bank_!=&bank||shape_!=&shape||!generation||generation_!=generation||materials_!=shape.mMaterialList||count_!=shape.mMaterialCount||!gfx.mCamera)return false;
 std::array<Sample,128> samples;
 for(size_t i=0;i<entries_.size();++i){const auto& e=entries_[i];const auto& m=shape.mMaterialList[e.host];
  if(!storage(m)||m.mTevInfo!=e.storage||!sample(bank,e.track,frame,samples[i]))return false;
  for(int j=0;j<shape.mMaterialCount;++j)if(unsigned(j)!=e.host&&storage(shape.mMaterialList[j])&&shape.mMaterialList[j].mTevInfo==e.storage)return false;
 }
 std::array<std::optional<Scope>,128> scopes;
 for(size_t i=0;i<entries_.size();++i){const auto& e=entries_[i];scopes[i].emplace(*e.storage,bank.tracks[e.track].kind,e.reg,samples[i]);}
 CacheScope cache(gfx);shape.drawshape(gfx,*gfx.mCamera,nullptr);return true;
}
}
