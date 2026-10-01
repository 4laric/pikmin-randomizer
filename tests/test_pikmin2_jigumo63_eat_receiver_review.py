"""Focused tests for the Jigumo63 EAT-receiver review checker (#689)."""
import unittest

from experimental.pikmin2_jigumo63_eat_receiver_review import review

GEN = 374003
BIND = "P2_JIGUMO_BIND generator=%d source_id=63 visual_only=0" % GEN


def throw(n, hp):
    return "P2_JIGUMO_THROW n=%d generator=%d dist=180.0 hp=%.1f" % (n, GEN, hp)


def bite(frame=13):
    return "P2_JIGUMO_BITE generator=%d frame=%d pikmin=1" % (GEN, frame)


def eat():
    return "P2_JIGUMO_EAT generator=%d pikmin=1" % GEN


def vitals(tick, hp):
    return "P2_JIGUMO_VITALS tick=%d hp=%.1f x=0.0 y=0.0 z=0.0 ground=0.0" % (tick, hp)


def dead():
    return "P2_JIGUMO_DEAD generator=%d source_id=26 health=0" % GEN


class JigumoEatReceiverReviewTests(unittest.TestCase):
    def test_pass1_shape_reports_throughput_block(self):
        lines = [BIND] + [throw(n, 500.0 - n) for n in range(1, 118)]
        lines += [bite(), eat()] * 7 + [bite()] * 2
        lines += [vitals(1550, 380.0)]
        verdict = review("\n".join(lines))
        self.assertEqual(verdict["generator"], GEN)
        self.assertEqual(verdict["throws"], 117)
        self.assertEqual(verdict["bites"], 9)
        self.assertEqual(verdict["eats"], 7)
        self.assertEqual(verdict["deaths"], 0)
        self.assertEqual(verdict["hp_min"], 380.0)
        self.assertEqual(verdict["receiver"], "observed")
        self.assertEqual(verdict["death"], "blocked:throughput")
        self.assertEqual(verdict["verdict"],
                         "receiver-observed death-blocked-throughput")
        self.assertFalse(verdict["blocked"])

    def test_no_bite_means_receiver_unobserved(self):
        verdict = review("\n".join([BIND, throw(1, 500.0), vitals(50, 485.0)]))
        self.assertEqual(verdict["receiver"], "unobserved")
        self.assertEqual(verdict["death"], "blocked:receiver")

    def test_death_observed_when_present(self):
        verdict = review("\n".join([BIND, bite(), eat(), dead()]))
        self.assertEqual(verdict["receiver"], "observed")
        self.assertEqual(verdict["death"], "observed")
        self.assertEqual(verdict["deaths"], 1)

    def test_missing_bind_unobserved(self):
        verdict = review("\n".join([bite(), eat()]))
        self.assertFalse(verdict["bound"])
        self.assertEqual(verdict["receiver"], "unobserved")

    def test_generator_mismatch_refused(self):
        other = bite().replace("generator=%d" % GEN, "generator=374004")
        verdict = review("\n".join([BIND, other, eat()]))
        self.assertFalse(verdict["coherent"])
        self.assertEqual(verdict["verdict"], "refused:mismatch")

    def test_injected_rejected(self):
        text = "\n".join([BIND, bite(), eat(), "mHealth=0 injected"])
        verdict = review(text)
        self.assertTrue(verdict["injected"])
        self.assertEqual(verdict["verdict"], "refused:injected")

    def test_captain_down_blocks(self):
        verdict = review("\n".join([BIND, "GAMEEND_PikminExtinction"]))
        self.assertTrue(verdict["blocked"])
        self.assertEqual(verdict["block_reason"], "captain-down")

    def test_empty_log_unobserved(self):
        verdict = review("")
        self.assertEqual(verdict["receiver"], "unobserved")
        self.assertEqual(verdict["generator"], -1)


if __name__ == "__main__":
    unittest.main()
