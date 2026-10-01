// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_mouth_snapshot_test.cpp
// Reproduces the index-based Stickers traversal (creatureStick.cpp) against a
// linked sticker list and shows that kill-while-iterating skips neighbours
// (Emperor ate 7, killed 4) while snapshot-then-kill kills every one.
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "pc_p2_mouth_snapshot.h"

struct Node {
    int id;
    bool mouth;
    bool dead = false;
    Node* next = nullptr;
};

struct List {
    Node* head = nullptr;
    void unlink(Node* n)
    {
        Node** pp = &head;
        while (*pp && *pp != n) pp = &(*pp)->next;
        if (*pp) *pp = n->next;
        n->next = nullptr;
    }
};

static void kill(List& l, Node* n)
{
    n->dead = true;
    l.unlink(n);
}

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_mouth_snapshot_test: %s\n", what);
        std::_Exit(1);
    }
}

static void build(List& l, std::vector<Node>& pool, int n)
{
    pool.assign(n, Node{});
    l.head = nullptr;
    for (int i = n - 1; i >= 0; --i) {
        pool[i].id = i;
        pool[i].mouth = true;
        pool[i].next = l.head;
        l.head = &pool[i];
    }
}

int main()
{
    for (int n = 1; n <= 9; ++n) {
        // Index-based iteration exactly like Stickers: re-walk from head each step.
        List l;
        std::vector<Node> pool;
        build(l, pool, n);
        int count = n;
        for (int idx = 0; idx < count; ++idx) {
            Node* c = l.head;
            for (int i = 0; i < idx && c; ++i) c = c->next;
            if (!c) break;
            kill(l, c);
            // mCount is refreshed lazily in the engine; emulate the stale bound.
        }
        int killedNaive = 0;
        for (auto& p : pool) killedNaive += p.dead ? 1 : 0;
        if (n >= 2) require(killedNaive < n, "naive iterate-and-kill skips a neighbour");

        build(l, pool, n);
        auto snap = p2mouth::snapshotLinked(l.head, [](Node* x) { return x->next; },
                                            [](Node* x) { return x->mouth; });
        require((int)snap.size() == n, "snapshot sees every mouth sticker");
        for (Node* x : snap) kill(l, x);
        int killed = 0;
        for (auto& p : pool) killed += p.dead ? 1 : 0;
        require(killed == n, "snapshot-then-kill kills every mouth sticker");
        require(l.head == nullptr, "sticker list is empty afterwards");
    }
    // Non-mouth stickers are left alone.
    List l;
    std::vector<Node> pool;
    build(l, pool, 5);
    pool[1].mouth = false;
    pool[3].mouth = false;
    auto snap = p2mouth::snapshotLinked(l.head, [](Node* x) { return x->next; }, [](Node* x) { return x->mouth; });
    require(snap.size() == 3, "predicate filters non-mouth stickers");
    std::printf("PASS p2_mouth_snapshot_test checks=%d\n", gChecks);
    return 0;
}
