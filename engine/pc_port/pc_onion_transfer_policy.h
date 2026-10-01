#pragma once
#include <algorithm>
#include <cstdint>

namespace pc_onion_transfer {
struct Counts {
    int stock, containerCapacity, squad, squadCapacity, field, fieldLimit;
};
inline int room(int limit, int used) {
    return static_cast<int>(std::max<std::int64_t>(0, std::int64_t(std::max(0, limit)) - std::max(0, used)));
}
// Positive means deposit; negative means withdraw. Invalid selections shrink
// towards zero and never change direction, including an already-overfull field.
inline int clamp(int requested, const Counts& c) {
    if (requested > 0)
        return std::min({requested, std::max(0, c.squad), room(c.containerCapacity, c.stock)});
    if (requested < 0) {
        const std::int64_t wanted = -std::int64_t(requested);
        const std::int64_t allowed = std::min({wanted, std::int64_t(std::max(0, c.stock)),
            std::int64_t(room(c.squadCapacity, c.squad)), std::int64_t(room(c.fieldLimit, c.field))});
        return -static_cast<int>(allowed);
    }
    return 0;
}
}
