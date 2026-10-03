#pragma once
#include "pc_p2_original_resource_state.h"
namespace p2originalresource {
// Pure optional campaign-card payload. Full campaign SHA is checked separately
// from each original generator catalog SHA. Prospective actual born-child graph
// must be validated before decode; physical actors adopt in the owner transaction.
bool encodeResources(const ResourceSnapshot&,const std::string& campaignSha,const EggContents&,std::string& bytes,std::string& error);
bool decodeResources(const std::string& bytes,const std::string& expectedCampaignSha,const EggContents& prospective,ResourceSnapshot&,std::string& error);
}
