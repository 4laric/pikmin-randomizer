#pragma once
#include "pc_p2_original_group.h"
namespace p2original {
// Physical families opt in by literal retail source ID. Every row is routed;
// a family's permissive filtering cannot silently admit another source.
class Dispatch final : public GroupProvider {
public:
 bool add(unsigned source, GroupProvider&, const Catalog::Capability&, std::string&);
 bool capability(const CatalogRow&, std::string&) const;
 bool preflight(const std::vector<CatalogRow>&, std::string&) override;
 bool reserve(const std::vector<CatalogRow>&, std::string&) override;
 bool birth(const CatalogRow&, Generator*, unsigned, const Position&, float, Creature*&, std::string&) override;
 bool bind(const CatalogRow&, Creature*, unsigned, std::string&) override;
 bool release(Creature*, unsigned, std::string&) override;
 // Native kill already disposed the physical family; do not call it twice.
 void retired(Creature*);
private:
 struct Family {GroupProvider* provider; Catalog::Capability capability;};
 struct Owned {GroupProvider* provider; unsigned uid;};
 std::map<unsigned,Family> mFamilies;
 std::map<unsigned,CatalogRow> mRows;
 std::map<Creature*,Owned> mOwned;
 bool mPrepared=false,mReserved=false;
 unsigned familyKey(unsigned source)const;
};
}
