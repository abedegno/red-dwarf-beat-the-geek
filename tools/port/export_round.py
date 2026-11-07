"""Normalize this DVD's selected round to native semantic data and prepared media."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spu
from asset_cache import cache_identity, cache_valid, record_cache, validate_button_fingerprint
from source_commands import require_known_commands, validate_inventory


def command_value(text):
    match = re.fullmatch(r'g\[10\] = 0x([0-9a-f]+), LinkTailPGC \(button (\d+)\)', text)
    if not match:
        raise ValueError(f'Unsupported answer command: {text}')
    return int(match[1], 16), int(match[2])


def activation_rows(rows, origin):
    """One visible control per authored HLI interval, not per early NAV packet."""
    by_sector = defaultdict(list)
    for row in rows:
        by_sector[row['sector']].append(row)
    intervals = {}
    for group in by_sector.values():
        row = min(group, key=lambda r: r['button'])
        start = max(0, row['highlightStart'] - origin)
        end = min(row['highlightEnd'], row['selectionEnd']) - origin
        if end <= start:
            raise ValueError(f'Invalid authored activation interval at sector {row["sector"]}')
        key = (start, end)
        previous = intervals.get(key)
        if previous and (previous['command'] != row['command'] or previous['rectangle'] != row['rectangle']):
            raise ValueError(f'Conflicting repeated highlight interval at sector {row["sector"]}')
        intervals[key] = row
    ordered = sorted(intervals)
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        raise ValueError('Overlapping authored activation intervals')
    return [(intervals[key], *key) for key in ordered]


def control_groups(rows):
    def overlaps(a,b):
        width=max(0,min(a[2],b[2])-max(a[0],b[0])+1)
        height=max(0,min(a[3],b[3])-max(a[1],b[1])+1)
        return width*height>min((a[2]-a[0]+1)*(a[3]-a[1]+1),(b[2]-b[0]+1)*(b[3]-b[1]+1))/2
    groups=[]
    for row in sorted(rows,key=lambda r:tuple(r['rectangle'])):
        matching=[g for g in groups if any(overlaps(row['rectangle'],r['rectangle']) for r in g)]
        group=[row]
        for found in matching:groups.remove(found);group.extend(found)
        groups.append(group)
    return sorted(groups,key=lambda g:(min(r['rectangle'][1] for r in g),min(r['rectangle'][0] for r in g)))


def choice_groups(rows):
    groups=control_groups(rows)
    if len(groups)!=4:raise ValueError(f'Expected four answer areas, found {len(groups)}')
    return groups


def normalize_question(pgc: dict, rows: list[dict], decoded: dict, origin=None, prompt_cell=1, reveal_cell=2) -> dict:
    require_known_commands(pgc,decoded)
    cell = next(c for c in pgc['cells'] if c['cell']==prompt_cell)
    rows = [r for r in rows if r['group'] == 1 and cell['firstSector'] <= r['sector'] <= cell['lastSector']]
    if not rows:
        raise ValueError(f'No question controls in PGC {pgc["pgc"]}')
    groups=choice_groups(rows)
    choices, correct = [], []
    sequence = []
    for code in pgc.get('commands', {}).get('pre', []):
        match = re.fullmatch(r'if \(g\[15\] == 0x([1-4])\) g\[14\] \+= 0x1', decoded.get(code, ''))
        if match:
            sequence.append('ABCD'[int(match[1])-1])
    if sequence and len(sequence) != 4:
        raise ValueError('Unsupported source ordering question')
    if origin is None:
        origin = min(r['vobuStart'] for r in rows)
    windows = []
    for index, group in enumerate(groups):
        top=min(r['rectangle'][1] for r in group)
        rect = {'x': min(r['rectangle'][0] for r in group), 'y': top,
                'width': max(r['rectangle'][2] for r in group) - min(r['rectangle'][0] for r in group) + 1,
                'height': max(r['rectangle'][3] for r in group) - top + 1}
        id = 'ABCD'[index]
        answers = ({False} if sequence else {command_value(decoded[r['command']])[1] <= 4 for r in group})
        if len(answers) != 1:
            raise ValueError(f'Inconsistent answer association in PGC {pgc["pgc"]}')
        if answers == {True}:
            correct.append(id)
        choices.append({'id': id, 'label': id, 'rect': rect, 'highlightSrc': ''})
        for window_index, (row, start, end) in enumerate(activation_rows(group, origin)):
            # DVD mouse activation chooses the first matching area. Web pointer
            # and visible keyboard choices share that native semantic mapping.
            if sequence:
                if decoded[row['command']] != f'LinkPGCN {pgc["pgc"]}':
                    raise ValueError('Unsupported ordering control')
                mask = 0  # Ordering selections retain the selected source slot.
            else:
                mask, _ = command_value(decoded[row['command']])
            windows.append({'startTicks': start,
                            'endTicks': end, 'choiceId': id, 'feedbackVariant': f'{id}-{window_index}',
                            'nextCandidateMask': mask})
    if not sequence and len(correct) != 1:
        raise ValueError(f'Ambiguous correct choice in PGC {pgc["pgc"]}')
    return {'id': f'gk-l1-{pgc["pgc"]:03d}', 'text': '', 'choices': choices,
            'kind': 'sequence' if sequence else 'single', 'correctSequence': sequence,
            'correctChoice': correct[0] if correct else None, 'durationSeconds': cell['duration'],
            'revealSeconds': next(c['duration'] for c in pgc['cells'] if c['cell']==reveal_cell), 'windows': sorted(windows, key=lambda w: (w['startTicks'], w['choiceId']))}


def read_cell(source: Path, pgc: dict, cell: dict) -> bytes:
    vts = pgc['vts']
    name = 'VIDEO_TS.VOB' if vts == 0 else f'VTS_{vts:02d}_{1 if pgc["domain"]=="title" else 0}.VOB'
    size = (cell['lastSector'] - cell['firstSector'] + 1) * 2048
    if size <= 0:
        raise ValueError('Invalid source cell range')
    with (source / 'VIDEO_TS' / name).open('rb') as f:
        f.seek(cell['firstSector'] * 2048)
        data = f.read(size)
    if len(data) != size:
        raise ValueError(f'Truncated source cell: {name}:{cell["firstSector"]}')
    return data


def select_audio(pgc: dict, logical: int, streams: list[dict]) -> str | None:
    controls = pgc['audioControl']
    if not any(controls):
        return None
    if pgc['domain'] != 'title':
        logical = 0
    if not 0 <= logical < len(controls) or not controls[logical] & 0x8000:
        raise ValueError(f'Unavailable logical audio {logical}')
    physical = (controls[logical] >> 8) & 7
    found = [s['id'] for s in streams if s['codec_type'] == 'audio' and (int(s['id'], 0) & 7) == physical]
    if len(found) != 1:
        raise ValueError(f'Missing or ambiguous physical audio {physical}')
    return found[0]


class Oracle:
    def __init__(self, source: Path):
        binary = Path(__file__).resolve().parents[1] / 'dvd/build/round_oracle'
        self.diagnostics = tempfile.TemporaryFile(mode='w+t')
        self.process = subprocess.Popen([str(binary), str(source / 'VIDEO_TS')], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=self.diagnostics, text=True)

    def call(self, command: str) -> dict:
        self.process.stdin.write(command + '\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        self.diagnostics.seek(0)
        diagnostics=self.diagnostics.read()
        if re.search(r'unknown|unsupported|unimplemented',diagnostics,re.I):
            raise RuntimeError(f'Unsupported source instruction after {command}: {diagnostics.strip()}')
        if not line:
            raise RuntimeError(f'Source oracle stopped after {command}')
        return json.loads(line)

    def start(self, pgc, mask=1, variant=2, score=0, remaining=2, seed=42):
        return self.call(f'start 3 {pgc} {mask} {variant} {score} {remaining} {seed}')

    def close(self):
        try:self.process.communicate('quit\n', timeout=5)
        finally:self.diagnostics.close()


def source_ref(row):
    return {'vts': row['vts'], 'domain': 'title' if row['domain'] == 2 else 'vts-menu',
            'pgc': row['pgc'], 'cell': row['cell'], 'audio': row['audio']}


def build_model(source: Path, analysis: Path) -> dict:
    ifo = json.loads((analysis / 'ifo.json').read_text())
    validate_inventory(ifo)
    pgcs = {(p['vts'], p['domain'], p['pgc']): p for p in ifo['pgcs']}
    question_ids = {p['pgc'] for p in ifo['pgcs'] if p['vts'] == 3 and p['domain'] == 'vts-menu'
                    and p['commands']['pre'] and p['commands']['pre'][0] == '6100000f00030000'}
    oracle = Oracle(source)
    def path(row, stop, loop_ok=False):
        scenes, seen = [], set()
        for _ in range(100):
            if stop(row):
                return scenes, row, False
            ref = source_ref(row)
            key = tuple(ref.values())
            if key in seen:
                if loop_ok:
                    return scenes, row, True
                raise ValueError(f'Unexpected source loop: {ref}')
            seen.add(key)
            p = pgcs[(ref['vts'], ref['domain'], ref['pgc'])]
            if not any(c['cell'] == ref['cell'] for c in p['cells']):
                raise ValueError(f'No source cell: {ref}')
            scenes.append(ref)
            row = oracle.call('cell')
        raise ValueError('Source path exceeded bound')
    routes, route_cases, intros, endings = {}, {}, {}, {}
    try:
        for variant in [2, 3, 4]:
            for bit in range(16):
                mask = 1 << bit
                options = {}
                # Enumerate both outcomes of the variant-4 fallback draw.
                for seed in [1, 42, 1234, 50000, 200000, 1000000]:
                    row = oracle.start(90 + variant, mask, variant, remaining=6, seed=seed)
                    scenes, row, _ = path(row, lambda r: r['pgc'] in question_ids and r['cell'] == 1)
                    effective = row['variant']
                    option = {'questionId': f'gk-l1-{row["pgc"]:03d}', 'questionPgc': row['pgc'],
                              'introRefs': scenes, 'variant': effective, 'mask': mask}
                    options[effective] = option
                    route_cases[(effective, mask)] = option
                    if variant != 4 or mask < 64 or len(options) == 2:
                        break
                if variant == 4 and mask >= 64 and len(options) != 2:
                    raise ValueError(f'Could not establish both fallback outcomes: {mask}')
                routes[f'{variant}:{mask}'] = [options[k] for k in sorted(options)]
        print('Selection routes normalized', len(route_cases), flush=True)
        feedback = {}
        for (variant, selected_mask), option in route_cases.items():
            for outcome in ['correct', 'wrong']:
                for bit in range(16):
                    candidate = 1 << bit
                    row = oracle.start(option['questionPgc'], selected_mask, variant)
                    # The source's post-command evaluates LinkTailPGC's button
                    # value, not the on-screen row or original button number.
                    target = 1 if outcome == 'correct' else 5
                    if option['questionPgc'] == 43:
                        for button in ([2,4,1,3] if outcome == 'correct' else [1,1,1,1]):
                            oracle.call(f'select {button}')
                            row = oracle.call('answer 200400000000002b')
                    else:
                        code = f'7101000a{candidate:04x}{target << 2:02x}0d'
                        row = oracle.call('answer ' + code)
                    scenes, row, _ = path(row, lambda r: r['remaining'] != 2)
                    if row['score'] != (1 if outcome == 'correct' else 0):
                        raise ValueError(f'Oracle outcome mismatch: {variant=}, {selected_mask=}, {option=}, {outcome=}, {candidate=}, {scenes=}, {row=}')
                    feedback[f'{variant}:{selected_mask}:{outcome}:{candidate}'] = scenes
        print('Answer paths normalized', len(feedback), flush=True)
        for bit in range(16):
            mask = 1 << bit
            row = oracle.start(204, mask, remaining=7)
            scenes, _, _ = path(row, lambda r: r['remaining'] != 7)
            intros[str(mask)] = scenes
            for score in range(7):
                row = oracle.start(190, mask, score=score, remaining=0)
                scenes, end, looped = path(row, lambda r: r['vts'] != 3, loop_ok=True)
                endings[f'{score}:{mask}'] = {'refs': scenes, 'loop': looped,
                                              'loopRef': source_ref(end) if looped else None}
        return {'sourceFingerprint': ifo['sourceFingerprint'], 'routes': routes,
                'feedback': feedback, 'intros': intros, 'endings': endings,
                'questionPgcs': sorted({o['questionPgc'] for o in route_cases.values()})}
    finally:
        oracle.close()


def nav_origin(data: bytes) -> int:
    index = data[:2048].find(b'\0\0\1\xbf\x03\xd4\0')
    if index < 0:
        raise ValueError('Cell does not begin with a NAV packet')
    return int.from_bytes(data[index + 19:index + 23], 'big')


def has_audio_packets(data: bytes) -> bool:
    for start in range(0,len(data),2048):
        block=data[start:start+2048]
        if len(block)!=2048 or block[:4]!=b'\0\0\1\xba':continue
        offset=14+(block[13]&7)
        while offset+6<=2048 and block[offset:offset+3]==b'\0\0\1':
            length=int.from_bytes(block[offset+4:offset+6],'big');end=offset+6+length
            if not length or end>2048:break
            stream=block[offset+3]
            if 0xc0<=stream<=0xdf:return True
            if stream==0xbd and offset+9<end:
                payload=offset+9+block[offset+8]
                if payload<end and 0x80<=block[payload]<=0xaf:return True
            offset=end
    return False


class Assets:
    def __init__(self, source, analysis, output, pgcs):
        self.source, self.analysis, self.output, self.pgcs = source, analysis, output, pgcs
        self.media = output / 'media'
        self.cache = analysis / 'native-cache'
        self.media.mkdir(parents=True, exist_ok=True)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.jobs, self.scenes, self.provenance = {}, {}, {}
        configuration = output.parent / 'encoding.json'
        self.encoding = json.loads(configuration.read_text()) if configuration.exists() else {
            'crf':18,'preset':'fast','audio_bitrate':'160k','threads':2,'workers':3}
        self.workers = self.encoding.get('workers',3)

    def parts(self, ref):
        p = self.pgcs[(ref['vts'], ref['domain'], ref['pgc'])]
        c = next(c for c in p['cells'] if c['cell'] == ref['cell'])
        return p, c

    def register(self, ref, kind='clip'):
        p, c = self.parts(ref)
        logical = ref.get('audio', 0) if ref['domain'] == 'title' else 0
        physical = (p['audioControl'][logical] >> 8) & 7 if any(p['audioControl']) else -1
        id = f's{ref["vts"]:02}{"t" if ref["domain"]=="title" else "m"}-{c["firstSector"]}-{c["lastSector"]}-a{physical}'
        if id not in self.jobs:
            self.jobs[id] = {**ref, 'audio': logical}
            self.scenes[id] = {'id': id, 'src': f'/media/{id}.mp4', 'durationSeconds': c['duration'],
                               'kind': kind, 'audioVariant': logical if physical >= 0 else None}
            self.provenance[id] = {**ref, **c, 'physicalAudio': physical}
        return id

    def raw(self, ref):
        p, c = self.parts(ref)
        data = read_cell(self.source, p, c)
        key = hashlib.sha256(data).hexdigest()[:20]
        path = self.cache / f'{key}.vob'
        if not path.exists() or path.read_bytes()!=data:
            with tempfile.NamedTemporaryFile(dir=self.cache,suffix='.vob',delete=False) as stream:
                stream.write(data)
                temporary=Path(stream.name)
            temporary.replace(path)
        return path, data

    def encode(self, item):
        id, ref = item
        p, c = self.parts(ref)
        target = self.media / f'{id}.mp4'
        raw, data = self.raw(ref)
        probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(raw)]))
        if not any(s['codec_type']=='video' for s in probe['streams']):
            raise ValueError(f'No video in {ref}')
        audio = select_audio(p, ref['audio'], probe['streams']) if has_audio_packets(data) else None
        if not audio:self.scenes[id]['audioVariant']=None
        recipe={'version':1,'video':'libx264','preset':self.encoding['preset'],'crf':self.encoding['crf'],'size':[768,576],
                'fps':25,'pixelFormat':'yuv420p','audio':'aac'+self.encoding['audio_bitrate']+'-apad' if audio else None,
                'duration':c['duration'],'holdLastFrame':True,'faststart':True,
                'ffmpeg':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0]}
        if self.encoding['threads']!=2:recipe['threads']=self.encoding['threads']
        identity=cache_identity(hashlib.sha256(data).hexdigest(),audio,recipe)
        if cache_valid(target,identity):
            return
        temporary=target.with_suffix('.tmp.mp4')
        command = ['ffmpeg','-v','error','-i',str(raw),'-map','0:v:0']
        if audio:
            command += ['-map',f'0:i:{audio}','-c:a','aac','-b:a',self.encoding['audio_bitrate'],'-af','apad']
        else:
            command += ['-an']
        command += ['-vf',f'scale=768:576,setsar=1,tpad=stop_mode=clone:stop_duration={c["duration"]}',
                    '-r','25','-t',str(c['duration']),'-c:v','libx264','-preset',self.encoding['preset'],'-crf',str(self.encoding['crf']),
                    '-pix_fmt','yuv420p','-threads',str(self.encoding['threads']),'-movflags','+faststart','-y',str(temporary)]
        run = subprocess.run(command, capture_output=True, text=True)
        if run.returncode:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f'{id}: {run.stderr}')
        try:
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(temporary)]))
            video=next(stream for stream in info['streams'] if stream['codec_type']=='video')
            has_audio=any(stream['codec_type']=='audio' for stream in info['streams'])
            if (video['width'],video['height'])!=(768,576) or abs(float(info['format']['duration'])-c['duration'])>.12 or has_audio!=bool(audio):
                raise ValueError('Prepared stream/duration mismatch: '+id)
            temporary.replace(target)
            record_cache(target,identity)
        finally:
            temporary.unlink(missing_ok=True)

    def highlight(self, ref, button, id):
        target = self.media / f'{id}.png'
        p, _ = self.parts(ref)
        _, data = self.raw(ref)
        identity=cache_identity(hashlib.sha256(data).hexdigest(),None,{
            'version':1,'format':'SPU-RGBA720x576','palette':p['palette'],
            'rectangle':button['rectangle'],'colourIndex':button['colourIndex'],
            'colourTable':button['colourTable'],'decoderSha256':hashlib.sha256(Path(spu.__file__).read_bytes()).hexdigest()})
        if cache_valid(target,identity):return f'/media/{id}.png'
        packets = spu.extract_packets(data)
        if not packets:
            raise ValueError(f'Missing original highlight bitmap: {ref}')
        bitmap = spu.decode_packet(packets[0]['data'])
        table = button['colourTable'][button['colourIndex']-1][0]
        rgba = spu.render_rgba(bitmap['pixels'], p['palette'], table)
        out = bytearray(720*576*4)
        area = button['rectangle']
        rect = bitmap['rect']
        for y in range(max(area[1],rect['y']), min(area[3]+1,rect['y']+rect['height'])):
            left, right = max(area[0],rect['x']), min(area[2]+1,rect['x']+rect['width'])
            begin = ((y-rect['y'])*rect['width'] + left-rect['x'])*4
            out[(y*720+left)*4:(y*720+right)*4] = rgba[begin:begin+(right-left)*4]
        temporary=target.with_suffix('.tmp.png')
        spu.write_png(temporary,720,576,out)
        temporary.replace(target)
        record_cache(target,identity)
        return f'/media/{id}.png'

    def question_text(self, ref, id):
        raw, _ = self.raw(ref)
        image = self.cache / f'{id}.png'
        if not image.exists():
            subprocess.run(['ffmpeg','-v','error','-i',str(raw),'-frames:v','1',
                            '-vf','scale=768:576','-y',str(image)], check=True)
        textfile = self.cache / f'{id}.txt'
        if not textfile.exists():
            textfile.write_text(subprocess.check_output(['tesseract',str(image),'stdout','--psm','6'], stderr=subprocess.DEVNULL,text=True))
        lines = textfile.read_text().splitlines()
        choices, body, current = {}, [], None
        for line in lines:
            line = line.strip()
            match = re.match(r'^[Oo0()\s]*([ABCD])[.\s:]\s*(.+)', line)
            if match:
                current = match[1]
                choices[current] = match[2]
            elif line and current is None and 'General Knowledge' not in line:
                body.append(line)
            elif line and current is not None:
                choices[current] += ' ' + line
        return ' '.join(body), choices


def export_round(source: Path, analysis: Path, output: Path) -> dict:
    ifo = json.loads((analysis / 'ifo.json').read_text())
    validate_inventory(ifo)
    model_path = analysis / 'native-model.json'
    model = json.loads(model_path.read_text()) if model_path.exists() else build_model(source, analysis)
    ifo = json.loads((analysis / 'ifo.json').read_text())
    if model['sourceFingerprint'] != ifo['sourceFingerprint']:
        raise ValueError('Model and inventory fingerprints differ')
    pgcs = {(p['vts'],p['domain'],p['pgc']):p for p in ifo['pgcs']}
    assets = Assets(source,analysis,output,pgcs)
    labels=json.loads((Path(__file__).parent/'labels.json').read_text())
    if labels['sourceFingerprint']!=ifo['sourceFingerprint']:
        raise ValueError('Verified accessibility labels belong to a different source')
    button_rows = defaultdict(list)
    for line in (analysis/'buttons.jsonl').open():
        row = json.loads(line)
        name = Path(row['vob']).name
        if name in ('VTS_02_0.VOB','VTS_03_0.VOB'):
            validate_button_fingerprint(row,ifo['sourceFingerprint'])
            button_rows[int(name[4:6])].append(row)
    def controls(ref):
        _, c = assets.parts(ref)
        return [r for r in button_rows[ref['vts']] if r['group']==1 and c['firstSector']<=r['sector']<=c['lastSector']]
    def scene_list(refs):
        return [assets.register(ref) for ref in refs]
    questions = []
    for n in model['questionPgcs']:
        p = pgcs[(3,'vts-menu',n)]
        ref = {'vts':3,'domain':'vts-menu','pgc':n,'cell':1,'audio':0}
        rows = controls(ref)
        _, raw = assets.raw(ref)
        question = normalize_question(p,rows,ifo['decodedCommands'],nav_origin(raw))
        question['promptScene'] = assets.register(ref,'question-loop')
        question['revealScene'] = assets.register({**ref,'cell':2})
        if str(n) not in labels['questions'] or len(labels['questions'][str(n)][1])!=4:
            raise ValueError('Verified accessibility labels are missing')
        question['text'], choice_labels = labels['questions'][str(n)]
        for choice in question['choices']:
            choice['label'] = choice_labels['ABCD'.index(choice['id'])]
            row = next(r for r in rows if r['rectangle'][1]==choice['rect']['y'])
            choice['highlightSrc'] = assets.highlight(ref,row,question['id']+'-'+choice['id'])
        questions.append(question)
    selection = {key:[{'questionId':o['questionId'],'introScenes':scene_list(o['introRefs']),
                       'variant':o['variant']} for o in options] for key,options in model['routes'].items()}
    answers = {key:scene_list(refs) for key,refs in model['feedback'].items()}
    endings = {}
    for key, entry in model['endings'].items():
        ids = scene_list(entry['refs'])
        value = {'scenes':ids,'loopScene':assets.register(entry['loopRef'],'still') if entry['loop'] else None}
        if entry['loop']:
            ref = entry['loopRef'];rows=controls(ref)
            if not rows:
                raise ValueError('End loop has no continue control')
            row=rows[0];a=row['rectangle']
            value['continue']={'label':'Continue','rect':{'x':a[0],'y':a[1],'width':a[2]-a[0]+1,'height':a[3]-a[1]+1},
                               'highlightSrc':assets.highlight(ref,row,'round-continue')}
        endings[key]=value
    menus=[]
    for n,name,label,which in [(1,'main','One player','top'),(6,'player-type','General Knowledge','bottom'),(8,'holly','Norman Lovett’s Holly','left')]:
        ref={'vts':2,'domain':'vts-menu','pgc':n,'cell':1,'audio':0}
        rows=controls(ref)
        target = (min(r['rectangle'][0] for r in rows) if which=='left' else
                  (max if which=='bottom' else min)(r['rectangle'][1] for r in rows))
        group=[r for r in rows if r['rectangle'][0 if which=='left' else 1]==target]
        row=min(group,key=lambda r:r['button']);a=row['rectangle']
        _,raw=assets.raw(ref);origin=nav_origin(raw)
        windows=[]
        for r,start,end in activation_rows(group,origin):
            text=ifo['decodedCommands'][r['command']]
            match=re.search(r'g\[10\] = 0x([0-9a-f]+)',text)
            if not match:raise ValueError('Menu candidate is not understood: '+text)
            windows.append({'startTicks':start,'endTicks':end,
                            'candidateMask':int(match[1],16)})
        menus.append({'id':name,'scene':assets.register(ref,'question-loop'),'label':label,
                      'rect':{'x':a[0],'y':a[1],'width':a[2]-a[0]+1,'height':a[3]-a[1]+1},
                      'highlightSrc':assets.highlight(ref,row,'menu-'+name),'windows':windows})
    boot=scene_list([{'vts':0,'domain':'vmg-menu','pgc':3,'cell':c,'audio':0} for c in [1,2]])
    boot+=scene_list([{'vts':11,'domain':'title','pgc':1,'cell':1,'audio':0}])
    setup=scene_list([{'vts':2,'domain':'vts-menu','pgc':n,'cell':1,'audio':0} for n in [9,15,23]])
    entry={'boot':boot,'menus':menus,'setupScenes':setup,
           'roundIntros':{key:scene_list(refs) for key,refs in model['intros'].items()}}
    print('Prepared-media jobs',len(assets.jobs),'questions',len(questions),flush=True)
    with ThreadPoolExecutor(max_workers=assets.workers) as pool:
        list(pool.map(assets.encode,assets.jobs.items()))
    # Probe every prepared file, including cached outputs.
    for scene in assets.scenes.values():
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output/scene['src'].lstrip('/'))]))
        video=next(s for s in info['streams'] if s['codec_type']=='video')
        if (video['width'],video['height'])!=(768,576) or abs(float(info['format']['duration'])-scene['durationSeconds'])>.12:
            raise ValueError('Prepared asset dimensions/duration mismatch: '+scene['id'])
        if scene['audioVariant'] is not None and not any(s['codec_type']=='audio' for s in info['streams']):
            raise ValueError('Prepared audio missing: '+scene['id'])
    poster_scene=assets.scenes[menus[0]['scene']]
    subprocess.run(['ffmpeg','-v','error','-ss','5','-i',str(output/poster_scene['src'].lstrip('/')),
                    '-frames:v','1','-y',str(output/'media/menu-poster.png')],check=True)
    result={'schemaVersion':1,'sourceFingerprint':ifo['sourceFingerprint'],'scenes':list(assets.scenes.values()),
            'questions':questions,'selection':selection,'feedback':{'answers':answers,'endings':endings},'entry':entry}
    (output/'round.json').write_text(json.dumps(result,indent=2)+'\n')
    (analysis/'native-provenance.json').write_text(json.dumps(assets.provenance,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('disc/2EDVD108'))
    parser.add_argument('--analysis', type=Path, default=Path('analysis'))
    parser.add_argument('--model-only', action='store_true')
    parser.add_argument('--output',type=Path,default=Path('app/public'))
    args = parser.parse_args()
    if args.model_only:
        model = build_model(args.source.resolve(), args.analysis.resolve())
        (args.analysis / 'native-model.json').write_text(json.dumps(model, indent=2) + '\n')
        print('Reachable question PGCs:', model['questionPgcs'])
    else:
        result=export_round(args.source.resolve(),args.analysis.resolve(),args.output.resolve())
        print('Exported native round:',len(result['questions']),'questions',len(result['scenes']),'scenes')
