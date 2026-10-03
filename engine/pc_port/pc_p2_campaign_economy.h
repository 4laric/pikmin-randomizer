#pragma once
#include "pc_p2_treasure_catalog.h"
#include <algorithm>
#include <set>

namespace p2economy {
constexpr std::uint64_t Debt = 10000;
enum class Phase { RepayingDebt, TreasureHunt, Complete };
struct Progress {
    std::uint64_t pokos = 0;
    int collected = 0, available = 0;
    std::uint64_t remaining() const { return pokos >= Debt ? 0 : Debt - pokos; }
    bool debt_repaid() const { return pokos >= Debt; }
    bool hoard_complete() const { return available > 0 && collected == available; }
    Phase phase() const {
        return !debt_repaid() ? Phase::RepayingDebt : hoard_complete() ? Phase::Complete : Phase::TreasureHunt;
    }
};
// Reconstruct a view from already accepted provider receipts. This is deliberately
// not a second persistent ledger. Existing provider/card authentication owns state.
class CollectionView {
    const p2treasure::Catalog& catalog;
    std::set<std::string> seen;
    std::uint64_t pokos = 0;
public:
    explicit CollectionView(const p2treasure::Catalog& source) : catalog(source) {}
    bool observe(const std::string& id, int value) {
        const auto* entry = catalog.find(id);
        if (!entry || !entry->unique || entry->classification != p2treasure::Classification::Campaign
            || value != entry->value || !seen.insert(id).second) return false;
        pokos += static_cast<std::uint64_t>(value); return true;
    }
    Progress progress() const { return {pokos,static_cast<int>(seen.size()),catalog.campaign_count()}; }
};
inline std::string ship_summary(bool diamondDelivered, const p2treasure::Catalog* catalog) {
    // #1191 is the sole authenticated ordinary retail provider currently wired.
    // Preview/corpse/AP sidecars never feed this projection. Debt/ending engine
    // transitions remain gated until additional ordinary providers are implemented.
    Progress progress;
    progress.pokos = diamondDelivered ? 180 : 0;
    std::string collection = "Catalog not staged";
    if (catalog) {
        CollectionView view(*catalog);
        if (diamondDelivered) view.observe("dia_a_red",180);
        progress = view.progress();
        collection = "Hoard " + std::to_string(progress.collected) + "/" + std::to_string(progress.available);
    }
    return std::to_string(progress.pokos) + " Pokos | Debt " + std::to_string(progress.remaining()) + " | " + collection;
}
}
