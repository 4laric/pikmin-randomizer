#pragma once
#include "types.h"
#include "Vector.h"
#include <string>
#include <cstdint>
#include <type_traits>
class Navi;
class Piki;
class PaniAnimKeyListener;
namespace pc_midday {
// The scene codec owns stable IDs and the transaction. No pointer bytes are saved.
enum class Mode { Capture, Validate, Apply };
enum class ScalarKind { U8, S8, U16, S16, U32, S32, U64, S64, F32, F64, Bool };
enum class RefKind { Creature, CollPart, WayPoint, Path, Animation, Action,
    Traversable, CPlate, FormationMgr, Grass, GrassGen, RockGen, Pebble, Plane,
    DynCollObject, AnimKey, AnimListener, ParticleGenerator, Vector3,
    Camera, Controller, SlotListener, Locus, Generator, FormPoint, UpdateMgr,
    CollInfo, CreatureProp, CollTriInfo, Shape, SeContext, Effect,
    ProjectileToken, SAIStateMachine, ItemShape, PelletConfig, PelletView,
    UfoShape, DynParticle, DynBuildShape, Joint, StaticText,
    ObjCollInfo, CollPartUpdater, ParticleNode, ParticleManager,
    ParticleCallback, ParticleData, Texture, ShapeDynMaterials, Material,
    TexAttr, PVWTevInfo, CollGroup, PVWTextureData, Count };
// Ephemeral storage metadata for native census only; never serialized.
struct StrongStorageSlot {
    const void* storage;
    const void* owner;
    const char* ownerType;
    const char* member;
    int index;
    const void* target;
};
class ActorArchive {
public:
    virtual ~ActorArchive() = default;
    virtual Mode mode() const = 0;
    virtual double clock_now() const = 0;
    // Validate and Apply decode into the supplied STAGING local. Failure must
    // leave the transaction rejected. Validate never changes live engine fields.
    virtual bool scalar(const char* key, ScalarKind kind, void* staging) = 0;
    virtual bool reference(const char* key, RefKind kind, void*& staging) = 0;
    virtual bool strongReference(const char* key, RefKind kind, void*& staging, const StrongStorageSlot&) {
        return reference(key,kind,staging);
    }
    virtual bool fail(const char* reason) = 0;
    // Runtime pool handles require the same stable-identity remapping as pointers.
    virtual bool handle(const char* key, RefKind kind, u32& staging) = 0;
    // Opaque 64-bit runtime identities are remapped, never saved as scalars.
    virtual bool token64(const char*, RefKind, u64&) {
        return fail("64-bit logical token adapter unavailable");
    }
    template<class T> bool value(const char* key, ScalarKind kind, T& live) {
        T staging = mode() == Mode::Capture ? live : T{};
        if (!scalar(key, kind, &staging)) return false;
        if (mode() == Mode::Apply) live = staging;
        return true;
    }
#define PC_MIDDAY_FIELD(type, kind) bool field(const char* key, type& v) { return value(key, ScalarKind::kind, v); }
    PC_MIDDAY_FIELD(u8,U8) PC_MIDDAY_FIELD(s8,S8)
    PC_MIDDAY_FIELD(u16,U16) PC_MIDDAY_FIELD(s16,S16)
    PC_MIDDAY_FIELD(u32,U32) PC_MIDDAY_FIELD(s32,S32)
    PC_MIDDAY_FIELD(std::uint64_t,U64) PC_MIDDAY_FIELD(std::int64_t,S64)
    PC_MIDDAY_FIELD(float,F32) PC_MIDDAY_FIELD(double,F64) PC_MIDDAY_FIELD(bool,Bool)
#undef PC_MIDDAY_FIELD
    bool field(const char* key, Vector3f& v);
    template<class Storage> bool strongRef(const char* key, Storage& storage, const void* owner,
                                           const char* ownerType, const char* member, int index=-1) {
        using Pointer=typename std::remove_reference<decltype(storage.mPtr)>::type;
        void* staging=mode()==Mode::Capture?const_cast<void*>(static_cast<const void*>(storage.mPtr)):nullptr;
        StrongStorageSlot slot{&storage,owner,ownerType,member,index,staging};
        if(!strongReference(key,RefKind::Creature,staging,slot))return false;
        if(mode()==Mode::Apply)storage.mPtr=static_cast<Pointer>(staging);
        return true;
    }
    template<class T> bool ref(const char* key, RefKind kind, T*& live) {
        void* staging = mode() == Mode::Capture ? const_cast<void*>(static_cast<const void*>(live)) : nullptr;
        if (!reference(key, kind, staging)) return false;
        if (mode() == Mode::Apply) live = static_cast<T*>(staging);
        return true;
    }
};
class PrefixArchive final : public ActorArchive {
    ActorArchive& parent;
    std::string prefix;
public:
    PrefixArchive(ActorArchive& p, const char* key) : parent(p), prefix(std::string(key)+".") {}
    Mode mode() const override { return parent.mode(); }
    double clock_now() const override { return parent.clock_now(); }
    bool scalar(const char* key, ScalarKind kind, void* p) override { return parent.scalar((prefix+key).c_str(),kind,p); }
    bool reference(const char* key, RefKind kind, void*& p) override { return parent.reference((prefix+key).c_str(),kind,p); }
    bool strongReference(const char* key,RefKind kind,void*& p,const StrongStorageSlot& slot) override { return parent.strongReference((prefix+key).c_str(),kind,p,slot); }
    bool handle(const char* key, RefKind kind, u32& v) override { return parent.handle((prefix+key).c_str(),kind,v); }
    bool token64(const char* key, RefKind kind, u64& v) override { return parent.token64((prefix+key).c_str(),kind,v); }
    bool fail(const char* reason) override { return parent.fail(reason); }
};
inline bool ActorArchive::field(const char* key, Vector3f& v) {
    PrefixArchive a(*this,key);
    return a.field("x",v.x) && a.field("y",v.y) && a.field("z",v.z);
}
// Capture at an engine tick boundary. Pure payload schema and logical reference
// closure validation MUST precede scene begin/allocation. Then allocate actors
// and subobjects in a disposable stage, bind without callbacks/ticks, verify the
// complete stage, and publish paused last. Never transit/init/cleanup here.
// Allocate initialized callback tokens after actor creation, before binding any
// animator listener references. Apply only on a disposable stage.
bool navi_state_subobjects(Navi&, ActorArchive&);
bool navi_listener_index(Navi&, const PaniAnimKeyListener*, u32&);
PaniAnimKeyListener* navi_listener_at(Navi&, u32);
bool navi_states(Navi&, ActorArchive&);
bool piki_states(Piki&, ActorArchive&);
bool piki_actions(Piki&, ActorArchive&);
}
