#include "pc_p2_kurage_receiver.h"
#include "pc_p2_kurage_ingestion.h"
#include "pc_p2_kurage_suction_policy.h"
#include "pc_p2_captain.h"

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
// Multi-owner table (wave 3 flyers): every bound Kurage registers its own
// mouth part so several Jellyfloats can hold Pikmin at once. sOwner/sMouth
// remain the "primary" owner that the legacy single-owner API (arena, staged
// OniKurage, fixtures) addresses; the campaign adapters use the *_for API.
struct OwnerSlot {
    Creature* owner = nullptr;
    CollPart* mouth = nullptr;
    // Campaign OWN Jellyfloat (#960): the mouth part is the source `suck` part on
    // the Proom joint, any standing Pikmin under the bell is takeable (source
    // suckPikmin has no mayIstick gate) and is pulled to the joint, not to the
    // bottom of a sphere at the body origin.
    bool own = false;
    float bodyCentreOffsetY = 0.0f; // log only: body origin to body centre
};
constexpr int kMaxOwners = 64; // a saturated smoke seed binds ~25 Jellyfloats
std::array<OwnerSlot, kMaxOwners> sOwners;
Creature* sOwner = nullptr;
CollPart* sMouth = nullptr;
unsigned long long sGeneration = 1;
// 10 held Pikmin per Jellyfloat (ip11 maxSuckPiki) for up to kMaxOwners bodies.
std::array<Entry, 10 * kMaxOwners> sEntries;

const OwnerSlot* ownerSlot(const Creature* owner)
{
    if (!owner) return nullptr;
    for (const OwnerSlot& o : sOwners) if (o.owner == owner) return &o;
    return nullptr;
}

bool ownerIsOwn(const Creature* owner)
{
    const OwnerSlot* o = ownerSlot(owner);
    return o && o->own;
}

// Refusal diagnostics: the first few per process, so a run log says why a
// Pikmin under a hovering body was not taken (#960: the small Jellyfloat
// "just hovering").
void refuse(const char* reason)
{
    static int logged = 0;
    if (logged >= 8) return;
    ++logged;
    std::printf("P2_KURAGE_RECEIVER_REFUSE reason=%s\n", reason);
    std::fflush(stdout);
}

// Pikmin the receiver may take. Campaign OWN owners follow the source
// (every live Pikmin not stuck to the body, minus unsafe P1 states); the other
// owners keep the original mayIstick gate.
bool pikiEligible(const Creature* owner, Piki* piki)
{
    if (!piki) return false;
    if (ownerIsOwn(owner))
        return p2kuragesuck::pikiSuckable(piki->isAlive(), piki->isStickTo(), piki->getState(), piki->mayIstick());
    return piki->isAlive() && !piki->isStickTo() && piki->mayIstick() && piki->getState() != PIKISTATE_Flying;
}

bool ownerRegistered(const Creature* owner, const CollPart* mouth)
{
    if (!owner || !mouth) return false;
    for (const OwnerSlot& o : sOwners) if (o.owner == owner && o.mouth == mouth) return true;
    return false;
}

int ownerEntryCount(const Creature* owner)
{
    int n = 0;
    for (const Entry& e : sEntries) if (e.piki && e.owner == owner) ++n;
    return n;
}

bool registered(const Piki* piki)
{
    for (const Entry& entry : sEntries) if (entry.piki == piki) return true;
    return false;
}

void dispose(Entry e, bool kill, bool restoreDetached)
{
    if (!e.piki) return;
    Piki* piki = e.piki;
    // Revoke squad authority before detach/AI callbacks can capture again. A
    // stale epoch means a callback already revoked and recaptured the actor
    // under a newer tick: preserve that replacement and touch nothing
    // (codex/p2-lane12-review c29ec8398/b4ac39825, #130).
    if (!pc_p2_captain::release_captive_free(e.generation, e.piki)) return;
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
    if (!e.piki || !ownerRegistered(e.owner, e.mouth) || e.generation != sGeneration
        || !pc_p2_captain::is_captive_for(e.generation, e.piki)
        || !e.piki->isAlive()) return false;
    return e.phase == Entry::Phase::MouthTravel ? !e.piki->isStickTo()
        : e.piki->getStickObject() == e.owner && e.piki->getStickPart() == e.mouth;
}

bool reserve(Piki* piki, Entry::Phase phase, Creature* owner, CollPart* mouth)
{
    if (!ownerRegistered(owner, mouth) || !piki) return false;
    // A thrown Pikmin (PikiFlyingState) still reads its captain (mNavi, flower
    // glide) every tick; the captain adapter clears it on capture, so a Pikmin
    // sucked mid-throw crashed the state. Pikmin that are airborne from a
    // throw land (or latch onto the body) first (pikiEligible refuses them).
    if (!pikiEligible(owner, piki)) { refuse("piki_not_eligible"); return false; }
    for (const Entry& e : sEntries) if (e.piki == piki) return false;
    if (ownerEntryCount(owner) >= 10) return false; // ip11 per body
    for (Entry& e : sEntries) {
        if (e.piki) continue;
        // Bind the squad capture to this receiver generation tick first: the
        // captain adapter abandons the formation action, then clears squad
        // ownership. A refused capture (already captive, dead actor) refuses
        // admission. Requires the live captain binding (setup_from_navi_mgr).
        if (!pc_p2_captain::capture_actor(sGeneration, piki)) { refuse("captain_seam_refused"); return false; }
        if (!e.ingestion.admit(false, false, true)) {
            pc_p2_captain::release_actor(sGeneration, piki, P2CaptainInvalid);
            return false;
        }
        e.piki = piki;
        e.owner = owner;
        e.mouth = mouth;
        e.capturedScale = piki->mSRT.s;
        e.generation = sGeneration;
        e.phase = phase;
        std::printf("P2_KURAGE_RECEIVER_HIT owner=%p piki=%p phase=%s alive=%d stick=%d\n",
                    (void*)owner, (void*)piki,
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
    if (!piki || !piki->isAlive() || piki->isStickTo() || !pikiEligible(e.owner, piki)
        || e.generation != sGeneration || !ownerRegistered(e.owner, e.mouth))
        return false;
    const bool stickBefore = piki->isStickTo();
    piki->startStickObject(e.owner, e.mouth, -1, 0.0f);
    if (ownerIsOwn(e.owner) && piki->getStickObject() == e.owner && piki->getStickPart() == e.mouth) {
        // Hold the Pikmin inside the stomach sphere instead of on its surface in
        // the direction it arrived from (below the bell). The mouth part keeps an
        // identity joint matrix, so the attach position is in world axes relative
        // to the part centre. A golden-angle ring keeps ten of them apart.
        int index = 0;
        for (const Entry& other : sEntries)
            if (other.piki && &other != &e && other.owner == e.owner && other.phase == Entry::Phase::Stomach) ++index;
        const p2kuragesuck::HoldOffset hold = p2kuragesuck::holdOffset(index, e.mouth->mRadius);
        piki->mAttachPosition.set(hold.x, hold.y, hold.z);
        const OwnerSlot* slot = ownerSlot(e.owner);
        const float centreY = e.owner->mSRT.t.y + (slot ? slot->bodyCentreOffsetY : 0.0f);
        const float heldY = e.mouth->mCentre.y + hold.y;
        std::printf("P2_KURAGE_HOLD kind=pikmin index=%d held_y=%.1f mouth_y=%.1f body_origin_y=%.1f body_centre_y=%.1f "
                    "held_minus_origin=%.1f held_minus_centre=%.1f\n",
                    index, heldY, e.mouth->mCentre.y, e.owner->mSRT.t.y, centreY, heldY - e.owner->mSRT.t.y,
                    heldY - centreY);
        std::fflush(stdout);
    }
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
    sOwners = {};
    sOwner = nullptr;
    sMouth = nullptr;
    ++sGeneration;
    for (const Entry& entry : entries) dispose(entry, false, true);
}

bool pc_p2_kurage_receiver_setup(Creature* owner, CollPart* mouth)
{
    pc_p2_kurage_receiver_reset();
    if (!owner || !mouth) return false;
    sOwners[0] = OwnerSlot{owner, mouth};
    sOwner = owner;
    sMouth = mouth;
    return true;
}

bool pc_p2_kurage_receiver_register(Creature* owner, CollPart* mouth)
{
    if (!owner || !mouth) return false;
    for (OwnerSlot& o : sOwners) {
        if (o.owner == owner) { o.mouth = mouth; if (sOwner == owner) sMouth = mouth; return true; }
    }
    for (OwnerSlot& o : sOwners) {
        if (o.owner) continue;
        o = OwnerSlot{owner, mouth};
        if (!sOwner) { sOwner = owner; sMouth = mouth; }
        return true;
    }
    return false; // more than kMaxOwners Jellyfloats: refuse, caller logs the reason
}

void pc_p2_kurage_receiver_configure_own(Creature* owner, float bodyCentreOffsetY)
{
    if (!owner) return;
    for (OwnerSlot& o : sOwners)
        if (o.owner == owner) { o.own = true; o.bodyCentreOffsetY = bodyCentreOffsetY; }
}

bool pc_p2_kurage_receiver_capture(Piki* piki)
{
    if (!reserve(piki, Entry::Phase::Stomach, sOwner, sMouth)) return false;
    Entry& e = *std::find_if(sEntries.begin(), sEntries.end(), [piki](const Entry& x) { return x.piki == piki; });
    if (enterStomach(e)) return true;
    // Roll back to the previous squad owner; the failed stomach entry is dead.
    pc_p2_captain::release_actor(e.generation, piki, P2CaptainInvalid);
    e = {};
    return false;
}

bool pc_p2_kurage_receiver_admit_for(Creature* owner, Piki* piki)
{
    CollPart* mouth = nullptr;
    for (const OwnerSlot& o : sOwners) if (o.owner == owner) mouth = o.mouth;
    return reserve(piki, Entry::Phase::MouthTravel, owner, mouth);
}

bool pc_p2_kurage_receiver_admit(Piki* piki)
{
    // Kurage passes a null tube collpart and `suck` as the stomach part.  This
    // adapter preserves its mouth-only approach; there is no string/tube leg.
    return reserve(piki, Entry::Phase::MouthTravel, sOwner, sMouth);
}

bool pc_p2_kurage_receiver_controls(const Piki* piki)
{
    if (!piki) return false;
    for (const Entry& e : sEntries) {
        if (e.piki == piki && controls(e)) return true;
    }
    return false;
}

int pc_p2_kurage_receiver_scan_admit_for(Creature* owner, float verticalOffset, float attackRadius,
                                        int maxAdmissions, bool admitEligible)
{
    if (!owner || !pikiMgr || !std::isfinite(verticalOffset)
        || !std::isfinite(attackRadius) || verticalOffset < 0.0f || attackRadius <= 0.0f
        || maxAdmissions <= 0) return 0;
    if (!admitEligible) return 0;
    const Vector3f ownerPos = owner->mSRT.t;
    const float minY = ownerPos.y - verticalOffset - 50.0f;
    const float maxRange = attackRadius * attackRadius;
    int admitted = 0;
    ObjectMgr* manager = static_cast<ObjectMgr*>(pikiMgr);
    for (int it = manager->getFirst(); !manager->isDone(it) && admitted < maxAdmissions;
         it = manager->getNext(it)) {
        Piki* piki = static_cast<Piki*>(manager->getCreature(it));
        // P1's PikiMgr is typed, so every entry is a Pikmin equivalent.  The
        // source's mSticker exclusion maps to its current stick object.
        if (!piki || !piki->isAlive() || piki->getStickObject() == owner || !pikiEligible(owner, piki)) continue;
        const Vector3f pos = piki->mSRT.t;
        const float dx = pos.x - ownerPos.x;
        const float dz = pos.z - ownerPos.z;
        if (pos.y <= minY || pos.y >= ownerPos.y || dx * dx + dz * dz >= maxRange) continue;
        if (pc_p2_kurage_receiver_admit_for(owner, piki)) ++admitted;
    }
    return admitted;
}

int pc_p2_kurage_receiver_scan_admit(float verticalOffset, float attackRadius, int maxAdmissions, bool admitEligible)
{
    return pc_p2_kurage_receiver_scan_admit_for(sOwner, verticalOffset, attackRadius, maxAdmissions, admitEligible);
}

void pc_p2_kurage_receiver_update_for(Creature* owner, float delta, bool ownerAlive, bool ownerHasHealth, bool bittered)
{
    if (!std::isfinite(delta) || delta < 0.0f) return;
    for (int i = 0; i < static_cast<int>(sEntries.size()); ++i) {
        Entry& e = sEntries[i];
        if (!e.piki || e.owner != owner) continue;
        const bool owned = controls(e);
        if (!ownerAlive || !owner || !owned) { release(i, false); continue; }
        Piki* piki = e.piki;
        if (e.phase == Entry::Phase::MouthTravel) {
            Vector3f mouthTarget = e.mouth->mCentre;
            // Source: toward the `suck` part itself (suckVec = partPos - pikiPos).
            // Legacy owners keep the bottom of the mouth sphere.
            if (!ownerIsOwn(e.owner)) mouthTarget.y -= e.mouth->mRadius;
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

void pc_p2_kurage_receiver_update(float delta, bool ownerAlive, bool ownerHasHealth, bool bittered)
{
    pc_p2_kurage_receiver_update_for(sOwner, delta, ownerAlive, ownerHasHealth, bittered);
}

void pc_p2_kurage_receiver_release_all_for(Creature* owner)
{
    for (Entry& slot : sEntries) {
        if (!slot.piki || slot.owner != owner) continue;
        const Entry entry = slot;
        slot = {};
        dispose(entry, false, entry.generation == sGeneration);
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
    if (!owner) return;
    bool known = false;
    int owners = 0;
    for (const OwnerSlot& o : sOwners) {
        if (o.owner == owner) known = true;
        if (o.owner) ++owners;
    }
    if (!known) return;
    if (owners == 1) {
        // The last (historically the only) owner: full reset, byte-identical
        // to the old single-owner behaviour.
        pc_p2_kurage_receiver_reset();
        return;
    }
    // Release only this owner's Pikmin; other Jellyfloats keep theirs.
    pc_p2_kurage_receiver_release_all_for(owner);
    for (OwnerSlot& o : sOwners) if (o.owner == owner) o = {};
    if (owner == sOwner) {
        sOwner = nullptr;
        sMouth = nullptr;
        for (const OwnerSlot& o : sOwners) if (o.owner) { sOwner = o.owner; sMouth = o.mouth; break; }
    }
}

void pc_p2_kurage_receiver_piki_invalidated(Piki* piki)
{
    if (!piki) return;
    // Creature::kill invokes this before its own stick cleanup.  Releasing
    // here would transition a dying Piki back into FreeMode; revocation must
    // only drop receiver authority and let the normal death path continue.
    // Predeath captain revocation: the id must never be reused by a
    // replacement lifetime (codex/p2-lane12-review c29ec8398/b4ac39825, #130).
    pc_p2_captain_forget_piki(piki);
    for (Entry& entry : sEntries)
        if (entry.piki == piki) { entry = {}; return; }
}

int pc_p2_kurage_receiver_count_for(const Creature* owner)
{
    return ownerEntryCount(owner);
}

int pc_p2_kurage_receiver_count()
{
    int count = 0;
    for (const Entry& e : sEntries) if (e.piki) ++count;
    return count;
}

int pc_p2_kurage_receiver_stomach_count_for(const Creature* owner)
{
    int count = 0;
    for (const Entry& e : sEntries)
        if (e.piki && e.owner == owner && e.phase == Entry::Phase::Stomach) ++count;
    return count;
}

int pc_p2_kurage_receiver_stomach_count()
{
    int count = 0;
    for (const Entry& e : sEntries)
        if (e.piki && e.phase == Entry::Phase::Stomach) ++count;
    return count;
}
