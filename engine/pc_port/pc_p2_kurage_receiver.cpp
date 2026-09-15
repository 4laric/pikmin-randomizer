#include "pc_p2_kurage_receiver.h"
#include "pc_p2_kurage_ingestion.h"

#include "Creature.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "system.h"

#include <array>
#include <algorithm>
#include <cmath>
#include <cstdio>

namespace {
struct Entry {
    enum class Phase { MouthTravel, Stomach };
    Piki* piki = nullptr;
    Creature* owner = nullptr;
    CollPart* mouth = nullptr;
    Vector3f capturedScale;
    P2KurageIngestion ingestion;
    unsigned long long generation = 0;
    Phase phase = Phase::Stomach;
};
Creature* sOwner = nullptr;
CollPart* sMouth = nullptr;
unsigned long long sGeneration = 1;
std::array<Entry, 10> sEntries;

bool registered(const Piki* piki)
{
    for (const Entry& entry : sEntries) if (entry.piki == piki) return true;
    return false;
}

void dispose(Entry e, bool kill, bool restoreDetached)
{
    if (!e.piki) return;
    Piki* piki = e.piki;
    if (registered(piki)) return; // A callback established a newer reservation.
    const Vector3f capturedScale = e.capturedScale;
    const bool owned = piki->isAlive() && piki->getStickObject() == e.owner
        && piki->getStickPart() == e.mouth;
    // A live Piki that was externally detached has no newer owner to protect.
    // Restore its scale before dropping the entry; a replacement attachment is
    // deliberately excluded by isStickTo().  Piki invalidation clears entries
    // before destruction, and generation prevents stale reset-side authority.
    const bool externallyDetached = piki->isAlive() && !piki->isStickTo()
        && restoreDetached;
    // Clear the table before touching engine state: callbacks can re-enter the
    // receiver and must observe that this slot is already revoked.
    if (!owned && !externallyDetached) return;
    // The source shrinks only while the stomach link is owned.  Restore the
    // precise capture scale before releasing or killing that owned Piki.
    piki->mSRT.s = capturedScale;
    piki->mVelocity.set(0.0f, 0.0f, 0.0f);
    piki->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
    if (!owned) return;
    piki->endStickObject();
    // endStickObject is an engine callback and may rebind or kill the Piki.
    // Never apply the old disposition to a changed link.
    if (registered(piki) || !piki->isAlive() || piki->isStickTo()) return;
    if (kill) {
        piki->setEraseKill();
        piki->kill(false);
        std::printf("P2_KURAGE_RECEIVER_KILL owner=%p piki=%p alive_after=%d\n",
                    (void*)e.owner, (void*)piki, int(piki->isAlive()));
        std::fflush(stdout);
    } else {
        if (piki->mFSM) piki->mFSM->transit(piki, PIKISTATE_Normal);
        piki->changeMode(PikiMode::FreeMode, naviMgr ? naviMgr->getNavi() : nullptr);
    }
}

void release(int i, bool kill)
{
    const Entry entry = sEntries[i];
    sEntries[i] = {};
    dispose(entry, kill, entry.generation == sGeneration);
}

bool controls(const Entry& e)
{
    if (!e.piki || !sOwner || !sMouth || e.generation != sGeneration
        || e.owner != sOwner || e.mouth != sMouth || !e.piki->isAlive()) return false;
    return e.phase == Entry::Phase::MouthTravel ? !e.piki->isStickTo()
        : e.piki->getStickObject() == e.owner && e.piki->getStickPart() == e.mouth;
}

bool reserve(Piki* piki, Entry::Phase phase)
{
    if (!sOwner || !sMouth || !piki || !piki->isAlive() || piki->isStickTo()
        || !piki->mayIstick()) return false;
    for (const Entry& e : sEntries) if (e.piki == piki) return false;
    for (Entry& e : sEntries) {
        if (e.piki) continue;
        if (!e.ingestion.admit(false, false, true)) return false;
        e.piki = piki;
        e.owner = sOwner;
        e.mouth = sMouth;
        e.capturedScale = piki->mSRT.s;
        e.generation = sGeneration;
        e.phase = phase;
        std::printf("P2_KURAGE_RECEIVER_HIT owner=%p piki=%p phase=%s alive=%d stick=%d\n",
                    (void*)sOwner, (void*)piki,
                    phase == Entry::Phase::Stomach ? "stomach" : "mouth",
                    int(piki->isAlive()), int(piki->isStickTo()));
        std::fflush(stdout);
        return true;
    }
    return false;
}

bool enterStomach(Entry& e)
{
    Piki* piki = e.piki;
    if (!piki || !piki->isAlive() || piki->isStickTo() || !piki->mayIstick()
        || e.generation != sGeneration || e.owner != sOwner || e.mouth != sMouth)
        return false;
    const bool stickBefore = piki->isStickTo();
    piki->startStickObject(e.owner, e.mouth, -1, 0.0f);
    const bool linked = piki->getStickObject() == e.owner && piki->getStickPart() == e.mouth;
    if (!linked || !e.ingestion.capture()) {
        if (linked && piki->isAlive()) piki->endStickObject();
        return false;
    }
    piki->mVelocity.set(0.0f, 0.0f, 0.0f);
    piki->mTargetVelocity.set(0.0f, 0.0f, 0.0f);
    e.phase = Entry::Phase::Stomach;
    std::printf("P2_KURAGE_RECEIVER_ATTACH owner=%p piki=%p stick_before=%d stick_after=%d alive=%d scale=%.2f\n",
                (void*)e.owner, (void*)piki, int(stickBefore), int(piki->isStickTo()),
                int(piki->isAlive()), piki->mSRT.s.x);
    std::fflush(stdout);
    return true;
}
}

void pc_p2_kurage_receiver_reset()
{
    // Revoke the entire old batch before callbacks; callbacks may set up a new
    // receiver. Never sweep those new entries as part of this reset.
    const auto entries = sEntries;
    sEntries = {};
    sOwner = nullptr;
    sMouth = nullptr;
    ++sGeneration;
    for (const Entry& entry : entries) dispose(entry, false, true);
}

bool pc_p2_kurage_receiver_setup(Creature* owner, CollPart* mouth)
{
    pc_p2_kurage_receiver_reset();
    if (!owner || !mouth) return false;
    sOwner = owner;
    sMouth = mouth;
    return true;
}

bool pc_p2_kurage_receiver_capture(Piki* piki)
{
    if (!reserve(piki, Entry::Phase::Stomach)) return false;
    Entry& e = *std::find_if(sEntries.begin(), sEntries.end(), [piki](const Entry& x) { return x.piki == piki; });
    if (enterStomach(e)) return true;
    e = {};
    return false;
}

bool pc_p2_kurage_receiver_admit(Piki* piki)
{
    // Kurage passes a null tube collpart and `suck` as the stomach part.  This
    // adapter preserves its mouth-only approach; there is no string/tube leg.
    return reserve(piki, Entry::Phase::MouthTravel);
}

bool pc_p2_kurage_receiver_controls(const Piki* piki)
{
    if (!piki || !sOwner || !sMouth) return false;
    for (const Entry& e : sEntries) {
        if (e.piki == piki && controls(e)) return true;
    }
    return false;
}

int pc_p2_kurage_receiver_scan_admit(float verticalOffset, float attackRadius, int maxAdmissions, bool admitEligible)
{
    if (!sOwner || !sMouth || !pikiMgr || !std::isfinite(verticalOffset)
        || !std::isfinite(attackRadius) || verticalOffset < 0.0f || attackRadius <= 0.0f
        || maxAdmissions <= 0) return 0;
    if (!admitEligible) return 0;
    const Vector3f ownerPos = sOwner->mSRT.t;
    const float minY = ownerPos.y - verticalOffset - 50.0f;
    const float maxRange = attackRadius * attackRadius;
    int admitted = 0;
    ObjectMgr* manager = static_cast<ObjectMgr*>(pikiMgr);
    for (int it = manager->getFirst(); !manager->isDone(it) && admitted < maxAdmissions;
         it = manager->getNext(it)) {
        Piki* piki = static_cast<Piki*>(manager->getCreature(it));
        // P1's PikiMgr is typed, so every entry is a Pikmin equivalent.  The
        // source's mSticker exclusion maps to its current stick object.
        if (!piki || !piki->isAlive() || piki->getStickObject() == sOwner || !piki->mayIstick()) continue;
        const Vector3f pos = piki->mSRT.t;
        const float dx = pos.x - ownerPos.x;
        const float dz = pos.z - ownerPos.z;
        if (pos.y <= minY || pos.y >= ownerPos.y || dx * dx + dz * dz >= maxRange) continue;
        if (pc_p2_kurage_receiver_admit(piki)) ++admitted;
    }
    return admitted;
}

void pc_p2_kurage_receiver_update(float delta, bool ownerAlive, bool ownerHasHealth, bool bittered)
{
    if (!std::isfinite(delta) || delta < 0.0f) return;
    for (int i = 0; i < static_cast<int>(sEntries.size()); ++i) {
        Entry& e = sEntries[i];
        if (!e.piki) continue;
        const bool owned = controls(e);
        if (!ownerAlive || !sOwner || !owned) { release(i, false); continue; }
        Piki* piki = e.piki;
        if (e.phase == Entry::Phase::MouthTravel) {
            Vector3f mouthTarget = sMouth->mCentre;
            mouthTarget.y -= sMouth->mRadius;
            Vector3f diff = mouthTarget - piki->mSRT.t;
            const float length = std::sqrt(diff.x * diff.x + diff.y * diff.y + diff.z * diff.z);
            if (length < 10.0f) {
                if (!enterStomach(e)) release(i, false);
                continue;
            }
            const float step = delta * 600.0f;
            if (step > 0.0f) {
                const Vector3f suctionVelocity(diff.x / length * 600.0f, diff.y / length * 600.0f,
                    diff.z / length * 600.0f);
                // Creature::moveVelocity steers mVelocity toward mTargetVelocity
                // before movement.  Own both while Piki::doAI is suppressed.
                piki->mVelocity = suctionVelocity;
                piki->mTargetVelocity = suctionVelocity;
            }
            continue;
        }
        const bool stomachLinked = piki->getStickObject() == e.owner && piki->getStickPart() == e.mouth;
        if (!stomachLinked) { release(i, false); continue; }
        // Admission is currently the private receiver capture hook, an
        // approximation of source stomach entry.  From that point, retain the
        // retail 16 s stomach interval and separate 0.5 s shrink interval.
        const auto event = e.ingestion.update(delta, ownerAlive, ownerHasHealth, bittered, stomachLinked);
        if (event == P2KurageIngestion::Event::Killed) { release(i, true); continue; }
        if (event == P2KurageIngestion::Event::Released || event == P2KurageIngestion::Event::Ejected) { release(i, false); continue; }
        if (piki && piki->isAlive() && piki->getStickObject() == e.owner
            && piki->getStickPart() == e.mouth) {
            const float scale = e.ingestion.scale();
            piki->mSRT.s.set(e.capturedScale.x * scale, e.capturedScale.y * scale,
                e.capturedScale.z * scale);
        }
    }
}

void pc_p2_kurage_receiver_release_all()
{
    const auto entries = sEntries;
    sEntries = {};
    for (const Entry& entry : entries)
        dispose(entry, false, entry.generation == sGeneration);
}

void pc_p2_kurage_receiver_owner_invalidated(Creature* owner)
{
    if (!owner || owner != sOwner) return;
    pc_p2_kurage_receiver_reset();
}

void pc_p2_kurage_receiver_piki_invalidated(Piki* piki)
{
    if (!piki) return;
    // Creature::kill invokes this before its own stick cleanup.  Releasing
    // here would transition a dying Piki back into FreeMode; revocation must
    // only drop receiver authority and let the normal death path continue.
    for (Entry& entry : sEntries)
        if (entry.piki == piki) { entry = {}; return; }
}

int pc_p2_kurage_receiver_count()
{
    int count = 0;
    for (const Entry& e : sEntries) if (e.piki) ++count;
    return count;
}

int pc_p2_kurage_receiver_stomach_count()
{
    int count = 0;
    for (const Entry& e : sEntries)
        if (e.piki && e.phase == Entry::Phase::Stomach) ++count;
    return count;
}
