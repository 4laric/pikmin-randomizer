#pragma once
struct Creature {};
struct InteractAttack {
    Creature* mOwner;
    void* mCollPart;
    float mDamage;
    bool flag;
    InteractAttack(Creature* owner, void* part, float damage, bool value)
        : mOwner(owner), mCollPart(part), mDamage(damage), flag(value) {}
};
