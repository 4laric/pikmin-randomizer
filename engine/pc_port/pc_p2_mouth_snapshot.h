// Snapshot-then-act helper for Chappy-family mouth contents (#289 follow-up).
//
// The engine's Stickers traversable is index based (Stickers::getCreature walks
// mStickListHead by index). Killing a Pikmin unlinks it from the sticker list,
// so `for each sticker: stimulate(InteractKill)` skips the element that slides
// into the freed index: an Emperor that ate 7 Pikmin killed 4 and left 3 stuck
// (hidden) in its mouth, still counted in the field. Collect the mouth Pikmin
// first (a linked-list walk with no mutation), then apply the kill.
#pragma once

#include <vector>

namespace p2mouth {

// Walks a singly linked sticker list starting at `head` (next(node) -> node)
// and returns every node accepted by `pred`, before any of them is mutated.
template <class Node, class NextFn, class PredFn>
std::vector<Node*> snapshotLinked(Node* head, NextFn next, PredFn pred)
{
    std::vector<Node*> out;
    for (Node* n = head; n; n = next(n)) {
        if (pred(n)) out.push_back(n);
    }
    return out;
}

} // namespace p2mouth
