from pathlib import Path
import tempfile
import unittest
from experimental.pikmin2_bulblax_runtime import retail_evidence


class RetailDisplayTests(unittest.TestCase):
    def test_source_events_and_reload_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory);(source/'Queen').mkdir()
            (source/'Queen/enemyanimmgr.txt').write_bytes(b'1 { x wait1.bca 0 2 -1 }')
            clips=[dict(species='Queen',name='wait1',duration=30)]
            event='P2_BULBLAX_RETAIL_EVENT enemy=30 clip=wait1 frame=0 type=2\n'
            text='P2_BULBLAX_RETAIL_READY \n'*2+event+'P2_BULBLAX_RELOAD_REQUEST\n'+event
            self.assertTrue(all(retail_evidence(text,'Queen',clips,source).values()))
            self.assertFalse(retail_evidence(text.replace('type=2','type=9'),'Queen',clips,source)['retail_source_events'])
            self.assertFalse(retail_evidence(text.replace('enemy=30','enemy=53'),'Queen',clips,source)['retail_source_events'])
            self.assertFalse(retail_evidence(text.rsplit(event,1)[0],'Queen',clips,source)['retail_reload_events'])
            self.assertTrue(all(retail_evidence('', 'disabled', [], source).values()))
            self.assertFalse(all(retail_evidence(event,'disabled',[],source).values()))
