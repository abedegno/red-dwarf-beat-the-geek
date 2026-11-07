"""Read-only DVD research report; observed paths are not exhaustive game rules."""
import argparse
from collections import Counter, defaultdict
import html
import json
from pathlib import Path
import re


def location(row):
    return {key: row.get(key) for key in ('vts', 'domain', 'pgc', 'language')}


def identity(row):
    return tuple(row.get(key) for key in ('vts', 'domain', 'pgc', 'language'))


def build_report(ifo: dict, buttons: list[dict], traces: list[dict]) -> dict:
    pgcs = ifo.get('pgcs', [])
    decoded = ifo.get('decodedCommands', {})
    command_edges, observed = [], []
    for p in pgcs:
        for kind, commands in p['commands'].items():
            for index, command in enumerate(commands, 1):
                text = decoded.get(command, '')
                edge = {'from': location(p), 'table': kind, 'line': index,
                        'command': command, 'description': text,
                        'condition': text[:text.find('LinkPGCN')].strip() if 'LinkPGCN' in text else text,
                        'to': None, 'status': 'unresolved'}
                match = re.search(r'\bLinkPGCN (\d+)\b', text)
                if match:
                    target = {**location(p), 'pgc': int(match[1])}
                    edge.update(to=target, status='conditional' if text.startswith('if ') else 'static')
                    if not any(identity(t) == identity(target) for t in pgcs):
                        edge['status'] = 'unresolved'
                elif text == 'Nop' or (text.startswith('g[') and not any(
                        word in text for word in ('Link', 'Jump', 'Call', 'Goto'))):
                    edge['status'] = 'non-navigation'
                command_edges.append(edge)
    known_locations = {identity(p) for p in pgcs}
    unresolved_locations = {}
    previous = None
    for index, row in enumerate(traces):
        if row.get('event') == 'header':
            previous = None
            continue
        if 'pgc' not in row:
            continue
        if identity(row) not in known_locations:
            unresolved_locations[identity(row)] = location(row)
        if previous is not None and identity(previous) != identity(row):
            observed.append({'from': location(previous), 'to': location(row),
                             'stateBefore': previous.get('registers', {}),
                             'stateAfter': row.get('registers', {}),
                             'traceIndex': index, 'input': row.get('input'),
                             'fromResolved': identity(previous) in known_locations,
                             'toResolved': identity(row) in known_locations,
                             'status': 'observed; condition not inferred'})
        previous = row
    ranges = defaultdict(list)
    for p in pgcs:
        for cell in p.get('cells', []):
            key = (p['vts'], p['domain'])
            ranges[key].append((cell['firstSector'], cell['lastSector'],
                                {**location(p), 'cell': cell['cell']}))
    summaries, unmatched, matches = {}, 0, {}
    for b in buttons:
        name = Path(b['vob']).name
        match = re.fullmatch(r'VTS_(\d+)_0\.VOB', name, flags=re.I)
        key = (int(match[1]), 'vts-menu') if match else (0, 'vmg-menu')
        cache_key = (*key, b['sector'])
        if cache_key not in matches:
            matches[cache_key] = [ref for lo, hi, ref in ranges[key] if lo <= b['sector'] <= hi]
        refs = matches[cache_key]
        if not refs:
            unmatched += 1
        for ref in refs:
            k = identity(ref)
            summary = summaries.setdefault(k, {'source': ref, 'records': 0, 'buttons': set(),
                                               'rectangles': set(), 'commands': set()})
            summary['records'] += 1
            summary['buttons'].add(b['button'])
            summary['rectangles'].add(tuple(b['rectangle']))
            summary['commands'].add(b['command'])
    summaries = [{**s, 'buttons': sorted(s['buttons']), 'rectangles': sorted(s['rectangles']),
                  'commands': sorted(s['commands'])} for s in summaries.values()]
    fingerprints = {r['sourceFingerprint'] for r in [ifo, *traces]
                    if r.get('sourceFingerprint')}
    fingerprints.update(b['sourceFingerprint'] for b in buttons if b.get('sourceFingerprint'))
    if len(fingerprints) > 1:
        raise ValueError('Cannot combine exports from different source fingerprints')
    return {'schemaVersion': 1, 'sourceFingerprint': ifo.get('sourceFingerprint'),
            'label': ifo.get('label', 'DVD structure and observed navigation'),
            'coverageNote': 'Static command targets and observed paths; not a complete game state machine.',
            'pgcs': pgcs, 'commandEdges': command_edges, 'observedEdges': observed,
            'unresolvedObservedLocations': list(unresolved_locations.values()),
            'buttonSummary': summaries, 'unmatchedButtonRecords': unmatched,
            'counts': {'pgcs': len(pgcs), 'cells': sum(len(p.get('cells', [])) for p in pgcs),
                       'commands': len(command_edges), 'buttonRecords': len(buttons),
                       'traceEvents': len(traces)},
            'commandStatus': dict(Counter(e['status'] for e in command_edges))}


def render_html(report: dict, output: Path) -> None:
    esc = lambda v: html.escape(str(v), quote=True)
    blocks = ['<!doctype html><html lang="en"><meta charset="utf-8">',
              '<title>DVD research</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px}',
              'table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:8px;text-align:left}',
              'pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:12px 0}a{color:#165faa}</style>',
              '<h1>' + esc(report['label']) + '</h1>', '<p>' + esc(report['coverageNote']) + '</p>',
              '<pre>' + esc(json.dumps(report['counts'], indent=2)) + '</pre>',
              '<p>Unmatched button records: ' + esc(report['unmatchedButtonRecords']) + '</p>',
              '<p>Unresolved observed locations: ' + esc(len(report['unresolvedObservedLocations'])) + '</p>',
              '<p><a href="graph.json">Machine-readable structure and observations</a></p>']
    by_pgc = defaultdict(list)
    for edge in report['commandEdges']:
        by_pgc[identity(edge['from'])].append(edge)
    for p in report['pgcs']:
        label = f"VTS {p['vts']} / {p['domain']} / PGC {p['pgc']} / language {p.get('language')}"
        blocks.append('<details><summary>' + esc(label) + '</summary><pre>' +
                      esc(json.dumps(p.get('cells', []), indent=2)) + '</pre><table>')
        blocks.append('<tr><th>Table:line</th><th>Command</th><th>Decoded instruction</th><th>Status</th></tr>')
        for e in by_pgc[identity(p)]:
            blocks.append('<tr>' + ''.join('<td>' + esc(v) + '</td>' for v in (
                f"{e['table']}:{e['line']}", e['command'], e['description'], e['status'])) + '</tr>')
        blocks.append('</table></details>')
    blocks.append('<h2>Observed scene changes</h2><pre>' +
                  esc(json.dumps(report['observedEdges'], indent=2)) + '</pre></html>')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('\n'.join(blocks) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ifo', type=Path, required=True)
    parser.add_argument('--disassembly', type=Path,
                        help='stderr output from trace_game --disassemble')
    parser.add_argument('--buttons', type=Path)
    parser.add_argument('--trace', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, default=Path('analysis'))
    args = parser.parse_args()
    ifo = json.loads(args.ifo.read_text())
    if args.disassembly:
        decoded = dict(ifo.get('decodedCommands', {}))
        for number, line in enumerate(args.disassembly.read_text().splitlines(), 1):
            if not line.strip():
                continue
            match = re.fullmatch(r'([0-9a-f]{16})\t(.*)', line)
            if not match:
                raise ValueError(f'Invalid disassembly record at line {number}')
            decoded[match[1]] = match[2]
        ifo['decodedCommands'] = decoded
    buttons = [json.loads(l) for l in args.buttons.open()] if args.buttons else []
    traces = [json.loads(l) for path in args.trace for l in path.open()]
    report = build_report(ifo, buttons, traces)
    render_html(report, args.output / 'index.html')
    (args.output / 'graph.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['counts']))


if __name__ == '__main__':
    main()
