#pragma once
#include <cstdint>

// Isolated accept/reject policy for the Cloaking Burrow-nit (Armor, EnemyID 15)
// damage receiver. Source: Game/Entities/Armor.cpp Obj::damageCallBack
// (:117-128) and Obj::hipdropCallBack (:134-141) at research revision
// 632af93787b9c95b63f0c13be32b161375ce3a96. This translation unit depends only
// on <cstdint> so the matrix can be exercised without the engine.
//
// Source rule: damage is accepted only while the enemy is bittered
// (isEvent(0, EB_Bittered)) or when the collided part is 'dmg1'. A null part,
// any other part id and any non-bittered hit are rejected. hipdropCallBack
// routes through the same predicate.
namespace p2armorreceiver {

constexpr std::uint32_t fourCC(char a, char b, char c, char d)
{
    return (std::uint32_t(static_cast<unsigned char>(a)) << 24)
         | (std::uint32_t(static_cast<unsigned char>(b)) << 16)
         | (std::uint32_t(static_cast<unsigned char>(c)) << 8)
         |  std::uint32_t(static_cast<unsigned char>(d));
}

// 'dmg1' from Game/Armor.cpp :123.
constexpr std::uint32_t DamagePartID = fourCC('d', 'm', 'g', '1');

// The exact source predicate, reused for damageCallBack and hipdropCallBack.
inline bool sourceAccepts(bool bittered, bool has_part, std::uint32_t part_id)
{
    return bittered || (has_part && part_id == DamagePartID);
}

// Port adaptation inputs. The P1 host exposes the *target* collision part for a
// stuck-Piki InteractAttack (Piki::getStickPart() is the part on the stuck-to
// object), but the visual-only Armor rides the P1 Chappy collision and does not
// load the source model's 'dmg1' part. When the source part is absent the
// receiver registers one host collision part as a documented weakpoint sphere
// (by part id); non-bittered hits on any other part are still rejected. When no
// weakpoint resolves, all non-bittered damage is rejected - never silently
// accepted.
struct Inputs {
    bool bittered = false;
    bool has_part = false;
    std::uint32_t part_id = 0;
    bool weakpoint_active = false;
    std::uint32_t weakpoint_id = 0;
};

enum class Decision {
    Reject,
    AcceptBittered,
    AcceptDmg1,
    AcceptWeakpoint,
};

inline Decision decide(const Inputs& in)
{
    if (in.bittered) {
        return Decision::AcceptBittered;
    }
    if (in.has_part && in.part_id == DamagePartID) {
        return Decision::AcceptDmg1;
    }
    if (in.weakpoint_active && in.weakpoint_id != 0 && in.has_part
            && in.part_id == in.weakpoint_id) {
        return Decision::AcceptWeakpoint;
    }
    return Decision::Reject;
}

inline bool accepts(const Inputs& in) { return decide(in) != Decision::Reject; }

inline const char* decisionName(Decision decision)
{
    switch (decision) {
    case Decision::AcceptBittered: return "bittered";
    case Decision::AcceptDmg1: return "dmg1";
    case Decision::AcceptWeakpoint: return "weakpoint";
    default: return "reject";
    }
}

} // namespace p2armorreceiver
