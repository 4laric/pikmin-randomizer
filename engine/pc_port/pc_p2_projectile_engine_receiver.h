#pragma once

class Creature;

// Source-faithful engine receiver for the Kabuto Stone (74) / falling Rock (19)
// strikes (lane 20, #169 / #406 / #413 / #425). This is the "actual receiver
// mutation" half the proxy receiver (pc_p2_projectile_receiver.h) deliberately
// does not do: it routes already-classified projectile strikes into the engine's
// own interaction primitives, matching source Rock.cpp:204-238:
//
//   grounded Navi/Pikmin -> InteractPress(sourceEnemy-or-self, attackDamage)
//   Teki                 -> InteractAttack(self, 250.0f)
//
// The owner `source` is the host-resolved source-enemy Creature (the bound
// Kabuto actor when present, else nullptr: the host has no real Stone Creature,
// and the source attributes Teki damage to the Stone `this` rather than the
// firing enemy). Damage is never re-derived here; the caller passes the amount
// the Stone/Rock contact policy already produced.
//
// Side effect to be aware of (not "no side effect"): a Teki strike passes
// source=nullptr, so InteractAttack::actTeki -> tekibteki.cpp interactDefault
// stores `setCreaturePointer(1, nullptr)` on the target Teki, clearing its
// "last assailant" pointer to null (SmartPtr::set is null-safe; the source
// attributes Teki damage to the Stone self, which has no Creature here). A
// grounded Navi/Pikmin strike passes the real source (the bound Kabuto) when one
// is bound, so `playEventSound(mOwner)` and its attribution stay valid.
//
// This file is engine-aware (it calls Creature::stimulate with the interaction
// types defined in Interactions.h) and therefore has no standalone unit test;
// its acceptance path is the real-GL projectile arena, which observes the
// target's health / stored-damage change through the returned outcome.
//
// No shared hook is added and engine actor health is only ever mutated through
// the engine's own stimulate() dispatch, never by direct field writes.

// Observed outcome of one stimulate() call.
struct P2ProjectileEngineHit {
    bool attempted = false;   // a non-null target was offered
    bool applied = false;     // the interaction act* method returned true
    bool rejected = false;    // a live target that did not accept the strike
    float healthBefore = 0.0f;
    float healthAfter = 0.0f;
    float storedDamageBefore = 0.0f; // Teki mStoredDamage, else 0
    float storedDamageAfter = 0.0f;
};

// Apply one already-classified strike. `attack` selects InteractAttack
// (Teki path, source Rock.cpp:221-223) vs InteractPress (grounded Navi/Pikmin,
// Rock.cpp:212-219). `targetIsTeki` enables stored-damage observation, because
// Teki damage is deferred through mStoredDamage -> makeDamaged rather than
// applied to mHealth inside the interaction.
P2ProjectileEngineHit p2_projectile_apply_engine_strike(Creature* target, Creature* source,
                                                        bool attack, bool targetIsTeki,
                                                        float damage);
