"""Original Memory Morph objects, recall panels, scoring and selection metadata."""
import hashlib,json
from pathlib import Path
from export_extras import ExtraAssets,menu_ref

RECALLS=[[38,42,43,44,45],list(range(49,57)),list(range(61,73))]
def build_memory(m,assets):
    extra=ExtraAssets(m,assets);pages=[];objects=[];rounds=[];made=set()
    labels=json.loads(Path(__file__).with_name('memory_labels.json').read_text())
    if labels['sourceFingerprint']!=m.ifo['sourceFingerprint']:raise ValueError('Memory labels identify another source')
    def registers():
        r=[0]*16;r[0]=47;r[10]=1;r[15]=1;return r
    def simple(id,ref,after):
        if id in made:return
        made.add(id)
        if m.buttons.controls(ref):raise ValueError('Unmapped Memory presentation controls')
        pages.append({'id':id,'scene':assets.register(ref),'focus':0,'loop':False,'controls':[],'after':after})
    for object in range(1,31):
        ref=menu_ref(14,object+4);_,raw=assets.raw(ref);label=labels['objects'].get(str(object))
        if not label or label.get('verified') is not True or label['sourceSha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('Unverified original Memory object label')
        state=m.start(14,object+4,registers())
        if state['selected']!=1:raise ValueError('Unexpected original object cursor reset')
        id=f'memory-object-{object}';simple(id,ref,{'type':'memory-next'});objects.append({'id':object,'label':label['label'],'page':id})
    for stage,pgcs in enumerate(RECALLS):
        length=len(pgcs);intro=f'memory-intro-{stage}';simple(intro,menu_ref(14,39+stage),{'type':'memory-first'})
        recall=[];focuses=[]
        for index,pgc in enumerate(pgcs):
            row=m.start(14,pgc,registers());ref=m.ref(row);rows=m.controls(row)
            if {r['button'] for r in rows}!=set(range(1,31)):raise ValueError('Missing original recall object')
            if len({r['command'] for r in rows})<1:raise ValueError('Missing recall commands')
            actions={id:(objects[id-1]['label'],{'type':'memory-choice','objectId':id}) for id in range(1,31)}
            for object in range(1,31):
                values=registers()
                for slot in range(1,13):values[slot]=1000
                values[14]=0
                initial=m.start(14,pgc,values);after=m.activate(initial,object)
                if after['registers'][13]!=object*1000:raise ValueError('Original recall object mapping differs from its button')
            forced={r['forcedSelect'] for r in rows if r['forcedSelect']}
            if len(forced)>1:raise ValueError('Changing recall focus')
            focus=next(iter(forced)) if forced else row['selected'] or None;focuses.append(focus)
            id=f'memory-recall-{stage}-{index}';recall.append(id)
            pages.append({'id':id,'scene':assets.register(ref,'question-loop'),'focus':focus or 0,'loop':True,'controls':extra.controls(ref,actions),'after':None})
        last=pgcs[-1];base=registers()
        for i in range(1,13):base[i]=1000
        base[14]=0
        row=m.start(14,last,base);right=m.activate(row,1)['registers'][14]
        row=m.start(14,last,base);wrong=m.activate(row,2)['registers'][14]
        if right!=1 or wrong not in [0,1]:raise ValueError('Unexpected Memory comparison')
        always=wrong==1;results=[]
        for score in range(length+1):
            values=list(base);values[14]=max(0,score-1) if always else score
            row=m.start(14,last,values);row=m.activate(row,2)
            if row['pgc'] in pgcs:raise ValueError('Recall did not reach a result')
            ref=m.ref(row);pgc=row['pgc'];id=f'memory-result-{stage}-{pgc}';after=m.call('cell')
            if after['pgc']==36:ending={'type':'page','page':'memory-menu'}
            elif after['pgc'] in [40,41]:ending={'type':'memory-stage','stage':after['pgc']-39}
            else:raise ValueError('Unknown Memory result destination')
            simple(id,ref,ending);results.append(id)
        rounds.append({'length':length,'intro':intro,'recall':recall,'recallFocus':focuses,'results':results,'alwaysCorrectLast':always})
    offsets={}
    for remaining in range(1,14):
        values=registers();values[13]=remaining;values[14]=4;values[15]=0
        offsets[str(remaining)]=m.start(14,37,values)['registers'][15]
    initial=[]
    for variant in [0,3]:
        values=registers();values[12]=variant;initial.append(m.start(14,2,values)['registers'][15])
    return {'objects':objects,'rounds':rounds,'legacyOffsets':offsets,'initialLegacyCues':initial,'initialVariantThreshold':3,'pages':pages}
