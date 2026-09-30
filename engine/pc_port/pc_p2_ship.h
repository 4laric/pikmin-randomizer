#pragma once
class Piki;
struct PikiHeadItem;
class Navi;
bool pc_p2_ship_special(const Piki*);
bool pc_p2_ship_deposit(Piki*);
bool pc_p2_ship_store_sprout(PikiHeadItem*);
Piki* pc_p2_ship_withdraw(Navi*, int species);
void pc_p2_ship_tick(Navi*, bool active);
