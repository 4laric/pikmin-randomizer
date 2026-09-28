#include "pc_p2_kabuto_muzzle.h"

#include <cctype>
#include <string>

namespace {

bool iequals(const std::string& a, const char* b)
{
    if (!b) {
        return false;
    }
    std::size_t i = 0;
    for (; i < a.size() && b[i] != '\0'; ++i) {
        const unsigned char ca = static_cast<unsigned char>(a[i]);
        const unsigned char cb = static_cast<unsigned char>(b[i]);
        if (std::tolower(ca) != std::tolower(cb)) {
            return false;
        }
    }
    return i == a.size() && b[i] == '\0';
}

int findClip(const p2attach::Bank& bank, const char* name)
{
    const int exact = bank.clip(name);
    if (exact >= 0) {
        return exact;
    }
    for (std::size_t i = 0; i < bank.clips.size(); ++i) {
        if (iequals(bank.clips[i].name, name)) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

int findJoint(const p2attach::Bank& bank, const char* name)
{
    const int exact = bank.joint(name);
    if (exact >= 0) {
        return exact;
    }
    for (std::size_t i = 0; i < bank.joints.size(); ++i) {
        if (iequals(bank.joints[i].name, name)) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

} // namespace

const P2KabutoMouthClip& p2_kabuto_mouth_clip(P2KabutoSpecies species)
{
    // Kabuto and Rkabuto fire from the surfaced attack clip; the buried Fkabuto
    // fires from K_attack. Frames are the source KEYEVENT_2 emission frames.
    static const P2KabutoMouthClip kSurfaced = { "attack", "kuti", 50 };
    static const P2KabutoMouthClip kBuried = { "K_attack", "kuti", 55 };
    return species == P2KabutoSpecies::Fkabuto ? kBuried : kSurfaced;
}

bool p2_kabuto_mouth_resolve(const p2attach::Bank& bank, P2KabutoSpecies species,
                             P2KabutoMouthBinding& out)
{
    out = P2KabutoMouthBinding{};
    const P2KabutoMouthClip& descriptor = p2_kabuto_mouth_clip(species);
    const int clip = findClip(bank, descriptor.clip);
    if (clip < 0) {
        return false;
    }
    const int joint = findJoint(bank, descriptor.joint);
    if (joint < 0) {
        return false;
    }
    const p2attach::Clip& resolved = bank.clips[static_cast<std::size_t>(clip)];
    if (descriptor.fireFrame < 0 || descriptor.fireFrame > resolved.duration - 1) {
        return false;
    }
    out.clip = clip;
    out.joint = joint;
    out.fireFrame = descriptor.fireFrame;
    return true;
}

bool P2KabutoMuzzle::bind(const p2attach::Bank& bank, P2KabutoSpecies species)
{
    return p2_kabuto_mouth_resolve(bank, species, mBinding);
}

bool P2KabutoMuzzle::sampleMouth(p2attach::Instance& instance, p2attach::Token token,
                                 const p2attach::Affine& owner, std::uint64_t tick,
                                 p2attach::Vec& out) const
{
    if (!mBinding.valid()
        || !instance.sample(token, mBinding.clip, static_cast<float>(mBinding.fireFrame),
                            owner, tick)) {
        return false;
    }
    p2attach::Affine world;
    if (!instance.socket(token, mBinding.joint, world)) {
        return false;
    }
    const p2attach::Vec position = { world.m[0][3], world.m[1][3], world.m[2][3] };
    if (!p2pose::valid(position)) {
        return false;
    }
    out = position;
    return true;
}

bool P2KabutoMuzzle::takeBirth(P2KabutoCannon& cannon, p2attach::Instance& instance,
                               p2attach::Token token, const p2attach::Affine& owner,
                               std::uint64_t tick, float faceDir,
                               P2KabutoStoneBirth& out) const
{
    out = P2KabutoStoneBirth{};
    if (!cannon.hasPendingBirth()) {
        return false;
    }
    p2attach::Vec mouth;
    if (!sampleMouth(instance, token, owner, tick, mouth)) {
        return false;
    }
    const P2CannonStoneVec3 joint = { mouth.x, mouth.y, mouth.z };
    return cannon.takeBirth(joint, faceDir, out);
}
