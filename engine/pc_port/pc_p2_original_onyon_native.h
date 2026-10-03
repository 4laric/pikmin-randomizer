#pragma once
#include "pc_p2_original_onyon.h"
#include "Generator.h"
#include <functional>
struct PcOriginalOnyonProgress {std::uint8_t containers=0,boot=0;};
// Install before native generator read/cache preload. progress/onBooted are actual
// P2 PlayData authority callbacks, never AP receipt masks. Clear AFTER disposal.
bool pc_p2_original_onyon_install(const std::vector<p2original::OnyonRecord>&,
 std::function<PcOriginalOnyonProgress()> progress,std::function<void(int)> onBooted,std::string&);
void pc_p2_original_onyon_unload();
void pc_p2_original_onyon_register();
// After use-list resource initialization, before ANY original item birth.
// Requires the complete current typed inventory, including policy-skipped rows.
bool pc_p2_original_onyon_preflight(const std::vector<Generator*>&,std::string&);
bool pc_p2_original_onyon_generator_init(Generator*,bool& handled,std::string&);
bool pc_p2_original_onyon_identity(const Creature*,std::string&);
// Actual source body plus the verified original campaign bootstrap.
bool pc_p2_original_onyon_campaign_owned(const Creature*);
bool pc_p2_original_onyon_booted(const Creature*,bool&);
bool pc_p2_original_onyon_access(const Creature*);
// Source-owned actors exclusively use original boot progress; ordinary actors
// retain the caller's AP permission. AP cannot override an unopened source item.
bool pc_p2_original_onyon_color_access(const Creature*,bool apAllowed);
bool pc_p2_original_onyon_boot(Creature*);
struct GenObjectOriginalOnyon final:GenObject {
 GenObjectOriginalOnyon();
 void doRead(RandomAccessStream&)override;
 void doWrite(RandomAccessStream&)override;
 void ramLoadParameters(RandomAccessStream&)override;
 void ramSaveParameters(RandomAccessStream&)override;
 void updateUseList(Generator*,int)override;
 Creature* birth(BirthInfo&)override;
 unsigned uid=0;
};
