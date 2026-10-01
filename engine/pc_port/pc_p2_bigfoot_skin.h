#pragma once

// Engine-free J3D skin of the Raging Long Legs mesh (#1018).
//
// `longlegs_BigFoot_skin_00.txt` (P2_BIGFOOT_SKIN_1) is written by the root
// extractor experimental/pikmin2_long_legs_bank.py next to the pose bank, in
// the same vertex order as every baked pose: the authored EVP1 inverse matrix
// of every joint, the DRW1 table (rigid joint, or an envelope of joint/weight
// pairs) and each position/normal as its DRW1 index and raw value. evaluate()
// is J3DMtxBuffer::calcWeightEnvelopeMtx plus the bake's vertex maths
// (experimental/pikmin2_rigid.py apply): D = joint (rigid) or
// sum(weight * joint * inverse) (envelope); position D*p, normal
// cofactor(D)*n / det, normalised. So the clip body with the source IK legs
// gives exactly the mesh J3D would draw for that skeleton.

#include "pc_p2_long_legs_ik.h"

#include <cmath>
#include <sstream>
#include <string>
#include <vector>

namespace p2bigfootskin {

struct Influence {
    int joint = 0;
    float weight = 1.0f;
};

struct Skin {
    int jointCount = 0;
    std::vector<p2ik::M34> inverse;               // per joint
    std::vector<std::vector<Influence>> draws;    // per DRW1 entry
    std::vector<bool> rigid;                      // per DRW1 entry
    std::vector<int> posDraw, nrmDraw;
    std::vector<p2ik::V3> posRaw, nrmRaw;

    bool parse(const std::string& text, std::string* error)
    {
        auto fail = [&](const char* why) {
            if (error) *error = why;
            *this = Skin();
            return false;
        };
        std::istringstream in(text);
        std::string word;
        int count = 0;
        if (!(in >> word) || word != "P2_BIGFOOT_SKIN_1") return fail("header");
        if (!(in >> word >> count) || word != "joints" || count < 1 || count > 64) return fail("joints");
        jointCount = count;
        inverse.assign(size_t(count), p2ik::M34());
        for (int i = 0; i < count; ++i) {
            int index = -1;
            if (!(in >> word >> index) || word != "i" || index != i) return fail("inverse row");
            for (int r = 0; r < 3; ++r)
                for (int c = 0; c < 4; ++c)
                    if (!(in >> inverse[size_t(i)].m[r][c]) || !std::isfinite(inverse[size_t(i)].m[r][c]))
                        return fail("inverse value");
        }
        int drawCount = 0;
        if (!(in >> word >> drawCount) || word != "draws" || drawCount < 1 || drawCount > 1024) return fail("draws");
        draws.assign(size_t(drawCount), {});
        rigid.assign(size_t(drawCount), true);
        for (int i = 0; i < drawCount; ++i) {
            int index = -1;
            std::string kind;
            if (!(in >> word >> index >> kind) || word != "d" || index != i) return fail("draw row");
            if (kind == "r") {
                Influence inf;
                if (!(in >> inf.joint) || inf.joint < 0 || inf.joint >= count) return fail("rigid joint");
                draws[size_t(i)].push_back(inf);
            } else if (kind == "e") {
                int n = 0;
                if (!(in >> n) || n < 1 || n > 8) return fail("envelope count");
                float sum = 0.0f;
                for (int k = 0; k < n; ++k) {
                    Influence inf;
                    if (!(in >> inf.joint >> inf.weight) || inf.joint < 0 || inf.joint >= count
                            || !(inf.weight >= 0.0f))
                        return fail("envelope influence");
                    sum += inf.weight;
                    draws[size_t(i)].push_back(inf);
                }
                if (std::fabs(sum - 1.0f) > 1.0e-3f) return fail("envelope weights");
                rigid[size_t(i)] = false;
            } else {
                return fail("draw kind");
            }
        }
        for (int pass = 0; pass < 2; ++pass) {
            const char* label = pass == 0 ? "positions" : "normals";
            std::vector<int>& idx = pass == 0 ? posDraw : nrmDraw;
            std::vector<p2ik::V3>& values = pass == 0 ? posRaw : nrmRaw;
            int n = 0;
            if (!(in >> word >> n) || word != label || n < 1 || n > 65536) return fail(label);
            idx.assign(size_t(n), 0);
            values.assign(size_t(n), p2ik::V3());
            for (int i = 0; i < n; ++i) {
                p2ik::V3& v = values[size_t(i)];
                if (!(in >> idx[size_t(i)] >> v.x >> v.y >> v.z)) return fail("vertex row");
                if (idx[size_t(i)] < 0 || idx[size_t(i)] >= drawCount) return fail("vertex draw");
                if (!std::isfinite(v.x) || !std::isfinite(v.y) || !std::isfinite(v.z)) return fail("vertex value");
            }
        }
        if (!(in >> word) || word != "end" || (in >> word)) return fail("trailer");
        return true;
    }

    // `joints` are model-space joint matrices (jointCount of them).
    void evaluate(const p2ik::M34* joints, std::vector<p2ik::V3>& pos, std::vector<p2ik::V3>& nrm) const
    {
        std::vector<p2ik::M34> d(draws.size());
        for (size_t i = 0; i < draws.size(); ++i) {
            if (rigid[i]) {
                d[i] = joints[draws[i][0].joint];
                continue;
            }
            p2ik::M34 sum;
            for (int r = 0; r < 3; ++r)
                for (int c = 0; c < 4; ++c) sum.m[r][c] = 0.0f;
            for (const Influence& inf : draws[i]) {
                const p2ik::M34 m = p2ik::mul(joints[inf.joint], inverse[size_t(inf.joint)]);
                for (int r = 0; r < 3; ++r)
                    for (int c = 0; c < 4; ++c) sum.m[r][c] += m.m[r][c] * inf.weight;
            }
            d[i] = sum;
        }
        pos.resize(posRaw.size());
        for (size_t i = 0; i < posRaw.size(); ++i) pos[i] = p2ik::apply(d[size_t(posDraw[i])], posRaw[i]);
        nrm.resize(nrmRaw.size());
        for (size_t i = 0; i < nrmRaw.size(); ++i) nrm[i] = normal(d[size_t(nrmDraw[i])], nrmRaw[i]);
    }

    // experimental/pikmin2_rigid.py apply(normal=True): cofactor / det, normalised.
    static p2ik::V3 normal(const p2ik::M34& m, const p2ik::V3& n)
    {
        const float a = m.m[0][0], b = m.m[0][1], c = m.m[0][2];
        const float d = m.m[1][0], e = m.m[1][1], f = m.m[1][2];
        const float g = m.m[2][0], h = m.m[2][1], i = m.m[2][2];
        const float cof[3][3] = {{e * i - f * h, f * g - d * i, d * h - e * g},
                                 {c * h - b * i, a * i - c * g, b * g - a * h},
                                 {b * f - c * e, c * d - a * f, a * e - b * d}};
        float det = a * cof[0][0] + b * cof[0][1] + c * cof[0][2];
        if (std::fabs(det) < 1.0e-12f) det = det < 0.0f ? -1.0f : 1.0f;
        p2ik::V3 r((cof[0][0] * n.x + cof[0][1] * n.y + cof[0][2] * n.z) / det,
                   (cof[1][0] * n.x + cof[1][1] * n.y + cof[1][2] * n.z) / det,
                   (cof[2][0] * n.x + cof[2][1] * n.y + cof[2][2] * n.z) / det);
        const float len = std::sqrt(r.x * r.x + r.y * r.y + r.z * r.z);
        return len > 0.0f ? p2ik::V3(r.x / len, r.y / len, r.z / len) : r;
    }
};

} // namespace p2bigfootskin
