#include "pc_p2_bigtreasure.h"

namespace {
bool validWeapon(int weapon) { return weapon >= 0 && weapon < P2BTWEAPON_Count; }
} // namespace

P2BigTreasureOwnership::P2BigTreasureOwnership()
{
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        mAttached[i] = false;
        mHealth[i]   = 0.0f;
    }
    mLouieAttached = false;
}

void P2BigTreasureOwnership::attachWeapon(int weapon)
{
    if (!validWeapon(weapon)) return;
    mAttached[weapon] = true;
    mHealth[weapon]   = kWeaponMaxHealth;
}

void P2BigTreasureOwnership::attachLouie()
{
    mLouieAttached = true;
}

bool P2BigTreasureOwnership::isWeaponAttached(int weapon) const
{
    return validWeapon(weapon) && mAttached[weapon];
}

bool P2BigTreasureOwnership::hasAnyWeapon() const
{
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        if (mAttached[i]) return true;
    }
    return false;
}

int P2BigTreasureOwnership::weaponCount() const
{
    int count = 0;
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        if (mAttached[i]) count++;
    }
    return count;
}

float P2BigTreasureOwnership::weaponHealth(int weapon) const
{
    return validWeapon(weapon) ? mHealth[weapon] : 0.0f;
}

bool P2BigTreasureOwnership::addWeaponDamage(int weapon, float damage, bool bittered)
{
    if (!isWeaponAttached(weapon)) return false;
    const float starting = mHealth[weapon];
    float adjusted       = bittered ? damage * kBitterWeaponFactor : damage;
    mHealth[weapon] -= adjusted;
    if (mHealth[weapon] < 0.0f) mHealth[weapon] = 0.0f;
    return starting >= kPinchSmokeThreshold && mHealth[weapon] < kPinchSmokeThreshold;
}

bool P2BigTreasureOwnership::isNormalAttack(int weapon) const
{
    return mHealth[weapon] > kPinchSmokeThreshold;
}

P2BigTreasureDamageResult P2BigTreasureOwnership::damageCallBack(bool fromPiki, bool hasCollPart,
                                                                 int collWeapon, float damage,
                                                                 P2BigTreasurePhase state, bool bittered,
                                                                 bool* outPinchSmoke)
{
    if (outPinchSmoke) *outPinchSmoke = false;
    if (!hasCollPart || !fromPiki) return P2BTDMG_Ignored;

    float adjusted = damage;
    if (state == P2BT_Land) adjusted *= kLandDamageFactor;

    if (isWeaponAttached(collWeapon)) {
        const bool pinch = addWeaponDamage(collWeapon, adjusted, bittered);
        if (outPinchSmoke) *outPinchSmoke = pinch;
        return P2BTDMG_Weapon;
    }

    // Not a weapon part: body damage only once every weapon is gone.
    if (!hasAnyWeapon()) return P2BTDMG_Body;
    return P2BTDMG_Ignored;
}

bool P2BigTreasureOwnership::hipdropCallBack(bool fromPiki, bool hasCollPart, int collWeapon,
                                             float damage, P2BigTreasurePhase state, bool bittered)
{
    // Source: return damageCallBack(...) == false. "sure."
    return damageCallBack(fromPiki, hasCollPart, collWeapon, damage, state, bittered) == P2BTDMG_Ignored;
}

std::size_t P2BigTreasureOwnership::update(P2BigTreasureDropEvent* outDrops, std::size_t maxDrops)
{
    std::size_t written = 0;
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        if (mAttached[i] && mHealth[i] <= 0.0f) {
            if (outDrops && written < maxDrops) {
                outDrops[written].weapon      = i;
                outDrops[written].isLouie     = false;
                outDrops[written].velocity    = P2BigTreasureVec3{ 0.0f, kKnockOffPopY, 0.0f };
            }
            written++;
            mAttached[i] = false;
            mHealth[i]   = 0.0f;
        }
    }
    return written;
}

int P2BigTreasureOwnership::pickWeapon(float threshold) const
{
    float total = 0.0f;
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        if (mAttached[i]) total += kPickWeightBase - mHealth[i];
    }
    if (total <= 0.0f) return -1;

    // Bands in elec/fire/gas/water order; first band exceeding the threshold wins.
    float accumulated = 0.0f;
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        if (!mAttached[i]) continue;
        accumulated += kPickWeightBase - mHealth[i];
        if (accumulated > threshold) return i;
    }
    return -1;
}

bool P2BigTreasureOwnership::releaseLouie(P2BigTreasureDropEvent* outDrop)
{
    if (!mLouieAttached) return false;
    if (outDrop) {
        outDrop->weapon   = -1;
        outDrop->isLouie  = true;
        outDrop->velocity = P2BigTreasureVec3{ 0.0f, kLouiePopY, 0.0f };
    }
    mLouieAttached = false;
    return true;
}

std::size_t P2BigTreasureOwnership::defeat(P2BigTreasureDropEvent* outDrops, std::size_t maxDrops)
{
    // Lane policy for source gap 1: source never releases mTreasures[] at
    // kill. Release each captured weapon with the standard knock-off pop so
    // no pellet outlives its owner, then release Louie as onKill does.
    std::size_t written = 0;
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        if (mAttached[i]) {
            if (outDrops && written < maxDrops) {
                outDrops[written].weapon   = i;
                outDrops[written].isLouie  = false;
                outDrops[written].velocity = P2BigTreasureVec3{ 0.0f, kKnockOffPopY, 0.0f };
            }
            written++;
            mAttached[i] = false;
            mHealth[i]   = 0.0f;
        }
    }
    if (mLouieAttached) {
        if (outDrops && written < maxDrops) {
            outDrops[written].weapon   = -1;
            outDrops[written].isLouie  = true;
            outDrops[written].velocity = P2BigTreasureVec3{ 0.0f, kLouiePopY, 0.0f };
        }
        written++;
        mLouieAttached = false;
    }
    return written;
}

bool P2BigTreasureAttackPacer::tick(float delta, int liveWeapons, bool targetInBox,
                                    bool unstuckOutsiderNearby)
{
    const float threshold = 4.0f + 2.0f * static_cast<float>(liveWeapons);
    if (mTimer > threshold) return targetInBox;
    mTimer += unstuckOutsiderNearby ? 3.0f * delta : delta;
    return false;
}

P2BigTreasurePhase p2_bigtreasure_weapon_loss_guard(P2BigTreasurePhase current, bool anyWeapons,
                                                    bool chosenWeaponAlive)
{
    switch (current) {
    case P2BT_ItemWait:
        // ItemWait only checks "any weapons"; losing all exits to DropItem.
        return anyWeapons ? current : P2BT_DropItem;
    case P2BT_PreAttack:
    case P2BT_Attack:
    case P2BT_PutItem:
        if (!anyWeapons) return P2BT_DropItem;
        if (!chosenWeaponAlive) return P2BT_PreAttack;
        return current;
    default:
        return current;
    }
}

P2BigTreasureAttackPools::P2BigTreasureAttackPools()
{
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        mStarted[i]  = false;
        mInFlight[i] = 0;
    }
    mElecMaxNodes = 15; // source BigTreasureAttackData default
}

int P2BigTreasureAttackPools::poolIndex(int element) const
{
    return (element >= 0 && element < P2BTWEAPON_Count) ? element : -1;
}

int P2BigTreasureAttackPools::capacity(int element) const
{
    switch (element) {
    case P2BTWEAPON_Fire: return kFireCapacity;
    case P2BTWEAPON_Gas: return kGasCapacity;
    case P2BTWEAPON_Water: return kWaterCapacity;
    case P2BTWEAPON_Elec: return kElecCapacity;
    default: return 0;
    }
}

int P2BigTreasureAttackPools::inFlight(int element) const
{
    const int idx = poolIndex(element);
    return idx >= 0 ? mInFlight[idx] : 0;
}

bool P2BigTreasureAttackPools::isStarted(int element) const
{
    const int idx = poolIndex(element);
    return idx >= 0 && mStarted[idx];
}

bool P2BigTreasureAttackPools::start(int element)
{
    const int idx = poolIndex(element);
    if (idx < 0 || mStarted[idx]) return false;
    mStarted[idx] = true;
    return true;
}

bool P2BigTreasureAttackPools::emit(int element)
{
    const int idx = poolIndex(element);
    if (idx < 0 || mInFlight[idx] >= capacity(element)) return false;
    mInFlight[idx]++;
    return true;
}

bool P2BigTreasureAttackPools::recycleOne(int element)
{
    const int idx = poolIndex(element);
    if (idx < 0 || mInFlight[idx] <= 0) return false;
    mInFlight[idx]--;
    return true;
}

bool P2BigTreasureAttackPools::setElecMaxDischarge(int maxNodes)
{
    // 1 invisible anchor node + maxNodes visible nodes must fit the pool.
    if (maxNodes < 0 || 1 + maxNodes > kElecCapacity) return false;
    mElecMaxNodes = maxNodes;
    return true;
}

void P2BigTreasureAttackPools::finishAttack()
{
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        mStarted[i] = false;
    }
    // finishFireAttack/finishGasAttack fade effects; nodes self-recycle at
    // extent in source, so their in-flight counts persist briefly there too.
    // finishElecAttack recycles every elec node with break effects.
    mInFlight[P2BTWEAPON_Elec] = 0;
    // finishWaterAttack is empty in source: in-flight bubbles persist.
}

void P2BigTreasureAttackPools::bitterWeaponLost(int element)
{
    // Source: bittered + lost weapon force-finishes the whole attack.
    (void)element;
    finishAttack();
}

void P2BigTreasureAttackPools::defeat()
{
    for (int i = 0; i < P2BTWEAPON_Count; i++) {
        mStarted[i]  = false;
        mInFlight[i] = 0;
    }
}
