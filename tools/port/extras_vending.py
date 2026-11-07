"""Original Vending Machine products, keypad stages and semantic selection cues."""
import re
from export_extras import ExtraAssets,menu_ref

DEFINITIONS=[(4,12,13,14,[9,10,11],3),(5,21,22,23,[16,17,18,19],5),(6,34,32,33,[25,26,27,28,29],5)]
def build_vending(m,assets):
    extra=ExtraAssets(m,assets);pages=[];rounds=[];provenance={}
    def registers(flag=47):
        r=[0]*16;r[0]=flag;r[10]=1;r[15]=1;return r
    def simple(id,ref,after):
        if m.buttons.controls(ref):raise ValueError('Unmapped Vending presentation controls')
        pages.append({'id':id,'scene':assets.register(ref),'focus':0,'loop':False,'controls':[],'after':after})
    for n,(intro,selector,success,wrong,pgcs,limit) in enumerate(DEFINITIONS):
        products=[];pgc_ids={p:f'vending-product-{n}-{i}' for i,p in enumerate(pgcs)}
        for i,pgc in enumerate(pgcs):
            id=pgc_ids[pgc];r=registers();r[1]=1;row=m.start(13,pgc,r);stage_pages=[]
            if row['pgc']!=pgc:raise ValueError('Unexpected used-product fallback')
            provenance[id]={'pgc':pgc,'bit':row['registers'][3]}
            for stage in range(n+2):
                ref=m.ref(row);before=row['registers'][12];m.call('save 300');groups={}
                for c in m.controls(row):groups.setdefault(c['button'],[]).append(c)
                if set(groups)!=set(range(1,11)):raise ValueError('Missing original vending digit')
                actions={};correct=[]
                for button,group in groups.items():
                    m.call('restore 300');after=m.activate(row,button)
                    delta=after['registers'][12]-before
                    if delta not in [0,1]:raise ValueError('Unexpected source digit scoring')
                    if after['pgc']==pgc:
                        next_stage=after['cell']-1
                        if not 0<=next_stage<n+2:raise ValueError(f'Unsupported source digit continuation product={pgc} stage={stage} button={button} selected={after["selected"]} cell={after["cell"]}')
                    elif after['pgc'] in [success,wrong]:next_stage=None
                    else:raise ValueError('Unexpected original vending digit destination')
                    description=m.ifo['decodedCommands'][group[0]['command']]
                    if re.fullmatch(r'LinkNoLink \(button \d+\)',description):
                        if delta or after['pgc']!=pgc or after['cell']!=row['cell']:raise ValueError('Unexpected selection-only digit')
                        action={'type':'focus','controlId':after['selected']}
                    else:
                        if after['pgc']==pgc and after['selected']!=button:raise ValueError('Unmapped digit focus change')
                        action={'type':'vending-digit','digit':button%10,'correct':delta==1,'nextStage':next_stage}
                    actions[button]=(str(button%10),action)
                    if delta:correct.append(button)
                if len(correct)!=1:raise ValueError('Original vending code has ambiguous digit')
                page=f'{id}-digit-{stage}';stage_pages.append(page)
                pages.append({'id':page,'scene':assets.register(ref,'question-loop'),'focus':1,'loop':True,'controls':extra.controls(ref,actions),'after':None})
                m.call('restore 300');row=m.activate(row,correct[0])
            products.append({'id':id,'pages':stage_pages})
        cue_products={}
        for seed in [1,42,1234,50000,200000,1000000]+[(i*2654435761)%2147483647 for i in range(1,129)]:
            row=m.start(13,selector,registers(10000),seed=seed);cue=row['registers'][15]
            cue_products[str(cue)]=pgc_ids[row['pgc']]
            if len(cue_products)==limit:break
        if len(cue_products)!=limit:raise ValueError('Missing randomized vending alternatives')
        for cue in [6,7,100]:
            r=registers();r[15]=cue-2;row=m.start(13,selector,r)
            if row['registers'][15]!=cue:raise ValueError('Unexpected legacy vending cue')
            cue_products[str(cue)]=pgc_ids[row['pgc']]
        default=cue_products.pop('100')
        # Verify each used-item redirect against the real source, not array order alone.
        for index,product in enumerate(products):
            r=registers();r[3]=provenance[product['id']]['bit'];row=m.start(13,pgcs[index],r)
            if pgc_ids[row['pgc']]!=products[(index+1)%len(products)]['id']:raise ValueError('Noncyclic original product fallback')
        intro_pages=[f'vending-intro-{n}',f'vending-table-{n}']
        for cell,id in enumerate(intro_pages,1):simple(id,menu_ref(13,intro,cell),{'type':'vending-table' if cell==1 else 'vending-order'})
        success_page=f'vending-success-{n}';wrong_page=f'vending-wrong-{n}'
        simple(success_page,menu_ref(13,success),{'type':'vending-order'});simple(wrong_page,menu_ref(13,wrong),{'type':'page','page':'vending-menu'})
        rounds.append({'intro':intro_pages,'products':products,'randomRange':limit,'cueProducts':cue_products,'defaultProduct':default,'successPage':success_page,'wrongPage':wrong_page})
    simple('vending-complete',menu_ref(13,35),{'type':'page','page':'vending-menu'})
    initial={}
    for bit in range(16):
        seed=1<<bit;r=registers();r[10]=seed;row=m.start(13,8,r);initial[str(seed)]=row['registers'][15]
    r=registers();r[10]=3;row=m.start(13,8,r);default_initial=row['registers'][15]
    overrides=[]
    for pgc in [15,24]:
        table={}
        for bit in range(1,15):
            r=registers();r[10]=1<<(bit-1);r[15]=200;row=m.start(13,pgc,r)
            if row['registers'][10]!=1<<bit:raise ValueError('Unexpected vending seed doubling')
            if row['registers'][15]!=200:table[str(1<<bit)]=row['registers'][15]
        overrides.append(table)
    (m.analysis/'extras/vending-provenance.json').write_text(__import__('json').dumps(provenance,indent=2)+'\n')
    return {'rounds':rounds,'initialCues':initial,'initialCueDefault':default_initial,'initialRandomRange':3,'roundCueOverrides':overrides,'completePage':'vending-complete','pages':pages}
