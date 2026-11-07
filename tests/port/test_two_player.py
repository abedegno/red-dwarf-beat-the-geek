import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/port'))

class TwoPlayerTests(unittest.TestCase):
    def test_actual_menu_commands_produce_all_nine_session_codes(self):
        from two_player import TwoPlayerSource
        from export_game import mode_menu_group
        cases=[('general-knowledge','general-knowledge',11121),('general-knowledge','viewer',12121),('general-knowledge','geek',13121),('viewer','general-knowledge',11221),('viewer','viewer',12221),('viewer','geek',13221),('geek','general-knowledge',11321),('geek','viewer',12321),('geek','geek',13321)]
        with TwoPlayerSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for first,second,code in cases:
                row=m.start2(2,3)
                for pgc,mode in [(6,first),(7,second)]:
                    self.assertEqual(row['pgc'],pgc)
                    group=mode_menu_group(m.buttons.controls({'vts':2,'pgc':pgc,'cell':1}),mode)
                    button=min(group,key=lambda r:r['button'])
                    m.oracle.call('select '+str(button['button']))
                    row=m.oracle.call('answer '+button['command'])
                self.assertEqual((row['pgc'],row['registers'][0]),(9,code))

    def test_nine_original_mode_combinations_and_alternating_credit(self):
        from two_player import TwoPlayerSource,session_code
        modes=['general-knowledge','viewer','geek']
        with TwoPlayerSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for a in modes:
                for b in modes:
                    code=session_code(a,b)
                    for remaining,expected in [(12,(1,0)),(11,(0,1))]:
                        row=m.start2(3,4,a,b,remaining=remaining)
                        self.assertEqual(row['registers'][0],code)
                        self.assertEqual((row['registers'][1]%100,(row['registers'][1]%10000)//100),expected)
                        self.assertEqual(row['pgc'] in range(113,121),remaining==12)
            with self.assertRaises(ValueError):session_code('invalid','geek')

    def test_each_player_routes_to_own_mode(self):
        from two_player import TwoPlayerSource
        with TwoPlayerSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for a,b in [('viewer','geek'),('geek','general-knowledge'),('general-knowledge','viewer')]:
                for remaining,mode in [(12,a),(11,b)]:
                    row=m.start2(3,108,a,b,remaining=remaining,variant=1)
                    self.assertEqual(row['pgc'],109 if remaining==12 else 110)
                    refs,row,_=m.walk(row,m.is_question)
                    from mode_profiles import mode_profile
                    from progression_model import discover_levels
                    selectors=discover_levels(m.ifo,mode)[0]['selectorPgcs']
                    row2=m.start(3,selectors['2'],mask=1,variant=2)
                    _,row2,_=m.walk(row2,m.is_question)
                    self.assertEqual(row['pgc'],row2['pgc'])

    def test_scorecards_are_separate_and_preserve_presenter_audio(self):
        from two_player import TwoPlayerSource
        with TwoPlayerSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for vts in range(3,11):
                for player in [0,1]:
                    p=m.scorecard(vts,player,5,5)
                    audio={r['audio'] for r in p['refs'] if r['domain']=='title'}
                    self.assertEqual(audio,{2 if player==0 else 5})
                    self.assertEqual(p['destination'],'next-player' if player==0 else 'complete' if vts==10 else 'next-level')

    def test_either_player_gets_own_perfect_bonus_and_returns_to_correct_boundary(self):
        from two_player import TwoPlayerSource
        with TwoPlayerSource(ROOT/'disc/2EDVD108',ROOT/'analysis') as m:
            for player in [0,1]:
                self.assertEqual(m.scorecard(10,player,6,48)['destination'],'bonus')
                self.assertNotEqual(m.scorecard(10,player,6,47)['destination'],'bonus')
                for mode in ['general-knowledge','viewer','geek']:
                    for variant in [2,3]:
                        b=m.bonus_paths(mode,player,variant)
                        self.assertEqual(b['correct']['gate']['ref']['pgc'],301)
                        self.assertEqual(b['correct']['destination'],'next-player' if player==0 else 'complete')
                        self.assertEqual(b['wrong']['destination'],b['correct']['destination'])

if __name__=='__main__':unittest.main()
