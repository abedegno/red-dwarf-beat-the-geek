import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/port'))

class ExtrasSourceTests(unittest.TestCase):
    def test_changed_source_disassembly_is_rejected_before_use(self):
        from extras_source import ExtrasSource
        with tempfile.TemporaryDirectory() as tmp:
            ifo=json.loads((ROOT/'analysis/ifo.json').read_text())
            code=next(code for code,line in ifo['decodedCommands'].items() if line!='Nop')
            ifo['decodedCommands'][code]='Nop'
            (Path(tmp)/'ifo.json').write_text(json.dumps(ifo))
            with self.assertRaisesRegex(ValueError,'description mismatch'):
                with ExtrasSource(ROOT/'disc/2EDVD108',Path(tmp)):pass

    def test_main_menu_opens_instruction_choice_and_archive_introduction(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for button,target in [(9,26),(13,4)]:
                initial=m.start(2,1)
                commands={r['command'] for r in m.controls(initial) if r['button']==button}
                self.assertGreater(len(commands),1)
                for command in commands:
                    row=m.start(2,1);row=m.activate(row,button,command)
                    self.assertEqual((row['vts'],row['pgc']),(2,target))

    def test_shared_guard_collision_restarts_first_play(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            registers=[0]*16;registers[0]=47;registers[1]=registers[10]=2000
            row=m.start(12,1,registers)
            self.assertEqual((row['vts'],row['pgc']),(0,3))
            self.assertEqual(m.ref(row)['domain'],'vmg-menu')

    def test_actual_keypad_opens_five_original_games_without_earned_flags(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for code,vts,pgc in [('7523',11,17),('1921',12,7),('3598',13,2),('9639',14,36),('7148',15,15)]:
                row=m.start(2,24)
                for index,digit in enumerate(code):
                    self.assertEqual(row['cell'],index+1)
                    row=m.activate(row,int(digit) or 10)
                self.assertEqual((row['cell'],row['registers'][15]),(5,int(code)))
                row=m.call('cell');self.assertEqual((row['vts'],row['pgc']),(vts,pgc))

    def test_invalid_code_menu_and_game_quit_have_distinct_return_paths(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            row=m.start(2,24)
            for _ in range(4):row=m.activate(row,10)
            row=m.call('cell');self.assertEqual((row['vts'],row['pgc']),(2,27))
            row=m.call('cell');self.assertEqual((row['vts'],row['pgc']),(2,1))
            row=m.start(2,24);row=m.activate(row,11);self.assertEqual((row['vts'],row['pgc']),(2,1))
            for vts,pgc,quit_button in [(11,17,2),(12,7,3),(13,2,3),(14,36,3),(15,15,3)]:
                row=m.start(vts,pgc);row=m.activate(row,quit_button)
                self.assertEqual((row['vts'],row['pgc']),(2,4))
                row=m.call('cell');self.assertEqual((row['pgc'],row['registers'][15]),(24,0))

    def test_instruction_choices_set_subpicture_and_return_with_it_off(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for button,spu in [(1,0),(2,64)]:
                row=m.start(2,26);row=m.activate(row,button)
                self.assertEqual((row['domain'],row['pgc'],row['cell'],row['subpicture']),(2,1,1,spu))
                row=m.call('cell');row=m.call('cell')
                self.assertEqual((row['vts'],row['domain'],row['pgc'],row['subpicture']),(2,8,1,0))

    def test_main_menu_and_game_quit_guard_collision_restarts_before_archive_intro(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            r=[0]*16;r[0]=47;r[1]=r[10]=3
            for vts,pgc,button in [(12,7,3),(2,24,11),(2,26,3)]:
                row=m.start(vts,pgc,r);row=m.activate(row,button)
                self.assertEqual((row['vts'],row['domain'],row['pgc']),(0,4,3))

    def test_source_checkpoints_preserve_partial_keypad_state(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            row=m.start(2,24);row=m.activate(row,7);saved=m.call('save 0')
            row=m.activate(row,5);self.assertEqual(row['registers'][15],7500)
            row=m.call('restore 0');self.assertEqual(row,saved)
            row=m.call('cell');self.assertEqual(row['cell'],2)

    def test_black_holes_success_switches_source_selection_mode(self):
        from extras_source import ExtrasSource
        with ExtrasSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            row=m.start(11,12);self.assertEqual(row['registers'][0],47)

if __name__=='__main__':unittest.main()
