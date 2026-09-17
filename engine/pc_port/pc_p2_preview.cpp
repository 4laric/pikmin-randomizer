#include "pc_p2_frog.h"
#include "pc_p2_kogane.h"
#include "pc_p2_mamuta.h"
#include "pc_p2_waterwraith_register.h"
#include "pc_p2_tank.h"
#include "pc_p2_hiba.h"
#include "pc_p2_dweevil.h"
#include "pc_p2_bombotakara.h"
#include "pc_p2_qurione.h"
#include "pc_p2_shijimi.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_bombsarai_teki.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_groink_teki.h"
#include "pc_p2_sheargrub.h"
#include "pc_p2_king_teki.h"
#include "pc_p2_queen_teki.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_dwarf_orange.h"
#include "pc_p2_kochappy_fsm.h"
#include "pc_p2_breadbug_visual.h"
#include "pc_p2_giant_breadbug_visual.h"
#include "pc_p2_bulblax_visual.h"
#include "pc_p2_breadbug_actor.h"
#include "pc_p2_giant_breadbug_actor.h"
#include "pc_p2_queen.h"
#include "pc_p2_king.h"
#include "pc_p2_flora_actor.h"
#include "pc_p2_pom.h"
#include "pc_p2_plant.h"
#include "pc_p2_batch2.h"
#include "pc_p2_sokkuri.h"
#include "pc_p2_armor.h"
#include "pc_p2_otakara.h"
#include "pc_p2_elecbug.h"
#include "pc_p2_tamago.h"
#include "pc_p2_umimushi.h"
#include "pc_p2_jigumo.h"
#include "pc_p2_snakejoint.h"
#include "pc_p2_dangomushi.h"
#include "pc_p2_catfish.h"
#include "pc_p2_mar.h"
#include "pc_p2_mar_receipt.h"
#include "pc_p2_hanachirashi.h"
#include "pc_p2_tadpole.h"
#include "pc_p2_hana.h"
#include "pc_p2_imomushi.h"
#include "pc_p2_batch3.h"
#include "pc_p2_long_legs.h"
#include "pc_p2_projectiles.h"
#include "pc_p2_hardlanes.h"
#include "pc_p2_preview.h"
#include "pc_bbft.h"
#include "Pellet.h"
#include "PlayerState.h"
#include "MapMgr.h"
#include "Shape.h"
#include "Graphics.h"
#include "Camera.h"
#include <SDL2/SDL.h>
#include "gameflow.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Texture.h"
#include "system.h"
#include "pc_p2_economy.h"
#include "pc_p2_purple.h"
#include "pc_p2_purple_flight.h"
#include "pc_p2_purple_motion.h"
#include "pc_p2_white.h"
#include "pc_p2_bulbmin.h"
#include "pc_p2_white_poison.h"
#include "pc_p2_cave.h"
#include "pc_p2_enemy.h"
#include "pc_p2_cargo.h"
#include "pc_p2_preview_policy.h"
#include "pc_p2_placement_probe.h"
#include <fstream>
#include <filesystem>
#include <vector>
#include "GoalItem.h"
#include "ItemMgr.h"
#include "Generator.h"
#include "teki.h"
#include <map>
#include <string>
#include <cstdio>
#include <cstdlib>

// One disposable room only. This is deliberately not a campaign treasure registry.
static Pellet* previewTreasure = nullptr;
static Shape* previewShape = nullptr;
static bool delivered = false;
static bool cargoFree = false;
static bool setupComplete = false;
static int initialRepairs = 0;
static GoalItem* podAnchor=nullptr;
static Shape* podShape=nullptr;
static P2Economy economy;
static std::string treasureId;
static int treasureValue=0,corpseValue=0;
static std::map<PelletView*,std::string> corpses;
struct Cargo { P2CargoSpec spec; Pellet* actor; Shape* shape; PelletConfig* config; };
static std::vector<Cargo> cargo;
static Cargo* cargoFor(Pellet* p){for(auto& c:cargo)if(c.actor==p)return &c;return nullptr;}
int pc_p2_preview_cargo_count(){return int(cargo.size());}
Pellet* pc_p2_preview_cargo_at(int index){return index>=0&&index<int(cargo.size())?cargo[index].actor:nullptr;}
Shape* pc_p2_preview_cargo_shape(Pellet* p){Cargo* c=cargoFor(p);return c?c->shape:nullptr;}
// Lifecycle (#397): re-scan live Chappy actors into the corpse receipt registry
// without touching the economy or loaded shapes. Existing entries (including a
// corpse already in flight) are preserved, so a second delivery after a respawn
// resolves to the same generator-keyed receipt. Additive and behavior-neutral
// for any caller that never invokes it.
void pc_p2_preview_rebind_corpses() {
    if(!pc_pikipelago_room_preview() || !podAnchor) return;
    const size_t before=corpses.size();
    Iterator enemies(tekiMgr);
    CI_LOOP(enemies) {
        Teki* enemy=static_cast<Teki*>(*enemies);
        if(enemy && enemy->mTekiType==TEKI_Chappy && enemy->mGenerator)
            corpses[static_cast<PelletView*>(enemy)]="corpse:"+std::to_string(enemy->mGenerator->_70);
    }
    std::printf("[Pikipelago] P2_POD_CORPSES_REBOUND before=%zu after=%zu\n",before,corpses.size());
    std::fflush(stdout);
}
int pc_p2_preview_corpse_count(){return int(corpses.size());}
// Build a fresh Parameters chain and CoreNode; never copy their intrusive links.
// Values/immutable source name are copied individually. Configs live on App heap,
// like the actors, for this one-floor process. They are not deleted on collection.
static PelletConfig* privateConfig(PelletConfig* source,int weight,int slots) {
    PelletConfig* result=new PelletConfig;
#define COPY_VALUE(name) result->name.mValue=source->name.mValue
    COPY_VALUE(mPelletName);COPY_VALUE(mPelletType);COPY_VALUE(mPelletColor);
    COPY_VALUE(mUseDynamicMotion);COPY_VALUE(_A0);COPY_VALUE(_B0);COPY_VALUE(_C0);
    COPY_VALUE(mMatchingOnyonSeeds);COPY_VALUE(mNonMatchingOnyonSeeds);
    COPY_VALUE(mPelletScale);COPY_VALUE(mCarryInfoHeight);COPY_VALUE(mAnimSoundID);COPY_VALUE(mBounceSoundID);
#undef COPY_VALUE
    result->mModelId=source->mModelId;result->mPelletId=source->mPelletId;result->mUnusedId=source->mUnusedId;
    result->mRepairAnimJointIndex=source->mRepairAnimJointIndex;
    result->mCarryMinPikis.mValue=weight;result->mCarryMaxPikis.mValue=slots;
    return result;
}
static void podTitle(const std::string& recent) {
    if(SDL_Window* window=SDL_GL_GetCurrentWindow()) {
        std::string title="Pikipelago - Research Pod: "+std::to_string(economy.total())+" Pokos";
        if(!recent.empty())title+=" | "+recent;
        SDL_SetWindowTitle(window,title.c_str());
    }
}
Suckable* pc_p2_preview_goal(){return pc_pikipelago_room_preview()?podAnchor:nullptr;}
bool pc_p2_preview_is_pod(GoalItem* goal){return pc_pikipelago_room_preview() && podAnchor && goal==podAnchor;}
int pc_p2_preview_pokos(){return podAnchor?economy.total():-1;}
bool pc_p2_preview_ready() { return pc_pikipelago_room_preview() && previewShape && previewTreasure; }
bool pc_p2_preview_cargo_free_ready() { return pc_pikipelago_room_preview() && cargoFree && setupComplete; }
Pellet* pc_p2_preview_treasure() { return previewTreasure; }

void pc_p2_preview_setup() {
    if (!pc_pikipelago_room_preview()) return;
    previewTreasure = nullptr; previewShape = nullptr; delivered = false;
    cargoFree=false;setupComplete=false;treasureId.clear();treasureValue=0;corpseValue=0;
    podAnchor=nullptr;podShape=nullptr;corpses.clear();
    initialRepairs = playerState->getCurrParts();
    cargo.clear();std::vector<P2CargoSpec> specs;
    const bool hasCargoConfig=std::filesystem::exists("p2-cargo.txt");
    if(std::filesystem::exists("p2-cargo-free.txt")) {
        std::ifstream config("p2-cargo-free.txt");
        try { p2ReadCargoFree(config); cargoFree=true; }
        catch(const std::exception& e){std::fprintf(stderr,"P2 preview: %s\n",e.what());std::abort();}
        if(hasCargoConfig){std::fprintf(stderr,"P2 cargo-free preview forbids cargo config\n");std::abort();}
    }
    if(hasCargoConfig) {
        std::ifstream config("p2-cargo.txt");if(!config){std::fprintf(stderr,"Cannot read P2 cargo config\n");std::abort();}
        try{specs=p2ReadCargo(config);}catch(const std::exception& e){std::fprintf(stderr,"P2 cargo: %s\n",e.what());std::abort();}
    }
    std::map<uint32_t,Pellet*> spawned;
    int roomBolts = 0, stagedBolts = 0;
    Pellet* roomBoltTreasure = nullptr;
    Iterator it(pelletMgr);
    CI_LOOP(it) {
        Pellet* pellet = static_cast<Pellet*>(*it);
        if (pellet && pellet->mConfig->mModelId.mId == 'pr05') {
            // Reconcile preview pr05 pellets with arena overlays (#679/#695):
            // the isolated room spawns its own generator-less (id 0) pr05 bolts
            // and a room may legitimately carry more than one, so room bolts are
            // never staged cargo and never count as a duplicate treasure. In
            // no-cargo mode the first room bolt is kept as a fallback treasure;
            // a staged (nonzero generator id) pr05 still wins and must be
            // unique, so a genuinely ambiguous arena with two staged bolts
            // still aborts below.
            const uint32_t genId = pellet->mGenerator ? pellet->mGenerator->_70 : 0;
            if(!specs.empty()) {
                if (genId == 0) { ++roomBolts; continue; }
                ++stagedBolts;
                if(!spawned.emplace(genId,pellet).second){std::fprintf(stderr,"P2 cargo duplicate/missing generator\n");std::abort();}
                continue;
            }
            if (genId == 0) { ++roomBolts; if(!roomBoltTreasure) roomBoltTreasure = pellet; continue; }
            ++stagedBolts;
            if (previewTreasure) { std::fprintf(stderr,"P2 preview: duplicate treasure\n"); std::abort(); }
            previewTreasure = pellet;
        }
    }
    std::printf("[Pikipelago] P2_PREVIEW_PR05 room_bolts=%d staged=%d cargo=%d\n", roomBolts, stagedBolts, int(!specs.empty()));
    std::fflush(stdout);
    if(!specs.empty()) {
        if(spawned.size()!=specs.size()){std::fprintf(stderr,"P2 cargo actor count mismatch\n");std::abort();}
        for(const auto& spec:specs){auto found=spawned.find(spec.generator);if(found==spawned.end()){std::fprintf(stderr,"P2 cargo unknown actor %u\n",spec.generator);std::abort();}cargo.push_back({spec,found->second,nullptr,nullptr});}
        previewTreasure=cargo.front().actor;
    }
    // No-cargo fallback (#695): with no staged treasure, the room's own bolt is
    // still a valid preview treasure, so the default room preview reaches
    // P2_ROOM_READY instead of aborting on the room's second bolt.
    else if(!previewTreasure) previewTreasure = roomBoltTreasure;
    try { p2ValidatePreviewCargo(cargoFree,hasCargoConfig,previewTreasure!=nullptr); }
    catch(const std::exception& e){std::fprintf(stderr,"P2 preview: %s\n",e.what());std::abort();}
    const int previousHeap = gsys->setHeap(SYSHEAP_App);
    std::printf("[Pikipelago] P2_PREVIEW_HEAP previous=%d map_vertices=%p movie_range=%p..%p\n", previousHeap,
        static_cast<void*>(mapMgr->mMapModel->mVertexList),
        reinterpret_cast<void*>(gsys->mHeaps[SYSHEAP_Movie].mInitialStackTop),
        reinterpret_cast<void*>(gsys->mHeaps[SYSHEAP_Movie].mInitialStackLimit));
    if(!cargoFree) {
    std::string firstModel=cargo.empty()?"treasure":cargo.front().spec.model;
    previewShape = gameflow.loadShape(("courses/pikmin2room/"+firstModel+".mod").c_str(), true);
    if (!previewShape) { std::fprintf(stderr,"P2 preview: converted treasure missing\n"); std::abort(); }
    // Stage finalSetup can run during rendering, where attachObjs is forbidden.
    // Upload only this late-loaded static model's textures through the PC texture API.
    for (int i=0;i<previewShape->mTexAttrCount;++i)
        if (previewShape->mTexAttrList[i].mTexture) previewShape->mTexAttrList[i].mTexture->attach();
    }
    if(FILE* config=std::fopen("p2-pod.txt","r")) {
        char version[32],id[64],corpseId[64];int weight,capacity;
        bool valid=std::fscanf(config,"%31s %63s %d %d %d %63s %d",version,id,&treasureValue,&weight,&capacity,corpseId,&corpseValue)==7;
        std::fclose(config);
        if(!valid || std::string(version)!="P2_POD_1" || weight<1 || weight>1000 || capacity<1 || capacity>128 || treasureValue<0 || treasureValue>1000000 || corpseValue<0 || corpseValue>1000000 || std::string(corpseId)!="Kochappy") {
            std::fprintf(stderr,"Invalid P2 pod config\n");std::abort();
        }
        treasureId=id;economy.load("p2-economy.txt");
        podAnchor=itemMgr->getContainer(Red);
        if(!podAnchor){std::fprintf(stderr,"P2 pod anchor missing\n");std::abort();}
        if(previewTreasure && cargo.empty()) {
            previewTreasure->mConfig->mCarryMinPikis.mValue=weight;
            previewTreasure->mConfig->mCarryMaxPikis.mValue=capacity;
        }
        podShape=gameflow.loadShape("courses/pikmin2room/pod.mod",true);
        if(!podShape){std::fprintf(stderr,"P2 pod shape missing\n");std::abort();}
        for(int i=0;i<podShape->mTexAttrCount;++i)if(podShape->mTexAttrList[i].mTexture)podShape->mTexAttrList[i].mTexture->attach();
        pc_p2_preview_rebind_corpses();
        std::printf("[Pikipelago] P2_POD_READY treasure=%s value=%d weight=%d capacity=%d pokos=%d\n",id,treasureValue,weight,capacity,economy.total());
        podTitle("");
    }
    if(!cargo.empty()) {
        if(!podAnchor){std::fprintf(stderr,"P2 cargo requires Pod\n");std::abort();}
        for(auto& c:cargo) {
            c.config=privateConfig(c.actor->mConfig,c.spec.weight,c.spec.slots);
            c.actor->mConfig=c.config;
            c.shape=&c==&cargo.front()?previewShape:gameflow.loadShape(("courses/pikmin2room/"+c.spec.model+".mod").c_str(),true);
            if(!c.shape){std::fprintf(stderr,"P2 cargo missing model\n");std::abort();}
            for(int i=0;i<c.shape->mTexAttrCount;++i)if(c.shape->mTexAttrList[i].mTexture)c.shape->mTexAttrList[i].mTexture->attach();
            std::printf("P2_CARGO_READY generator=%u instance=%s model=%s value=%d weight=%d slots=%d config=%p\n",c.spec.generator,c.spec.instance.c_str(),c.spec.model.c_str(),c.spec.value,c.spec.weight,c.spec.slots,(void*)c.config);
        }
        treasureId=cargo.front().spec.instance;treasureValue=cargo.front().spec.value;
    }
    pc_p2_snow_setup();
    pc_p2_sheargrub_setup();
    pc_p2_kochappy_setup();
    pc_p2_dwarf_orange_setup();
    pc_p2_kochappy_fsm_setup();
    pc_p2_breadbug_visual_setup();
    pc_p2_giant_breadbug_visual_setup();
    pc_p2_bulblax_visual_setup();
    pc_p2_queen_setup();
    pc_p2_king_setup();
    pc_p2_breadbug_actor_setup();
    pc_p2_giant_breadbug_actor_setup();
    pc_p2_frog_setup();
    pc_p2_kogane_setup();
    pc_p2_mamuta_setup();
    pc_p2_tank_setup();
    pc_p2_hiba_setup();
    pc_p2_flora_setup();
    pc_p2_pom_setup();
    pc_p2_plant_setup();
    pc_p2_dweevil_setup();
    pc_p2_bombotakara_setup();
    pc_p2_qurione_setup();
    pc_p2_shijimi_setup();
    pc_p2_batch2_setup();
    pc_p2_sokkuri_setup();
    pc_p2_armor_setup();
    pc_p2_otakara_setup();
    pc_p2_elecbug_setup();
    pc_p2_tamago_setup();
    pc_p2_umimushi_setup();
    pc_p2_jigumo_setup();
    pc_p2_snakejoint_setup();
    pc_p2_dangomushi_setup();
    pc_p2_catfish_setup();
    pc_p2_mar_setup();
    pc_p2_hanachirashi_setup();
    pc_p2_tadpole_setup();
    pc_p2_hana_setup();
    pc_p2_imomushi_setup();
    pc_p2_batch3_setup();
    pc_p2_long_legs_setup();
    pc_p2_projectiles_setup();
    pc_p2_hardlanes_setup();
    pc_p2_purple_setup();
    pc_p2_purple_flight_setup();
    pc_p2_purple_motion_setup();
    pc_p2_white_setup();
    pc_p2_bulbmin_setup();
    pc_p2_white_poison_setup();
    pc_p2_cave_setup();
    // Lane-11 opt-in driver: resolve the Mother Bulbmin stand-in host (the
    // labeled Dwarf Red registry, else the bare Chappy-family generator row) and
    // birth the source flock behind it. Runs AFTER pc_p2_cave_setup so the wild
    // births do not perturb the cave's restore spawn-count validation. No-op
    // unless PIKMIN_P2_BULBMIN/p2-bulbmin.txt is set.
    pc_p2_bulbmin_attach_mother(static_cast<Creature*>(pc_p2_bulbmin_mother_host()));
    // Lane-11 dedicated mother path: register the same host under an explicit
    // label from PIKMIN_P2_BULBMIN_MOTHER (no-op unless the env value is set).
    pc_p2_bulbmin_attach_dedicated_mother();
    gsys->setHeap(previousHeap);
    const float points[][2]={{-85,0},{-175,-100},{185,-180},{-220,-180}};
    for (const auto& point : points)
        std::printf("[Pikipelago] P2_ROOM_GROUND x=%.1f z=%.1f y=%.3f\n",point[0],point[1],mapMgr->getMinY(point[0],point[1],true));
    // Lane-04 (placement) native evidence probe: sample live terrain/water/route
    // facts at each spawned actor's position. Read-only; additively after the
    // legacy room ground probe.
    pc_p2_placement_probe_run();
    setupComplete=true;
    if(cargoFree) std::printf("[Pikipelago] P2_ROOM_CARGO_FREE_READY cargo=0 repairs=%d\n",initialRepairs);
    else std::printf("[Pikipelago] P2_ROOM_READY treasure=%s carry=%d repairs=%d\n",podAnchor?treasureId.c_str():"bolt",previewTreasure->mConfig->mCarryMinPikis(),initialRepairs);
    std::fflush(stdout);
}

bool pc_p2_preview_draw(Pellet* pellet, Graphics& gfx, Matrix4f& matrix) {
    if(!pc_pikipelago_room_preview() || !pellet)return false;
    Cargo* c=cargoFor(pellet);Shape* shape=c?c->shape:(pellet==previewTreasure?previewShape:nullptr);
    if(!shape || pellet->mConfig->mModelId.mId!='pr05')return false;
    shape->updateAnim(gfx,matrix,nullptr,pellet);
    shape->drawshape(gfx,*gfx.mCamera,nullptr);
    return true;
}

bool pc_p2_preview_deliver(Pellet* pellet) {
    if(!pellet)return false;
    if(pc_pikipelago_room_preview() && podAnchor) {
        // P1's long-idle captain can be carried like a pellet. Returning him to
        // the Pod must finish the normal wake-up path, never create money/seeds.
        if(naviMgr && pellet->mConfig->mModelId.mId=='navi' && pellet->mPelletView==static_cast<PelletView*>(naviMgr->getNavi())) {
            std::puts("[Pikipelago] P2_POD_CAPTAIN_RETURN pokos_unchanged=1 seeds=0");return true;
        }
        // P2 Pellet Posy capture receptor: the released pellet was observed and
        // claimed by the flora module; persist its receipt before consuming it.
        if(pc_p2_flora_receipt(pellet)) {
            std::printf("[Pikipelago] P2_FLORA_DELIVER onion_receipt=1\n");std::fflush(stdout);return true;
        }
        if(cargoFree){std::fprintf(stderr,"Cargo-free P2 Pod refuses cargo rewards and seed side effects\n");std::abort();}
        std::string receipt;int value=0;Cargo* c=cargoFor(pellet);bool waterwraithCorpse=false;
        if(c){receipt="treasure:"+c->spec.instance;value=c->spec.value;}
        else if(pellet==previewTreasure){receipt="treasure:"+treasureId;value=treasureValue;}
        else if(unsigned generator=0;pc_p2_sheargrub_receipt(pellet->mPelletView,generator,value)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"uji:"+std::to_string(generator);
        }
        else if(unsigned generator=0;pc_p2_mamuta_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"mamuta:"+std::to_string(generator);value=corpseValue;
        }
        else if(unsigned generator=0;pc_p2_mar_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"mar:"+std::to_string(generator);value=corpseValue;
        }
        else if(unsigned generator=0;pc_p2_bombsarai_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"bombsarai:"+std::to_string(generator);value=corpseValue;
        }
        else if(unsigned generator=0;pc_p2_kurage_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"kurage:"+std::to_string(generator);value=corpseValue;
        }
        else if(unsigned generator=0;pc_p2_sarai_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"sarai:"+std::to_string(generator);value=corpseValue;
        }
        else if(unsigned generator=0;pc_p2_otakara_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"otakara:"+std::to_string(generator);value=corpseValue;
        }
        else if(unsigned generator=0;pc_p2_waterwraith_receipt(pellet,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"waterwraith:"+std::to_string(generator);value=corpseValue;
            waterwraithCorpse=true;
        }
        else if(unsigned generator=0;pc_p2_king_teki_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"king:"+std::to_string(generator);value=corpseValue;
        }
        else if(unsigned generator=0;pc_p2_queen_teki_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"queen:"+std::to_string(generator);value=corpseValue;
        }
        // Lane 21 (#198): Groink carcass sidecar receipt (corpse:groink:<gen>).
        else if(unsigned generator=0;pc_p2_groink_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"groink:"+std::to_string(generator);value=corpseValue;
        }
        // Lane 28 (#245): Fuefuki (Antenna Beetle) carcass via the vehicle host.
        else if(unsigned generator=0;pc_p2_hardlanes_fuefuki_receipt(pellet->mPelletView,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"fuefuki:"+std::to_string(generator);value=corpseValue;
        }
        // Lane 26 (#312): Long Legs corpse receipt (corpse:longlegs:<gen>), keyed on
        // the delivered Pellet* (a viewless stand-in corpse would still resolve).
        else if(unsigned generator=0;pc_p2_long_legs_receipt(pellet,generator)) {
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+"longlegs:"+std::to_string(generator);value=corpseValue;
        }
        else {
            auto found=corpses.find(pellet->mPelletView);
            if(found==corpses.end()) {std::fprintf(stderr,"Unregistered P2 pod cargo id=%08x view=%p pellet=%p treasure=%p; refusing seed side effects\n",pellet->mConfig->mModelId.mId,(void*)pellet->mPelletView,(void*)pellet,(void*)previewTreasure);std::abort();}
            receipt="corpse:"+pc_p2_cave_receipt_prefix()+found->second.substr(7);value=corpseValue;
        }
        bool added=economy.credit(receipt,value);
        podTitle(std::string(waterwraithCorpse ? "Waterwraith" : (c?c->spec.instance.c_str():pellet==previewTreasure?treasureId.c_str():(pc_p2_king_teki_name(pellet->mPelletView)?pc_p2_king_teki_name(pellet->mPelletView):pc_p2_queen_teki_name(pellet->mPelletView)?pc_p2_queen_teki_name(pellet->mPelletView):pc_p2_sheargrub_name(pellet->mPelletView)?pc_p2_sheargrub_name(pellet->mPelletView):pc_p2_enemy_name(pellet->mPelletView)?pc_p2_enemy_name(pellet->mPelletView):"Dwarf Bulborb"))) + " +" + std::to_string(added?value:0));
        pc_p2_purple_status();
        std::printf("[Pikipelago] P2_POD_RECEIPT id=%s value=%d new=%d pokos=%d seeds=0\n",receipt.c_str(),value,int(added),economy.total());
        if(pellet==previewTreasure) {
            delivered=true;
            if(FILE* file=std::fopen("treasure-receipt.txt","w")){std::fprintf(file,"treasure=%s count=1 pokos=%d\n",treasureId.c_str(),economy.total());std::fclose(file);}
        }
        if(playerState->getCurrParts()!=initialRepairs){std::fprintf(stderr,"P2 pod changed repairs\n");std::abort();}
        std::fflush(stdout);return true;
    }
    if (!pc_pikipelago_room_preview() || pellet != previewTreasure || pellet->mConfig->mModelId.mId != 'pr05') return false;
    if (!delivered) {
        delivered = true;
        const int repairs = playerState->getCurrParts();
        if (repairs != initialRepairs) { std::fprintf(stderr,"P2 preview: unexpected repair progression\n"); std::abort(); }
        if (FILE* file=std::fopen("treasure-receipt.txt","w")) {
            std::fprintf(file,"room=room_4x4a_4_conc treasure=bolt count=1 repairs=%d\n",repairs);
            std::fclose(file);
        }
        std::printf("[Pikipelago] P2_TREASURE_DELIVERED id=bolt count=1 repairs=%d seeds=0\n",repairs);
        std::fflush(stdout);
    }
    return true;
}

bool pc_p2_preview_draw_pod(GoalItem* goal,Graphics& gfx,Matrix4f& matrix) {
    if(!pc_p2_preview_is_pod(goal) || !podShape)return false;
    // Static visual uses the existing destination's suction height; animation is deferred.
    Matrix4f world,view;Vector3f position=goal->mSRT.t;position.y+=74;
    world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),position);
    gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
    podShape->updateAnim(gfx,view,nullptr,goal);podShape->drawshape(gfx,*gfx.mCamera,nullptr);
    return true;
}
