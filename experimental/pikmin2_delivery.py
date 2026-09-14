"""P2 ordinary delivery receiver over the lane 06 receipt ledger.

The ordinary Onion/AP path resolves an enemy source against a reward identity,
derives a per-generator delivery slot/actor and delegates every grant to
:class:`experimental.pikmin2_receipts.ReceiptLedger`. The P1-proxy and P2-source
identity vocabularies are deliberately disjoint prefixes so a proxied P1 reward
can never be confused with a real P2 source, even when their numeric parts line
up. Exactly-once semantics, persistence and restart behavior are inherited from
the ledger; this module contributes no native save mutation.
"""
from experimental.pikmin2_receipts import ReceiptLedger


def p1_proxy_identity(teki_type, stage):
    """Proxy identity for an ordinary P1 enemy encountered on ``stage``."""
    return f"corpse:p1:{teki_type}:{stage}"


def p2_source_identity(source_id, stage):
    """Source identity for an imported P2 enemy ``source_id`` on ``stage``."""
    return f"corpse:p2:{source_id}:{stage}"


class DeliveryReceiver:
    """Mirror of the native ordinary-delivery receiver.

    ``source_id == 0`` selects the P1-proxy identity path; any non-zero source
    id selects the P2-source identity path. Grants and probes delegate to the
    wrapped :class:`ReceiptLedger` so exactly-once guarantees hold unchanged.
    """

    def __init__(self, ledger):
        if not isinstance(ledger, ReceiptLedger):
            raise ValueError('Expected a receipt ledger')
        self.ledger = ledger

    def identity(self, source_id, teki_type, stage):
        if source_id != 0:
            return p2_source_identity(source_id, stage)
        return p1_proxy_identity(teki_type, stage)

    def slot_or_actor(self, generator_token):
        return f"g{generator_token}"

    def deliver(self, seed, source_id, teki_type, stage, generator_token, encounter):
        return self.ledger.grant(seed, self.identity(source_id, teki_type, stage),
                                 self.slot_or_actor(generator_token), encounter)

    def delivered(self, seed, source_id, teki_type, stage, generator_token, encounter):
        return self.ledger.has(seed, self.identity(source_id, teki_type, stage),
                               self.slot_or_actor(generator_token), encounter)
