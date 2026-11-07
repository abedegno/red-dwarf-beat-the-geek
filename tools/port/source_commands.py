"""Reject unsupported or inconsistent offline DVD command metadata."""
from pathlib import Path
import re
import subprocess
import tempfile

DISASSEMBLER=Path(__file__).resolve().parents[1]/'dvd/build/trace_game'
UNKNOWN=re.compile(r'warning|unknown|unsupported|unimplemented',re.I)


def require_known_commands(pgc,decoded):
    location=f"VTS {pgc.get('vts')} {pgc.get('domain')} PGC {pgc.get('pgc')}"
    for codes in pgc.get('commands',{}).values():
        for code in codes:
            if (not re.fullmatch(r'[0-9a-f]{16}',code) or int(code[:2],16)>>5==7
                    or code not in decoded or UNKNOWN.search(decoded[code])):
                raise ValueError(f'Unsupported source command {code} in {location}')


def validate_inventory(ifo):
    decoded=ifo['decodedCommands']
    for pgc in ifo['pgcs']:require_known_commands(pgc,decoded)
    codes=sorted(decoded)
    require_known_commands({'commands':{'all':codes}},decoded)
    # Decode bytes independently; a plausible description cannot hide an unknown
    # opcode, sub-instruction, or unexamined bits in supplied metadata.
    with tempfile.TemporaryFile(mode='w+t') as source, tempfile.TemporaryFile(mode='w+t') as errors:
        source.write('\n'.join(codes)+'\n');source.seek(0)
        subprocess.run([str(DISASSEMBLER),'--disassemble'],stdin=source,
                       stdout=subprocess.DEVNULL,stderr=errors,check=True,timeout=30)
        errors.seek(0);diagnostics=errors.read()
    lines=diagnostics.splitlines()
    if UNKNOWN.search(diagnostics) or len(lines)!=len(codes):
        raise ValueError('Unsupported source command in pinned disassembly: '+diagnostics[-500:])
    for code,line in zip(codes,lines):
        if line!=code+'\t'+decoded[code]:
            raise ValueError(f'Unsupported source command description mismatch: {code}')
