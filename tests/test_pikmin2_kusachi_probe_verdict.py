"""Focused tests for the kusachi probe-stream verdict analyzer (#809).

No runtime: synthetic streams exercise both verdict branches, the absent-window
refusal, and fail-closed malformed handling. The real #793 stream is asserted
to be honestly refused (window absent), never guessed.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experimental.pikmin2_kusachi_probe_verdict import (
    CASCADE,
    DIRECT,
    PROBE_PREFIX,
    UNRESOLVED,
    VerdictRefused,
    analyze,
    classify_window,
    find_extinction_window,
    parse_probe_line,
    parse_probe_stream,
)

REAL_PROBE = ("C:/Users/alari/pikmin-randomizer/output/workflow/autofill/"
              "prerequisites/kusachi-extinction-probe-native/run-793/"
              "probe0/probe.log")


def line(tick, navimgr=1, navi=1, navi_alive=1, orima_dead=0, alive=8,
         reds=0):
    slots = "1" * alive
    return ("%stick=%d navimgr=%d navi=%d navi_alive=%d orima_dead=%d "
            "alive=%d reds=%d slots=%s"
            % (PROBE_PREFIX, tick, navimgr, navi, navi_alive, orima_dead,
               alive, reds, slots))


def write_stream(tmp, lines):
    path = os.path.join(tmp, "probe.log")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def classify(lines):
    rows = [parse_probe_line(l) for l in lines]
    index, before, after = find_extinction_window(rows)
    return classify_window(rows, index)


class VerdictTests(unittest.TestCase):
    def test_direct_manager_clear(self):
        verdict, _ = classify(
            [line(t) for t in (1, 2, 3)] + [line(4, alive=0)])
        self.assertEqual(verdict, DIRECT)

    def test_navi_drop_same_tick_cascade(self):
        verdict, _ = classify(
            [line(t) for t in (1, 2, 3)]
            + [line(4, navi_alive=0, orima_dead=1, alive=0)])
        self.assertEqual(verdict, CASCADE)

    def test_navi_drop_precedes_collapse_cascade(self):
        """The defining cascade shape: captain lost, squad released later."""
        verdict, _ = classify(
            [line(t) for t in (1, 2, 3)]
            + [line(4, navi_alive=0, orima_dead=1)]      # squad still alive
            + [line(5, navi_alive=0, orima_dead=1, alive=0)])
        self.assertEqual(verdict, CASCADE)

    def test_ambiguous_unresolved(self):
        """naviMgr gone (navi flags flat 0) - not a captain loss signal."""
        verdict, _ = classify(
            [line(t, navimgr=0, navi=0, navi_alive=0, orima_dead=0)
             for t in (1, 2)]
            + [line(3, navimgr=0, navi=0, navi_alive=0, orima_dead=0,
                    alive=0)])
        self.assertEqual(verdict, UNRESOLVED)


class RefusalTests(unittest.TestCase):
    def test_no_transition_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = write_stream(tmp, [line(t) for t in range(1, 20)])
            with self.assertRaises(VerdictRefused) as ctx:
                analyze(path)
            self.assertIn("no live->extinct transition", str(ctx.exception))

    def test_malformed_line_refused(self):
        with self.assertRaises(VerdictRefused):
            parse_probe_line(PROBE_PREFIX + "tick=1 alive=2")

    def test_slots_mismatch_refused(self):
        with self.assertRaises(VerdictRefused):
            parse_probe_line(
                PROBE_PREFIX + "tick=9 navimgr=1 navi=1 navi_alive=1 "
                "orima_dead=0 alive=2 reds=0 slots=10")

    def test_non_integer_refused(self):
        with self.assertRaises(VerdictRefused):
            parse_probe_line(
                PROBE_PREFIX + "tick=9 navimgr=x navi=1 navi_alive=1 "
                "orima_dead=0 alive=0 reds=0 slots=")

    def test_empty_stream_refused(self):
        with self.assertRaises(VerdictRefused):
            parse_probe_stream("no probes here\n")

    def test_forbidden_marker_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = write_stream(
                tmp, [line(1), line(2), line(3, alive=0),
                      "P2_FIXTURE_CAPTAIN_DOWN tick=9"])
            with self.assertRaises(VerdictRefused) as ctx:
                analyze(path)
            self.assertIn("forbidden marker", str(ctx.exception))

    def test_synthetic_full_analyze_direct(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = write_stream(tmp, [line(t) for t in (1, 2, 3)]
                                + [line(4, alive=0)])
            result = analyze(path)
            self.assertEqual(result["verdict"], DIRECT)
            self.assertEqual(result["after"]["tick"], 4)

    def test_synthetic_full_analyze_cascade(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = write_stream(
                tmp, [line(t) for t in (1, 2, 3)]
                + [line(4, navi_alive=0, orima_dead=1, alive=0)])
            result = analyze(path)
            self.assertEqual(result["verdict"], CASCADE)
            self.assertEqual(result["after"]["tick"], 4)


@unittest.skipUnless(os.path.exists(REAL_PROBE),
                     "landed #793 probe stream unavailable")
class RealStreamTests(unittest.TestCase):
    def test_real_stream_is_honestly_refused(self):
        """The landed stream has NO extinction window; refuse, never guess."""
        with self.assertRaises(VerdictRefused) as ctx:
            analyze(REAL_PROBE)
        self.assertIn("no live->extinct transition", str(ctx.exception))

    def test_real_stream_holds_a_live_squad(self):
        text = open(REAL_PROBE, "rb").read().decode("utf-16")
        rows = parse_probe_stream(text)
        self.assertGreater(len(rows), 600)
        self.assertEqual(rows[-1]["alive"], 8)


if __name__ == "__main__":
    unittest.main()
