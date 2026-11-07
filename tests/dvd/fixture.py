"""Author tiny, original test media; no commercial disc data in fixtures."""
from pathlib import Path
import subprocess
import struct
import zlib


def highlight_png(path: Path):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = []
    for y in range(576):
        rows.append(b'\0' + b''.join(
            b'\xff\xff\xff\xff' if 100 <= y <= 120 and (100 <= x <= 120 or 200 <= x <= 220)
            else b'\0\0\0\0' for x in range(720)))
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 720, 576, 8, 6, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))


def author_disc(root: Path, buttons=False, menu_language='en', vm_menu_media=False):
    media = root / 'blue.vob'
    subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                    'color=c=blue:s=720x576:r=25:d=2', '-f', 'lavfi', '-i',
                    'anullsrc=r=48000:cl=stereo', '-t', '2', '-target', 'pal-dvd',
                    '-aspect', '16:9', '-y', str(media)], check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    menu = media
    button_xml = ''
    if buttons:
        png = root / 'highlight.png'
        highlight_png(png)
        spu = root / 'spu.xml'
        spu.write_text(f'''<subpictures><stream>
          <spu start="00:00:00.00" end="00:00:00.80" highlight="{png}" select="{png}">
            <button name="one" x0="100" y0="100" x1="120" y1="120" right="two"/>
            <button name="two" x0="200" y0="100" x1="220" y1="120" left="one"/>
          </spu>
          <spu start="00:00:00.80" end="00:00:02.00" highlight="{png}" select="{png}">
            <button name="one" x0="90" y0="100" x1="130" y1="120" right="two"/>
            <button name="two" x0="190" y0="100" x1="230" y1="120" left="one"/>
          </spu>
        </stream></subpictures>''')
        menu = root / 'menu.vob'
        with media.open('rb') as inp, menu.open('wb') as out:
            result = subprocess.run(['spumux', str(spu)], stdin=inp, stdout=out, stderr=subprocess.PIPE)
        if result.returncode:
            raise RuntimeError(result.stderr.decode())
        button_xml = '<button name="one">g0=g0+1; jump menu 2;</button><button name="two">jump title 2;</button>'
    xml = root / 'disc.xml'
    vm_body = (f'<vob file="{media}"/><post>jump titleset 1 menu;</post>'
               if vm_menu_media else '<pre>jump titleset 1 menu;</pre>')
    xml.write_text(f'''<dvdauthor dest="{root / 'dvd'}">
      <vmgm><fpc>g0=7; jump menu 1;</fpc><menus lang="{menu_language}"><video format="pal" />
        <pgc entry="title">{vm_body}</pgc>
      </menus></vmgm>
      <titleset><menus lang="{menu_language}"><video format="pal" aspect="16:9"/>
        <pgc entry="root"><vob file="{menu}" pause="1"/>{button_xml}
          <post>jump title 2;</post></pgc>
        <pgc><pre>if (g0 == 8) jump title 1; jump title 2;</pre></pgc>
      </menus><titles><video format="pal" aspect="16:9"/>
        <pgc><pre>g1=9;</pre><vob file="{media}" chapters="0,1"/>
          <post>g0=9; call menu;</post></pgc>
        <pgc><vob file="{media}"/><post>call menu;</post></pgc>
      </titles></titleset></dvdauthor>''')
    result = subprocess.run(['dvdauthor', '-x', str(xml)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return root / 'dvd' / 'VIDEO_TS'
