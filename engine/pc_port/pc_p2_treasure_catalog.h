#pragma once
// Source IDs/numeric profiles are staged privately from the GPVE01 #140 audit.
// Catalog membership is metadata; it never grants a receipt or spawns an actor.
#include "netplay/pc_netplay_sha256.h"
#include <cstdint>
#include <fstream>
#include <istream>
#include <sstream>
#include <set>
#include <string>
#include <vector>

namespace p2treasure {
constexpr int RetailCount = 201;
constexpr const char* RetailDigest = "f0f9c1f60953f63b5460037e5bf276193172f526b869f7642b97d44a0704d751";
enum class Classification { Campaign, ModeOnly, Unused };
struct Entry {
    std::string id, kind;
    Classification classification = Classification::Unused;
    int index = 0, dictionary = 0, value = 0, strength = 0, slots = 0, code = 0;
    bool unique = false;
};
inline bool safe_id(const std::string& id) {
    return !id.empty() && id.size() <= 64
        && id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_") == std::string::npos;
}
struct Catalog {
    std::vector<Entry> entries;
    const Entry* find(const std::string& id) const {
        for (const auto& entry : entries) if (entry.id == id) return &entry;
        return nullptr;
    }
    int campaign_count() const {
        int count = 0;
        for (const auto& entry : entries) if (entry.classification == Classification::Campaign && entry.unique) ++count;
        return count;
    }
    // Transactional parser also supports small synthetic catalogs for controls.
    // Production loading below additionally requires the exact full retail digest.
    bool read(std::istream& in) {
        std::string magic; int count;
        if (!(in >> magic >> count) || magic != "P2_TREASURE_CATALOG_1" || count < 1 || count > RetailCount) return false;
        Catalog next; std::set<std::string> ids; std::set<int> dictionaries;
        std::set<std::pair<std::string,int>> indices;
        for (int i = 0; i < count; ++i) {
            Entry entry; std::string category, unique;
            if (!(in >> entry.id >> entry.kind >> category >> entry.index >> entry.dictionary
                >> entry.value >> entry.strength >> entry.slots >> entry.code >> unique)) return false;
            if (!safe_id(entry.id) || (entry.kind != "otakara" && entry.kind != "item")
                || entry.index < 0 || entry.index > 255 || entry.dictionary < 1 || entry.dictionary > RetailCount
                || entry.value < 0 || entry.value > 1000000 || entry.strength < 1 || entry.strength > 1000
                || entry.slots < 1 || entry.slots > 128 || entry.code < 0 || entry.code > 65535
                || (unique != "yes" && unique != "no")) return false;
            if (category == "campaign") entry.classification = Classification::Campaign;
            else if (category == "mode_only") entry.classification = Classification::ModeOnly;
            else if (category == "unused") entry.classification = Classification::Unused;
            else return false;
            entry.unique = unique == "yes";
            if (!ids.insert(entry.id).second || !dictionaries.insert(entry.dictionary).second
                || !indices.insert({entry.kind,entry.index}).second) return false;
            next.entries.push_back(entry);
        }
        if (in >> magic || !in.eof()) return false;
        entries = std::move(next.entries); return true;
    }
    bool load_retail(const char* path) {
        std::ifstream in(path, std::ios::binary); if (!in) return false;
        std::string bytes; char buffer[4096];
        while (in.read(buffer,sizeof(buffer)) || in.gcount()) {
            const auto count = static_cast<std::size_t>(in.gcount());
            if (count > 32768 - bytes.size()) return false;
            bytes.append(buffer,count);
        }
        if (!in.eof()) return false;
        std::uint8_t digest[32]; pc_netplay_sha::sha256(bytes.data(),bytes.size(),digest);
        if (pc_netplay_sha::hex(digest,32) != RetailDigest) return false;
        Catalog next; std::istringstream text(bytes);
        if (!next.read(text) || next.entries.size() != RetailCount || next.campaign_count() != RetailCount) return false;
        entries = std::move(next.entries); return true;
    }
};
}
