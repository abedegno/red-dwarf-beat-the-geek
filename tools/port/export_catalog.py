"""Publish a complete local catalog only after every supported mode validates."""
import argparse,hashlib,json
from pathlib import Path
from export_game import export_game,validate_game
from mode_profiles import PROFILES,mode_profile
MODE_ORDER=['viewer','geek','general-knowledge']

def publish_catalog(games,output,hattie_games=None):
    if set(games)!=set(PROFILES):raise ValueError('All three complete quiz modes are required')
    if hattie_games is not None and set(hattie_games)!=set(PROFILES):raise ValueError('All three complete Hattie modes are required')
    collections=[('',games)]+([('hattie-',hattie_games)] if hattie_games is not None else [])
    fingerprints={g.get('sourceFingerprint') for _,collection in collections for g in collection.values()}
    if len(fingerprints)!=1 or not next(iter(fingerprints)):raise ValueError('Quiz modes identify different sources')
    prepared={};entries={}
    for prefix,collection in collections:
        own={}
        for id in MODE_ORDER:
            game=collection[id];validate_game(game)
            if len(game['bonuses'])!=2:raise ValueError('Both final bonus variants are required: '+id)
            if prefix:
                holly=game['entry']['menus'][2]
                if not holly.get('windows') or any(w['endTicks']<=w['startTicks'] for w in holly['windows']):raise ValueError('Missing presenter activation windows: '+id)
                if len(game['entry'].get('setupOptions',[]))!=3:raise ValueError('Missing Hattie setup alternatives: '+id)
            menu=game['entry']['menus'][1]
            if not menu.get('windows') or any(w['endTicks']<=w['startTicks'] for w in menu['windows']):raise ValueError('Missing mode activation windows: '+id)
            payload=(json.dumps(game,separators=(',',':'))+'\n').encode()
            path=f'/games/{prefix}{id}-{hashlib.sha256(payload).hexdigest()}.json';prepared[path]=payload
            own[id]={'label':mode_profile(id).label,'dataPath':path,'control':{key:menu[key] for key in ['label','rect','highlightSrc','windows']}}
        entries[prefix]=own
    result={'schemaVersion':2 if hattie_games is not None else 1,'sourceFingerprint':next(iter(fingerprints)),'modes':entries['']}
    if hattie_games is not None:result['hattieModes']=entries['hattie-']
    for name,payload in prepared.items():
        target=output/name.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():
            temporary=target.with_suffix('.tmp.json');temporary.write_bytes(payload);temporary.replace(target)
        elif target.read_bytes()!=payload:raise ValueError('Versioned dataset content mismatch: '+name)
    output.mkdir(parents=True,exist_ok=True)
    temporary=output/'catalog.tmp.json';temporary.write_text(json.dumps(result,separators=(',',':'))+'\n');temporary.replace(output/'catalog.json')
    return result

def export_catalog(source,analysis,output):
    games={id:export_game(source,analysis,output,mode=id) for id in PROFILES}
    hattie={id:export_game(source,analysis,output,mode=id,presenter='hattie') for id in PROFILES}
    return publish_catalog(games,output,hattie)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=Path('disc/2EDVD108'))
    parser.add_argument('--analysis',type=Path,default=Path('analysis'))
    parser.add_argument('--output',type=Path,default=Path('app/public'))
    args=parser.parse_args();export_catalog(args.source.resolve(),args.analysis.resolve(),args.output.resolve())
