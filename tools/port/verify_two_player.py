"""Continuously run the original two-player DVD logic against native records."""
import json
from pathlib import Path
from two_player import TwoPlayerSource,MODES
from mode_profiles import mode_profile
from export_round import Assets,source_ref,activation_rows,choice_groups

def verify():
    root=Path('app/public');metadata=json.loads((root/'two-player.json').read_text())
    games=[[json.loads((root/mode_profile(mode,'norman' if player==0 else 'hattie').dataset_file).read_text()) for mode in MODES] for player in [0,1]]
    results=[]
    with TwoPlayerSource(Path('disc/2EDVD108'),Path('analysis')) as m:
        assets=Assets(Path('disc/2EDVD108'),Path('analysis'),root,m.pgcs)
        def scene(row):return assets.register(source_ref(row))
        def consume(row,p):
            for id in p['scenes']:
                assert scene(row)==id,(source_ref(row),id)
                if p.get('gate',{}).get('scene')==id:
                    controls=m.buttons.controls(source_ref(row));assert len({r['command'] for r in controls})==1
                    row=m.oracle.call('answer '+controls[0]['command'])
                    for after in p['gate']['afterScenes']:
                        assert scene(row)==after,(source_ref(row),after)
                        row=m.oracle.call('cell')
                else:row=m.oracle.call('cell')
            return row
        def answer(row,q,ids):
            controls=m.buttons.controls(source_ref(row))
            for choice in ids:
                group=choice_groups(controls)['ABCD'.index(choice)]
                button=activation_rows(group,min(r['vobuStart'] for r in controls))[0][0]
                m.oracle.call('select '+str(button['button']))
                row=m.oracle.call('answer '+button['command'])
            return row
        for first in MODES:
            for second in MODES:
                for strategy in ['correct','wrong','mixed','late-timeouts']:
                    row=m.start2(3,m.levels[3]['introPgc'],first,second,remaining=13,seed=42)
                    totals=[0,0];scores=[0,0];n=0;events=[];bonuses=[];current_level=1;seen_banks={}
                    for step in range(4000):
                        if row['vts']==2:break
                        vts=row['vts'];level=vts-3
                        if level+1!=current_level:scores=[0,0];current_level=level+1;seen_banks={}
                        if m.is_question(row):
                            player=n%2;mode=[first,second][player];data=games[player][MODES.index(mode)]
                            q=next(q for q in data['levels'][level]['questions'] if int(q['id'].split('-')[-1])==row['pgc'])
                            slot=row['registers'][11];bank=mode_profile(mode).mask_register
                            assert not seen_banks.get(mode,0)&slot,('duplicate',first,second,n,slot)
                            seen_banks[mode]=seen_banks.get(mode,0)|slot
                            assert row['registers'][bank]==seen_banks[mode]
                            correct=strategy=='correct' or strategy=='mixed' and (n//2)%2==0
                            remaining=row['remaining'];variant=row['variant']
                            if strategy=='late-timeouts' and level>=3:
                                initial=row;plays=0
                                while row['pgc']==initial['pgc'] and row['cell']==initial['cell']:
                                    row=m.oracle.call('cell');plays+=1
                                    assert plays<=4
                                assert plays==max(1,q.get('promptPlays',1)-initial['registers'][9])
                            else:
                                ids=q['correctSequence'] if q['kind']=='sequence' and correct else ['A']*4 if q['kind']=='sequence' else [q['correctChoice'] if correct else next(c['id'] for c in q['choices'] if c['id']!=q['correctChoice'])]
                                row=answer(row,q,ids);totals[player]+=int(correct);scores[player]+=int(correct)
                                w=next(w for w in q['windows'] if w['choiceId']==ids[-1]);candidate=w['nextCandidateMask'] or slot
                                key=f"{variant}:{slot}:{'correct' if correct else 'wrong'}:{candidate}:{w['feedbackVariant']}"
                                refs,row,_=m.walk(row,lambda r:r['remaining']!=remaining)
                                assert [assets.register(r) for r in refs]==data['levels'][level]['answers'][key],(first,second,strategy,n,key)
                            n+=1
                            assert [row['registers'][1]%100,(row['registers'][1]%10000)//100]==totals
                            events.append({'event':'answer','number':n,'player':player+1,'question':q['id'],'totals':totals[:]})
                            continue
                        card_pgcs=[193,194] if vts==3 else [77,78]
                        if row['domain']==8 and row['pgc'] in card_pgcs:
                            player=card_pgcs.index(row['pgc']);p=metadata['levels'][level]['scorecards'][player][f'{scores[player]}:{totals[player]}']
                            candidate_before=row['candidate'];row=consume(row,p)
                            assert row['registers'][9]==p['nextOrderingRepeatOffset']
                            if p['destination']!='bonus':assert row['candidate']==candidate_before
                            events.append({'event':'scorecard','level':level+1,'player':player+1,'score':scores[player],'total':totals[player],'destination':p['destination'],'candidateBefore':candidate_before,'candidateAfter':row['candidate'],'orderingRepeatCarry':row['registers'][9]})
                            assert (row['vts']==10 and row['pgc'] in [283,284])==(p['destination']=='bonus')
                            if p['destination']=='bonus':
                                mode=[first,second][player];data=games[player][MODES.index(mode)];i=0 if row['variant']<3 else 1
                                extra=metadata['bonuses'][player][mode][i];b=data['bonuses'][i]
                                for id in extra['introScenes']:
                                    assert scene(row)==id;row=m.oracle.call('cell')
                                assert scene(row)==b['question']['promptScene']
                                row=answer(row,b['question'],[b['question']['correctChoice']]);row=consume(row,extra['correct']);bonuses.append(player)
                            continue
                        controls=m.buttons.controls(source_ref(row)) if row['domain']==8 else []
                        if controls:
                            assert len({r['command'] for r in controls})==1,source_ref(row)
                            row=m.oracle.call('answer '+controls[0]['command'])
                        else:row=m.oracle.call('cell')
                    else:raise AssertionError('Two-player source failed to terminate')
                    expected={'correct':[48,48],'wrong':[0,0],'mixed':[24,24],'late-timeouts':[0,0]}[strategy]
                    assert n==96 and totals==expected,(first,second,strategy,n,totals)
                    assert bonuses==([0,1] if strategy=='correct' else [])
                    results.append({'players':[first,second],'strategy':strategy,'questions':n,'totals':totals,'bonuses':bonuses,'events':events})
                    print(first,second,strategy,n,totals,bonuses,flush=True)
    Path('analysis/two-player/continuous-source.json').write_text(json.dumps(results,indent=2)+'\n')

if __name__=='__main__':verify()
