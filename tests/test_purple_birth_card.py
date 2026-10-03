import hashlib,struct,unittest
from pathlib import Path
from scripts.purple_birth_ledger import decode_stock,saved_census,SAVE
class CardControls(unittest.TestCase):
 def setUp(self):
  # Synthetic source-format card: no legal assets or native receipt claims.
  payload=bytearray(32768);payload[0]=2;payload[2]=3
  payload[4:16]=struct.pack('>3i',21,0,0)
  payload[20:24]=b'cont';payload[24:60]=struct.pack('>9i',0,0,0,21,0,0,0,0,0);payload[60:64]=b'cach'
  header=b'PIKMIN_CAMPAIGN_PURPLE_1 '+b'998bc5919c9fdc8f8fd1e5ab6eb8d21d0b1f470837594cdce4273991b6a9bf92 1 0 0 0 0 1 0 0 0 0 0'
  checksum=14695981039346656037
  for byte in header+b'\n'+payload:checksum=((checksum^byte)*1099511628211)&((1<<64)-1)
  self.data=header+b' '+str(checksum).encode()+b'\n'+payload
  self.args=dict(sha256=hashlib.sha256(self.data).hexdigest(),fingerprint='998bc5919c9fdc8f8fd1e5ab6eb8d21d0b1f470837594cdce4273991b6a9bf92',benefit_count=4,check_count=1000,day=3)
 def test_synthetic_source_format_card_not_runtime_acceptance(self):
  self.assertEqual(decode_stock(self.data,**self.args)['rgb'],[0,0,0,21,0,0,0,0,0])
 def test_wrong_identity_schema_day_refused(self):
  for k,v in [('sha256','0'*64),('fingerprint','0'*64),('benefit_count',3),('benefit_count',True),('day',2)]:
   with self.subTest(k=k,v=v),self.assertRaises(ValueError):decode_stock(self.data,**dict(self.args,**{k:v}))
 def test_changed_payload_checksum_refused(self):
  changed=self.data[:-1]+bytes([self.data[-1]^1])
  with self.assertRaises(ValueError):decode_stock(changed,**dict(self.args,sha256=hashlib.sha256(changed).hexdigest()))
 def test_all_fifteen_match_control_not_runtime(self):
  stock=decode_stock(self.data,**self.args);counts=stock['rgb']+stock['p2']+[0,0,0]
  rows=[f'P2_PURPLE_BIRTH_CENSUS stage=saved species={s} maturity={m} field=0 stock={counts[s*3+m]} heads=0 read_only=1' for s in range(6) for m in range(3)]
  self.assertEqual(saved_census('\n'.join(rows+[SAVE]),stock)['card_compartments_matched'],15)
  for label,altered in [('missing',rows[:-1]),('duplicate',rows+[rows[0]]),('head', [rows[0].replace('heads=0','heads=1')]+rows[1:]),('field',[rows[0].replace('field=0','field=1')]+rows[1:]),('stock',[rows[0].replace('stock=0','stock=1')]+rows[1:]),('late',rows+[SAVE,rows[0]])]:
   with self.subTest(label=label),self.assertRaises(ValueError):saved_census('\n'.join(altered+[SAVE]),stock)
if __name__=='__main__':unittest.main()
