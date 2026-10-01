#pragma once
// Opt-in lane-23 real-engine Candypop binding (#448, family #171).
//
// Binds the real engine `Pom` Boss (src/plugPikiNishimura/PomAi.cpp) for the
// three P1-representable colour Candypops (BluePom 3 / RedPom 4 / YellowPom 5)
// declared in a strict sidecar (`p2-pom-engine.txt`, reusing the lane-23
// `P2_POM_1` Candypop parser), so conversion runs through the genuine actor
// instead of the module-local injected `PIKISTATE_Flying` path in pc_p2_pom.cpp.
// Inert without `p2-pom-engine.txt`; fail-closed on malformed input.
//
// The conversion hook implements the source own-colour refund: a same-colour
// input births a replacement sprout and spends no budget slot, a different
// colour spends one, and population is conserved (inputs in == sprouts born +
// Pikmin left alive). RandPom is the Queen: it never refunds, cycles
// Blue/Red/Yellow every fp02 = 2.6 s, and shoots ip13 = 9 leaf sprouts per
// swallowed Pikmin. BlackPom/WhitePom stay with the existing violet/ivory
// providers.
class Pom;

void pc_p2_candypop_setup();
void pc_p2_candypop_reset();
void pc_p2_candypop_tick();

// Source budget for a bound bud (0 when `pom` is not a lane-23 engine bud).
// Called at Pom init, where only the birth position is known.
int pc_p2_candypop_budget(const Pom* pom);
// Real-actor conversion. Returns non-refunded slots used, or -1 when `pom` is
// not a bound lane-23 engine bud (so the caller keeps its existing behaviour).
int pc_p2_convert_candypop(Pom* pom, int remaining);
