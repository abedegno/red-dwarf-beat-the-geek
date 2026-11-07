"""Named one-player Norman Holly source profiles; never shipped as DVD commands."""
from dataclasses import dataclass,replace

@dataclass(frozen=True)
class ModeProfile:
    id:str
    label:str
    source_value:int
    mask_register:int
    prefix:str
    bonus_pgcs:tuple[int,int]
    presenter:str="norman"

    @property
    def bonus_intro_pgc(self):return 283 if self.presenter=="hattie" else 284
    def named(self,name):return name if self.presenter=="norman" else name.replace(".json","-hattie.json")

    @property
    def model_file(self):return self.named('native-game-model.json' if self.id=='general-knowledge' else f'native-{self.id}-model.json')
    @property
    def labels_file(self):return 'game_labels.json' if self.id=='general-knowledge' else f'{self.id}_labels.json'
    @property
    def dataset_file(self):return self.named('game.json' if self.id=='general-knowledge' else f'game-{self.id}.json')
    @property
    def provenance_file(self):return self.named('native-game-provenance.json' if self.id=='general-knowledge' else f'native-{self.id}-provenance.json')

PROFILES={p.id:p for p in [ModeProfile('general-knowledge','General Knowledge',10101,4,'gk',(285,286)),
    ModeProfile('viewer','Viewer',10201,5,'viewer',(287,288)),ModeProfile('geek','Geek',10301,6,'geek',(289,290))]}

def mode_profile(id='general-knowledge',presenter=None):
    if isinstance(id,ModeProfile):return id
    if id not in PROFILES:raise ValueError('Unsupported quiz mode: '+str(id))
    if presenter not in [None,'norman','hattie']:raise ValueError('Unsupported presenter: '+str(presenter))
    p=PROFILES[id]
    return p if presenter!='hattie' else replace(p,source_value=p.source_value+1,bonus_pgcs=tuple(n+6 for n in p.bonus_pgcs),presenter=presenter)
