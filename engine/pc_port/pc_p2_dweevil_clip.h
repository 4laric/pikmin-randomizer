#pragma once
// Dweevil death-clip choice helper (wf7 dweevil-impl, #871).
//
// Pure, engine-free rule used by the batch-2 draw path for dweevil keys
// ("dweevil|FireOtakara", "dweevil|WaterOtakara", "dweevil|GasOtakara",
// "dweevil|ElecOtakara"): a dead dweevil must play its death clip then hold
// the dead pose as a corpse, never the attack clip. While alive the visual
// follows the Otakara module's forced clip only; the generic P1 motion
// fallback (Damage/Type1 -> attack) must never independently animate a
// dweevil, so no actor is animated by two P2 layers.
#include <string>

namespace p2dweevilclip {

// True for the four elemental dweevil visual keys owned by batch-2.
inline bool isDweevilKey(const std::string& key) {
    return key.compare(0, 8, "dweevil|") == 0;
}

// Clip choice for dweevil keys. Returns the clip name to draw, or empty when
// the caller should fall back to its generic wait/move selection (never
// attack). Parameters:
//   corpse    - pellet-corpse draw path (viewDraw, corpse=true)
//   dead      - actor dead (mHealth<=0 or mDeadState!=0)
//   hasForced - Otakara module provided a clip for this actor
//   forced    - that clip name (e.g. "wait1", "move1", "attack1", "dead")
//   hasDead   - bank contains a dead clip
//   hasAttack - bank contains an attack clip (unused: attack only via forced)
inline std::string choose(const std::string& key, bool corpse, bool dead,
                          bool hasForced, const std::string& forced,
                          bool hasDead, bool /*hasAttack*/) {
    if (!isDweevilKey(key)) return std::string();
    // Dead (live path after mHealth<=0, or any corpse draw) forces the death
    // clip. Never the attack clip, even when the native animator still sits
    // on an attack/Type1 motion or the Otakara binding is already forgotten.
    if (corpse || dead) {
        if (hasDead) return std::string("dead");
        return std::string();
    }
    // Alive: follow the Otakara FSM only. During Flick the forced clip is
    // "attack1", which is the single legitimate attack source. Without a
    // forced clip fall back to wait/move (caller), never motion-based attack.
    if (hasForced && !forced.empty()) return forced;
    return std::string();
}

}  // namespace p2dweevilclip
