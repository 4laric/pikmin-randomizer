#pragma once
#include "pc_p2_material_color.h"
#include "Material.h"
class Shape;
namespace p2color {
struct Target {std::string material;unsigned kind=0,reg=0,hostMaterial=0,hostReg=0;};
class Binding {
 struct Entry {size_t track;unsigned host,reg;PVWTevInfo* storage;};
 const Bank* bank_=nullptr;const Shape* shape_=nullptr;Material* materials_=nullptr;
 int count_=0;std::uint64_t generation_=0;std::vector<Entry> entries_;
public:
 void reset(){bank_=nullptr;shape_=nullptr;materials_=nullptr;count_=0;generation_=0;entries_.clear();}
 bool bind(const Bank&,Shape&,const std::vector<Target>&,std::uint64_t generation);
 bool draw(const Bank&,Shape&,Graphics&,double frame,std::uint64_t generation)const;
};
}
