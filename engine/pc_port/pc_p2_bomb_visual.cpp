#include "pc_p2_bomb_visual.h"
#include "Graphics.h"
#include "EffectMgr.h"
#include "ItemMgr.h"
#include "Shape.h"
#include "Vector.h"
#include <vector>

void P2BombGauge::draw(Graphics& gfx, const Vector3f& bombWorldPos, float health, float maxHealth) {
    if (!gfx.mCamera) return;
    if (!ready) {
        gauge.mSnapToTargetHealth = true; // bombItem.cpp:82
        gauge.mRenderStyle = LifeGauge::Wheel;
        ready = true;
    }
    gauge.updValue(health, maxHealth);
    gauge.mPosition.input(bombWorldPos);
    gauge.mOffset.set(0.0f, p2bombtelegraph::kGaugeHeight - 15.0f, 0.0f);
    gauge.mScale = 5000.0f / gfx.mCamera->mNear;
    gauge.refresh(gfx);
}

bool pc_p2_bomb_draw_shape(Graphics& gfx, const Matrix4f& view, bool flashing, bool flashOn, float ratio) {
    if (!gfx.mCamera || !itemMgr || !itemMgr->mItemShapes || !itemMgr->mItemShapes[2]) return false;
    Shape* shape = itemMgr->mItemShapes[2]->mShape;
    if (!shape) return false;
    return pc_p2_bomb_draw_tinted(gfx, *shape, view, flashing, flashOn, ratio);
}

bool pc_p2_bomb_draw_tinted(Graphics& gfx, Shape& drawn, const Matrix4f& view, bool flashing, bool flashOn, float ratio) {
    if (!gfx.mCamera) return false;
    Shape* shape = &drawn;
    const p2bombtelegraph::Tint tint = p2bombtelegraph::flashTint(flashOn, ratio);
    struct Saved {
        Material* material;
        Colour poly, konst;
        int r, g, b;
        bool hasTev;
    };
    std::vector<Saved> saved;
    auto mul = [](unsigned char base, unsigned char t) { return (unsigned char)((unsigned)base * t / 255u); };
    if (flashing && shape->mMaterialList && shape->mMaterialCount > 0) {
        for (int m = 0; m < shape->mMaterialCount; ++m) {
            Material& material = shape->mMaterialList[m];
            Saved sv;
            sv.material = &material;
            sv.poly = material.mColourInfo.mColour;
            sv.hasTev = material.mTevInfo != nullptr;
            if (sv.hasTev) {
                sv.konst = material.mTevInfo->mKonstColors[0];
                sv.r = material.mTevInfo->mTevColRegs[0].mAnimatedColor.r;
                sv.g = material.mTevInfo->mTevColRegs[0].mAnimatedColor.g;
                sv.b = material.mTevInfo->mTevColRegs[0].mAnimatedColor.b;
                material.mTevInfo->mKonstColors[0].set(mul(sv.konst.r, tint.r), mul(sv.konst.g, tint.g),
                                                       mul(sv.konst.b, tint.b), sv.konst.a);
                material.mTevInfo->mTevColRegs[0].mAnimatedColor.r = sv.r * tint.r / 255;
                material.mTevInfo->mTevColRegs[0].mAnimatedColor.g = sv.g * tint.g / 255;
                material.mTevInfo->mTevColRegs[0].mAnimatedColor.b = sv.b * tint.b / 255;
            }
            material.mColourInfo.mColour.set(mul(sv.poly.r, tint.r), mul(sv.poly.g, tint.g), mul(sv.poly.b, tint.b),
                                             sv.poly.a);
            saved.push_back(sv);
        }
    }
    shape->updateAnim(gfx, view, nullptr, nullptr);
    shape->drawshape(gfx, *gfx.mCamera, nullptr);
    for (const Saved& sv : saved) {
        sv.material->mColourInfo.mColour = sv.poly;
        if (sv.hasTev) {
            sv.material->mTevInfo->mKonstColors[0] = sv.konst;
            sv.material->mTevInfo->mTevColRegs[0].mAnimatedColor.r = sv.r;
            sv.material->mTevInfo->mTevColRegs[0].mAnimatedColor.g = sv.g;
            sv.material->mTevInfo->mTevColRegs[0].mAnimatedColor.b = sv.b;
        }
    }
    return true;
}

void P2BombSparks::spawn(int effect, float x, float y, float z) {
    if (!effectMgr || count >= 32) return;
    Vector3f pos(x, y, z);
    zen::particleGenerator* gen =
        effectMgr->create(static_cast<EffectMgr::effTypeTable>(effect), pos, nullptr, nullptr);
    if (gen) live[count++] = Live{static_cast<void*>(gen), 0.0f};
}

void P2BombSparks::update(float dt, float maxAge) {
    int kept = 0;
    for (int i = 0; i < count; ++i) {
        live[i].age += dt;
        if (live[i].age > maxAge) {
            if (effectMgr) effectMgr->kill(static_cast<zen::particleGenerator*>(live[i].gen), true);
        } else {
            live[kept++] = live[i];
        }
    }
    count = kept;
}

void P2BombSparks::killAll() {
    if (effectMgr)
        for (int i = 0; i < count; ++i) effectMgr->kill(static_cast<zen::particleGenerator*>(live[i].gen), true);
    count = 0;
}

unsigned pc_p2_bomb_live_generators() { return effectMgr ? effectMgr->getLiveGeneratorCount() : 0u; }
