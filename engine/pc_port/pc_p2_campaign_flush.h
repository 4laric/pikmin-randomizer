#pragma once
#include <string>
#include <vector>
#include <utility>
class Generator;
// Preserve the running scene's cache lifecycle and list indices around a SAVE.
// Both successful publication and physical-card failure leave live gameplay
// using its pre-flush cache, while the immutable card retains the new snapshot.
class PcP2CampaignLiveCache {
    std::string image;
    std::vector<std::pair<Generator*,int>> indices;
public:
    PcP2CampaignLiveCache();
    void restore() const;
};

// Flush the current native scene into its existing GeneratorCache bank without
// sunset, stock deposits, actor teardown or a realm switch. Call at a settled
// gameplay boundary. The cache image can be restored if card publication fails.
bool pc_p2_campaign_flush(std::string& reason);
