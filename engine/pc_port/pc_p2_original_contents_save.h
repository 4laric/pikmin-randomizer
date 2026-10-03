#pragma once
#include "pc_p2_original_resource_contents.h"
namespace p2originalresource {
// Complete immutable outcomes only. Version1 textual codec is bounded to
// 1MiB,4096 source records,two actual child attempts per source. Campaign SHA
// authenticates this envelope; each source retains its distinct catalog SHA.
// No RNG, manager births, consumption or physical graph adoption occurs here.
bool encodeContents(const std::vector<ContentsRecord>&,const std::string& actualCampaignFullSHA,std::string& bytes,std::string& error);
bool decodeContents(const std::string& bytes,const std::string& expectedCampaignFullSHA,std::vector<ContentsRecord>&,std::string& error);
}
