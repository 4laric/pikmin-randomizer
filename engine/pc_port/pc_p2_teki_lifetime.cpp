#include "pc_p2_teki_lifetime.h"

#include "pc_p2_armor.h"
#include "pc_p2_elecbug.h"
#include "pc_p2_tamago.h"
#include "pc_p2_umimushi.h"
#include "pc_p2_jigumo.h"
#include "pc_p2_snakejoint.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_hanachirashi.h"
#include "pc_p2_catfish.h"
#include "pc_p2_mar.h"
#include "pc_p2_tadpole.h"
#include "pc_p2_hana.h"
#include "pc_p2_imomushi.h"
#include "pc_p2_batch2.h"
#include "pc_p2_batch3.h"
#include "pc_p2_breadbug_actor.h"
#include "pc_p2_breadbug_visual.h"
#include "pc_p2_bulblax_visual.h"
#include "pc_p2_enemy.h"
#include "pc_p2_frog.h"
#include "pc_p2_flora_actor.h"
#include "pc_p2_plant.h"
#include "pc_p2_pom.h"
#include "pc_p2_hiba.h"
#include "pc_p2_bombotakara.h"
#include "pc_p2_dweevil.h"
#include "pc_p2_giant_breadbug_actor.h"
#include "pc_p2_giant_breadbug_visual.h"
#include "pc_p2_king.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_p2_kogane.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_long_legs.h"
#include "pc_p2_mamuta.h"
#include "pc_p2_onikurage_teki.h"
#include "pc_p2_projectiles.h"
#include "pc_p2_queen.h"
#include "pc_p2_qurione.h"
#include "pc_p2_shijimi.h"
#include "pc_p2_sheargrub.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_tank.h"

// Family registrations released before death teardown or manager-slot reuse.
void pc_p2_forget_teki(BTeki* actor)
{
	if (!actor) {
		return;
	}

	pc_p2_snow_forget(actor);
	pc_p2_sheargrub_forget(actor);
	pc_p2_kochappy_forget(actor);
	pc_p2_dwarf_orange_forget(actor);
	pc_p2_giant_breadbug_actor_forget(actor);
	pc_p2_breadbug_actor_forget(actor);
	pc_p2_frog_forget(actor);
	pc_p2_flora_forget(actor);
	pc_p2_kogane_forget(actor);
	pc_p2_mamuta_forget(actor);
	pc_p2_tank_forget(actor);
	pc_p2_qurione_forget(actor);
	pc_p2_shijimi_forget(actor);
	pc_p2_kurage_teki_forget(actor);
	pc_p2_onikurage_teki_forget(actor);
	pc_p2_batch2_forget(actor);
	pc_p2_projectiles_forget(actor);
	pc_p2_sokkuri_forget(actor);
	pc_p2_armor_forget(actor);
	pc_p2_elecbug_forget(actor);
    pc_p2_tamago_forget(actor);
    pc_p2_umimushi_forget(actor);
    pc_p2_jigumo_forget(actor);
    pc_p2_snakejoint_forget(actor);
    pc_p2_dangomushi_forget(actor);
    pc_p2_hanachirashi_forget(actor);
    pc_p2_catfish_forget(actor);
    pc_p2_mar_forget(actor);
    pc_p2_tadpole_forget(actor);
    pc_p2_hana_forget(actor);
    pc_p2_imomushi_forget(actor);
	pc_p2_batch3_forget(actor);
	pc_p2_long_legs_forget(actor);
}

// Stage-boundary teardown. The family set mirrors TekiMgr::reset() exactly; the
// four kurage resets that GameCoreSection::exitStage already performed are a
// subset, so this is additive for the remaining families and idempotent for
// kurage. Every *_reset() only clears private family state, so ordering against
// the existing exitStage steps is not significant.
void pc_p2_reset_all_teki()
{
	pc_p2_snow_reset();
	pc_p2_sheargrub_reset();
	pc_p2_kochappy_reset();
	pc_p2_dwarf_orange_reset();
	pc_p2_breadbug_visual_reset();
	pc_p2_giant_breadbug_visual_reset();
	pc_p2_bulblax_visual_reset();
	pc_p2_giant_breadbug_actor_reset();
	pc_p2_breadbug_actor_reset();
	pc_p2_queen_reset();
	pc_p2_king_reset();
	pc_p2_frog_reset();
	pc_p2_flora_reset();
	pc_p2_plant_reset();
	pc_p2_pom_reset();
	pc_p2_hiba_reset();
    pc_p2_bombotakara_reset();
    pc_p2_dweevil_reset();
	pc_p2_kogane_reset();
	pc_p2_mamuta_reset();
	pc_p2_tank_reset();
	pc_p2_qurione_reset();
	pc_p2_shijimi_reset();
	pc_p2_kurage_teki_reset();
	pc_p2_onikurage_teki_reset();
	pc_p2_batch2_reset();
	pc_p2_projectiles_reset();
	pc_p2_sokkuri_reset();
	pc_p2_armor_reset();
    pc_p2_elecbug_reset();
    pc_p2_tamago_reset();
    pc_p2_umimushi_reset();
    pc_p2_jigumo_reset();
    pc_p2_snakejoint_reset();
    pc_p2_dangomushi_reset();
    pc_p2_hanachirashi_reset();
    pc_p2_catfish_reset();
    pc_p2_mar_reset();
    pc_p2_tadpole_reset();
    pc_p2_hana_reset();
    pc_p2_imomushi_reset();
	pc_p2_batch3_reset();
	pc_p2_long_legs_reset();
}

namespace {
unsigned long sSceneGeneration = 0;
}

void pc_p2_scene_begin()
{
	++sSceneGeneration;
}

unsigned long pc_p2_scene_generation()
{
	return sSceneGeneration;
}
