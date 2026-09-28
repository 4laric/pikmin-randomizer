// Lane 46 (#484, cave wave #468): engine glue for physical cave-item placement.
//
// Reads the host bridge's P2_CAVE_ITEMS_1 config, validates it against the live
// lane-44 proxy rooms layout, spawns one real ``Pellet`` per item at its host
// unit's ground position, draws it with the converted treasure model and credits
// it exactly once through the lane-06 ordinary receipt provider. This is proxy
// geometry and a proxy model: it is a physical placement/carry/receipt slice,
// never a generation PASS.
#include "pc_p2_cave_items_engine.h"
#include "pc_p2_cave_rooms_engine.h"
#include "pc_p2_receipt_host.h"

#include "Camera.h"
#include "Graphics.h"
#include "MapMgr.h"
#include "Pellet.h"
#include "Shape.h"
#include "gameflow.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>
#include <vector>

namespace {
P2CaveItemPlacement placement;
bool itemsActive = false;
Shape* itemShape = nullptr;

struct Spawned {
    P2CaveItemEntry entry;
    Pellet* pellet = nullptr;
};
std::vector<Spawned> spawned;
int deliveredCount = 0;
int deliveryEventCount = 0;

bool readPlacement(const std::string& path, P2CaveItemPlacement& out, std::string& error)
{
    std::ifstream in(path);
    if (!in) {
        error = "cannot open items config: " + path;
        return false;
    }
    return p2CaveItemsParse(in, out, error);
}

// Fresh Parameters chain; never copy the intrusive CoreNode links. Mirrors the
// private-config pattern the room preview uses for cargo actors.
PelletConfig* privateConfig(PelletConfig* source, int weight, int slots)
{
    PelletConfig* result = new PelletConfig;
#define COPY_VALUE(name) result->name.mValue = source->name.mValue
    COPY_VALUE(mPelletName);
    COPY_VALUE(mPelletType);
    COPY_VALUE(mPelletColor);
    COPY_VALUE(mUseDynamicMotion);
    COPY_VALUE(_A0);
    COPY_VALUE(_B0);
    COPY_VALUE(_C0);
    COPY_VALUE(mMatchingOnyonSeeds);
    COPY_VALUE(mNonMatchingOnyonSeeds);
    COPY_VALUE(mPelletScale);
    COPY_VALUE(mCarryInfoHeight);
    COPY_VALUE(mAnimSoundID);
    COPY_VALUE(mBounceSoundID);
#undef COPY_VALUE
    result->mModelId = source->mModelId;
    result->mPelletId = source->mPelletId;
    result->mUnusedId = source->mUnusedId;
    result->mRepairAnimJointIndex = source->mRepairAnimJointIndex;
    result->mCarryMinPikis.mValue = weight;
    result->mCarryMaxPikis.mValue = slots;
    return result;
}

int indexOf(Pellet* pellet)
{
    for (std::size_t i = 0; i < spawned.size(); ++i) {
        if (spawned[i].pellet == pellet) return static_cast<int>(i);
    }
    return -1;
}

PelletConfig* treasureTemplate()
{
    if (!pelletMgr) return nullptr;
    Iterator it(pelletMgr);
    CI_LOOP(it) {
        Pellet* pellet = static_cast<Pellet*>(*it);
        if (pellet && pellet->mConfig && pellet->mConfig->mModelId.mId == 'pr05') {
            return pellet->mConfig;
        }
    }
    return nullptr;
}
// #441 receipt-host API: grant goes through an explicit ledger handle.
P2ReceiptHostHandle receiptHandle = nullptr;
}  // namespace

bool pc_p2_cave_items_active() { return itemsActive; }

const P2CaveItemPlacement* pc_p2_cave_items_placement() { return itemsActive ? &placement : nullptr; }

int pc_p2_cave_items_spawned() { return static_cast<int>(spawned.size()); }

int pc_p2_cave_items_delivered() { return deliveredCount; }

int pc_p2_cave_items_delivery_events() { return deliveryEventCount; }

Pellet* pc_p2_cave_items_pellet_for(const char* item)
{
    if (!item) return nullptr;
    for (Spawned& entry : spawned) {
        if (entry.entry.item == item) return entry.pellet;
    }
    return nullptr;
}

void pc_p2_cave_items_shutdown()
{
    placement = P2CaveItemPlacement{};
    itemsActive = false;
    itemShape = nullptr;
    spawned.clear();
    deliveredCount = 0;
    deliveryEventCount = 0;
    if (receiptHandle) pc_p2_receipt_host_close(receiptHandle);
    receiptHandle = nullptr;
}

void pc_p2_cave_items_setup()
{
    placement = P2CaveItemPlacement{};
    itemsActive = false;
    spawned.clear();
    deliveredCount = 0;
    deliveryEventCount = 0;
    itemShape = nullptr;

    const char* env = std::getenv("PIKMIN_CAVE_ITEMS");
    const std::string path = env && env[0] ? env : "p2-cave-items.txt";
    if (!std::ifstream(path)) return;

    std::string error;
    if (!readPlacement(path, placement, error)) {
        std::printf("P2_CAVE_ITEMS FAILED reason=%s\n", error.c_str());
        std::fflush(stdout);
        return;
    }
    const P2CaveRoomLayout* rooms = pc_p2_cave_rooms_layout();
    if (!rooms) {
        std::printf("P2_CAVE_ITEMS FAILED reason=no rooms layout\n");
        std::fflush(stdout);
        return;
    }
    if (!p2CaveItemsValidatePlacement(placement, *rooms, error)) {
        std::printf("P2_CAVE_ITEMS FAILED reason=placement: %s\n", error.c_str());
        std::fflush(stdout);
        return;
    }

    PelletConfig* templateConfig = treasureTemplate();
    if (!templateConfig) {
        std::printf("P2_CAVE_ITEMS FAILED reason=no pr05 treasure template\n");
        std::fflush(stdout);
        return;
    }

    itemShape = gameflow.loadShape("courses/pikmin2room/treasure.mod", true);
    if (!itemShape) {
        std::printf("P2_CAVE_ITEMS FAILED reason=missing converted treasure model\n");
        std::fflush(stdout);
        return;
    }
    for (int i = 0; i < itemShape->mTexAttrCount; ++i) {
        if (itemShape->mTexAttrList[i].mTexture) itemShape->mTexAttrList[i].mTexture->attach();
    }

    for (const P2CaveItemEntry& entry : placement.items) {
        const P2CaveRoomUnit* unit = p2CaveRoomsFind(*rooms, entry.host);
        if (!unit) {
            std::printf("P2_CAVE_ITEMS FAILED reason=missing host unit %s\n", entry.host.c_str());
            std::fflush(stdout);
            return;
        }
        const float x = p2CaveRoomsWorldX(*rooms, *unit);
        const float z = p2CaveRoomsWorldZ(*rooms, *unit);
        const float y = mapMgr ? mapMgr->getMinY(x, z, true) : 0.f;
        // PelletMgr::newPellet/getConfig key on the config's model id (not its
        // mPelletId), so spawn from the room treasure's model id ('pr05').
        Pellet* pellet = pelletMgr->newPellet(templateConfig->mModelId.mId, nullptr);
        if (!pellet) {
            std::printf("P2_CAVE_ITEMS FAILED reason=spawn refused slot=%s\n", entry.slot_id.c_str());
            std::fflush(stdout);
            return;
        }
        pellet->mConfig = privateConfig(templateConfig, 1, 1);
        pellet->init(Vector3f(x, y, z));
        pellet->startAI(0);
        Spawned record;
        record.entry = entry;
        record.pellet = pellet;
        spawned.push_back(record);
        std::printf("P2_CAVE_ITEM_ACTOR slot=%s item=%s host=%s kind=%s tagged=%d x=%.3f y=%.3f z=%.3f pellet=%p\n",
                    entry.slot_id.c_str(), entry.item.c_str(), entry.host.c_str(), entry.kind.c_str(),
                    entry.tagged ? 1 : 0, x, y, z, static_cast<void*>(pellet));
    }
    // Lane-06 ordinary receipt provider: durable exactly-once ledger for the
    // physical cave treasures. Opened lazily on the first grant so a run that
    // never collects one leaves no sidecar.
    itemsActive = true;
    std::printf("%s\n", p2CaveItemsMarker(placement).c_str());
    std::printf("%s\n", p2CaveItemsProjection(placement).c_str());
    std::fflush(stdout);
}

bool pc_p2_cave_items_draw_pellet(Pellet* pellet, Graphics& gfx, Matrix4f& matrix)
{
    if (!itemsActive || !pellet) return false;
    if (indexOf(pellet) < 0) return false;
    if (itemShape) {
        itemShape->updateAnim(gfx, matrix, nullptr, pellet);
        itemShape->drawshape(gfx, *gfx.mCamera, nullptr);
    }
    return true;
}

bool pc_p2_cave_items_deliver(Pellet* pellet)
{
    if (!itemsActive || !pellet) return false;
    const int index = indexOf(pellet);
    if (index < 0) return false;
    const P2CaveItemEntry& entry = spawned[index].entry;

    if (!receiptHandle) {
        const char* env = std::getenv("PIKMIN_P2_ITEM_RECEIPT_PATH");
        const char* path = env && env[0] ? env : "p2-cave-item-receipts.txt";
        receiptHandle = pc_p2_receipt_host_open(path);
        if (!receiptHandle) {
            std::printf("P2_CAVE_ITEM_RECEIPT ERROR slot=%s open_failed=1\n", entry.slot_id.c_str());
            std::fflush(stdout);
            return true;
        }
    }
    const std::string reward = "treasure:" + placement.cave + ":f"
                               + std::to_string(placement.floor) + ":" + entry.slot_id;
    const std::string seed = std::to_string(placement.seed);
    const P2ReceiptHostResult result = pc_p2_receipt_host_grant(
        receiptHandle, seed.c_str(), reward.c_str(), entry.host.c_str(), "cave_treasure");
    const bool granted = result == P2ReceiptHostResult::Granted;
    if (granted) ++deliveredCount;
    if (result != P2ReceiptHostResult::Error) ++deliveryEventCount;
    std::printf("P2_CAVE_ITEM_RECEIPT id=%s item=%s host=%s tagged=%d new=%d tag=cave_treasure seed=%llu result=%d\n",
                reward.c_str(), entry.item.c_str(), entry.host.c_str(), entry.tagged ? 1 : 0,
                granted ? 1 : 0, static_cast<unsigned long long>(placement.seed),
                static_cast<int>(result));
    std::fflush(stdout);
    return true;
}
