#pragma once
#include "pc_p2_proxy_table.h"

// Engine-linked proxy table loader (#871). Reads p2-proxy-campaign.txt from
// the current directory once per reset (see pc_p2_proxy_reset); per-generator
// spawn queries hit the latched copy and never re-read.
const p2proxy::Table& pc_p2_proxy_table();
int pc_p2_proxy_host(unsigned source);
// Clears the latched table so the next pc_p2_proxy_table() call re-reads.
// Called from pc_p2_batch2_reset (reached via pc_p2_reset_all_teki at stage
// teardown and via TekiMgr::reset); never called per spawn.
void pc_p2_proxy_reset();
