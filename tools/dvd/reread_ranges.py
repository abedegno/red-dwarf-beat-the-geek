"""Read suspect decrypted DVD sectors individually into separate recovery files."""
import argparse
import ctypes as c
import ctypes.util
import hashlib
import json
from pathlib import Path


def reread_file(vob: Path, start: int, count: int) -> bytes:
    """Use mounted filesystem addressing and libdvdcss instead of UDF mapping."""
    if start < 0 or count < 1 or (start + count) * 2048 > vob.stat().st_size:
        raise ValueError('Requested range exceeds VOB size')
    library = ctypes.util.find_library('dvdcss')
    if not library:
        raise RuntimeError('libdvdcss is required')
    lib = c.CDLL(library)
    lib.dvdcss_open.argtypes, lib.dvdcss_open.restype = [c.c_char_p], c.c_void_p
    lib.dvdcss_close.argtypes = [c.c_void_p]
    lib.dvdcss_seek.argtypes, lib.dvdcss_seek.restype = [c.c_void_p, c.c_int, c.c_int], c.c_int
    lib.dvdcss_read.argtypes = [c.c_void_p, c.c_void_p, c.c_int, c.c_int]
    lib.dvdcss_read.restype = c.c_int
    handle = lib.dvdcss_open(str(vob).encode())
    if not handle:
        raise RuntimeError('Cannot open VOB through filesystem')
    try:
        # Obtain the title key at the beginning of this file before seeking.
        if lib.dvdcss_seek(handle, 0, 2) != 0:
            raise RuntimeError('Cannot establish file title key')
        if lib.dvdcss_seek(handle, start, 0) != start:
            raise RuntimeError('Cannot seek to requested sector')
        buffer = c.create_string_buffer(count * 2048)
        if lib.dvdcss_read(handle, buffer, count, 1) != count:
            raise RuntimeError('Short filesystem read')
        return buffer.raw
    finally:
        lib.dvdcss_close(handle)


def reread_ranges(device: str, requests: list[dict], output: Path) -> list[dict]:
    library = ctypes.util.find_library('dvdread')
    if not library:
        raise RuntimeError('libdvdread is required')
    lib = c.CDLL(library)
    lib.DVDOpen.argtypes, lib.DVDOpen.restype = [c.c_char_p], c.c_void_p
    lib.DVDClose.argtypes = [c.c_void_p]
    lib.DVDOpenFile.argtypes, lib.DVDOpenFile.restype = [c.c_void_p, c.c_int, c.c_int], c.c_void_p
    lib.DVDCloseFile.argtypes = [c.c_void_p]
    lib.DVDFileSize.argtypes, lib.DVDFileSize.restype = [c.c_void_p], c.c_ssize_t
    lib.DVDReadBlocks.argtypes = [c.c_void_p, c.c_int, c.c_size_t, c.c_void_p]
    lib.DVDReadBlocks.restype = c.c_ssize_t
    dvd = lib.DVDOpen(device.encode())
    if not dvd:
        raise RuntimeError(f'Cannot open DVD: {device}')
    output.mkdir(parents=True, exist_ok=True)
    results = []
    try:
        for index, request in enumerate(requests):
            vts, domain, start, count = (request[k] for k in ('vts', 'domain', 'start', 'count'))
            if domain not in (2, 3) or not 0 <= vts <= 99 or start < 0 or count < 1:
                raise ValueError('Invalid VOB sector request')
            stream = lib.DVDOpenFile(dvd, vts, domain)
            if not stream:
                raise RuntimeError(f'Cannot open VTS {vts}, domain {domain}')
            try:
                if start + count > lib.DVDFileSize(stream):
                    raise ValueError('Requested sector range exceeds VOB size')
                data = bytearray()
                buffer = c.create_string_buffer(2048)
                for sector in range(start, start + count):
                    if lib.DVDReadBlocks(stream, sector, 1, buffer) != 1:
                        raise RuntimeError(f'Failed to read sector {sector}')
                    data.extend(buffer.raw)
                # Publish only complete reads. The canonical backup is untouched.
                path = output / f'{index:04d}-vts{vts:02d}-domain{domain}-{start}-{count}.bin'
                with path.open('xb') as target:
                    target.write(data)
                results.append({**request, 'file': str(path), 'bytes': len(data),
                                'sha256': hashlib.sha256(data).hexdigest()})
            finally:
                lib.DVDCloseFile(stream)
    finally:
        lib.DVDClose(dvd)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', required=True)
    parser.add_argument('--requests', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    results = reread_ranges(args.device, json.loads(args.requests.read_text()), args.output)
    (args.output / 'manifest.json').write_text(json.dumps(results, indent=2) + '\n')
    print(f'Recovered {sum(r["count"] for r in results)} sectors in {len(results)} ranges')


if __name__ == '__main__':
    main()
