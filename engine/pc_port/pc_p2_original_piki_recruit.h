#pragma once
#include <string>
class Piki;
// Startup owns admission of this distinct campaign/catalog pair. Both must
// match the actual installed authorities; never synthesize one from the other.
bool pc_p2_original_piki_recruit_bind(const std::string& campaign,
    const std::string& catalog,std::string& error);
void pc_p2_original_piki_recruit_unbind() noexcept;
// Call on the native game thread. Ordinary unlabelled P1 bodies are inert.
// Source bodies also require native callable/captain eligibility from the
// actual whistle or contact path. This is not an AI/state-machine replacement.
bool pc_p2_original_piki_recruit_allowed(Piki*,unsigned captain,bool movieActive,
    bool nativeEligible,std::string& error);
bool pc_p2_original_piki_recruit_accepted(Piki*,unsigned captain,bool movieActive,
    bool nativeEligible,std::string& error);

// Contact's legacy player ID must not override an authenticated story captain
// split. Ordinary P1 and versus retain the original player-ID gate exactly.
bool pc_p2_original_piki_contact_owner_allowed(Piki*,int playerId,unsigned captain,
    bool versus,std::string& error);

// Read-only authority check for original-only captain lifecycle hooks.
bool pc_p2_original_piki_recruit_pair_ready() noexcept;
