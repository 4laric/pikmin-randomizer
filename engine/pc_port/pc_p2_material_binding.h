#pragma once
#include "pc_p2_material_scope.h"

namespace p2material {
// Explicit converter-owned mapping. Source names are not host array indices.
struct Target {
 std::string material;
 unsigned slot=0, hostMaterial=0;
};

class Binding {
 struct Entry {
  std::size_t track;
  unsigned host;
  PVWTextureData* texture;
  PVWTexGenData* generator;
 };
 const Bank* bank_=nullptr;
 const Shape* shape_=nullptr;
 Material* materials_=nullptr;
 int materialCount_=0;
 std::uint64_t generation_=0;
 std::vector<Entry> entries_;
public:
 // A failed bind clears the previous binding. Bank/model storage must remain
 // immutable and alive; the scene owner must advance generation before reuse.
 bool bind(const Bank&, Shape&, const std::vector<Target>&, std::uint64_t generation);
 bool draw(const Bank&, Shape&, Graphics&, double sourceFrame, std::uint64_t generation) const;
 void reset();
 bool ready()const{return bank_!=nullptr;}
};
}
