#pragma once
#include "pc_p2_original_egg_snapshot.h"
namespace p2original { namespace egg {
// Pure prospective payload; the native owner supplies the authoritative context.
bool encodeSnapshot(const Snapshot&,const std::string& campaignFullSHA,const SnapshotContext&,std::string& bytes,std::string& error);
bool decodeSnapshot(const std::string& bytes,const std::string& expectedCampaignFullSHA,const SnapshotContext&,Snapshot&,std::string& error);
} }
