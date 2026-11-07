"""Verify complete extras publication, immutable baselines and local package bytes."""
import argparse,hashlib,json,stat
from pathlib import Path
from extras_validation import validate_extras,extras_media

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def verify(output=Path('app/public'),analysis=Path('analysis'),package=None,preservation=False,evidence=False):
 catalog=json.loads((output/'catalog.json').read_text());path=catalog['extras']['dataPath'];payload=output/path.lstrip('/');data=json.loads(payload.read_text())
 assert path=='/games/extras-'+sha(payload)+'.json','Extras content address mismatch'
 validate_extras(data,output,catalog['sourceFingerprint'])
 baseline=json.loads((analysis/'extras/baseline.json').read_text())
 for name,digest in baseline.items():assert sha(Path('tools/dvd/build/round_oracle') if name=='round_oracle' else output/name)==digest,'Baseline changed: '+name
 summary={'sourceFingerprint':data['sourceFingerprint'],'extrasPath':path,'pages':len(data['pages']),'scenes':len(data['scenes']),'media':len(extras_media(data)),'baselineHashes':baseline}
 if package:
  count=size=0
  for original in output.rglob('*'):
   if not original.is_file():continue
   target=package/original.relative_to(output);st=target.lstat()
   assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_ino!=original.stat().st_ino,'Package assets must be independent regular files'
   assert sha(target)==sha(original),'Package byte mismatch: '+str(target)
   count+=1;size+=st.st_size
  build=Path('app/dist')
  for original in [build/'index.html',*(build/'assets').glob('*')]:
   target=package/original.relative_to(build);st=target.lstat();assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_ino!=original.stat().st_ino,'Bundle must be independent regular files';assert sha(target)==sha(original),'Stale bundle'
  summary['package']={'path':str(package),'publicFiles':count,'publicBytes':size,'independentRegularFiles':True}
 if preservation:
  source=Path('disc/2EDVD108/VIDEO_TS');files=sorted(p for p in source.rglob('*') if p.is_file())
  assert len(files)==63 and sum(p.stat().st_size for p in files)==5935634432,'Disc inventory changed'
  for line in Path('disc/SHA256SUMS').read_text().splitlines():
   digest,name=line.split(None,1);assert sha(Path('disc')/name)==digest,'Disc file changed: '+name
  summary['preservation']={'discFiles':63,'discBytes':5935634432,'discHashes':'all matched'}
  iso=Path('disc/images/Red_Dwarf_Beat_the_Geek_DVD.iso')
  if iso.is_file():
   digest=sha(iso);assert iso.stat().st_size==5937125376 and digest=='9a96026739f2de1d9d10c50c9467065f8897aac32c6a776d1328f6f889d1c081','Preservation ISO changed'
   summary['preservation']['isoSha256']=digest
  else:summary['preservation']['isoNotChecked']='Recorded path absent; no current ISO verification claimed'

 if evidence:
  logs={
   'converter-review-final.log':r'Ran 76 tests.*\n\nOK',
   'native-review-final.log':r'Tests\s+224 passed',
   'browser-final-corrected.log':r'24 passed',
   'lager-browser-corrected.log':r'6 passed',
   'quiz-browser-review-regression.log':r'12 passed',
   'review-browser-green.log':r'10 passed',
   'lager-browser-package.log':r'2 passed',
  }
  import re
  for name,pattern in logs.items():
   content=(analysis/'extras'/name).read_text();assert re.search(pattern,content,re.S) and not re.search(r'\b[1-9]\d* failed\b',content),'Incomplete/failed acceptance: '+name
  counts={'maze':2,'legacy-quiz':15,'whack':8,'vending':48,'memory':20,'lager':24}
  for name,count in counts.items():assert len(json.loads((analysis/'extras'/f'{name}-traces.json').read_text()))==count,'Missing source traces'
  summary['acceptance']={'converter':76,'native':224,'originalPacedBrowser':32,'quizMenuRegression':12,'reviewRejectionBrowser':10,'continuousSourceCases':counts}
 (analysis/'extras/release-verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return summary
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=Path('app/public'));p.add_argument('--analysis',type=Path,default=Path('analysis'));p.add_argument('--package',type=Path);p.add_argument('--preservation',action='store_true');p.add_argument('--evidence',action='store_true');a=p.parse_args();verify(a.output,a.analysis,a.package,a.preservation,a.evidence)
