#pragma once
#include <cstddef>
// Revoke without compacting: an interaction callback may invalidate a slot
// while the actor is iterating this same list. Keep its indexes/count stable.
template<class T, std::size_t N>
void p2ActorForgetSlots(T* (&slots)[N], int count, const T* object) {
    if (!object || count < 0 || count > static_cast<int>(N)) return;
    for (int i = 0; i < count; ++i) if (slots[i] == object) slots[i] = nullptr;
}
