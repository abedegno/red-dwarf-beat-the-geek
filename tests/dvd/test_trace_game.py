import json
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from fixture import author_disc

ROOT = Path(__file__).resolve().parents[2]


class TraceTests(unittest.TestCase):
    def start(self, disc):
        executable = ROOT / 'tools/dvd/build/trace_game'
        self.assertTrue(executable.exists(), 'trace recorder is not implemented')
        proc = subprocess.Popen([str(executable), str(disc), '--seed', '42'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True)
        def cleanup():
            if proc.poll() is None:
                proc.communicate('quit\n', timeout=5)
            proc.stdin.close()
            proc.stdout.close()
        self.addCleanup(cleanup)
        self.assertEqual(json.loads(proc.stdout.readline())['seed'], 42)
        self.events = []
        return proc

    def send(self, proc, command):
        proc.stdin.write(command + '\n')
        proc.stdin.flush()
        row = proc.stdout.readline()
        self.assertTrue(row, f'tracer stopped after {command}')
        event = json.loads(row)
        self.events.append(event)
        self.assertTrue(event['ok'], event)
        return event

    def until(self, proc, predicate):
        for _ in range(150):
            event = self.send(proc, 'next')
            if predicate(event):
                return event
            if event['event'] == 'WAIT':
                self.send(proc, 'advance-wait')
        self.fail('trace never reached expected state')

    def test_state_dependent_branch_and_register_deltas(self):
        self.assertTrue((ROOT / 'tools/dvd/build/trace_game').exists(), 'trace recorder is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.start(author_disc(Path(tmp), buttons=True))
            menu = self.until(proc, lambda e: e['buttons'] == 2 and e['event'] == 'NAV_PACKET')
            self.assertEqual(menu['registers']['gprm'][0], 7)
            selected = self.send(proc, 'select 1')
            self.assertEqual(selected['input'], 'select 1')
            activation = self.send(proc, 'activate')
            self.assertEqual(activation['registers']['gprm'][0], 8)
            self.assertIn({'bank': 'gprm', 'index': 0, 'before': 7, 'after': 8}, activation['registerDelta'])
            title1 = self.until(proc, lambda e: e['domain'] == 'title' and e['event'] == 'CELL_CHANGE')
            self.assertEqual(title1['pgc'], 1)
            self.until(proc, lambda e: e['domain'] == 'vts-menu' and e['buttons'] == 2 and e['event'] == 'NAV_PACKET')
            self.send(proc, 'select 1')
            self.send(proc, 'activate')
            title2 = self.until(proc, lambda e: e['domain'] == 'title' and e['event'] == 'CELL_CHANGE')
            self.assertEqual(title2['pgc'], 2)

    def test_still_wait_requires_explicit_advance(self):
        self.assertTrue((ROOT / 'tools/dvd/build/trace_game').exists(), 'trace recorder is not implemented')
        with tempfile.TemporaryDirectory() as tmp:
            proc = self.start(author_disc(Path(tmp), buttons=True))
            still = self.until(proc, lambda e: e['event'] == 'STILL_FRAME')
            self.assertEqual(still['stillSeconds'], 1)
            again = self.send(proc, 'next')
            self.assertEqual(again['event'], 'STILL_FRAME')
            self.send(proc, 'advance-still')
            title = self.until(proc, lambda e: e['domain'] == 'title' and e['event'] == 'CELL_CHANGE')
            self.assertEqual(title['pgc'], 2)

    def test_trace_source_references_join_inventory_with_language_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            # The VM prefers English by default; this disc offers only French.
            disc = author_disc(Path(tmp), buttons=True, menu_language='fr', vm_menu_media=True)
            proc = self.start(disc)
            self.until(proc, lambda e: e['event'] == 'NAV_PACKET' and e['domain'] == 'vts-menu')
            self.send(proc, 'select 1')
            self.send(proc, 'activate')
            self.until(proc, lambda e: e['event'] == 'CELL_CHANGE' and e['domain'] == 'title')
            inventory = json.loads(subprocess.check_output(
                [str(ROOT / 'tools/dvd/build/inspect_ifo'), str(disc)], text=True))
            for event in self.events:
                if event['domain'] in ('vmg-menu', 'vts-menu'):
                    self.assertEqual(event.get('language'), 26226)  # fr, not preferred en.
                if event['domain'] == 'vmg-menu':
                    self.assertEqual(event['vts'], 0)
                if event['domain'] == 'title':
                    self.assertEqual(event.get('language'), 0)
            spec = importlib.util.spec_from_file_location('report', ROOT / 'tools/dvd/report.py')
            report_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(report_mod)
            report = report_mod.build_report(inventory, [], self.events)
            self.assertGreater(len(report['observedEdges']), 1)
            self.assertEqual(report['unresolvedObservedLocations'], [])
            for edge in report['observedEdges']:
                self.assertTrue(edge['fromResolved'])
                self.assertTrue(edge['toResolved'])
