"""Pom actor-birth provider contract for consumer #448.

Lane shard-enemies-1-pom-actor-provider. This module is the Python half of
the provider: the marker grammar for the deferred-birth record
(P2_POM_ACTOR_BIRTH / P2_POM_BASE_REJECTED with parent-id accounting), and
the machine-readable provider contract. It stages nothing, injects
nothing, and emits no markers.

The BEHAVIORAL proof lives in native/tools/p2_pom_actor_seam_test.cpp
(resolve/refusal/ownership/format checks against the real provider).
A log grammar agreement here alone can never pass acceptance; validate_log
exists so the follow-on in-game-birth lane gets deterministic verdicts on
future fixture logs.
"""
import re

PROVIDER = "p2-pom-actor/1"
CONSUMER_ISSUE = 448

COLORED_FIRST = 3
COLORED_LAST = 8
BASE_ID = 82
PARENT_ID = 82

_BIRTH_RE = re.compile(
    r"P2_POM_ACTOR_BIRTH generator=(\d+) source_id=(\d+) parent_id=(\d+)")
_REFUSAL_RE = re.compile(
    r"P2_POM_BASE_REJECTED generator=(\d+) source_id=(\d+)")

_INJECTED_MARKERS = (
    "P2_POM_INJECT",
    "p2-pom-inject",
    "injection=1",
    "P2_POM_ACTOR_INJECT",
)


def provider_contract():
    """Machine-readable provider contract for consumer #448."""
    return {
        "schema": PROVIDER,
        "consumer_issue": CONSUMER_ISSUE,
        "native_api": "native/pc_port/pc_p2_pom_actor.h",
        "native_test": "native/tools/p2_pom_actor_seam_test.cpp",
        "colored_source_ids": list(range(COLORED_FIRST, COLORED_LAST + 1)),
        "parent_id": PARENT_ID,
        "base_refused": BASE_ID,
        "lifecycle": ["resolve", "bind", "recordBirth", "release"],
        "exactly_once": True,
        "routing": "host manager births through its own manager and hands "
                   "the pool the generator token plus the resolved record",
        "runtime_claim": False,
    }


def _fields(pattern, line):
    match = pattern.search(line)
    return match.groups() if match else None


def validate_log(text):
    """Validate one future fixture log against the provider grammar.

    Returns (verdict, detail): True only when every birth line carries a
    colored source id with parent 82, every refusal names base 82, each
    generator shows at most one birth with no source disagreement, and no
    injected markers appear. Empty input fails closed.
    """
    if not isinstance(text, str) or not text.strip():
        return False, "empty log"
    births = {}
    refusals = 0
    injected = False
    for line in text.splitlines():
        if any(marker in line for marker in _INJECTED_MARKERS):
            injected = True
        fields = _fields(_BIRTH_RE, line)
        if fields:
            generator, source, parent = (int(fields[0]), int(fields[1]),
                                         int(fields[2]))
            if not COLORED_FIRST <= source <= COLORED_LAST:
                return False, "birth with non-colored source %d" % source
            if parent != PARENT_ID:
                return False, "birth with wrong parent %d" % parent
            record = births.setdefault(generator, {"count": 0,
                                                   "sources": set()})
            record["count"] += 1
            record["sources"].add(source)
        fields = _fields(_REFUSAL_RE, line)
        if fields:
            if int(fields[1]) != BASE_ID:
                return False, "refusal names non-base source"
            refusals += 1
    if injected:
        return False, "injected markers present"
    if not births and not refusals:
        return False, "no provider markers"
    for generator, record in births.items():
        if len(record["sources"]) > 1:
            return False, "generator %d source disagreement" % generator
        if record["count"] > 1:
            return False, "generator %d birthed twice" % generator
    return True, "providers=%d refusals=%d" % (len(births), refusals)
