"""Python binding contract for the native receipt-ledger endpoint (#749).

Mirrors native/pc_port/pc_p2_receipt_ledger_endpoint.h stage for stage over
the four #724 pins (Onyon::isSuckReady :195, InteractSuckDone::actOnyon :403,
PlayData::obtainPellet_Main :800, ledger write :832) plus the log-grammar
validator consumed by future fixture logs. Stdlib only; no engine import.
Malformed inputs and out-of-order calls are refused, never corrected.
"""
import re

PINS = (
    ("SuckReady", "Onyon::isSuckReady", 195),
    ("ActOnyon", "InteractSuckDone::actOnyon", 403),
    ("ObtainPellet", "PlayData::obtainPellet_Main", 800),
    ("LedgerWrite", "ledger write", 832),
)

STAGE_RE = re.compile(r"P2_RECEIPT_ENDPOINT stage=(SuckReady|ActOnyon|ObtainPellet|LedgerWrite)(?: identity=(\S+))?(?: slot=(\S+))?(?: granted=(\d+))?(?: duplicate=(\d+))?")
REFUSED_RE = re.compile(r"P2_RECEIPT_ENDPOINT_REFUSED stage=(\S+) reason=(\S+) state=(\S+)")
GRANT_RE = re.compile(r"P2_RECEIPT_ENDPOINT stage=LedgerWrite identity=(\S+) granted=(\d+)(?: duplicate=(\d+))?")
SELFTEST_RE = re.compile(r"P2_RECEIPT_LEDGER_SELFTEST_PASS rows=(\d+)")
PASS_RE = re.compile(r"^PASS RECEIPT_LEDGER contract stages=4 negatives=(\d+)$", re.M)
DOWN_RE = re.compile(r"P2_FIXTURE_CAPTAIN_DOWN")


class ContractError(Exception):
    """A binding call violates the endpoint contract."""


def _token(value, limit, label):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ContractError("bad %s" % label)
    if not re.fullmatch(r"[A-Za-z0-9_:/.\-]+", value):
        raise ContractError("bad %s" % label)
    return value


class Endpoint:
    """Ordered four-stage receipt endpoint over an exactly-once key set."""

    def __init__(self, seed):
        self._seed = _token(seed, 128, "seed")
        self._grants = set()
        self.reset()

    def reset(self):
        self._stage = 0
        self._identity = None
        self._slot = None
        self._encounter = None

    @property
    def stage(self):
        return ("Idle", "SuckReady", "ActOnyon", "ObtainPellet")[self._stage]

    def suck_ready(self, identity):
        if self._stage != 0:
            raise ContractError("suckReady refused: not-idle")
        self._identity = _token(identity, 90, "identity")
        self._stage = 1
        return True

    def act_onyon(self, slot):
        if self._stage != 1:
            raise ContractError("actOnyon refused: order")
        self._slot = _token(slot, 128, "slot")
        self._stage = 2
        return True

    def obtain_pellet(self, encounter):
        if self._stage != 2:
            raise ContractError("obtainPellet refused: order")
        self._encounter = _token(encounter, 128, "encounter")
        self._stage = 3
        return True

    def ledger_write(self):
        """Returns 1 granted, 2 duplicate. Resets either way."""
        if self._stage != 3:
            raise ContractError("ledgerWrite refused: order")
        key = (self._seed, self._identity, self._slot, self._encounter)
        granted = key not in self._grants
        self._grants.add(key)
        self.reset()
        return 1 if granted else 2


def validate_log(text):
    """Classify a fixture log against the endpoint marker grammar."""
    lines = text.splitlines()
    stages = [m.group(1) for line in lines for m in [STAGE_RE.search(line)] if m]
    refused = [(m.group(1), m.group(2)) for line in lines for m in [REFUSED_RE.search(line)] if m]
    grants = [(m.group(1), int(m.group(2))) for line in lines for m in [GRANT_RE.search(line)] if m]
    selftest = [int(m.group(1)) for line in lines for m in [SELFTEST_RE.search(line)] if m]
    negatives = [int(m.group(1)) for line in lines for m in [PASS_RE.search(line)] if m]
    return {
        "stages_observed": stages,
        "refusals": refused,
        "grants": grants,
        "selftest_rows": selftest,
        "contract_negatives": negatives,
        "captain_down": any(DOWN_RE.search(l) for l in lines),
        "lines": len(lines),
    }
