"""Build the tracer together with pinned libdvdnav, avoiding private ABI guesses."""
import argparse
import hashlib
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile

SHA256 = 'a2a18f5ad36d133c74bf9106b6445806fa253b09141a46392550394b647b221e'
URL = 'https://download.videolan.org/pub/videolan/libdvdnav/7.0.0/libdvdnav-7.0.0.tar.xz'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path, help=f'Official source: {URL}')
    parser.add_argument('--entry', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != SHA256:
        raise SystemExit('libdvdnav source archive checksum mismatch')
    here = Path(__file__).resolve().parent
    build = here / 'build'
    build.mkdir(exist_ok=True)
    with tarfile.open(args.archive) as archive:
        # Python 3.11.0 predates tarfile's extraction filter. Reject links and
        # traversal explicitly there; newer Python also applies the data filter.
        members = archive.getmembers()
        for member in members:
            destination = (build/member.name).resolve()
            if not destination.is_relative_to(build.resolve()) or member.issym() or member.islnk():
                raise ValueError('Unsafe libdvdnav archive member')
        if hasattr(tarfile, 'data_filter'):
            archive.extractall(build, members=members, filter='data')
        else:
            archive.extractall(build, members=members)
    src = build / 'libdvdnav-7.0.0' / 'src'
    (build / 'config.h').write_text('#define VERSION "7.0.0"\n#define HAVE_GETTIMEOFDAY 1\n')
    sources = ['dvdnav.c', 'highlight.c', 'logger.c', 'navigation.c', 'read_cache.c',
               'searching.c', 'settings.c', 'vm/decoder.c', 'vm/getset.c', 'vm/play.c',
               'vm/vm.c', 'vm/vmcmd.c', 'vm/vmget.c']
    flags = shlex.split(subprocess.check_output(
        ['pkg-config', '--cflags', '--libs', 'dvdnav', 'dvdread'], text=True))
    # All navigation objects are built here; do not link the installed dvdnav.
    flags = [flag for flag in flags if flag != '-ldvdnav']
    if sys.platform != 'darwin':
        flags.extend(shlex.split(subprocess.check_output(
            ['pkg-config', '--cflags', '--libs', 'openssl'], text=True)))
    subprocess.run(['cc', '-std=c11', '-O2', '-Wall',
                    '-Wno-unneeded-internal-declaration', '-I' + str(build),
                    '-D_DEFAULT_SOURCE', '-DHAVE_GETTIMEOFDAY=1', '-DVERSION="7.0.0"',
                    '-I' + str(src), '-I' + str(src / 'vm'),
                    str((args.entry or here / 'trace_game.c').resolve()), *[str(src / s) for s in sources],
                    '-o', str((args.output or build / 'trace_game').resolve()), *flags, '-lpthread'], check=True)
    print((args.output or build / 'trace_game').resolve())


if __name__ == '__main__':
    main()
