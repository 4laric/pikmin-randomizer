#include "pc_p2_proxy.h"
#include "pc_p2_campaign_policy.h"
#include "pc_randomizer.h"
#include "pc_randomizer_p2_roster.h"
#include "teki.h"
#include <cstdio>
#include <fstream>

// Latched once per reset, not once per process (#871 D4): stage teardown
// (pc_p2_reset_all_teki -> pc_p2_batch2_reset -> pc_p2_proxy_reset) clears
// this so the next session re-reads. Per-generator spawn queries only read
// the latch and never touch the disk.
static p2proxy::Table sProxyTable;
static bool sProxyTableLoaded = false;

void pc_p2_proxy_reset() {
    sProxyTable = p2proxy::Table();
    sProxyTableLoaded = false;
}

const p2proxy::Table& pc_p2_proxy_table() {
    if (!sProxyTableLoaded) {
        sProxyTableLoaded = true;
        std::ifstream in("p2-proxy-campaign.txt");
        if (!in) {
            sProxyTable.valid = false;
            sProxyTable.error.clear();
            sProxyTable.rows.clear();
        } else {
            sProxyTable = p2proxy::parse(in, randomizerP2IsBindable, TEKI_TypeCount);
            if (sProxyTable.valid) {
                // D2: static-host sources are untouchable by the visual path.
                // Drop those rows here (host selection already ignores them
                // via hasStaticHost in pc_randomizer.cpp); the rest stays valid.
                p2proxy::Table filtered =
                    p2proxy::withoutStaticSources(sProxyTable, p2campaign::hasStaticHost);
                for (std::vector<p2proxy::Row>::size_type i = 0; i < sProxyTable.rows.size(); ++i) {
                    if (!p2proxy::bySource(filtered, sProxyTable.rows[i].source))
                        std::printf("P2_SETUP_SKIP proxy static_source source=%u species=%s\n",
                                    sProxyTable.rows[i].source, sProxyTable.rows[i].species.c_str());
                }
                sProxyTable = filtered;
                std::printf("P2_PROXY_TABLE rows=%u\n", (unsigned)sProxyTable.rows.size());
            } else {
                std::printf("P2_SETUP_SKIP proxy table_invalid %s\n", sProxyTable.error.c_str());
            }
        }
    }
    return sProxyTable;
}

int pc_p2_proxy_host(unsigned source) {
    // Finding 4: without the tier handshake a stray p2-proxy-campaign.txt
    // must not affect a non-tier seed; the proxy family binds nothing.
    if (!pc_randomizer_p2_proxy_tier()) return -1;
    const p2proxy::Table& table = pc_p2_proxy_table();
    if (!table.valid) return -1;
    const p2proxy::Row* row = p2proxy::bySource(table, source);
    return row ? row->host : -1;
}
