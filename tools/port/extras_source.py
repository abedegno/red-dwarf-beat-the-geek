"""Pinned offline oracle and controls for Instructions and Games Archive."""
import json,re,subprocess,tempfile
from pathlib import Path
from functools import cached_property
from button_index import ButtonIndex
from source_commands import UNKNOWN, validate_inventory as validate_extras_inventory

class ExtrasSource:
    def __init__(self,source:Path,analysis:Path):
        self.source,self.analysis=source,analysis
        self.ifo=json.loads((analysis/'ifo.json').read_text())
        validate_extras_inventory(self.ifo)
        self.pgcs={(p['vts'],p['domain'],p['pgc']):p for p in self.ifo['pgcs']}
        self.diagnostics=tempfile.TemporaryFile(mode='w+t')
        binary=Path(__file__).resolve().parents[1]/'dvd/build/extras_oracle'
        try:self.process=subprocess.Popen([str(binary),str(source/'VIDEO_TS')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.diagnostics,text=True)
        except BaseException:
            self.diagnostics.close();raise

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):
        try:self.process.communicate('quit\n',timeout=5)
        finally:self.diagnostics.close()

    def call(self,command):
        self.process.stdin.write(command+'\n');self.process.stdin.flush()
        line=self.process.stdout.readline();self.diagnostics.seek(0);diagnostics=self.diagnostics.read()
        if UNKNOWN.search(diagnostics):raise RuntimeError('Unsupported extras source command: '+diagnostics[-500:])
        if not line:raise RuntimeError('Extras oracle stopped after '+command+': '+diagnostics[-500:])
        return json.loads(line)

    def start(self,vts,pgc,registers=None,seed=42):
        values=[10000,10000,0,0,0,0,0,0,0,0,1,0,0,0,0,0] if registers is None else list(registers)
        if len(values)!=16 or any(not isinstance(v,int) or not 0<=v<=65535 for v in values):raise ValueError('Invalid source snapshot')
        return self.call(f'start {vts} {pgc} {seed} '+' '.join(map(str,values)))

    @cached_property
    def buttons(self):
        inventory={**self.ifo,'pgcs':[p for p in self.ifo['pgcs'] if p['vts']==2 or p['vts']>=11]}
        with (self.analysis/'buttons.jsonl').open() as stream:return ButtonIndex(inventory,(json.loads(line) for line in stream))

    def controls(self,row):return self.buttons.controls({'vts':row['vts'],'pgc':row['pgc'],'cell':row['cell']}) if row['domain']==8 else []

    def activate(self,row,button,command=None):
        choices=[r for r in self.controls(row) if r['button']==button]
        if not choices:raise ValueError(f'No source button {button} at {row}')
        if command is None:
            codes={r['command'] for r in choices}
            if len(codes)!=1:raise ValueError('Timed source button requires explicit interval command')
            command=choices[0]['command']
        elif command not in {r['command'] for r in choices}:raise ValueError('Command outside source button')
        self.call(f'select {button}');return self.call('answer '+command)

    def ref(self,row):return {'vts':row['vts'],'domain':{1:'first-play',2:'title',4:'vmg-menu',8:'vts-menu'}[row['domain']],'pgc':row['pgc'],'cell':row['cell'],'audio':row['audio']}

    def cell_command(self,row):
        p=self.pgcs[(row['vts'],'vts-menu',row['pgc'])];cell=next(c for c in p['cells'] if c['cell']==row['cell'])
        return p['commands']['cell'][cell['commandNumber']-1] if cell['commandNumber'] else None
