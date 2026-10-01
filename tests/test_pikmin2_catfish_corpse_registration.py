"""Contract tests for the Catfish26 corpse->receipt registration (#652).

Dependency-free run-log reader for the exact marker grammar named by #641:
``P2_CATFISH_CORPSE_READY generator=<gen> source_id=26
receipt=corpse:catfish:<gen>`` emitted once per natural death beside the
``P2_CATFISH_DEAD`` edge. Fail-closed: any missing leg, id mismatch,
death-after-registration order, injected marker, or captain-down evidence
yields False. Emits no markers; cannot fabricate acceptance.
"""
import json
import sys
import unittest

BIND = "P2_CATFISH_BIND"
DEATH = "P2_CATFISH_DEAD"
CORPSE = "P2_CATFISH_CORPSE_READY"
RECEIPT = "P2_POD_RECEIPT"

_CAPTAIN_DOWN_TOKENS = (
    "GAMEEND_PikminExtinction",
    "DEMOID_Extinction",
    "P2_FIXTURE_CAPTAIN_DOWN",
    "orima_dead=1",
    "OrimaDown",
    "NaviDown",
)

_INJECTED_TOKENS = ("P2_MUSE_DAMAGUMO_INJECT", "mHealth=", "health=99999")


def _fields(tokens):
    fields = {}
    for token in tokens:
        key, sep, value = token.partition("=")
        if sep:
            fields[key] = value
    return fields


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _receipt_generator(fields):
    ident = fields.get("receipt", fields.get("id", ""))
    # Family receipt marker carries the infix ("corpse:catfish:<gen>"); the
    # generic Pod receipt is a bare numeric tail ("corpse:<gen>"), resolved
    # only by exact generator correlation plus death-before-receipt order.
    if "corpse:catfish:" in ident:
        ident = ident.split("corpse:catfish:", 1)[1]
    elif ident.startswith("corpse:"):
        ident = ident.split("corpse:", 1)[1]
    else:
        return None
    tail = ident.split(":")[-1]
    return _int(tail) if tail and tail.isdigit() else None


def parse(text):
    text = text or ""
    for token in _CAPTAIN_DOWN_TOKENS:
        if token in text:
            return {"bound": False, "dead": False, "registered": False,
                    "receipt_ok": False, "generator": -1, "gate_ok": False,
                    "blocked": True, "block_reason": "captain-down"}
    injected = any(token in text for token in _INJECTED_TOKENS)

    binds = []
    deaths = []
    corpses = []
    receipts = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        tokens = line.split()
        if not tokens:
            continue
        fields = _fields(tokens)
        if BIND in tokens:
            binds.append((line_no, _int(fields.get("generator"))))
        if DEATH in tokens and fields.get("source_id") == "26":
            deaths.append((line_no, _int(fields.get("generator"))))
        if CORPSE in tokens and fields.get("source_id") == "26":
            gen = _int(fields.get("generator"))
            if gen == _receipt_generator(fields):
                corpses.append((line_no, gen))
        if RECEIPT in tokens:
            receipts.append((line_no, _receipt_generator(fields)))

    match = None
    for bind_line, bind_gen in binds:
        if bind_gen is None:
            continue
        death_lines = [ln for ln, gen in deaths if gen == bind_gen and ln > bind_line]
        if not death_lines:
            continue
        first_death = min(death_lines)
        corpse_lines = [ln for ln, gen in corpses
                        if gen == bind_gen and ln >= first_death]
        if not corpse_lines:
            continue
        first_corpse = min(corpse_lines)
        receipt_lines = [ln for ln, gen in receipts
                         if gen == bind_gen and ln > first_corpse]
        match = {
            "generator": bind_gen,
            "bind_line": bind_line,
            "death_line": first_death,
            "corpse_line": first_corpse,
            "receipt_line": min(receipt_lines) if receipt_lines else None,
        }
        break

    if match is None:
        return {"bound": bool(binds), "dead": bool(deaths),
                "registered": False, "receipt_ok": False, "generator": -1,
                "gate_ok": False, "blocked": False, "block_reason": None,
                "injected": injected}
    gate_ok = not injected and match["receipt_line"] is not None
    return {"bound": True, "dead": True, "registered": True,
            "receipt_ok": match["receipt_line"] is not None,
            "generator": match["generator"], "gate_ok": gate_ok,
            "blocked": False, "block_reason": None, "injected": injected,
            "lines": {k: v for k, v in match.items() if k != "generator"}}


GEN = 340001
BIND_LINE = "P2_CATFISH_BIND generator=%d source_id=26 visual_only=0" % GEN
DEATH_LINE = "P2_CATFISH_DEAD generator=%d source_id=26 health=0" % GEN
CORPSE_LINE = ("P2_CATFISH_CORPSE_READY generator=%d source_id=26 "
               "receipt=corpse:catfish:%d" % (GEN, GEN))
RECEIPT_LINE = ("[Pikipelago] P2_POD_RECEIPT id=corpse:%d value=2 new=1 "
                "pokos=2 seeds=0" % GEN)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Run-log path (default stdin)")
    args = parser.parse_args(argv)
    text = (open(args.path, encoding="utf-8", errors="replace").read()
            if args.path else sys.stdin.read())
    print(json.dumps(parse(text), indent=2))


class CatfishCorpseRegistrationTests(unittest.TestCase):
    def test_full_chain_passes(self):
        verdict = parse("\n".join([BIND_LINE, DEATH_LINE, CORPSE_LINE, RECEIPT_LINE]))
        self.assertTrue(verdict["registered"])
        self.assertTrue(verdict["receipt_ok"])
        self.assertTrue(verdict["gate_ok"])
        self.assertEqual(verdict["generator"], GEN)

    def test_registration_without_receipt_is_partial(self):
        verdict = parse("\n".join([BIND_LINE, DEATH_LINE, CORPSE_LINE]))
        self.assertTrue(verdict["registered"])
        self.assertFalse(verdict["receipt_ok"])
        self.assertFalse(verdict["gate_ok"])

    def test_missing_corpse_fails(self):
        verdict = parse("\n".join([BIND_LINE, DEATH_LINE, RECEIPT_LINE]))
        self.assertFalse(verdict["registered"])
        self.assertFalse(verdict["gate_ok"])

    def test_missing_death_fails(self):
        verdict = parse("\n".join([BIND_LINE, CORPSE_LINE, RECEIPT_LINE]))
        self.assertFalse(verdict["gate_ok"])

    def test_generator_mismatch_fails(self):
        other = CORPSE_LINE.replace("generator=%d" % GEN, "generator=340002")
        verdict = parse("\n".join([BIND_LINE, DEATH_LINE, other, RECEIPT_LINE]))
        self.assertFalse(verdict["registered"])

    def test_receipt_id_mismatch_fails(self):
        other = CORPSE_LINE.replace("receipt=corpse:catfish:%d" % GEN,
                                    "receipt=corpse:catfish:340002")
        verdict = parse("\n".join([BIND_LINE, DEATH_LINE, other, RECEIPT_LINE]))
        self.assertFalse(verdict["registered"])

    def test_wrong_source_id_fails(self):
        other = DEATH_LINE.replace("source_id=26", "source_id=27")
        verdict = parse("\n".join([BIND_LINE, other, CORPSE_LINE, RECEIPT_LINE]))
        self.assertFalse(verdict["gate_ok"])

    def test_corpse_before_death_fails(self):
        verdict = parse("\n".join([BIND_LINE, CORPSE_LINE, DEATH_LINE, RECEIPT_LINE]))
        self.assertFalse(verdict["registered"])

    def test_injected_run_rejected(self):
        text = "\n".join([BIND_LINE, DEATH_LINE, CORPSE_LINE, RECEIPT_LINE,
                          "mHealth=0 injected"])
        verdict = parse(text)
        self.assertTrue(verdict["injected"])
        self.assertFalse(verdict["gate_ok"])

    def test_captain_down_blocks(self):
        text = "\n".join([BIND_LINE, "GAMEEND_PikminExtinction"])
        verdict = parse(text)
        self.assertTrue(verdict["blocked"])
        self.assertFalse(verdict["gate_ok"])

    def test_empty_log_fails(self):
        verdict = parse("")
        self.assertFalse(verdict["gate_ok"])
        self.assertEqual(verdict["generator"], -1)


if __name__ == "__main__":
    unittest.main()
