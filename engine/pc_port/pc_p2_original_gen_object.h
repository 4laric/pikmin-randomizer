#pragma once
#include "Generator.h"
#include "pc_p2_original_group.h"
// A native factory/cache object, never a P1 teki personality or AP slot.
// Only POD source state and a transient owner are retained; full species fields
// and float placement authority remain in the immutable original catalog.
struct GenObjectOriginalEnemy final:GenObject {
 GenObjectOriginalEnemy();
 void doRead(RandomAccessStream&) override;
 void doWrite(RandomAccessStream&) override;
 void ramLoadParameters(RandomAccessStream&) override;
 void ramSaveParameters(RandomAccessStream&) override;
 Creature* birth(BirthInfo&) override;
 p2original::GeneratorState mState;
 Generator* mOwner=nullptr;
};
void pc_p2_original_gen_object_register();
// Called for the complete original generator inventory before course install.
// Literal metadata must come from the current authoritative source manifest,
// including cached members. Failed calls leave output/native fields unchanged.
bool pc_p2_original_gen_object_collect(Generator*,const p2original::GeneratorState& literal,p2original::GroupBinding& out,std::string& error);
