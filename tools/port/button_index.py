"""Compact repeated NAV controls by physical cell and authored HLI identity."""
from bisect import bisect_right
from collections import defaultdict
import json
from pathlib import Path
from asset_cache import validate_button_fingerprint


class ButtonIndex:
    def __init__(self,ifo,rows):
        self.pgcs={(p['vts'],p['pgc']):p for p in ifo['pgcs'] if p['domain']=='vts-menu'}
        cells=defaultdict(set)
        for p in self.pgcs.values():
            for c in p['cells']:cells[p['vts']].add((c['firstSector'],c['lastSector']))
        ranges={v:sorted(cs) for v,cs in cells.items()}
        starts={v:[c[0] for c in cs] for v,cs in ranges.items()}
        self.rows=defaultdict(list);seen=set()
        for row in rows:
            name=Path(row['vob']).name
            if not name.startswith('VTS_') or not name.endswith('_0.VOB'):continue
            vts=int(name[4:6])
            if vts not in ranges:continue
            validate_button_fingerprint(row,ifo['sourceFingerprint'])
            if row['group']!=1:continue
            position=bisect_right(starts[vts],row['sector'])-1
            if position<0 or ranges[vts][position][1]<row['sector']:continue
            first=ranges[vts][position][0]
            signature=(vts,first,json.dumps({k:row[k] for k in ['button','highlightStart','highlightEnd','selectionEnd','rectangle','command','colourIndex','colourTable']},sort_keys=True))
            if signature in seen:continue
            seen.add(signature);self.rows[(vts,first)].append(row)

    def controls(self,ref):
        p=self.pgcs[(ref['vts'],ref['pgc'])]
        c=next(c for c in p['cells'] if c['cell']==ref['cell'])
        return self.rows[(ref['vts'],c['firstSector'])]
