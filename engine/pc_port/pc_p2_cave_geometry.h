// Lane 45 (#483, cave wave #468): real unit geometry + electric-gate actor for a
// generated cave floor.
//
// Lane 44 draws every cave-room node as a proxy floor square. This module consumes
// the host bridge's ``P2_CAVE_GEOMETRY_1`` plan (one real converted unit model per
// choke/leaf/gate node, plus a real electric-gate actor on the electric leaf door)
// so the running port can instantiate real geometry instead of proxy markers.
//
// This header is engine-free on purpose: the parser, validation and marker shapes
// live here and the one-consumer test includes only this file. The engine glue
// (model loading, drawing, the live gate actor) lives in pc_p2_cave_geometry.cpp.
//
// A plan may be ``real``, ``mixed`` or ``proxy``; only ``real`` is a real-geometry
// plan. Proxy nodes are never claimed as real, matching the fan-out acceptance
// contract ("no proxy artefact is a generation PASS").
//
// Grammar (fixed token order, whitespace separated, ``-`` for empty):
//
//   P2_CAVE_GEOMETRY_1
//   cave <cave>
//   floor <int>
//   seed <int>
//   salt <int>
//   geometry <real|mixed|proxy>
//   units <N>
//   <id> <kind> <hazard|none> <real|proxy> <model|-> <gx> <gz>
//   ... (N rows)
//   gates <M>
//   <node_id> <hazard> <actor> <model|-> <placed|0|1>
//   ... (M rows)
//   entrance <id>
//   hole <id>

#pragma once

#include <algorithm>
#include <cstdint>
#include <istream>
#include <ostream>
#include <string>
#include <utility>
#include <vector>

struct P2CaveGeometryNode {
    std::string id;
    std::string kind;    // segment / choke / leaf / bud / gate
    std::string hazard;  // empty when the node is hazard-free
    std::string model;   // loadShape path when real; empty for proxy
    bool real = false;
    int gx = 0;
    int gz = 0;
};

struct P2CaveGeometryGate {
    std::string node_id;  // the leaf/gate node the actor is attached to
    std::string hazard;   // "elec" for this lane
    std::string actor;    // engine actor id, e.g. p2_elec_gate
    std::string model;    // loadShape path for the gate mesh
    bool placed = false;
};

struct P2CaveGeometryPlan {
    std::string cave;
    int floor = 0;
    std::uint64_t seed = 0;
    int salt = 0;
    std::string geometry;  // real / mixed / proxy
    std::vector<P2CaveGeometryNode> nodes;
    std::vector<P2CaveGeometryGate> gates;
    std::string entrance;
    std::string hole;
};

inline bool p2CaveGeometryRequiredKind(const std::string& kind)
{
    return kind == "choke" || kind == "leaf" || kind == "gate";
}

inline bool p2CaveGeometryElectric(const std::string& hazard)
{
    return hazard == "elec";
}

inline const P2CaveGeometryNode* p2CaveGeometryFindNode(const P2CaveGeometryPlan& plan,
                                                        const std::string& id)
{
    for (const P2CaveGeometryNode& node : plan.nodes) {
        if (node.id == id) return &node;
    }
    return nullptr;
}

inline const P2CaveGeometryGate* p2CaveGeometryGateFor(const P2CaveGeometryPlan& plan,
                                                       const std::string& nodeId)
{
    for (const P2CaveGeometryGate& gate : plan.gates) {
        if (gate.node_id == nodeId) return &gate;
    }
    return nullptr;
}

// The plan is a real-geometry plan only when every hazard-bearing node has a real
// model and every electric leaf/gate carries a placed gate actor. This is derived
// from the nodes, never trusted from the header alone.
inline bool p2CaveGeometryIsReal(const P2CaveGeometryPlan& plan)
{
    int required = 0;
    for (const P2CaveGeometryNode& node : plan.nodes) {
        if (!p2CaveGeometryRequiredKind(node.kind)) continue;
        ++required;
        if (!node.real || node.model.empty()) return false;
    }
    for (const P2CaveGeometryNode& node : plan.nodes) {
        if (!p2CaveGeometryElectric(node.hazard) || !p2CaveGeometryRequiredKind(node.kind)) continue;
        const P2CaveGeometryGate* gate = p2CaveGeometryGateFor(plan, node.id);
        if (!gate || !gate->placed || gate->actor.empty()) return false;
    }
    return required > 0;
}

inline std::string p2CaveGeometryMarker(const P2CaveGeometryPlan& plan)
{
    int real = 0;
    int proxy = 0;
    int actors = 0;
    for (const P2CaveGeometryNode& node : plan.nodes) {
        if (node.real) ++real;
        else ++proxy;
    }
    for (const P2CaveGeometryGate& gate : plan.gates) {
        if (gate.placed) ++actors;
    }
    return "P2_CAVE_GEOMETRY_READY nodes=" + std::to_string(plan.nodes.size()) + " real="
           + std::to_string(real) + " proxy=" + std::to_string(proxy) + " gate_actors="
           + std::to_string(actors) + " geometry="
           + (plan.geometry.empty() ? std::string("proxy") : plan.geometry) + " cave=" + plan.cave
           + " floor=" + std::to_string(plan.floor) + " seed=" + std::to_string(plan.seed)
           + " salt=" + std::to_string(plan.salt);
}

inline std::string p2CaveGeometryNodeMarker(const P2CaveGeometryNode& node)
{
    return "P2_CAVE_GEOMETRY_NODE id=" + node.id + " kind=" + node.kind + " hazard="
           + (node.hazard.empty() ? std::string("none") : node.hazard) + " class="
           + (node.real ? std::string("real") : std::string("proxy")) + " model="
           + (node.model.empty() ? std::string("-") : node.model) + " proxy="
           + (node.real ? std::string("0") : std::string("1"));
}

// Fail-closed parse of the canonical geometry text. Any mismatch, truncation,
// duplicate id or unknown section token returns false with an error string.
inline bool p2CaveGeometryParse(std::istream& in, P2CaveGeometryPlan& out, std::string& error)
{
    std::string word;
    auto fail = [&error](const std::string& message) {
        error = message;
        return false;
    };
    if (!(in >> word) || word != "P2_CAVE_GEOMETRY_1") return fail("bad geometry header");
    if (!(in >> word) || word != "cave" || !(in >> out.cave)) return fail("missing cave");
    if (!(in >> word) || word != "floor" || !(in >> out.floor)) return fail("missing floor");
    if (!(in >> word) || word != "seed" || !(in >> out.seed)) return fail("missing seed");
    if (!(in >> word) || word != "salt" || !(in >> out.salt)) return fail("missing salt");
    if (!(in >> word) || word != "geometry" || !(in >> out.geometry)) return fail("missing geometry");
    if (out.geometry != "real" && out.geometry != "mixed" && out.geometry != "proxy")
        return fail("unknown geometry class");

    if (!(in >> word) || word != "units") return fail("expected units section");
    int unit_count = 0;
    if (!(in >> unit_count) || unit_count < 0) return fail("bad unit count");
    out.nodes.clear();
    for (int index = 0; index < unit_count; ++index) {
        P2CaveGeometryNode node;
        std::string real, model;
        if (!(in >> node.id >> node.kind >> node.hazard >> real >> model >> node.gx >> node.gz))
            return fail("truncated unit row");
        if (real != "real" && real != "proxy") return fail("bad unit class");
        node.real = (real == "real");
        if (model != "-") node.model = model;
        if (node.hazard == "none") node.hazard.clear();
        if (p2CaveGeometryFindNode(out, node.id)) return fail("duplicate unit id");
        out.nodes.push_back(node);
    }

    if (!(in >> word) || word != "gates") return fail("expected gates section");
    int gate_count = 0;
    if (!(in >> gate_count) || gate_count < 0) return fail("bad gate count");
    out.gates.clear();
    for (int index = 0; index < gate_count; ++index) {
        P2CaveGeometryGate gate;
        std::string model, placed;
        if (!(in >> gate.node_id >> gate.hazard >> gate.actor >> model >> placed))
            return fail("truncated gate row");
        if (placed != "0" && placed != "1") return fail("bad placed token");
        gate.placed = (placed == "1");
        if (model != "-") gate.model = model;
        if (gate.hazard == "none") gate.hazard.clear();
        if (gate.actor.empty() || gate.actor == "-") return fail("empty gate actor");
        if (!p2CaveGeometryFindNode(out, gate.node_id)) return fail("gate references unknown node");
        out.gates.push_back(gate);
    }

    if (!(in >> word) || word != "entrance" || !(in >> out.entrance))
        return fail("missing entrance");
    if (!(in >> word) || word != "hole" || !(in >> out.hole)) return fail("missing hole");
    if (!p2CaveGeometryFindNode(out, out.entrance)) return fail("entrance is not a unit");
    if (!p2CaveGeometryFindNode(out, out.hole)) return fail("hole is not a unit");
    return true;
}
