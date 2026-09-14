#include "DebugLog.h"
#include "Interactions.h"
#include "sysNew.h"
#include "teki.h"
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
#include "pc_p2_sokkuri.h"
#include "pc_p2_elecbug.h"
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
	if (pc_p2_kogane_attacked(teki)) {
		return true; // registered beetles take no attack damage (P2: only flips)
	}
	if (pc_p2_elecbug_attacked(teki)) {
		return true; // registered Anode Beetles are invulnerable until flipped
	}
#endif
	return teki->interact(TekiInteractionKey(TekiInteractType::Attack, this));
}

/**
 * @todo: Documentation
 */
bool InteractBomb::actTeki(Teki* teki) immut
{
	f32 bombFactor = teki->getParameterF(TPF_BombDamageRate);
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
	if (pc_p2_sokkuri_pressed(teki, mOwner)) {
		return true; // registered Skitter Leaves are crushed into their source Press state
	}
	if (pc_p2_elecbug_pressed(teki, mOwner)) {
		return true; // registered Anode Beetles flip into their source Reverse state
	}
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
