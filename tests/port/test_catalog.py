import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))

class CatalogTests(unittest.TestCase):
    def games(self):
        from test_export_game import GameExportTests
        games={}
        for id in ['general-knowledge','viewer','geek']:
            game=GameExportTests().fixture();game['sourceFingerprint']='source'
            game['bonuses']=[{'id':'perfect-bonus-'+name,'introScenes':['s'],'question':copy.deepcopy(game['levels'][0]['questions'][0]),'correct':{'scenes':['s'],'destination':'complete','nextCandidateMask':1},'wrong':{'scenes':['s'],'destination':'complete','nextCandidateMask':1}} for name in ['low','high']]
            game['entry']['menus']*=3
            game['entry']['menus'][1]={'id':'player-type','scene':'s','label':id,'rect':{'x':1,'y':2,'width':3,'height':4},'highlightSrc':'/media/h.png','windows':[{'startTicks':0,'endTicks':100000,'candidateMask':1}]}
            games[id]=game
        return games

    def test_complete_catalog_uses_versioned_content_and_preserves_prior_on_failure(self):
        from export_catalog import publish_catalog
        games=self.games()
        with tempfile.TemporaryDirectory() as root:
            out=Path(root);first=publish_catalog(games,out)
            before=(out/'catalog.json').read_bytes();second=publish_catalog(games,out)
            self.assertEqual(first,second)
            for id,item in first['modes'].items():
                self.assertIn('/games/'+id+'-',item['dataPath'])
                self.assertTrue((out/item['dataPath'].lstrip('/')).is_file())
            bad_fp=copy.deepcopy(games);bad_fp['geek']['sourceFingerprint']='other'
            bad_caption=copy.deepcopy(games);bad_caption['viewer']['levels'][0]['questions'][0]['choices'][0]['label']=''
            for bad in [{k:v for k,v in games.items() if k!='geek'},bad_fp,bad_caption]:
                with self.assertRaises(ValueError):publish_catalog(bad,out)
                self.assertEqual((out/'catalog.json').read_bytes(),before)
            bad=copy.deepcopy(games);bad['viewer']['levels'][0]['questions'][0]['promptScene']='missing'
            with self.assertRaises(ValueError):publish_catalog(bad,out)
            self.assertEqual((out/'catalog.json').read_bytes(),before)

    def test_shared_bonus_ids_have_mode_specific_highlight_assets(self):
        from export_game import highlight_id
        self.assertEqual(highlight_id('general-knowledge','perfect-bonus-low-A'),'perfect-bonus-low-A')
        self.assertEqual(highlight_id('viewer','perfect-bonus-low-A'),'viewer-perfect-bonus-low-A')
        self.assertEqual(highlight_id('geek','perfect-bonus-low-A'),'geek-perfect-bonus-low-A')

    def test_source_menu_families_match_original_visible_labels(self):
        from export_game import mode_menu_group
        from progression_model import SourceModel
        with SourceModel(ROOT/'disc/2EDVD108',ROOT/'analysis','viewer') as source:
            rows=source.buttons.controls({'vts':2,'domain':'vts-menu','pgc':6,'cell':1,'audio':0})
        for mode,buttons in [('viewer',set(range(1,6))),('geek',set(range(6,11))),('general-knowledge',set(range(11,16)))]:
            group=mode_menu_group(rows,mode)
            self.assertEqual({r['button'] for r in group},buttons)

    def test_six_game_publication_is_atomic_and_versions_hattie(self):
        from export_catalog import publish_catalog
        games=self.games();hattie=self.games()
        for game in hattie.values():
            game['entry']['menus'][2]=copy.deepcopy(game['entry']['menus'][1]);game['entry']['setupOptions']=[['s'],['s'],['s']]
        with tempfile.TemporaryDirectory() as root:
            out=Path(root);before=publish_catalog(games,out);old=(out/'catalog.json').read_bytes()
            for bad in [{k:v for k,v in hattie.items() if k!='viewer'}]:
                with self.assertRaises(ValueError):publish_catalog(games,out,bad)
                self.assertEqual((out/'catalog.json').read_bytes(),old)
            bad=copy.deepcopy(hattie);bad['geek']['bonuses'][0]['question']['text']=''
            with self.assertRaises(ValueError):publish_catalog(games,out,bad)
            self.assertEqual((out/'catalog.json').read_bytes(),old)
            for mutate in ['fingerprint','scene','bonus','presenter-window','setup']:
                bad=copy.deepcopy(hattie)
                if mutate=='fingerprint':bad['viewer']['sourceFingerprint']='other'
                if mutate=='scene':bad['viewer']['levels'][0]['questions'][0]['promptScene']='missing'
                if mutate=='bonus':bad['viewer']['bonuses']=[]
                if mutate=='presenter-window':bad['viewer']['entry']['menus'][2]['windows']=[]
                if mutate=='setup':bad['viewer']['entry']['setupOptions']=[['missing']]
                with self.assertRaises(ValueError):publish_catalog(games,out,bad)
                self.assertEqual((out/'catalog.json').read_bytes(),old)
            result=publish_catalog(games,out,hattie)
            self.assertEqual(result['schemaVersion'],2);self.assertEqual(result['modes'],before['modes'])
            for id,entry in result['hattieModes'].items():
                self.assertIn('/games/hattie-'+id+'-',entry['dataPath']);self.assertTrue((out/entry['dataPath'].lstrip('/')).is_file())
