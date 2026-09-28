import pytest

import randomizer.p2_placement as p2p
import randomizer.p2_placement_native as p2n


def slot(uid, label, evidence=None):
    record = {
        'uid': uid,
        'label': label,
        'stage': 0,
        'terrain': 'ground',
        'radius': 100,
        'corpse_route': True,
    }
    if evidence is not None:
        record['evidence'] = evidence
    return p2p.normalize_slot(record)


def profile(identity='Snow'):
    return p2p.normalize_profile({
        'identity': identity,
        'terrains': ['ground'],
        'cohort': None,
        'requires_corpse_route': True,
        'accepted_gates': ['arena'],
    })


def document(slots, profiles):
    return p2p.validate_document({
        'schema': p2p.SCHEMA,
        'slots': slots,
        'profiles': profiles,
    })


def ground_slot(uid=1):
    return slot(uid, f'ground_{uid}', evidence={'xyz': False, 'terrain': False, 'route': False})


def ground_document(*uids):
    return document([ground_slot(uid) for uid in uids], [profile()])


class TestNormalizeProbe:
    def test_accepts_valid_probe(self):
        probe = p2n.normalize_probe({
            'schema': p2n.PROBE_SCHEMA,
            'slots': [
                {'uid': 1, 'xyz': True, 'terrain': False, 'route': True},
                {'uid': 2, 'xyz': False, 'terrain': True, 'route': False},
            ],
        })
        assert probe == {
            'schema': p2n.PROBE_SCHEMA,
            'slots': [
                {'uid': 1, 'xyz': True, 'terrain': False, 'route': True},
                {'uid': 2, 'xyz': False, 'terrain': True, 'route': False},
            ],
        }

    def test_rejects_bad_schema(self):
        with pytest.raises(ValueError, match='probe schema must be'):
            p2n.normalize_probe({'schema': 'p2-placement-v1', 'slots': [{'uid': 1, 'xyz': True, 'terrain': True, 'route': True}]})

    def test_rejects_missing_keys(self):
        with pytest.raises(ValueError, match='missing required field'):
            p2n.normalize_probe({'schema': p2n.PROBE_SCHEMA, 'slots': [{'uid': 1, 'xyz': True}]})

    def test_rejects_extra_keys(self):
        with pytest.raises(ValueError, match='unknown field'):
            p2n.normalize_probe({'schema': p2n.PROBE_SCHEMA, 'slots': [{'uid': 1, 'xyz': True, 'terrain': True, 'route': True, 'extra': 1}]})

    def test_rejects_non_bool_evidence(self):
        with pytest.raises(ValueError, match='route must be a boolean'):
            p2n.normalize_probe({'schema': p2n.PROBE_SCHEMA, 'slots': [{'uid': 1, 'xyz': True, 'terrain': True, 'route': 'yes'}]})

    def test_rejects_duplicate_uid(self):
        with pytest.raises(ValueError, match='duplicate slot uids'):
            p2n.normalize_probe({'schema': p2n.PROBE_SCHEMA, 'slots': [
                {'uid': 1, 'xyz': True, 'terrain': True, 'route': True},
                {'uid': 1, 'xyz': False, 'terrain': False, 'route': False},
            ]})

    def test_rejects_negative_uid(self):
        with pytest.raises(ValueError, match='non-negative integer'):
            p2n.normalize_probe({'schema': p2n.PROBE_SCHEMA, 'slots': [{'uid': -1, 'xyz': True, 'terrain': True, 'route': True}]})

    def test_rejects_empty_slots(self):
        with pytest.raises(ValueError, match='non-empty list'):
            p2n.normalize_probe({'schema': p2n.PROBE_SCHEMA, 'slots': []})


class TestStampEvidence:
    def test_sets_matching_slot_and_leaves_others_false(self):
        doc = ground_document(1, 2)
        stamped = p2n.stamp_evidence(doc, {'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 1, 'xyz': True, 'terrain': True, 'route': True},
        ]})
        by_uid = {s['uid']: s for s in stamped['slots']}
        assert by_uid[1]['evidence'] == {'xyz': True, 'terrain': True, 'route': True}
        assert by_uid[2]['evidence'] == {'xyz': False, 'terrain': False, 'route': False}

    def test_never_downgrades_existing_evidence(self):
        doc = document(
            [slot(1, 'g', evidence={'xyz': False, 'terrain': True, 'route': False})],
            [profile()],
        )
        stamped = p2n.stamp_evidence(doc, {'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 1, 'xyz': True, 'terrain': False, 'route': True},
        ]})
        assert stamped['slots'][0]['evidence'] == {'xyz': True, 'terrain': True, 'route': True}

    def test_ignores_unknown_probe_uids(self):
        doc = ground_document(1)
        stamped = p2n.stamp_evidence(doc, {'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 999, 'xyz': True, 'terrain': True, 'route': True},
        ]})
        assert stamped['slots'][0]['evidence'] == {'xyz': False, 'terrain': False, 'route': False}

    def test_accepts_already_normalized_probe(self):
        doc = ground_document(1)
        probe = p2n.normalize_probe({'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 1, 'xyz': True, 'terrain': True, 'route': True},
        ]})
        stamped = p2n.stamp_evidence(doc, probe)
        assert stamped['slots'][0]['evidence'] == {'xyz': True, 'terrain': True, 'route': True}


class TestEndToEnd:
    def _evaluate_slot(self, stamped, uid):
        slot_record = next(s for s in stamped['slots'] if s['uid'] == uid)
        return p2p.evaluate(slot_record, profile())

    def test_denied_before_stamp_legal_after(self):
        doc = ground_document(1)
        assert self._evaluate_slot(doc, 1)['status'] == 'denied'
        stamped = p2n.stamp_evidence(doc, {'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 1, 'xyz': True, 'terrain': True, 'route': True},
        ]})
        assert self._evaluate_slot(stamped, 1)['status'] == 'legal'

    def test_route_false_stays_denied(self):
        doc = ground_document(1)
        stamped = p2n.stamp_evidence(doc, {'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 1, 'xyz': True, 'terrain': True, 'route': False},
        ]})
        result = self._evaluate_slot(stamped, 1)
        assert result['status'] == 'denied'
        assert 'slot lacks accepted native placement evidence' in result['reasons']


class TestAuditNative:
    def test_admits_snow_and_clears_evidence_reasons(self):
        doc = ground_document(1)
        report = p2n.audit_native(doc, {'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 1, 'xyz': True, 'terrain': True, 'route': True},
        ]})
        assert report['admitted'] == {'Snow': [1]}
        assert 'slot lacks accepted native placement evidence' not in report['denied_reasons']

    def test_slot_evidence_summary_reflects_stamp(self):
        doc = ground_document(1, 2)
        stamped = p2n.stamp_evidence(doc, {'schema': p2n.PROBE_SCHEMA, 'slots': [
            {'uid': 1, 'xyz': True, 'terrain': True, 'route': True},
        ]})
        summary = p2n.slot_evidence_summary(stamped)
        assert summary == {
            '1': {'xyz': True, 'terrain': True, 'route': True},
            '2': {'xyz': False, 'terrain': False, 'route': False},
        }
