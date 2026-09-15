#include "DebugLog.h"
#include "Interactions.h"
#include "sysNew.h"
#include "teki.h"
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
#include "pc_p2_sokkuri.h"
#include "pc_p2_elecbug.h"
#include "pc_p2_armor.h"
#include "pc_p2_hana.h"
#include "pc_p2_hardlanes.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_long_legs.h"
#endif

/**
 * @todo: Documentation
 * @note UNUSED Size: 00009C
 */
DEFINE_ERROR(__LINE__) // Never used in the DLL

/**
 * @todo: Documentation
 * @note UNUSED Size: 0000F4
 */
DEFINE_PRINT("tekiinteraction");

/**
 * @todo: Documentation
 * @note UNUSED Size: 00000C
 */
TekiInteractionKey::TekiInteractionKey(int type, immut Interaction* interaction)
{
	mInteractionType = type;
	mInteraction     = interaction;
}

/**
 * @todo: Documentation
 */
bool InteractAttack::actTeki(Teki* teki) immut
{
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	if (pc_p2_hana_rejects_attack(teki)) return true;
	if (pc_p2_elecbug_attacked(teki)) return true;
	if (pc_p2_kogane_attacked(teki)) {
		return true; // registered beetles take no attack damage (P2: only flips)
	}
	if (pc_p2_armor_receiver_rejects(teki, this)) {
		return false; // registered Armor rejects non-'dmg1'/non-bittered damage
	}
	if (pc_p2_dangomushi_invulnerable(teki)) {
		return true; // registered Crawbster is invulnerable outside the flip window
	}
	if (pc_p2_long_legs_receiver_rejects(teki, this)) {
		return false; // registered Long Legs rejects damage while bitter-immune (Stay/Land)
	}
#endif
	return teki->interact(TekiInteractionKey(TekiInteractType::Attack, this));
}

/**
 * @todo: Documentation
 */
bool InteractBomb::actTeki(Teki* teki) immut
{
	if (pc_p2_hana_rejects_attack(teki)) {
		return true; // registered Hana is buried: bomb swallowed, no damage
	}
	f32 bombFactor = teki->getParameterF(TPF_BombDamageRate);
	// A bomb carries no collision part; a registered Armor rejects it unless
	// bittered, matching the same source predicate as InteractAttack.
	InteractAttack attack(mOwner, nullptr, mDamage * bombFactor, false);
	if (pc_p2_armor_receiver_rejects(teki, &attack)) {
		return false;
	}
	if (pc_p2_dangomushi_invulnerable(teki)) {
		return true; // registered Crawbster is invulnerable outside the flip window
	}
	if (pc_p2_long_legs_receiver_rejects(teki, &attack)) {
		return false; // registered Long Legs is bitter-immune to bombs too
	}
	return teki->interact(
	    TekiInteractionKey(TekiInteractType::Attack, stack_new(InteractAttack)(mOwner, nullptr, mDamage * bombFactor, false)));
}

/**
 * @todo: Documentation
 */
bool InteractHitEffect::actTeki(Teki* teki) immut
{
	return teki->interact(TekiInteractionKey(TekiInteractType::HitEffect, this));
}

/**
 * @todo: Documentation
 */
bool InteractSwallow::actTeki(Teki*) immut
{
	return true;
}

/**
 * @todo: Documentation
 */
bool InteractPress::actTeki(Teki* teki) immut
{
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	if (pc_p2_elecbug_pressed(teki, mOwner)) return true;
	if (pc_p2_sokkuri_pressed(teki, mOwner)) return true;
	if (pc_p2_hardlanes_fuefuki_pressed(teki, mOwner)) return true;
	if (pc_p2_kogane_pressed(teki, mOwner)) {
		return true; // registered beetles flip instead of the host pressed state
	}
#endif
	teki->eventPerformed(TekiEvent(TekiEventType::Pressed, teki, mOwner));
	return true;
}

/**
 * @todo: Documentation
 */
bool InteractFlick::actTeki(Teki*) immut
{
	return true;
}
