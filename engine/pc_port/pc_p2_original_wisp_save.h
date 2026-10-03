#pragma once
#include "pc_p2_original_wisp_snapshot.h"
namespace p2original { namespace wisp {
// Pure bounded payload for the campaign SAVE owner. The envelope campaign SHA
// is distinct from the preserved source catalog SHA. Source bank context must
// match the saved motion. Native catalog/graph preflight remains mandatory.
bool encodeSnapshot(const Snapshot&,const std::string& expectedCampaign,const Initial&,int motionDuration,const std::vector<Key>& motionKeys,std::string& bytes,std::string& error);
bool decodeSnapshot(const std::string& bytes,const std::string& expectedCampaign,const Initial&,int motionDuration,const std::vector<Key>& motionKeys,Snapshot&,std::string& error);
} }
