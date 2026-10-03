#include "pc_p2_original_foliage_native.h"
#include "pc_p2_original_pelplant_native.h"
#include "DebugLog.h"
#include "Interactions.h"
#include "sysNew.h"
#include "teki.h"
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
#include "pc_p2_original_red_native.h"
#include "pc_p2_original_snow_native.h"
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_elecbug.h"
#include "pc_p2_armor.h"
#include "pc_p2_hana.h"
#include "pc_p2_hardlanes.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_long_legs.h"
#include "pc_p2_snakejoint.h"
#include "pc_p2_otakara.h"
#include "pc_p2_chappy.h"
#include "pc_p2_umimushi.h"
#include "pc_p2_groink_teki.h"
#include "pc_p2_breadbug_teki.h"
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
    if (pc_p2_original_foliage_owned(teki)) return false;
#endif
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
    if (pc_p2_original_pelplant_damage(teki, mDamage, mCollPart ? mCollPart->getCode().mId : 0)) return true;
#endif
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	if (teki->isP2Dying()) return false;
	if (pc_p2_hana_rejects_attack(teki)) return true;
	// Dweevil family (59-62): OtakaraBase::damageCallBack damages only through a collision part
	// (OtakaraBase.cpp:190-197); the partless ground punch is refused. -1 = not a registered Dweevil.
	if (pc_p2_otakara_attack_part(teki, mOwner, mCollPart, mDamage) == 0) return false;
	// #898: PanModoki::damageCallBack applies damage only while bittered.
	if (pc_p2_breadbug_teki_attack(teki, mOwner, mDamage)) return false;
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
	if (pc_p2_snakejoint_invulnerable(teki)) {
		return true; // registered Snagret is invulnerable while buried (Stay)
	}
	if (pc_p2_long_legs_receiver_rejects(teki, this)) {
		return false; // registered Long Legs rejects damage while bitter-immune (Stay/Land)
	}
	// #173: registered Man-at-Legs, source Houdai::damageCallBack (stuck
	// Pikmin only, Land 0.25x). -1 leaves every other actor untouched.
	const f32 legsRate = pc_p2_long_legs_damage_rate(teki, mOwner);
	if (legsRate == 0.0f) {
		return false;
	}
	if (legsRate > 0.0f && legsRate != 1.0f) {
		InteractAttack scaledLegs(mOwner, mCollPart, mDamage * legsRate, _10);
		return teki->interact(TekiInteractionKey(TekiInteractType::Attack, &scaledLegs));
	}
	// #884: registered Emperor Bulblax, source KingChappy::damageCallBack
	// (kingChappy.cpp:824-848). A refused hit takes no damage and adds no
	// flick; a partless hit low under the chin is scaled by 0.2.
	// #892: registered Gatling Groink: a Pikmin hurts it only through the stickable `body` it is
	// latched to; the face cover and unlatched ground hits are refused (P2 has no such hit).
	const f32 groinkRate = pc_p2_groink_teki_damage_rate(teki, mOwner, mCollPart);
	if (groinkRate == 0.0f) {
		return false;
	}
	const f32 kingRate = pc_p2_chappy_king_damage_rate(teki, mOwner, mCollPart);
	if (kingRate == 0.0f) {
		return false;
	}
	if (kingRate > 0.0f && kingRate != 1.0f) {
		InteractAttack scaled(mOwner, mCollPart, mDamage * kingRate, _10);
		const bool scaledAccepted = teki->interact(TekiInteractionKey(TekiInteractType::Attack, &scaled));
		pc_p2_chappy_attacked(teki, scaledAccepted);
		return scaledAccepted;
	}
	// #995: registered Bloyster (71/101), source UmiMushi::Obj::damageCallBack
	// (umiMushi.cpp:467-492): a hit that carries a part needs a stuck attacker (only the tail
	// bulb is stickable), a partless low hit is scaled by proper fp01 (0.03). -1 leaves every
	// other actor untouched.
	const f32 umiRate = pc_p2_umimushi_damage_rate(teki, mOwner, mCollPart);
	if (umiRate == 0.0f) {
		return false;
	}
	if (umiRate > 0.0f && umiRate != 1.0f) {
		InteractAttack scaledUmi(mOwner, mCollPart, mDamage * umiRate, _10);
		const bool umiAccepted = teki->interact(TekiInteractionKey(TekiInteractType::Attack, &scaledUmi));
		pc_p2_umimushi_attacked(teki, umiAccepted);
		return umiAccepted;
	}
#endif
	const bool damageAccepted = teki->interact(TekiInteractionKey(TekiInteractType::Attack, this));
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	// Lane 28 (#245 gate 3): real engine receiver observation for the bound
	// Fuefuki vehicle. No-op for every other actor.
	pc_p2_hardlanes_fuefuki_hit(teki, mOwner, mDamage, damageAccepted);
	// #245 OWN Antenna Beetle: attribute the hit (Pikmin / captain) for the
	// DAMAGE marker. Observer only; no-op for every other actor.
	pc_p2_fuefuki_teki_attacked(teki, mOwner, mDamage, damageAccepted);
	// #884: Emperor Bulblax flick timer (source addDamage flickSpeed). No-op
	// for every other actor.
	pc_p2_chappy_attacked(teki, damageAccepted);
	// #995: Bloyster flick timer (source addDamage flickSpeed). No-op for every other actor.
	pc_p2_umimushi_attacked(teki, damageAccepted);
	// #996: Skitter Leaf flick timer (source addDamage flickSpeed). No-op for
	// every other actor.
	pc_p2_sokkuri_attacked(teki, damageAccepted);
#endif
	return damageAccepted;
}

/**
 * @todo: Documentation
 */
bool InteractBomb::actTeki(Teki* teki) immut
{
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
    if (pc_p2_original_foliage_owned(teki)) return false;
#endif
	if (pc_p2_hana_rejects_attack(teki)) {
		return true; // registered Hana is buried: bomb swallowed, no damage
	}
	f32 bombFactor = teki->getParameterF(TPF_BombDamageRate);
	InteractAttack attack(mOwner, nullptr, mDamage * bombFactor, false);
	// #1014: the Armor does not override bombCallBack, so EnemyBase::bombCallBack applies the damage on any
	// part (no dmg1 rule, unlike damageCallBack for Pikmin and punches). Observer only.
	pc_p2_armor_bombed(teki, mDamage * bombFactor);
	if (pc_p2_dangomushi_invulnerable(teki)) {
		return true; // registered Crawbster is invulnerable outside the flip window
	}
	if (pc_p2_snakejoint_invulnerable(teki)) {
		return true; // registered Snagret is invulnerable while buried (Stay)
	}
	// #1018: registered Raging Long Legs, EnemyBase::bombCallBack (full damage).
	const f32 legsBomb = pc_p2_long_legs_bomb_rate(teki);
	if (legsBomb == 0.0f) {
		return false;
	}
	if (legsBomb < 0.0f) {
		if (pc_p2_long_legs_receiver_rejects(teki, &attack)) {
			return false; // registered Long Legs is bitter-immune to bombs too
		}
		if (pc_p2_long_legs_damage_rate(teki, mOwner) == 0.0f) {
			return false; // #173: Man-at-Legs takes no bomb damage (stuck Pikmin only)
		}
	}
	if (pc_p2_chappy_king_bomb(teki, mDamage * bombFactor)) {
		return true; // registered Emperor Bulblax: source bombCallBack (0.25 x damage)
	}
	const bool bombAccepted = teki->interact(
	    TekiInteractionKey(TekiInteractType::Attack, stack_new(InteractAttack)(mOwner, nullptr, mDamage * bombFactor, false)));
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
	// #995: source EnemyBase::bombCallBack -> addDamage(damage, flickSpeed 1.0); the Bloyster overrides
	// only damage/press/hipdrop/earthquake, so a bomb takes the base path at full damage.
	pc_p2_umimushi_attacked(teki, bombAccepted);
#endif
	return bombAccepted;
}

/**
 * @todo: Documentation
 */
bool InteractHitEffect::actTeki(Teki* teki) immut
{
#if defined(PIKI_PC_PORT) && PIKI_PC_PORT
    if (pc_p2_original_foliage_owned(teki)) return false;
#endif
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
    if (pc_p2_original_foliage_earthquake(teki)) return false;
	if (pc_p2_original_red_owned(teki)||pc_p2_original_snow_owned(teki)) return pc_p2_kochappy_fsm_original_pressed(teki,mOwner);
	if (pc_p2_elecbug_pressed(teki, mOwner)) return true;
	if (pc_p2_sokkuri_pressed(teki, mOwner)) return true;
	if (pc_p2_hardlanes_fuefuki_pressed(teki, mOwner)) return true;
	if (pc_p2_fuefuki_teki_pressed(teki, mOwner)) return true; // #245 OWN pressCallBack
	if (pc_p2_kogane_pressed(teki, mOwner)) {
		return true; // registered beetles flip instead of the host pressed state
	}
	if (pc_p2_otakara_pressed(teki, mOwner)) {
		return true; // #884: Dweevils have no source pressCallBack; no host squash
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
