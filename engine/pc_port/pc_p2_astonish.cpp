// P2 InteractAstonish receiver (issue #992). See pc_p2_astonish.h.
#include "pc_p2_astonish.h"
#include "pc_p2_tamago_policy.h"
#include "Piki.h"
#include "PikiState.h"
#include <cstdio>
#include <map>

namespace {
std::map<const Piki*, unsigned> sPending; // Pikmin whose next Panic entry is an astonish
std::map<const Piki*, unsigned> sActive;  // astonished, Panic state entered
std::map<const Piki*, unsigned> sIds;
unsigned sNextId = 1, sStarted = 0, sEnded = 0;

unsigned idOf(const Piki* p)
{
    auto it = sIds.find(p);
    if (it != sIds.end()) return it->second;
    return sIds[p] = sNextId++;
}
} // namespace

bool pc_p2_astonish_request(Piki* piki, Creature* source, unsigned token, const char* who)
{
    (void)source;
    if (!piki) return false;
    const bool accepted = p2tamagopolicy::astonishAccepts(piki->isAlive(), piki->mP2Purple, piki->getState());
    if (!accepted) return false;
    sPending[piki] = token;
    piki->mFSM->transit(piki, PIKISTATE_Panic);
    // PikiPanicState::init consumes the pending mark; if the transit was refused the
    // mark is cleared so a later gas panic is not mistaken for an astonish.
    if (piki->getState() != PIKISTATE_Panic) {
        sPending.erase(piki);
        return false;
    }
    ++sStarted;
    std::printf("P2_ASTONISH_START who=%s generator=%u piki=%u state=panic_astonish harm=none\n", who ? who : "?",
                token, idOf(piki));
    std::fflush(stdout);
    return true;
}

bool pc_p2_astonish_pending(const Piki* p)
{
    if (sPending.empty() || !p) return false;
    auto it = sPending.find(p);
    if (it == sPending.end()) return false;
    sActive[p] = it->second;
    sPending.erase(it);
    return true;
}

void pc_p2_astonish_end(Piki* p, bool timedOut)
{
    if (sActive.empty() || !p) return;
    auto it = sActive.find(p);
    if (it == sActive.end()) return;
    ++sEnded;
    std::printf("P2_ASTONISH_END generator=%u piki=%u reason=%s state=%d\n", it->second, idOf(p),
                timedOut ? "timeout_walk" : "state_change", p->getState());
    std::fflush(stdout);
    sActive.erase(it);
}

void pc_p2_astonish_reset()
{
    sPending.clear();
    sActive.clear();
    sIds.clear();
    sNextId = 1;
}

unsigned pc_p2_astonish_started() { return sStarted; }
unsigned pc_p2_astonish_ended() { return sEnded; }
