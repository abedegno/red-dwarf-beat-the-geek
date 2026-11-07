import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReportTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'tools/dvd/report.py'
        self.assertTrue(path.exists(), 'report builder is not implemented')
        spec = importlib.util.spec_from_file_location('report', path)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_state_dependent_edges_remain_distinct(self):
        def event(pgc, score):
            return {'vts': 1, 'domain': 'vts-menu', 'pgc': pgc,
                    'registers': {'gprm': [score]}, 'event': 'CELL_CHANGE'}
        # Two visits to menu 1, with different scores, lead to different menus.
        events = [event(1, 0), event(2, 1), event(1, 5), event(3, 6)]
        report = self.mod.build_report({'pgcs': []}, [], events)
        edges = [e for e in report['observedEdges'] if e['from']['pgc'] == 1]
        self.assertEqual([e['to']['pgc'] for e in edges], [2, 3])
        self.assertEqual([e['stateBefore']['gprm'][0] for e in edges], [0, 5])

    def test_unknown_targets_remain_unresolved(self):
        pgc = {'vts': 1, 'domain': 'vts-menu', 'pgc': 1, 'cells': [],
               'commands': {'pre': ['deadbeefdeadbeef'], 'post': [], 'cell': []}}
        report = self.mod.build_report({'pgcs': [pgc]}, [], [])
        edge = report['commandEdges'][0]
        self.assertEqual(edge['status'], 'unresolved')
        self.assertEqual(edge['command'], 'deadbeefdeadbeef')
        self.assertIsNone(edge['to'])

    def test_source_labels_are_escaped(self):
        report = self.mod.build_report({'pgcs': [], 'label': '<script>alert(1)</script>'}, [], [])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'index.html'
            self.mod.render_html(report, path)
            text = path.read_text()
            self.assertNotIn('<script>alert(1)</script>', text)
            self.assertIn('&lt;script&gt;', text)

    def test_unknown_trace_location_is_preserved_as_unresolved(self):
        known = {'vts': 0, 'domain': 'vmg-menu', 'pgc': 1, 'language': 25966,
                 'cells': [], 'commands': {'pre': []}}
        unknown = {**known, 'pgc': 999}
        report = self.mod.build_report({'pgcs': [known]}, [], [known, unknown])
        edge = report['observedEdges'][0]
        self.assertTrue(edge['fromResolved'])
        self.assertFalse(edge['toResolved'])
        self.assertEqual(edge['to']['pgc'], 999)
        self.assertEqual(report['unresolvedObservedLocations'], [
            {'vts': 0, 'domain': 'vmg-menu', 'pgc': 999, 'language': 25966}])

    def test_documented_disassembly_pipeline_recovers_conditional_target(self):
        code = '20f4000f000a0056'  # if g15 < 10, LinkPGCN 86.
        base = {'vts': 3, 'domain': 'vts-menu', 'language': 25966, 'cells': []}
        data = {'pgcs': [{**base, 'pgc': 2, 'commands': {'pre': [code]}},
                         {**base, 'pgc': 86, 'commands': {'pre': []}}]}
        decoded = subprocess.run([str(ROOT / 'tools/dvd/build/trace_game'), '--disassemble'],
                                 input=code+'\n', capture_output=True, text=True, check=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'ifo.json').write_text(json.dumps(data))
            (root / 'commands.txt').write_text(decoded.stderr)
            result = subprocess.run(['python3', str(ROOT / 'tools/dvd/report.py'),
                                     '--ifo', str(root / 'ifo.json'), '--disassembly',
                                     str(root / 'commands.txt'), '--output', str(root / 'out')],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((root / 'out/graph.json').read_text())
            edge = report['commandEdges'][0]
            self.assertEqual(edge['status'], 'conditional')
            self.assertEqual(edge['to']['pgc'], 86)
