import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class ExtrasPublicationTests(unittest.TestCase):
 def test_complete_immutable_publication_is_atomic_and_preserves_old_entries(self):
  from export_extras import publish_extras,extras_media
  data=json.loads((ROOT/'analysis/extras/gateway.json').read_text());catalog=json.loads((ROOT/'app/public/catalog.json').read_text());catalog.pop('extras',None)
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);(out/'catalog.json').write_text(json.dumps(catalog))
   for path in extras_media(data):
    target=out/path.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'original asset')
   result=publish_extras(data,out);old=(out/'catalog.json').read_bytes();self.assertEqual(publish_extras(data,out),result)
   self.assertEqual({k:v for k,v in result.items() if k!='extras'},catalog)
   immutable=out/result['extras']['dataPath'].lstrip('/');self.assertEqual(json.loads(immutable.read_text()),data)
   changes=[lambda d:d.pop('maze'),lambda d:d.pop('whack'),lambda d:d.pop('vending'),lambda d:d.pop('memory'),lambda d:d.pop('lager'),lambda d:d.update(sourceFingerprint='other'),lambda d:d['pages'][0].update(scene='missing'),lambda d:d['pages'][0]['controls'][0]['variants'][0].update(endTicks=-1),lambda d:d['lager']['stages'].pop(),lambda d:d['memory']['objects'][0].update(page='missing')]
   for id in ['archive-intro','keypad-confirm','invalid-code','instructions-video','vending-success-0','vending-wrong-0','vending-complete','memory-result-0-47']:
    changes.append(lambda d,id=id:next(p for p in d['pages'] if p['id']==id).update(after=None))
   changes.extend([
    lambda d:next(p for p in d['pages'] if p['id']=='archive-intro').update(after={'type':'memory-next'}),
    lambda d:next(p for p in d['pages'] if p['id']=='memory-result-0-47').update(after={'type':'vending-order'}),
    lambda d:next(p for p in d['pages'] if p['id']=='memory-result-0-47').update(after={'type':'page','page':'memory-menu'}),
    lambda d:next(p for p in d['pages'] if p['id']=='vending-success-0').update(after={'type':'page','page':'vending-menu'}),
    lambda d:next(p for p in d['pages'] if p['id']=='whack-menu')['controls'][0]['variants'][0].update(action={'type':'memory-next'}),
    lambda d:next(p for p in d['pages'] if p['id']=='vending-help')['controls'][0]['variants'][0].update(action={'type':'page','page':'memory-menu'}),
   ])
   for mutate in changes:
    bad=copy.deepcopy(data);mutate(bad)
    with self.assertRaises(ValueError):publish_extras(bad,out)
    self.assertEqual((out/'catalog.json').read_bytes(),old)
   missing=out/next(iter(extras_media(data))).lstrip('/');asset=missing.read_bytes();missing.unlink()
   with self.assertRaises(ValueError):publish_extras(data,out)
   self.assertEqual((out/'catalog.json').read_bytes(),old);missing.write_bytes(asset)
   immutable.write_bytes(b'corrupt')
   with self.assertRaises(ValueError):publish_extras(data,out)
   self.assertEqual((out/'catalog.json').read_bytes(),old)
if __name__=='__main__':unittest.main()
