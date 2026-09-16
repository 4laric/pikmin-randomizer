#pragma once
#include <cmath>
#include <cstdint>
#include <vector>

// Lane-owned engine-free follow-locomotion policy for the Fuefuki (Antenna
// Beetle) squad (#245). This is the follower half of the whistle-theft
// contract: the existing pc_p2_fuefuki_interference_policy.h decides *who*
// the beetle holds; this module decides *how a held Pikmin walks after the
// beetle*, bridging two source pieces that were previously unimplemented by
// the lane:
//
//  * the beetle's footprint trail: Fuefuki.cpp::Obj::updateFootmarks (509)
//    plus Game::Footmarks (src/plugProjectKandoU/gameFootmark.cpp), alloc(10);
//  * the Pikmin follower action PikiAI::ActTeki
//    (src/plugProjectKandoU/aiTeki.cpp): init/makeTarget/test_0/setTimer,
//    FOLLOW_DISTANCE 100, footprint seek and the 0.5..1.0 approach speed.
//
// Source revision: projectPiki/pikmin2 632af93787b9c95b63f0c13be32b161375ce3a96
// (US GPVE01 rev 0), read-only under native/pikmin2-research. No engine or
// map dependency: the host supplies positions, the beetle velocity and a
// randFloat() source; the module outputs a per-follower velocity command the
// host applies (P1 Piki::setSpeed / mTargetVelocity). Fixed owner-epoch
// discipline matches the interference policy.

// Retail randFloat() semantics: uniform [0, 1). Passed in so the policy has
// no global RNG; a deterministic LCG is used when this is null.
typedef float (*P2FuefukiRandFn)(void* context);

struct P2FuefukiFollowParms {
    float followDistance   = 100.0f;      // source FOLLOW_DISTANCE (aiTeki.cpp:8)
    float footmarkInterval = 2.5f / 60.0f; // |frame counter delta| > 2.5 at 60 fps
    float footmarkSpacing  = 20.0f;       // Footmarks::add rejects dist < 20
    int   footmarkCapacity = 10;          // Fuefuki::createFootmarks alloc(10)
    float farSpeed         = 1.0f;        // distance > FOLLOW_DISTANCE
    float nearSpeedMin     = 0.5f;        // 0.5 * randFloat() + 0.5
    float nearSpeedMax     = 1.0f;
    float parentTimerNear  = 0.3f;        // setTimer weight, dist < FOLLOW_DISTANCE
    float parentTimerFar   = 0.1f;
};

// Footprint trail, mirroring Game::Footmarks (gameFootmark.cpp). mCount is the
// allocated array size, capacity() the number of valid marks; slotAt(0) is the
// most recent and the raw slot index is stable across following ticks (the
// source holds a raw Footmark* the same way).
class P2FuefukiFootmarks {
public:
    struct Mark {
        float x = 0.0f, z = 0.0f;
    };

    explicit P2FuefukiFootmarks(int capacity = 10) { alloc(capacity); }

    void alloc(int capacity)
    {
        if (capacity < 1) capacity = 1;
        marks.assign(static_cast<std::size_t>(capacity), Mark{});
        count_ = capacity;
        capacity_ = 0;
        current_ = 0;
        lastRecord_ = -1.0f; // source mLastUpdateTime=0 vs a large frame timer
    }

    int capacity() const { return capacity_; }
    int allocated() const { return count_; }

    // Recency index -> raw slot (Game::Footmarks::get), or -1 when invalid.
    int slotAt(int index) const
    {
        if (index < 0 || index >= capacity_) return -1;
        return ((count_ + current_) - (index + 1)) % count_;
    }
    int mostRecentSlot() const { return capacity_ > 0 ? slotAt(0) : -1; }
    const Mark& at(int slot) const { return marks[static_cast<std::size_t>(slot)]; }

    // Mirrors Footmarks::add: skip when within footmarkSpacing of the previous
    // mark; otherwise store at the write cursor and advance. lastRecord_ only
    // moves on a stored mark, so a stationary beetle keeps retrying.
    bool add(float x, float z, float now, const P2FuefukiFollowParms& parms)
    {
        if (capacity_ >= 2) {
            const int prev = ((current_ + count_) - 1) % count_;
            const float dx = marks[static_cast<std::size_t>(prev)].x - x;
            const float dz = marks[static_cast<std::size_t>(prev)].z - z;
            if (std::sqrt(dx * dx + dz * dz) < parms.footmarkSpacing) return false;
        }
        Mark& slot       = marks[static_cast<std::size_t>(current_)];
        slot.x           = x;
        slot.z           = z;
        current_         = (current_ + 1) % count_;
        if (capacity_ < count_) capacity_++;
        lastRecord_ = now;
        return true;
    }

    bool due(float now, const P2FuefukiFollowParms& parms) const
    {
        return std::fabs(now - lastRecord_) > parms.footmarkInterval;
    }

private:
    std::vector<Mark> marks;
    int count_ = 0;      // allocated size (source mCount)
    int capacity_ = 0;   // valid mark count (source mCapacity)
    int current_ = 0;    // write cursor
    float lastRecord_ = -1.0f;
};

enum P2FuefukiFollowState {
    P2FUEFUKI_FOLLOW_PARENT    = 0, // TFS_Parent
    P2FUEFUKI_FOLLOW_FOOTPRINT = 1, // TFS_Footprint
};

// Per-tick follower command. hasMove=false means "no decision this tick";
// stop=true is the source TFS_Parent/arrived zero target velocity.
struct P2FuefukiFollowMove {
    bool hasMove = false;
    bool stop    = false;
    float speed  = 0.0f;
    float dirX   = 0.0f;
    float dirZ   = 0.0f;
};

class P2FuefukiFollowController {
public:
    explicit P2FuefukiFollowController(const P2FuefukiFollowParms& p = P2FuefukiFollowParms())
        : parms(p)
        , trail(p.footmarkCapacity)
    {
    }

    void setParms(const P2FuefukiFollowParms& p)
    {
        parms = p;
        reset();
    }
    const P2FuefukiFollowParms& getParms() const { return parms; }

    void reset()
    {
        trail.alloc(parms.footmarkCapacity);
        elapsed_ = 0.0f;
        followers_.clear();
        fallbackRand_ = 1u;
    }

    // Beetle side, once per simulation tick (source updateFootmarks).
    void beetleTick(float beetleX, float beetleZ, float delta)
    {
        if (!std::isfinite(delta) || delta < 0.0f) return;
        elapsed_ += delta;
        if (trail.due(elapsed_, parms) && trail.add(beetleX, beetleZ, elapsed_, parms)) {
            marksRecorded_++;
        }
    }

    // Claim/release events (mirror the interference policy's ownership set).
    void claim(std::uint32_t pikmin)
    {
        if (find(pikmin)) return;
        Follower f;
        f.id = pikmin;
        followers_.push_back(f);
    }
    void release(std::uint32_t pikmin)
    {
        for (std::size_t i = 0; i < followers_.size(); i++) {
            if (followers_[i].id == pikmin) {
                followers_.erase(followers_.begin() + static_cast<std::ptrdiff_t>(i));
                return;
            }
        }
    }
    void releaseAll() { followers_.clear(); }

    bool holds(std::uint32_t pikmin) const { return find(pikmin) != nullptr; }
    int followerCount() const { return static_cast<int>(followers_.size()); }
    std::uint32_t followerAt(int index) const
    {
        return (index >= 0 && index < followerCount()) ? followers_[static_cast<std::size_t>(index)].id : 0u;
    }
    int markCount() const { return trail.capacity(); }
    int marksRecorded() const { return marksRecorded_; }
    const P2FuefukiFootmarks& footmarks() const { return trail; }

    // Follower side, once per simulation tick per held Pikmin. Positions are
    // the host's real positions; beetleVX/VZ feed the source direction blend.
    P2FuefukiFollowMove followerTick(std::uint32_t pikmin, float px, float pz, float beetleX,
                                     float beetleZ, float beetleVX, float beetleVZ, float delta,
                                     P2FuefukiRandFn rnd = nullptr, void* rndContext = nullptr)
    {
        P2FuefukiFollowMove out;
        Follower* f = find(pikmin);
        if (!f || !std::isfinite(delta) || delta < 0.0f) return out;

        if (f->state == P2FUEFUKI_FOLLOW_PARENT) {
            const float distance = dist(beetleX, beetleZ, px, pz);
            f->parentFollowTimer -= delta;
            out.hasMove = true;
            out.stop    = true; // source mParent->mTargetVelocity = 0
            if (f->parentFollowTimer <= 0.0f || distance > parms.followDistance)
                makeTarget(*f, px, pz, beetleX, beetleZ, rnd, rndContext);
            return out;
        }

        // TFS_Footprint
        const int slot = f->targetSlot;
        if (slot < 0) {
            makeTarget(*f, px, pz, beetleX, beetleZ, rnd, rndContext);
            out.hasMove = true;
            out.stop    = true;
            return out;
        }

        float dirX = trail.at(slot).x - px;
        float dirZ = trail.at(slot).z - pz;
        const float distToFootprint = normalise(dirX, dirZ);

        if (distToFootprint > parms.followDistance) {
            makeTarget(*f, px, pz, beetleX, beetleZ, rnd, rndContext);
        } else if (distToFootprint < parms.followDistance * 0.5f) {
            // Source: target velocity zero, back to Parent, re-arm timer.
            out.hasMove = true;
            out.stop    = true;
            f->state    = P2FUEFUKI_FOLLOW_PARENT;
            setTimer(*f, px, pz, beetleX, beetleZ, rnd, rndContext);
            return out;
        }

        // Source's second `dist < FOLLOW_DISTANCE/2` blend branch is
        // unreachable (the branch above returns); kept for fidelity.
        if (distToFootprint < parms.followDistance * 0.5f) {
            float moveX = beetleVX, moveZ = beetleVZ;
            normalise(moveX, moveZ);
            dirX = dirX * 0.5f + moveX * 0.5f;
            dirZ = dirZ * 0.5f + moveZ * 0.5f;
            normalise(dirX, dirZ);
        }

        out.hasMove = true;
        out.stop    = false;
        out.speed   = f->moveSpeed;
        out.dirX    = dirX;
        out.dirZ    = dirZ;
        return out;
    }

private:
    struct Follower {
        std::uint32_t id = 0;
        int state = P2FUEFUKI_FOLLOW_PARENT;
        float parentFollowTimer = 0.0f;
        float moveSpeed = 0.0f;
        int targetSlot = -1;
    };

    static float dist(float ax, float az, float bx, float bz)
    {
        const float dx = ax - bx, dz = az - bz;
        const float d  = std::sqrt(dx * dx + dz * dz);
        return d > 0.0f ? d : 0.0f;
    }

    static float normalise(float& x, float& z)
    {
        const float len = std::sqrt(x * x + z * z);
        if (len > 0.0f) {
            x /= len;
            z /= len;
        }
        return len;
    }

    float rand01(P2FuefukiRandFn rnd, void* context)
    {
        if (rnd) return rnd(context);
        fallbackRand_ = fallbackRand_ * 1664525u + 1013904223u;
        return static_cast<float>((fallbackRand_ >> 8) & 0xFFFFFFu) * (1.0f / 16777216.0f);
    }

    // Source ActTeki::makeTarget (aiTeki.cpp:119). The source never updates
    // distanceToFootstep inside the scan, so the first (most recent) mark
    // within FOLLOW_DISTANCE of the beetle wins; reproduced deliberately.
    void makeTarget(Follower& f, float px, float pz, float bx, float bz, P2FuefukiRandFn rnd, void* ctx)
    {
        const float distance = dist(bx, bz, px, pz);

        if (trail.capacity() == 0) { // source fm->get(0) == nullptr
            f.targetSlot = -1;
            return;
        }

        float distanceToFootstep = 12800.0f;
        if (f.targetSlot >= 0)
            distanceToFootstep = dist(bx, bz, trail.at(f.targetSlot).x, trail.at(f.targetSlot).z);

        f.targetSlot = trail.mostRecentSlot();
        for (int i = trail.capacity() - 1; i >= 0; i--) {
            const int slot = trail.slotAt(i);
            if (slot < 0) continue;
            const float curDist = dist(bx, bz, trail.at(slot).x, trail.at(slot).z);
            if (distanceToFootstep > curDist && curDist < parms.followDistance) {
                f.targetSlot = slot;
                break;
            }
        }

        if (f.targetSlot < 0) return;

        f.state = P2FUEFUKI_FOLLOW_FOOTPRINT;
        if (distance > parms.followDistance)
            f.moveSpeed = parms.farSpeed;
        else
            f.moveSpeed = parms.nearSpeedMin * rand01(rnd, ctx) + (parms.nearSpeedMax - parms.nearSpeedMin);
    }

    // Source ActTeki::setTimer (aiTeki.cpp:254): weight * (0.5*rand+1.0).
    void setTimer(Follower& f, float px, float pz, float bx, float bz, P2FuefukiRandFn rnd, void* ctx)
    {
        const float d      = dist(bx, bz, px, pz);
        const float weight = d < parms.followDistance ? parms.parentTimerNear : parms.parentTimerFar;
        f.parentFollowTimer = weight * (0.5f * rand01(rnd, ctx) + 1.0f);
    }

    Follower* find(std::uint32_t id)
    {
        for (Follower& f : followers_)
            if (f.id == id) return &f;
        return nullptr;
    }
    const Follower* find(std::uint32_t id) const
    {
        for (const Follower& f : followers_)
            if (f.id == id) return &f;
        return nullptr;
    }

    P2FuefukiFollowParms parms;
    P2FuefukiFootmarks trail;
    std::vector<Follower> followers_;
    float elapsed_ = 0.0f;
    int marksRecorded_ = 0;
    std::uint32_t fallbackRand_ = 1u;
};
