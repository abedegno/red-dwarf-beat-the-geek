"""Offline DVD subpicture extraction and original highlight bitmap rendering."""
import struct
import zlib
from pathlib import Path


def extract_packets(data: bytes) -> list[dict]:
    buffers, packets = {}, []
    for start in range(0, len(data), 2048):
        sector = data[start:start + 2048]
        if len(sector) != 2048 or sector[:4] != b'\0\0\1\xba':
            continue
        offset = 14 + (sector[13] & 7)
        while offset + 6 <= 2048 and sector[offset:offset + 3] == b'\0\0\1':
            length = int.from_bytes(sector[offset + 4:offset + 6], 'big')
            end = offset + 6 + length
            if not length or end > 2048:
                break
            if sector[offset + 3] == 0xbd and offset + 9 <= end:
                payload = offset + 9 + sector[offset + 8]
                if payload < end and 0x20 <= sector[payload] <= 0x3f:
                    stream = sector[payload]
                    buffer = buffers.setdefault(stream, bytearray())
                    buffer.extend(sector[payload + 1:end])
                    while len(buffer) >= 4:
                        size = int.from_bytes(buffer[:2], 'big')
                        if size < 4:
                            raise ValueError('Invalid SPU packet size')
                        if len(buffer) < size:
                            break
                        packets.append({'stream': stream, 'sector': start // 2048,
                                        'data': bytes(buffer[:size])})
                        del buffer[:size]
            offset = end
    return packets


def decode_rle(data: bytes, width: int, height: int, offsets: tuple[int, int]) -> list[list[int]]:
    if not 0 < width <= 720 or not 0 < height <= 576:
        raise ValueError('Invalid SPU bitmap dimensions')
    pixels = [[0] * width for _ in range(height)]
    for field in (0, 1):
        cursor = offsets[field] * 2
        def nibble():
            nonlocal cursor
            if cursor // 2 >= len(data):
                raise ValueError('Truncated SPU bitmap')
            value = (data[cursor // 2] >> (0 if cursor & 1 else 4)) & 15
            cursor += 1
            return value
        for y in range(field, height, 2):
            x = 0
            while x < width:
                code = nibble()
                if code < 4:
                    code = (code << 4) | nibble()
                    if code < 16:
                        code = (code << 4) | nibble()
                        if code < 64:
                            code = (code << 4) | nibble()
                run, colour = code >> 2, code & 3
                if run == 0:
                    run = width - x
                if x + run > width:
                    raise ValueError('SPU run extends beyond scanline')
                pixels[y][x:x + run] = [colour] * run
                x += run
            cursor += cursor & 1
    return pixels


def decode_packet(packet: bytes) -> dict:
    if len(packet) < 4 or int.from_bytes(packet[:2], 'big') != len(packet):
        raise ValueError('Truncated SPU packet')
    control = int.from_bytes(packet[2:4], 'big')
    visited, rect, offsets, palette, alpha = set(), None, None, 0, 0
    while control not in visited:
        visited.add(control)
        if control + 4 > len(packet):
            raise ValueError('Invalid SPU control offset')
        next_control = int.from_bytes(packet[control + 2:control + 4], 'big')
        cursor = control + 4
        while cursor < len(packet):
            command = packet[cursor]
            cursor += 1
            if command == 0xff:
                break
            sizes = {0: 0, 1: 0, 2: 0, 3: 2, 4: 2, 5: 6, 6: 4}
            if command not in sizes:
                raise ValueError(f'Unsupported SPU control command {command:#x}')
            size = sizes[command]
            body = packet[cursor:cursor + size]
            if len(body) != size:
                raise ValueError('Truncated SPU control')
            if command == 3:
                palette = int.from_bytes(body, 'big')
            elif command == 4:
                alpha = int.from_bytes(body, 'big')
            elif command == 5:
                x = (body[0] << 4) | (body[1] >> 4)
                right = ((body[1] & 15) << 8) | body[2]
                y = (body[3] << 4) | (body[4] >> 4)
                bottom = ((body[4] & 15) << 8) | body[5]
                rect = {'x': x, 'y': y, 'width': right - x + 1, 'height': bottom - y + 1}
            elif command == 6:
                offsets = (int.from_bytes(body[:2], 'big'), int.from_bytes(body[2:], 'big'))
            cursor += size
        if rect is not None and offsets is not None:
            # The selected PCI colour table overrides palette/alpha. Bitmap is
            # retained from its first display definition, not later stop commands.
            return {'rect': rect, 'pixels': decode_rle(packet, rect['width'], rect['height'], offsets),
                    'palette': palette, 'alpha': alpha}
        control = next_control
    raise ValueError('SPU has no bitmap definition')


def render_rgba(pixels: list[list[int]], palette: list[int], colour_table: int) -> bytes:
    result = bytearray()
    for row in pixels:
        for pixel in row:
            value = palette[(colour_table >> (16 + pixel * 4)) & 15]
            y, cr, cb = (value >> 16) & 255, ((value >> 8) & 255) - 128, (value & 255) - 128
            channels = (1.164383 * (y - 16) + 1.596027 * cr,
                        1.164383 * (y - 16) - .812968 * cr - .391762 * cb,
                        1.164383 * (y - 16) + 2.017232 * cb)
            result.extend(max(0, min(255, round(c))) for c in channels)
            result.append(((colour_table >> (pixel * 4)) & 15) * 17)
    return bytes(result)


def png_bytes(width: int, height: int, rgba: bytes):
    if len(rgba) != width * height * 4:
        raise ValueError('RGBA buffer size mismatch')
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = b''.join(b'\0' + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
                     + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))


def write_png(path: Path, width: int, height: int, rgba: bytes):
    """Verify cached pixels and publish a complete PNG atomically."""
    import tempfile
    payload = png_bytes(width, height, rgba)
    path = Path(path)
    if path.is_file() and path.read_bytes() == payload:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.png', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
