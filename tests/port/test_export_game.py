import sys,tempfile,json,copy
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/port'))

class GameExportTests(unittest.TestCase):
    def fixture(self):
        levels=[]
        for level in range(1,9):
            questions=[{'id':f'q{level}-{n}','text':'A verified question','expiry':'loop','choices':[{'id':c,'label':c,'highlightSrc':'/media/h.png'} for c in 'ABCD'],'correctChoice':'A','correctSequence':[],'promptScene':'s','revealScene':'s'} for n in range(38)]
            levels.append({'number':level,'questions':questions,'selection':{'2:1':[{'questionId':questions[0]['id'],'introScenes':['s']}]},'answers':{'a':['s']},'timeouts':{},'intros':{'1':['s']},'endings':{'0:0:1':{'scenes':['s'],'destination':'complete','nextCandidateMask':1}}})
        return {'schemaVersion':2,'scenes':[{'id':'s','src':'/media/s.mp4'}],'entry':{'boot':['s'],'setupScenes':['s'],'menus':[{'scene':'s'}]},'levels':levels,'bonuses':[]}

    def test_manifest_references_and_captions_fail_before_replacing_dataset(self):
        from export_game import validate_game,publish_game
        data=self.fixture();validate_game(data)
        with tempfile.TemporaryDirectory() as root:
            out=Path(root);(out/'game.json').write_text('previous playable dataset')
            bad=copy.deepcopy(data);bad['levels'][3]['questions'][0]['promptScene']='missing'
            with self.assertRaisesRegex(ValueError,'missing'):publish_game(bad,out)
            self.assertEqual((out/'game.json').read_text(),'previous playable dataset')
            bad=copy.deepcopy(data);bad['levels'][1]['questions'][0]['choices'][2]['label']=''
            with self.assertRaisesRegex(ValueError,'caption'):validate_game(bad)

    def test_unverified_or_different_source_captions_are_rejected(self):
        from export_game import verified_labels
        entry={'text':'Prompt','choices':['One','Two','Three','Four'],'verified':True,'sourceSha256':'source'}
        self.assertEqual(verified_labels({'q':entry},'q','source'),('Prompt',['One','Two','Three','Four']))
        for bad in [{**entry,'verified':False},{**entry,'sourceSha256':'different'}]:
            with self.assertRaises(ValueError):verified_labels({'q':bad},'q','source')
