"""Source-specific offline normalization for the approved eight-level game."""
import json
from pathlib import Path
import re
from functools import cached_property
from button_index import ButtonIndex
from mode_profiles import mode_profile
from source_commands import validate_inventory, DISASSEMBLER
from export_round import Oracle, source_ref, activation_rows, command_value, choice_groups


def discover_levels(ifo: dict,mode='general-knowledge') -> list[dict]:
    profile=mode_profile(mode)
    decoded=ifo['decodedCommands'];result=[]
    for vts in range(3,11):
        pgcs=[p for p in ifo['pgcs'] if p['vts']==vts and p['domain']=='vts-menu']
        selector=next(p for p in pgcs if any(f'if (g[{profile.mask_register}] & g[10])' in decoded[c] for c in p['commands']['pre']))
        lines=[decoded[c] for c in selector['commands']['pre']]
        selectors={str(v):int(next(re.fullmatch(rf'if \(g\[12\] == 0x{v:x}\) LinkPGCN (\d+)',s).group(1) for s in lines if re.fullmatch(rf'if \(g\[12\] == 0x{v:x}\) LinkPGCN (\d+)',s))) for v in [3,4]}
        selectors['2']=int(re.fullmatch(r'LinkPGCN (\d+)',lines[-1]).group(1))
        entry=next(p for p in pgcs if p['pgc']==1)
        intro=int(re.fullmatch(r'LinkPGCN (\d+)',decoded[entry['commands']['pre'][-1]]).group(1))
        counter=next(p for p in pgcs if any(decoded[c]=='g[13] -= 0x1' for c in p['commands']['pre']))
        ending=int(next(re.fullmatch(r'if \(g\[13\] == 0x0\) LinkPGCN (\d+)',decoded[c]).group(1) for c in counter['commands']['pre'] if re.fullmatch(r'if \(g\[13\] == 0x0\) LinkPGCN (\d+)',decoded[c])))
        result.append({'number':vts-2,'vts':vts,'selectorPgcs':selectors,'introPgc':intro,'endingPgc':ending})
    return result


class SourceModel:
    def __init__(self,source:Path,analysis:Path,mode='general-knowledge',presenter=None):
        self.profile=mode_profile(mode,presenter)
        self._layouts={}
        self.analysis=analysis
        self.ifo=json.loads((analysis/'ifo.json').read_text())
        self.pgcs={(p['vts'],p['domain'],p['pgc']):p for p in self.ifo['pgcs']}
        self.oracle=Oracle(source)
        self.levels={p['vts']:p for p in discover_levels(self.ifo,self.profile)}

    def __enter__(self):return self
    def __exit__(self,*args):self.oracle.close()

    def start(self,vts,pgc,mask=1,variant=2,score=0,remaining=2,seed=42,total=None):
        return self.oracle.call(f'start {vts} {pgc} {mask} {variant} {score} {remaining} {seed} {score if total is None else total} {self.profile.source_value}')

    def entry_setups(self):
        choices={}
        for seed in [1,42,1234,50000,200000,1000000]+[(i*2654435761)%2147483647 for i in range(1,129)]:
            row=self.start(2,9,seed=seed)
            refs,_,_=self.walk(row,lambda r:r['vts']!=2)
            choices[tuple((r['pgc'],r['cell'],r['audio']) for r in refs)]=refs
            if len(choices)==3:break
        if len(choices)!=3:raise ValueError('Incomplete authored setup alternatives')
        return [choices[k] for k in sorted(choices)]

    def question_layout(self,vts,question):
        key=(vts,question)
        if key not in self._layouts:
            p=self.pgcs[(vts,'vts-menu',question)]
            prompts=[]
            for c in p['cells']:
                try:choice_groups(self.buttons.controls({'vts':vts,'pgc':question,'cell':c['cell']}))
                except ValueError:continue
                prompts.append(c['cell'])
            decoded=[self.ifo['decodedCommands'][c] for c in p['commands']['pre']]
            reveals=[(m[1],int(m[2])) for line in decoded if (m:=re.fullmatch(r'if \(g\[15\] >= 0x(?:2710|3e8)\) Link(PGN|CN) (\d+) \(button 0\)',line))]
            if len(prompts)!=1 or len(reveals)!=1:raise ValueError(f'Unsupported question cell roles: {vts}/{question}')
            self._layouts[key]={'prompt':prompts[0],'reveal':p['programs'][reveals[0][1]-1] if reveals[0][0]=='PGN' else reveals[0][1]}
        return self._layouts[key]

    def is_question(self,row):
        if row['domain']!=8:return False
        p=self.pgcs[(row['vts'],'vts-menu',row['pgc'])]
        return bool(p['commands']['pre'] and p['commands']['pre'][0]=='6100000f00030000' and row['cell']==self.question_layout(row['vts'],row['pgc'])['prompt'])

    def walk(self,row,stop,loop_ok=False):
        refs=[];seen=set()
        for _ in range(160):
            if stop(row):return refs,row,False
            ref=source_ref(row);key=tuple(ref.values())
            if key in seen:
                if loop_ok:return refs,row,True
                raise ValueError(f'Unexpected source presentation cycle: {ref}')
            seen.add(key);refs.append(ref);row=self.oracle.call('cell')
        raise ValueError('Source path exceeded160cells')

    def route(self,vts,variant,mask,seed):
        row=self.start(vts,self.levels[vts]['selectorPgcs'][str(variant)],mask,variant,remaining=6,seed=seed)
        refs,row,_=self.walk(row,self.is_question)
        return {'questionPgc':row['pgc'],'questionId':f'{self.profile.prefix}-l{vts-2}-{row["pgc"]:03d}','introRefs':refs,'variant':row['variant'],'mask':mask}

    def timeout(self,vts,question,mask,variant,seed):
        initial=self.start(vts,question,mask,variant,seed=seed)
        prompt=self.question_layout(vts,question)['prompt']
        _,initial,_=self.walk(initial,lambda r:r['pgc']==question and r['cell']==prompt)
        seen=set();plays=0
        while True:
            # DVD cell geometry can repeat while its authored loop counter advances.
            key=tuple(initial['registers'])
            if key in seen:return {'kind':'loop'}
            seen.add(key);plays+=1
            row=self.oracle.call('cell')
            if row['pgc']!=question or row['cell']!=prompt:break
            initial=row
            if plays>32:raise ValueError('Unsupported question repeat count')
        candidate=row['candidate']
        refs,row,_=self.walk(row,lambda r:r['remaining']!=2)
        if row['score']!=0 or candidate<1 or candidate>32768 or candidate&(candidate-1):
            raise ValueError(f'Unsupported timeout semantics: {vts}/{question}/{row}')
        return {'kind':'timeout','plays':plays,'initialHighlight':initial['registers'][10]//1024,
                'nextCandidateMask':candidate,'refs':refs}


    @cached_property
    def buttons(self):
        inventory={**self.ifo,'pgcs':[p for p in self.ifo['pgcs'] if 2<=p['vts']<=10]}
        with (self.analysis/'buttons.jsonl').open() as stream:
            return ButtonIndex(inventory,(json.loads(line) for line in stream))

    def presentation(self,row,vts,allow_bonus=False):
        stop=lambda r:r['vts']!=vts or (allow_bonus and vts==10 and r['pgc']==self.profile.bonus_intro_pgc)
        refs=[];seen=set();gate=None
        for _ in range(160):
            if stop(row):break
            ref=source_ref(row);key=tuple(ref.values())
            if key in seen:raise ValueError(f'Uncontrolled presentation loop: {ref}')
            seen.add(key);refs.append(ref)
            controls=self.buttons.controls(ref) if row['domain']==8 else []
            if controls:
                if len({r['command'] for r in controls})!=1:
                    raise ValueError(f'Unresolved presentation control: {ref}')
                control=min(controls,key=lambda r:r['button'])
                p=self.pgcs[(vts,'vts-menu',row['pgc'])]
                cell=next(c for c in p['cells'] if c['cell']==row['cell'])
                commands=([p['commands']['cell'][cell['commandNumber']-1]] if cell['commandNumber'] else p['commands']['post'])
                decoded=[self.ifo['decodedCommands'][c] for c in commands]
                loop=decoded==[f'LinkCN {row["cell"]} (button 0)']
                if not loop and decoded!=[self.ifo['decodedCommands'][control['command']]]:
                    raise ValueError(f'Different automatic/control presentation routes: {ref}: {decoded}')
                after=self.oracle.call('answer '+control['command'])
                after_refs,row,_=self.walk(after,stop)
                gate={'ref':ref,'buttonRow':control,'controlRows':controls,'afterRefs':after_refs,'loop':loop}
                break
            row=self.oracle.call('cell')
        else:raise ValueError('Presentation exceeded160cells')
        result={'refs':refs}
        if gate:result['gate']=gate
        result['destination']='bonus' if allow_bonus and row['vts']==10 and row['pgc']==self.profile.bonus_intro_pgc else ('next-level' if vts<10 else 'complete')
        expected=vts+1 if vts<10 else 2
        if result['destination']!='bonus' and row['vts']!=expected:
            raise ValueError(f'Unexpected presentation boundary: {row}')
        result['nextCandidateMask']=row['candidate']
        return result

    def ending(self,vts,score,total,mask,variant=2):
        row=self.start(vts,self.levels[vts]['endingPgc'],mask,variant,score,remaining=0,total=total)
        return self.presentation(row,vts,True)

    def prepare_bonus(self,variant):
        row=self.start(10,281,mask=0,variant=variant,score=6,remaining=0,total=48)
        refs,row,_=self.walk(row,lambda r:r['vts']==10 and r['pgc'] in self.profile.bonus_pgcs and r['cell']==2)
        return refs,row

    def bonus(self,variant):
        intros,row=self.prepare_bonus(variant)
        ref=source_ref(row);controls=self.buttons.controls(ref)
        groups=choice_groups(controls)
        paths=[];buttons=[]
        for group in groups:
            if len({r['command'] for r in group})!=1:raise ValueError('Changing final bonus answer command')
            button=min(group,key=lambda r:r['button']);buttons.append(button)
            self.prepare_bonus(variant)
            row=self.oracle.call('answer '+button['command'])
            paths.append(self.presentation(row,10))
        correct=[i for i,path in enumerate(paths) if path.get('gate',{}).get('ref',{}).get('pgc')==301]
        if len(correct)!=1:raise ValueError('Unresolved bonus correct association')
        wrongs=[path for i,path in enumerate(paths) if i not in correct]
        if any(path!=wrongs[0] for path in wrongs):raise ValueError('Nonuniform bonus wrong paths')
        self.prepare_bonus(variant);timeout=self.presentation(self.oracle.call('cell'),10)
        if timeout!=wrongs[0]:raise ValueError('Different bonus expiry path')
        return {'id':'perfect-bonus-low' if variant<3 else 'perfect-bonus-high','introRefs':intros,
                'questionRef':ref,'buttonRows':buttons,'controlRows':controls,'correctChoice':'ABCD'[correct[0]],
                'correct':paths[correct[0]],'wrong':wrongs[0],'timeout':timeout}


def build_game_model(source:Path,analysis:Path,mode='general-knowledge',presenter=None) -> dict:
    profile=mode_profile(mode,presenter)
    import hashlib
    from asset_cache import digest
    ifo=json.loads((analysis/'ifo.json').read_text())
    validate_inventory(ifo)
    identity={'mode':profile.id,'inventory':digest(analysis/'ifo.json'),'disassembler':digest(DISASSEMBLER),
              'normalizers':{name:digest(Path(__file__).with_name(name)) for name in ['button_index.py','source_commands.py','asset_cache.py','mode_profiles.py']},
              'source':ifo['sourceFingerprint'],'buttons':digest(analysis/'buttons.jsonl'),
              'code':digest(Path(__file__)),'shared':digest(Path(__file__).with_name('export_round.py')),
              'oracle':digest(Path(__file__).parents[1]/'dvd/build/round_oracle')}
    if profile.presenter!='norman':identity['presenter']=profile.presenter
    cache=analysis/profile.model_file
    if cache.exists():
        model=json.loads(cache.read_text())
        if model.get('identity')==identity:return model
    result={'sourceFingerprint':ifo['sourceFingerprint'],'identity':identity,'levels':[]}
    with SourceModel(source,analysis,profile) as model:
        for vts,definition in model.levels.items():
            routes={};cases={};answers={};timeouts={};expiry={};intros={};endings={}
            for variant in [2,3,4]:
                for bit in range(16):
                    mask=1<<bit;options={}
                    for seed in [1,42,1234,50000,200000,1000000]:
                        option=model.route(vts,variant,mask,seed)
                        options[option['variant']]=option;cases[(option['variant'],mask)]=option
                        if variant!=4 or mask<64 or len(options)==2:break
                    if variant==4 and mask>=64 and len(options)!=2:raise ValueError('Missing source fallback variant')
                    routes[f'{variant}:{mask}']=[options[k] for k in sorted(options)]
            print('Level',vts-2,'routes',len(cases),flush=True)
            for (variant,mask),option in cases.items():
                q=option['questionPgc'];pgc=model.pgcs[(vts,'vts-menu',q)]
                decoded=[ifo['decodedCommands'][c] for c in pgc['commands']['pre']]
                sequence=[int(re.fullmatch(r'if \(g\[15\] == 0x([1-4])\) g\[14\] \+= 0x1',line).group(1)) for line in decoded if re.fullmatch(r'if \(g\[15\] == 0x([1-4])\) g\[14\] \+= 0x1',line)]
                ref={'vts':vts,'domain':'vts-menu','pgc':q,'cell':model.question_layout(vts,q)['prompt']}
                controls=model.buttons.controls(ref)
                groups=choice_groups(controls)
                origin=min(r['vobuStart'] for r in controls)
                for index,group in enumerate(groups):
                    choice='ABCD'[index]
                    for window_index,(control,_,_) in enumerate(activation_rows(group,origin)):
                        for correct in ([False,True] if sequence and index+1==sequence[-1] else [False] if sequence else [command_value(ifo['decodedCommands'][control['command']])[1]<=4]):
                            candidate=mask if sequence else command_value(ifo['decodedCommands'][control['command']])[0]
                            model.start(vts,q,mask,variant)
                            if sequence:
                                for button in (sequence if correct else [1,1,1,index+1]):
                                    model.oracle.call(f'select {button}')
                                    row=model.oracle.call(f'answer 200400000000{q:04x}')
                            else:
                                model.oracle.call(f"select {control['button']}")
                                row=model.oracle.call('answer '+control['command'])
                            refs,row,_=model.walk(row,lambda r:r['remaining']!=2)
                            if row['score']!=int(correct):raise ValueError(f'Source score mismatch: {vts}/{q}')
                            key=f'{variant}:{mask}:{"correct" if correct else "wrong"}:{candidate}:{choice}-{window_index}'
                            if key in answers and answers[key]!=refs:raise ValueError(f'Ambiguous feedback button: {vts}/{q}/{key}')
                            answers[key]=refs
                choices={};count=4 if any('g[10] rnd 0x4' in line for line in decoded) else 1
                for seed in [1,42,1234,50000,200000,1000000]+[(i*2654435761)%2147483647 for i in range(1,129)]:
                    outcome=model.timeout(vts,q,mask,variant,seed)
                    if outcome['kind']=='loop':break
                    choices[outcome['initialHighlight']]=outcome
                    if len(choices)==count:break
                if outcome['kind']=='timeout' and len(choices)!=count:raise ValueError(f'Incomplete timeout outcomes: {vts}/{q}')
                timeouts[f'{variant}:{mask}']=[choices[k] for k in sorted(choices)]
                expiry_value={'kind':outcome['kind'],'plays':outcome.get('plays',0)}
                previous=expiry.setdefault(q,expiry_value)
                if previous!=expiry_value:raise ValueError('Variant-dependent expiry requires explicit rules')
            print('Level',vts-2,'answer/expiry paths',len(answers),len(timeouts),flush=True)
            for bit in range(16):
                mask=1<<bit
                row=model.start(vts,definition['introPgc'],mask,remaining=7)
                refs,_,_=model.walk(row,lambda r:r['remaining']!=7)
                intros[str(mask)]=refs
                for prior in range(6*(vts-3)+1):
                    for score in range(7):
                        total=prior+score
                        endings[f'{score}:{total}:{mask}']=model.ending(vts,score,total,mask)
            questions=sorted({o['questionPgc'] for o in cases.values()})
            if len(questions)!=38:raise ValueError(f'Unexpected question pool size in VTS{vts}')
            result['levels'].append({**definition,'questionPgcs':questions,'questionCells':{str(q):model.question_layout(vts,q) for q in questions},'routes':routes,'answers':answers,
                                     'timeouts':timeouts,'expiry':{str(q):kind for q,kind in expiry.items()},
                                     'intros':intros,'endings':endings})
            print('Level',vts-2,'complete;',len(endings),'cumulative endings',flush=True)
        result['bonuses']=[model.bonus(2),model.bonus(3)]
    temporary=cache.with_suffix('.tmp.json');temporary.write_text(json.dumps(result,separators=(',',':'))+'\n');temporary.replace(cache)
    return result
