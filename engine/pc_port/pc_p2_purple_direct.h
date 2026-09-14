#pragma once

class CollPart;
class Creature;
class Piki;
class BTeki;

struct PcP2PurpleDirectHit {
    enum Family { None, RedDwarf, AdultBulborb } family = None;
    bool handled = false;
    bool accepted = false;
    bool damageApplied = false;
};

void pc_p2_purple_direct_reset();
void pc_p2_purple_direct_setup();
void pc_p2_purple_direct_forget(BTeki*);
bool pc_p2_purple_direct_enabled();
bool pc_p2_purple_direct_adult_registered(const BTeki*);
PcP2PurpleDirectHit pc_p2_purple_direct_begin(Piki*, Creature*, CollPart*);
void pc_p2_purple_direct_finish(Piki*, Creature*, CollPart*, PcP2PurpleDirectHit&);
