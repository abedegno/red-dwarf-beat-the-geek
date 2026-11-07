"""Read-only verification of a DVD folder backup; local hashes are a baseline."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def scrambled_sector(sector: bytes) -> bool:
    if len(sector) != 2048 or sector[:4] != b'\x00\x00\x01\xba':
        return False
    offset = 14 + (sector[13] & 7)
    while offset + 6 <= len(sector):
        if sector[offset:offset + 3] != b'\x00\x00\x01':
            break
        stream = sector[offset + 3]
        # Only MPEG-2 PES packets carrying audio, video or private stream 1.
        if stream == 0xbd or 0xc0 <= stream <= 0xef:
            if offset + 6 < len(sector) and sector[offset + 6] & 0x30:
                return True
        length = int.from_bytes(sector[offset + 4:offset + 6], 'big')
        if not length:
            break
        offset += 6 + length
    return False


def verify_backup(source_inventory: Path, backup: Path, source: Path | None) -> dict:
    inventory = json.loads(source_inventory.read_text())
    expected = {item['path']: item['bytes'] for item in inventory['files']}
    errors, files, metadata = [], [], []
    for rel, size in sorted(expected.items()):
        path = backup / rel
        if not path.is_file():
            errors.append({'code': 'missing', 'path': rel})
            continue
        actual = path.stat().st_size
        if actual != size:
            errors.append({'code': 'size', 'path': rel, 'expected': size, 'actual': actual})
        digest, scrambled, zero_ranges, sector_number = hashlib.sha256(), 0, [], 0
        with path.open('rb') as stream:
            while chunk := stream.read(8 * 1024 * 1024):
                digest.update(chunk)
                if path.suffix.upper() == '.VOB':
                    for i in range(0, len(chunk), 2048):
                        sector = chunk[i:i + 2048]
                        scrambled += scrambled_sector(sector)
                        if sector == bytes(2048):
                            if zero_ranges and zero_ranges[-1][1] + 1 == sector_number:
                                zero_ranges[-1][1] = sector_number
                            else:
                                zero_ranges.append([sector_number, sector_number])
                        sector_number += 1
        entry = {'path': rel, 'bytes': actual, 'sha256': digest.hexdigest()}
        if path.suffix.upper() == '.VOB':
            entry['scrambledSectors'] = scrambled
            entry['zeroRanges'] = zero_ranges
        files.append(entry)
        if scrambled:
            errors.append({'code': 'scrambled', 'path': rel, 'sectors': scrambled})
        if zero_ranges:
            errors.append({'code': 'zero-sectors', 'path': rel, 'ranges': zero_ranges})
        if path.suffix.upper() in ('.IFO', '.BUP'):
            comparison = {'path': rel, 'matches': None}
            if source is not None:
                comparison['matches'] = path.read_bytes() == (source / rel).read_bytes()
                if not comparison['matches']:
                    errors.append({'code': 'metadata-mismatch', 'path': rel})
            metadata.append(comparison)
    for path in sorted(backup.rglob('*')):
        if path.is_file() and str(path.relative_to(backup)) not in expected:
            errors.append({'code': 'unexpected', 'path': str(path.relative_to(backup))})
    fingerprint = hashlib.sha256('\n'.join(
        f'{e["path"]}:{e["sha256"]}' for e in files
        if e['path'].upper().endswith('.IFO')).encode()).hexdigest()
    return {'schemaVersion': 1, 'sourceFingerprint': fingerprint,
            'status': 'incomplete' if errors else 'needs-review',
            'expectedFiles': len(expected), 'expectedBytes': sum(expected.values()),
            'actualBytes': sum(e['bytes'] for e in files), 'files': files,
            'metadataComparisons': metadata, 'errors': errors,
            'note': 'Local SHA-256 hashes are a baseline, not proof of correct decryption. '
                    'Completion additionally requires rip and representative decode evidence.'}


def apply_evidence(report: dict, evidence: dict, source_available: bool) -> dict:
    """Attach manual research evidence without erasing the original findings."""
    report = copy.deepcopy(report)
    report['evidence'] = copy.deepcopy(evidence)
    files = {f['path']: f for f in report['files']}
    reviewed, unresolved = [], []
    for error in report['errors']:
        f = files.get(error['path'], {})
        resolution = next((e for e in evidence.get('exceptions', [])
                           if error['code'] == e.get('code') == 'scrambled'
                           and error['path'] == e.get('path')
                           and f.get('sha256') == e.get('sha256')
                           and 0 < f.get('bytes', 0) <= 10240
                           and e.get('classification') == 'encrypted-placeholder-retained'
                           and e.get('reason')), None)
        if resolution:
            reviewed.append({'finding': error, 'resolution': resolution})
        else:
            unresolved.append(error)
    report['reviewedExceptions'], report['unresolvedErrors'] = reviewed, unresolved
    checks = evidence.get('mediaChecks', [])
    metadata = report.get('metadataComparisons', [])
    if unresolved:
        report['status'] = 'incomplete'
    elif (source_available and metadata and all(m['matches'] is True for m in metadata)
          and evidence.get('ripExitStatus') == 0 and evidence.get('logReview') == 'resolved'
          and checks and all(c.get('exitStatus') == 0 for c in checks)):
        report['status'] = 'complete'
    else:
        report['status'] = 'needs-review'
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    parser.add_argument('--source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--evidence', type=Path,
                        help='JSON recording ripExitStatus, logReview and mediaChecks')
    args = parser.parse_args()
    report = verify_backup(args.inventory, args.backup, args.source)
    if args.evidence:
        evidence = json.loads(args.evidence.read_text())
        report = apply_evidence(report, evidence, args.source is not None)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{report["status"]}: {len(report["files"])}/{report["expectedFiles"]} files, '
          f'{len(report["errors"])} findings, '
          f'{len(report.get("reviewedExceptions", []))} reviewed exceptions; {args.output}')
    return 0 if report['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
