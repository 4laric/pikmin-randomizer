"""Jigumo63 EAT-receiver review checker (issue #689, lane-16 via #167).

Dependency-free run-log inventory for the Jigumo EAT receiver path named by
the pass1 evidence: throw stimulus (P2_JIGUMO_THROW) -> bite capture
(P2_JIGUMO_BITE) -> swallow kill (P2_JIGUMO_EAT) -> HP drain (P2_JIGUMO_VITALS)
-> death (absent). Reports whether the receiver was OBSERVED (BITE+EAT
present) and whether death was blocked by damage throughput (receiver
observed, HP floor above zero, no DEAD) versus by a missing receiver (no
BITE/EAT at all). Fail-closed: injected markers, captain-down evidence, id
mismatches or missing legs yield a refused verdict. Emits no markers and
cannot fabricate acceptance; all six gates stay UNTESTED by this review.
"""
import json
import re
import sys

BIND_RE = re.compile(r"P2_JIGUMO_BIND generator=(\d+) source_id=63")
BITE_RE = re.compile(r"P2_JIGUMO_BITE generator=(\d+) frame=(\d+)")
EAT_RE = re.compile(r"P2_JIGUMO_EAT generator=(\d+)")
DEATH_RE = re.compile(r"P2_JIGUMO_DEAD generator=(\d+)")
VITALS_RE = re.compile(r"P2_JIGUMO_VITALS tick=(\d+) hp=([\d.]+)")
THROW_RE = re.compile(r"P2_JIGUMO_THROW n=(\d+) generator=(\d+).*?hp=([\d.]+)")

_CAPTAIN_DOWN_TOKENS = (
    "GAMEEND_PikminExtinction",
    "DEMOID_Extinction",
    "P2_FIXTURE_CAPTAIN_DOWN",
    "orima_dead=1",
    "OrimaDown",
    "NaviDown",
)

_INJECTED_TOKENS = ("P2_MUSE_DAMAGUMO_INJECT", "mHealth=", "health=99999")


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def review(text):
    text = text or ""
    for token in _CAPTAIN_DOWN_TOKENS:
        if token in text:
            return {"bound": False, "receiver": "blocked",
                    "death": "blocked", "generator": -1,
                    "verdict": "refused:interrupted",
                    "blocked": True, "block_reason": "captain-down"}
    injected = any(token in text for token in _INJECTED_TOKENS)

    binds = [int(m.group(1)) for m in BIND_RE.finditer(text)]
    bites = [(int(m.group(1)), int(m.group(2))) for m in BITE_RE.finditer(text)]
    eats = [int(m.group(1)) for m in EAT_RE.finditer(text)]
    deaths = [int(m.group(1)) for m in DEATH_RE.finditer(text)]
    throws = [(int(m.group(1)), int(m.group(2)), _float(m.group(3)))
              for m in THROW_RE.finditer(text)]
    vitals = [(int(m.group(1)), _float(m.group(2)))
              for m in VITALS_RE.finditer(text)]

    generator = binds[0] if binds else -1
    same_gen = lambda seq: all(g == generator for g, *_ in seq) if seq else True
    coherent = (bool(binds) and same_gen([(g,) for g in binds])
                and same_gen(bites) and same_gen([(g,) for g in eats])
                and same_gen([(g,) for g in deaths]))

    hp_values = [hp for _, hp in vitals if hp is not None]
    hp_values += [hp for _, _, hp in throws if hp is not None]
    hp_min = min(hp_values) if hp_values else None
    hp_max = max(hp_values) if hp_values else None

    receiver = "observed" if (bites and eats and coherent) else "unobserved"
    if not binds:
        receiver = "unobserved"
    if deaths and coherent and not injected:
        death = "observed"
    elif receiver == "observed" and (hp_min is not None and hp_min > 0):
        death = "blocked:throughput"
    elif receiver == "observed":
        death = "unobserved"
    else:
        death = "blocked:receiver"

    if injected or not coherent:
        verdict = "refused:injected" if injected else "refused:mismatch"
    elif receiver == "observed" and death == "blocked:throughput":
        verdict = "receiver-observed death-blocked-throughput"
    elif receiver == "observed" and death == "observed":
        verdict = "receiver-observed death-observed"
    elif receiver == "unobserved":
        verdict = "receiver-unobserved"
    else:
        verdict = "receiver-observed death-unobserved"

    return {"bound": bool(binds), "generator": generator,
            "throws": len(throws), "bites": len(bites), "eats": len(eats),
            "deaths": len(deaths), "hp_min": hp_min, "hp_max": hp_max,
            "receiver": receiver, "death": death, "verdict": verdict,
            "blocked": False, "block_reason": None, "injected": injected,
            "coherent": coherent}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run-log path (default stdin)")
    args = parser.parse_args(argv)
    text = (open(args.path, encoding="utf-8", errors="replace").read()
            if args.path else sys.stdin.read())
    print(json.dumps(review(text), indent=2))


if __name__ == "__main__":
    main()
