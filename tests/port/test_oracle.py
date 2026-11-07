import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class OracleTests(unittest.TestCase):
    def test_recorded_candidate_and_variant_reach_question34(self):
        executable = ROOT / 'tools/dvd/build/round_oracle'
        self.assertTrue(executable.exists(), 'offline round oracle is not implemented')
        run = subprocess.run([str(executable), str(ROOT / 'disc/2EDVD108/VIDEO_TS')],
                             input='start 3 93 8 3 0 6 42\nquit\n',
                             capture_output=True, text=True, check=True)
        row = json.loads(run.stdout.splitlines()[0])
        self.assertEqual((row['vts'], row['pgc'], row['cell']), (3, 34, 1))
        self.assertEqual(row['score'], 0)

    def test_ordered_source_answer_scores_only_after_four_selections(self):
        executable = ROOT / 'tools/dvd/build/round_oracle'
        commands = ['start 3 43 256 2 0 2 42']
        for button in [2,4,1,3]:
            commands.extend([f'select {button}', 'answer 200400000000002b'])
        run = subprocess.run([str(executable), str(ROOT / 'disc/2EDVD108/VIDEO_TS')],
                             input='\n'.join(commands)+'\nquit\n', capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [json.loads(l) for l in run.stdout.splitlines()]
        self.assertEqual([rows[i]['score'] for i in [2,4,6,8]], [0,0,0,1])
