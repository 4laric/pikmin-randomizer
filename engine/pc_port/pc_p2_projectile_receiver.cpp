#include "pc_p2_projectile_receiver.h"

const char* p2ProjectileReceiverStrikeKindName(P2ProjectileReceiverStrikeKind kind)
{
    switch (kind) {
    case P2ProjectileReceiverStrikeKind::None: return "None";
    case P2ProjectileReceiverStrikeKind::InteractPress: return "InteractPress";
    case P2ProjectileReceiverStrikeKind::InteractAttack: return "InteractAttack";
    }
    return "?";
}

P2ProjectileReceiver::P2ProjectileReceiver(std::uint64_t token, float maxHealth)
    : mToken(token), mMaxHealth(maxHealth > 0.0f ? maxHealth : 0.0f),
      mHealth(mMaxHealth), mAlive(mMaxHealth > 0.0f)
{
}

float P2ProjectileReceiver::applyDamage(float damage)
{
    if (!mAlive || !(damage > 0.0f)) {
        return 0.0f;
    }
    const float applied = damage < mHealth ? damage : mHealth;
    mHealth -= applied;
    if (mHealth <= 0.0f) {
        mHealth = 0.0f;
        mAlive = false;
    }
    return applied;
}

void P2ProjectileReceiverRegistry::reset()
{
    for (int i = 0; i < kMaxReceivers; ++i) {
        mReceivers[i] = P2ProjectileReceiver();
    }
    mCount = 0;
    mAny = P2ProjectileReceiver();
    mHasAny = false;
}

bool P2ProjectileReceiverRegistry::add(std::uint64_t token, float maxHealth)
{
    if (token == 0 || !(maxHealth > 0.0f) || mCount >= kMaxReceivers || find(token)) {
        return false;
    }
    mReceivers[mCount++] = P2ProjectileReceiver(token, maxHealth);
    return true;
}

bool P2ProjectileReceiverRegistry::addAny(float maxHealth)
{
    if (mHasAny || !(maxHealth > 0.0f)) {
        return false;
    }
    mAny = P2ProjectileReceiver(0, maxHealth);
    mHasAny = true;
    return true;
}

P2ProjectileReceiver* P2ProjectileReceiverRegistry::find(std::uint64_t token)
{
    for (int i = 0; i < mCount; ++i) {
        if (mReceivers[i].token() == token) {
            return &mReceivers[i];
        }
    }
    return nullptr;
}

const P2ProjectileReceiver* P2ProjectileReceiverRegistry::find(std::uint64_t token) const
{
    for (int i = 0; i < mCount; ++i) {
        if (mReceivers[i].token() == token) {
            return &mReceivers[i];
        }
    }
    return nullptr;
}

int P2ProjectileReceiverRegistry::aliveCount() const
{
    int alive = mHasAny && mAny.alive() ? 1 : 0;
    for (int i = 0; i < mCount; ++i) {
        alive += mReceivers[i].alive() ? 1 : 0;
    }
    return alive;
}

P2ProjectileReceiverHit P2ProjectileReceiverRegistry::applyStrike(
    P2ProjectileReceiverStrikeKind kind, float damage, std::uint64_t targetToken,
    std::uint64_t attributedToken)
{
    P2ProjectileReceiverHit hit;
    hit.kind = kind;
    hit.damage = damage;
    hit.targetToken = targetToken;
    hit.attributedToken = attributedToken;

    P2ProjectileReceiver* receiver = find(targetToken);
    if (!receiver && mHasAny) {
        receiver = &mAny;
    }
    if (!receiver) {
        return hit;
    }
    hit.known = true;
    hit.health = receiver->health();
    if (kind == P2ProjectileReceiverStrikeKind::None || !(damage > 0.0f)) {
        return hit;
    }

    const bool wasAlive = receiver->alive();
    hit.appliedDamage = receiver->applyDamage(damage);
    hit.applied = hit.appliedDamage > 0.0f;
    hit.health = receiver->health();
    hit.died = wasAlive && !receiver->alive();
    return hit;
}

P2ProjectileReceiverHit P2ProjectileReceiverRegistry::applyStrike(
    const P2CannonStoneContactResult& result)
{
    if (!result.strikeEmitted) {
        return P2ProjectileReceiverHit{};
    }
    P2ProjectileReceiverStrikeKind kind = P2ProjectileReceiverStrikeKind::None;
    if (result.strike.kind == P2CannonStoneStrikeKind::Press) {
        kind = P2ProjectileReceiverStrikeKind::InteractPress;
    } else if (result.strike.kind == P2CannonStoneStrikeKind::Attack) {
        kind = P2ProjectileReceiverStrikeKind::InteractAttack;
    }
    return applyStrike(kind, result.strike.damage, result.strike.targetToken,
                       result.strike.attributedToken);
}

P2ProjectileReceiverHit P2ProjectileReceiverRegistry::applyStrike(
    const P2RockHazardContactResult& result)
{
    if (!result.strikeEmitted) {
        return P2ProjectileReceiverHit{};
    }
    P2ProjectileReceiverStrikeKind kind = P2ProjectileReceiverStrikeKind::None;
    if (result.strike.kind == P2RockHazardStrikeKind::Press) {
        kind = P2ProjectileReceiverStrikeKind::InteractPress;
    } else if (result.strike.kind == P2RockHazardStrikeKind::Attack) {
        kind = P2ProjectileReceiverStrikeKind::InteractAttack;
    }
    return applyStrike(kind, result.strike.damage, result.strike.targetToken,
                       result.strike.attributedToken);
}
