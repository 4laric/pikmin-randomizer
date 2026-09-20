#pragma once
#include <string>
class BTeki; class Graphics; struct Matrix4f;
// Family-owned batch-2 P2 visual registration (#346, #349, #350, #352, #353).
// Optional, additive, opt-in via the Pikipelago room preview. Ordinary P1
// actors and unconfigured families are untouched.
// Per-species material tint (#207). The batch-2 converter bakes every dweevil
// species from the shared-base model (FireOtakara) and drops the retail
// per-species `change_texture` (otakara_red/blue/purple/yellow_s3tc.bti), so all
// four Otakara .mod banks are byte-identical and render grey. The draw path
// multiplies one of these tints over the shared material list at draw time
// (save/set/restore, after pc_p2_kogane's karada konst pattern). Values are the
// mean opaque texel of each retail change_texture .bti (see colour.md).
// Engine-free so the standalone tint test can include this header directly.
namespace p2batch2tint {
struct Tint { unsigned char r, g, b; };
inline bool tintForSpecies(const std::string& species, Tint& out) {
    if (species == "FireOtakara") { out.r = 206; out.g = 72; out.b = 69; return true; }
    if (species == "WaterOtakara") { out.r = 74; out.g = 118; out.b = 201; return true; }
    if (species == "GasOtakara") { out.r = 189; out.g = 67; out.b = 209; return true; }
    if (species == "ElecOtakara") { out.r = 201; out.g = 187; out.b = 75; return true; }
    return false;
}
// Actor keys are "family|species"; only dweevil-family Otakara are tinted.
// Every other family/species (Sokkuri, BombOtakara, flora, cannon,
// waterwraith) returns false and the draw path leaves materials untouched.
inline bool tintForKey(const std::string& key, Tint& out) {
    const std::string::size_type bar = key.find('|');
    if (bar == std::string::npos) return false;
    if (key.compare(0, bar, "dweevil") != 0) return false;
    return tintForSpecies(key.substr(bar + 1), out);
}
}  // namespace p2batch2tint
void pc_p2_batch2_setup();
// Re-entry path (#397): rebind present arena actors after a legitimate family
// death without requiring every configured actor to still exist. Ordinary
// startup keeps the strict pc_p2_batch2_setup() contract.
void pc_p2_batch2_rebind();
void pc_p2_batch2_reset();
void pc_p2_batch2_forget(BTeki*);
bool pc_p2_batch2_draw(BTeki*, Graphics&, const Matrix4f&, bool corpse = false);
// Runtime evidence helper: true once any live or corpse pose has been drawn.
bool pc_p2_batch2_any_drawn();
// Fixture observability (#397): read-only registration count / membership.
unsigned long pc_p2_batch2_count();
bool pc_p2_batch2_registered(BTeki*);
// Runtime evidence helper: count of authored clock events delivered exactly once
// by the sampled clock (#431). Does not execute damage/capture/drops.
unsigned long long pc_p2_batch2_event_count();
