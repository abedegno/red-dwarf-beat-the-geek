import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ExportTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'tools/port/export_round.py'
        self.assertTrue(path.exists(), 'round normalizer is not implemented')
        spec = importlib.util.spec_from_file_location('export_round', path)
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def source(self):
        pgc = {'vts': 3, 'pgc': 6, 'domain': 'vts-menu', 'audioControl': [32768]+[0]*7,
               'cells': [{'cell': 1, 'firstSector': 0, 'lastSector': 202, 'duration': 12.04},
                         {'cell': 2, 'firstSector': 203, 'lastSector': 235, 'duration': 3.0}]}
        rows, decoded = [], {}
        for i, y in enumerate([274, 308, 341, 374]):
            code = f'{i+1:016x}'
            decoded[code] = f'g[10] = 0x{1 << i:x}, LinkTailPGC (button {1 if i==0 else 5+i})'
            rows.append({'group': 1, 'sector': 0, 'vobuStart': 48600, 'vobuEnd': 102600,
                         'highlightStart':48600,'highlightEnd':318600,'selectionEnd':318600,
                         'button': i*4+1, 'rectangle': [73, y, 513, y+33], 'command': code})
        return pgc, rows, decoded

    def test_source_question6_geometry_correct_answer_and_loop(self):
        pgc, rows, decoded = self.source()
        question = self.mod.normalize_question(pgc, list(reversed(rows)), decoded)
        self.assertEqual(question['correctChoice'], 'A')
        self.assertEqual([c['rect']['y'] for c in question['choices']], [274, 308, 341, 374])
        self.assertEqual(question['durationSeconds'], 12.04)
        self.assertEqual(question['revealSeconds'], 3.0)
        self.assertEqual(question['windows'][0]['nextCandidateMask'], 1)

    def test_ambiguous_answer_association_fails(self):
        pgc, rows, decoded = self.source()
        decoded[rows[1]['command']] = 'g[10] = 0x2, LinkTailPGC (button 2)'
        with self.assertRaises(ValueError):
            self.mod.normalize_question(pgc, rows, decoded)

    def test_truncated_cell_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'VIDEO_TS').mkdir()
            (root/'VIDEO_TS/VTS_03_0.VOB').write_bytes(bytes(2048))
            with self.assertRaises(ValueError):
                self.mod.read_cell(root, {'vts':3,'domain':'vts-menu'},
                                   {'firstSector':0,'lastSector':1})

    def test_missing_required_audio_stream_fails(self):
        pgc, _, _ = self.source()
        with self.assertRaises(ValueError):
            self.mod.select_audio(pgc, 0, [{'codec_type':'video', 'id':'0x1e0'}])
        self.assertEqual(self.mod.select_audio(pgc, 0, [{'codec_type':'audio','id':'0x80'}]), '0x80')

    def test_menu_audio_uses_stream_zero_as_the_original_player_does(self):
        pgc, _, _ = self.source()
        self.assertEqual(self.mod.select_audio(pgc, 2, [{'codec_type':'audio','id':'0x80'}]), '0x80')

    def test_silent_cells_are_distinguished_from_audio_pes(self):
        block=bytearray(2048)
        block[:4]=b'\0\0\1\xba'
        self.assertFalse(self.mod.has_audio_packets(bytes(block)))
        block[14:25]=b'\0\0\1\xbd\0\x05\x80\0\0\x80\0'
        self.assertTrue(self.mod.has_audio_packets(bytes(block)))

    def test_ordering_question_preserves_four_step_answer(self):
        pgc, rows, decoded = self.source()
        pgc['pgc'] = 43
        codes=[f'73a00f0e000100{n:02x}' for n in [2,4,1,3]]
        pgc['commands'] = {'pre': codes}
        for code, expected in zip(codes, [2,4,1,3]):
            decoded[code] = f'if (g[15] == 0x{expected:x}) g[14] += 0x1'
        for row in rows:
            decoded[row['command']] = 'LinkPGCN 43'
        question = self.mod.normalize_question(pgc, rows, decoded)
        self.assertEqual(question['kind'], 'sequence')
        self.assertEqual(question['correctSequence'], ['B','D','A','C'])

    def test_authored_highlight_times_deduplicate_nav_repetitions(self):
        pgc, rows, decoded = self.source()
        extra=[]
        for row in rows:
            extra.append({**row,'sector':1,'vobuStart':91800})
            code='new'+row['command']
            decoded[code]=decoded[row['command']].replace('0x'+format(1 << (row['button']//4),'x'), '0x40')
            extra.append({**row,'sector':2,'vobuStart':307800,'highlightStart':318600,
                          'highlightEnd':588600,'selectionEnd':588600,'command':code})
        q=self.mod.normalize_question(pgc,rows+extra,decoded)
        a=[w for w in q['windows'] if w['choiceId']=='A']
        self.assertEqual([(w['startTicks'],w['endTicks']) for w in a],[(0,270000),(270000,540000)])

    def test_menu_activation_uses_selection_expiry_and_rejects_conflicts(self):
        _,rows,_=self.source();row=rows[0]
        row={**row,'highlightStart':57600,'selectionEnd':228600}
        windows=self.mod.activation_rows([row],48600)
        self.assertEqual([(start,end) for _,start,end in windows],[(9000,180000)])
        with self.assertRaises(ValueError):
            self.mod.activation_rows([row,{**row,'sector':1,'command':'conflict'}],48600)
