import json
import tempfile
from pathlib import Path
import unittest

from experimental.pikmin2_beasts_floor3_failure_runtime import arm,validate
from tests.test_pikmin2_beasts_floor3_runtime import party


TOKEN='a'*64


def evidence(reason):
    lines=['P2_ROOM_CARGO_FREE_READY cargo=0','P2_CAVE_READY floor=3 survivors=20 health=0.625',
        f'P2_BEASTS_ENTRY_READY floor=3 token={TOKEN} descent=disabled',
        f'P2_FLOOR3_FAILURE_ARMED token={TOKEN} reason={reason} active_descent_rejected=1',
        'P2_BEASTS_PARTY health=0.625 count=20']
    lines += [f'P2_BEASTS_SURVIVOR index={i} species={p["species"]} maturity={p["maturity"]}' for i,p in enumerate(party()['squad'])]
    lines += ['P2_BEASTS_PARTY_END',f'P2_FLOOR3_FAILURE_INJECTED reason={reason} repairs_unchanged=1 pokos=0',
        f'P2_BEASTS_FAILURE floor=3 destination=0 reason={reason} survivors=0 health=0']
    return '\n'.join(lines)+'\n',f'P2_BEASTS_FAILURE_1\n{TOKEN}\n3 0 0 0\n{reason}\n'.encode()


class NativeFailureTests(unittest.TestCase):
    def test_both_reasons_normalize_empty_terminal_party(self):
        for reason in ('extinction','knockout'):
            log,transfer=evidence(reason)
            result=validate(log,transfer,TOKEN,reason,party())
            self.assertEqual(result,dict(reason=reason,source_floor=3,destination=0,health=0,squad=[]))

    def test_wrong_transfer_identity_or_live_destination_rejected(self):
        log,transfer=evidence('extinction')
        for bad in (transfer.replace(b'3 0 0 0',b'3 4 0 0'),transfer.replace(b'3 0 0 0',b'3 0 1 0'),
                    transfer.replace(TOKEN.encode(),b'b'*64),transfer.replace(b'extinction',b'knockout'),
                    transfer+b'extra\n',transfer.replace(b'3 0 0 0',b'3 0 0 1')):
            with self.subTest(transfer=bad),self.assertRaises(ValueError):validate(log,bad,TOKEN,'extinction',party())

    def test_missing_duplicate_and_conflicting_runtime_evidence_rejected(self):
        log,transfer=evidence('knockout')
        for bad in (log+'FAIL injected\n',log+'P2_POD_RECEIPT\n',log+'P2_CAVE_TRANSFER floor=3\n',
                    log.replace('health=0.625','health=1'),log.replace('active_descent_rejected=1','active_descent_rejected=0'),
                    log.replace('floor=3 destination=0','floor=3 destination=4'),
                    log+'P2_BEASTS_FAILURE malformed\n',log.replace('P2_ROOM_CARGO_FREE_READY cargo=0',''),
                    log.replace('species=purple','species=red',1)):
            with self.subTest(log=bad[:60]),self.assertRaises(ValueError):validate(bad,transfer,TOKEN,'knockout',party())

    def test_arming_requires_bound_fresh_stage_and_hashes_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);survey=path/'survey.json'
            survey.write_text(json.dumps(dict(policy='legacy',party_restore_protocol_floor=2,input_sha256={})))
            with self.assertRaises(ValueError):arm(path,'extinction')
            self.assertFalse((path/'p2-floor3-failure-fixture.txt').exists())
            survey.write_text(json.dumps(dict(policy='P2_BEASTS_FLOOR3_ENTRY_SURVEY_1',party_restore_protocol_floor=3,input_sha256={})))
            arm(path,'knockout')
            report=json.loads(survey.read_text())
            self.assertEqual(report['terminal_fixture_reason'],'knockout')
            self.assertIn('p2-floor3-failure-fixture.txt',report['input_sha256'])
            with self.assertRaises(ValueError):arm(path,'extinction')


if __name__=='__main__':unittest.main()
