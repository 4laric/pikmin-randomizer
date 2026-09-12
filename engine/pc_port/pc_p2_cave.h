#pragma once
#include <string>
void pc_p2_cave_setup();
void pc_p2_cave_tick();
void pc_p2_cave_request();
bool pc_p2_cave_checkpoint(bool confirm);
int pc_p2_cave_floor();
std::string pc_p2_cave_receipt_prefix();
