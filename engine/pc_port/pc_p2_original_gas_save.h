#pragma once
#include "pc_p2_original_gas_native.h"
namespace p2original { namespace gas {
// Bounded typed checkpoint payload. The campaign checkpoint owns persistence.
// Neither function touches native bodies, RNG, counters or linked structures.
bool encodeSnapshot(const Snapshot&,std::string& bytes,std::string& error);
bool decodeSnapshot(const std::string& bytes,Snapshot&,std::string& error);
} }
