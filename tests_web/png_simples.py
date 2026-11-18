"""Decodificador PNG mínimo (biblioteca padrão) para medir pixels de capturas CDP nos testes."""
import zlib, struct
def ler(b):
    assert b[:8] == b'\x89PNG\r\n\x1a\n'; i = 8; idat = b''
    while i < len(b):
        n, = struct.unpack('>I', b[i:i+4]); tipo = b[i+4:i+8]; dado = b[i+8:i+8+n]; i += 12 + n
        if tipo == b'IHDR': w, h, prof, cor = struct.unpack('>IIBB', dado[:10])
        elif tipo == b'IDAT': idat += dado
    bpp = 4 if cor == 6 else 3; raw = zlib.decompress(idat); st = w * bpp; out = []; prev = bytearray(st); p = 0
    for _ in range(h):
        f = raw[p]; lin = bytearray(raw[p+1:p+1+st]); p += 1 + st
        for x in range(st):
            a = lin[x-bpp] if x >= bpp else 0; c = prev[x-bpp] if x >= bpp else 0; up = prev[x]
            if f == 1: lin[x] = (lin[x] + a) & 255
            elif f == 2: lin[x] = (lin[x] + up) & 255
            elif f == 3: lin[x] = (lin[x] + (a + up) // 2) & 255
            elif f == 4:
                pa, pb, pc = abs(up - c), abs(a - c), abs(a + up - 2 * c)
                lin[x] = (lin[x] + (a if pa <= pb and pa <= pc else up if pb <= pc else c)) & 255
        out.append(bytes(lin)); prev = lin
    return w, h, bpp, out
