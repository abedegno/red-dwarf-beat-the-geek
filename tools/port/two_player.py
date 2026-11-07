"""Offline source boundaries for the disc's two-player session."""
from progression_model import SourceModel
from mode_profiles import mode_profile
from export_round import source_ref,choice_groups

MODES=('general-knowledge','viewer','geek')

def session_code(first,second):
    return 10021+100*((mode_profile(first).source_value%1000)//100)+1000*((mode_profile(second).source_value%1000)//100)

class TwoPlayerSource(SourceModel):
    def start2(self,vts,pgc,first='general-knowledge',second='general-knowledge',mask=1,variant=2,scores=(0,0),totals=(0,0),remaining=12,seed=42):
        return self.oracle.call(f'two {vts} {pgc} {session_code(first,second)} {mask} {variant} {scores[0]} {scores[1]} {totals[0]} {totals[1]} {remaining} {seed}')

    def segment(self,row,vts,player,allow_bonus=True):
        next_card=194 if vts==3 else 78
        def stop(r):
            return r['vts']!=vts or (player==0 and r['domain']==8 and r['pgc']==next_card) or (allow_bonus and vts==10 and r['pgc'] in [283,284])
        refs=[];gate=None;seen=set()
        for _ in range(160):
            if stop(row):break
            ref=source_ref(row);key=tuple(ref.values())
            if key in seen:raise ValueError(f'Uncontrolled two-player segment: {ref}')
            seen.add(key);refs.append(ref)
            controls=self.buttons.controls(ref) if row['domain']==8 else []
            if controls:
                if gate or len({r['command'] for r in controls})!=1:raise ValueError(f'Unsupported two-player gate: {ref}')
                p=self.pgcs[(vts,'vts-menu',row['pgc'])]
                cell=next(c for c in p['cells'] if c['cell']==row['cell'])
                commands=[p['commands']['cell'][cell['commandNumber']-1]] if cell['commandNumber'] else p['commands']['post']
                decoded=[self.ifo['decodedCommands'][c] for c in commands]
                loop=decoded==[f'LinkCN {row["cell"]} (button 0)']
                control=min(controls,key=lambda r:r['button'])
                if not loop and decoded!=[self.ifo['decodedCommands'][control['command']]]:raise ValueError('Different two-player gate routes')
                after=self.oracle.call('answer '+control['command'])
                after_refs,row,_=self.walk(after,stop)
                gate={'ref':ref,'controlRows':controls,'afterRefs':after_refs,'loop':loop}
                break
            row=self.oracle.call('cell')
        else:raise ValueError('Two-player segment exceeds 160 cells')
        if not stop(row):raise ValueError('Unresolved segment boundary')
        dest='bonus' if row['vts']==10 and row['pgc'] in [283,284] else ('next-player' if player==0 else 'next-level' if vts<10 else 'complete')
        result={'refs':refs,'destination':dest,'nextCandidateMask':row['candidate'],'nextOrderingRepeatOffset':row['registers'][9]}
        if gate:result['gate']=gate
        return result

    def scorecard(self,vts,player,score,total,first='general-knowledge',second='general-knowledge',variant=2):
        scores=[0,0];scores[player]=score
        totals=[0,0];totals[player]=total
        row=self.start2(vts,192 if vts==3 else 76,first,second,scores=scores,totals=totals,remaining=3-player,variant=variant)
        return self.segment(row,vts,player)

    def bonus_paths(self,mode,player,variant):
        profile=mode_profile(mode,'norman' if player==0 else 'hattie')
        def prepare():
            row=self.start2(10,282,mode,mode,scores=(6,6),totals=(48,48),remaining=2-player,variant=variant)
            return self.walk(row,lambda r:r['pgc'] in profile.bonus_pgcs and r['cell']==2)[:2]
        intros,row=prepare();ref=source_ref(row)
        paths=[]
        for group in choice_groups(self.buttons.controls(ref)):
            if len({r['command'] for r in group})!=1:raise ValueError('Changing two-player bonus command')
            prepare()
            paths.append(self.segment(self.oracle.call('answer '+group[0]['command']),10,player,False))
        correct=[i for i,p in enumerate(paths) if p.get('gate',{}).get('ref',{}).get('pgc')==301]
        if len(correct)!=1:raise ValueError('Unresolved two-player bonus correct choice')
        wrong=[p for i,p in enumerate(paths) if i!=correct[0]]
        if any(p!=wrong[0] for p in wrong):raise ValueError('Nonuniform two-player bonus wrong paths')
        prepare()
        if self.segment(self.oracle.call('cell'),10,player,False)!=wrong[0]:raise ValueError('Different two-player bonus expiry')
        return {'introRefs':intros,'questionRef':ref,'correctChoice':'ABCD'[correct[0]],'correct':paths[correct[0]],'wrong':wrong[0]}
