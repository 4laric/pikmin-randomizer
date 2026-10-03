#pragma once
#include "pc_p2_campaign_economy.h"
#include <array>
#include <sstream>

// #1232: native-card-owned unique source receipts. No file persistence lives
// here: the campaign envelope owner commits/restores this record with the card.
// Production callers must supply a catalog verified by load_retail, bind source
// to the selected placement digest, and restore only after the enclosing native
// card authenticates. catalog_valid checks structure; this codec authenticates
// neither a catalog nor a card and must not be used as a standalone save file.
namespace p2treasurestate {
constexpr std::size_t BitmapBytes = 26;
constexpr std::size_t MaxRecordBytes = 188;
struct Snapshot {
    std::string source;
    std::array<std::uint8_t,BitmapBytes> bits{};
};
enum class Credit { Invalid = -1, Duplicate = 0, Added = 1 };
inline bool digest(const std::string& value) {
    return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string::npos;
}
inline bool catalog_valid(const p2treasure::Catalog& catalog) {
    if (catalog.entries.size() != p2treasure::RetailCount || catalog.campaign_count() != p2treasure::RetailCount) return false;
    std::array<bool,p2treasure::RetailCount> slots{};
    std::set<std::string> ids;
    for (const auto& entry : catalog.entries) {
        if (entry.dictionary < 1 || entry.dictionary > p2treasure::RetailCount
            || slots[entry.dictionary-1] || !p2treasure::safe_id(entry.id)
            || !ids.insert(entry.id).second || entry.value < 0 || entry.value > 1000000) return false;
        slots[entry.dictionary-1] = true;
    }
    return true;
}
inline bool snapshot_valid(const Snapshot& snapshot) {
    // Dictionary201 uses bit0 of byte25; the seven spare bits cannot hide state.
    return digest(snapshot.source) && (snapshot.bits.back() & 0xfe) == 0;
}
inline bool contains(const Snapshot& snapshot, int dictionary) {
    return dictionary >= 1 && dictionary <= p2treasure::RetailCount
        && (snapshot.bits[(dictionary-1)/8] & (1u << ((dictionary-1)%8))) != 0;
}
inline std::string encode(const Snapshot& snapshot) {
    if (!snapshot_valid(snapshot)) return {};
    static const char* hex = "0123456789abcdef";
    std::string bitmap;
    for (auto value : snapshot.bits) {bitmap += hex[value >> 4]; bitmap += hex[value & 15];}
    return std::string("P2TR1 ") + p2treasure::RetailDigest + " " + snapshot.source + " " + bitmap;
}
inline bool decode(const std::string& record, const p2treasure::Catalog& catalog,
                   const std::string& expectedSource, Snapshot& out) {
    if (record.size() != MaxRecordBytes || !catalog_valid(catalog) || !digest(expectedSource)) return false;
    std::istringstream in(record); std::string magic, catalogDigest, bitmap, extra; Snapshot next;
    if (!(in >> magic >> catalogDigest >> next.source >> bitmap) || in >> extra
        || magic != "P2TR1" || catalogDigest != p2treasure::RetailDigest
        || next.source != expectedSource || bitmap.size() != BitmapBytes*2
        || bitmap.find_first_not_of("0123456789abcdef") != std::string::npos) return false;
    auto nibble = [](char value) {return value <= '9' ? value-'0' : value-'a'+10;};
    for (std::size_t i=0; i<BitmapBytes; ++i) next.bits[i]=static_cast<std::uint8_t>((nibble(bitmap[i*2])<<4)|nibble(bitmap[i*2+1]));
    if (!snapshot_valid(next) || encode(next) != record) return false;
    out = std::move(next); return true;
}
class State {
    Snapshot current;
public:
    bool active() const {return !current.source.empty();}
    const std::string& source() const {return current.source;}
    Snapshot snapshot() const {return current;}
    void reset() {current = Snapshot{};}
    bool bind(const std::string& source) {
        if (!digest(source) || (active() && current.source != source)) return false;
        current.source = source; return true;
    }
    bool restore(const Snapshot& snapshot, const p2treasure::Catalog& catalog, const std::string& expectedSource) {
        if (!catalog_valid(catalog) || !snapshot_valid(snapshot) || snapshot.source != expectedSource) return false;
        current = snapshot; return true;
    }
    Credit credit(const p2treasure::Catalog& catalog, const std::string& id, int value) {
        if (!active() || !catalog_valid(catalog)) return Credit::Invalid;
        const auto* entry = catalog.find(id);
        if (!entry || value != entry->value) return Credit::Invalid;
        if (contains(current,entry->dictionary)) return Credit::Duplicate;
        current.bits[(entry->dictionary-1)/8] |= 1u << ((entry->dictionary-1)%8);
        return Credit::Added;
    }
    bool seen(const p2treasure::Catalog& catalog, const std::string& id) const {
        const auto* entry = catalog.find(id);
        return active() && entry && contains(current,entry->dictionary);
    }
    p2economy::Progress progress(const p2treasure::Catalog& catalog, bool whiteDiamondDelivered) const {
        p2economy::CollectionView view(catalog);
        if (catalog_valid(catalog)) {
            for (const auto& entry : catalog.entries)
                if (active() && contains(current,entry.dictionary)) view.observe(entry.id,entry.value);
            // Union by source ID: preserve White's existing card authority and
            // never add the same diamond twice, even if a general source uses it.
            if (whiteDiamondDelivered) view.observe("dia_a_red",180);
        }
        return view.progress();
    }
};
inline State state;
}
