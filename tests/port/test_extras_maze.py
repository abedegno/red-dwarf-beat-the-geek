import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))
class ExtrasMazeTests(unittest.TestCase):
    def test_original_maze_graph_has_all_dockings_hazards_retries_and_victory(self):
        from extras_maze import build_maze
        from extras_source import ExtrasSource
        from export_round import Assets
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            a=Assets(m.source,m.analysis,ROOT/'app/public',m.pgcs)
            result=build_maze(m,a)
        self.assertLess(len(result['nodes']),200)
        self.assertEqual({n['docking'] for n in result['nodes'].values()},{1,2,3})
        self.assertTrue(any(n['victory'] for n in result['nodes'].values()))
        self.assertTrue(any(n['lives']==0 for n in result['nodes'].values()))
        self.assertTrue(any(c['autoActivate'] for p in result['pages'] for c in p['controls']))
        self.assertTrue(any(not p['controls'] and p['after'] for p in result['pages']))
        ids={p['id'] for p in result['pages']}|{'maze-menu'}
        self.assertIn(result['entry']['page'],ids)
        for p in result['pages']:
            actions=[v['action'] for c in p['controls'] for v in c['variants']]+([p['after']] if p['after'] else [])
            for action in actions:
                self.assertEqual(action['type'],'maze-route');self.assertIn(action['page'],ids)
        text=json.dumps(result)
        for forbidden in ['registers','command','LinkPGCN','bytecode']:self.assertNotIn(forbidden,text)
if __name__=='__main__':unittest.main()
