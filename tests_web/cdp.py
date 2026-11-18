"""Cliente mínimo do Chrome DevTools Protocol (somente biblioteca padrão).

Usado pelos testes de responsividade para emular uma viewport real (ex.: 390×844):
no Windows, `--window-size` não desce abaixo de ~500 px, então capturas por janela
recortam um layout mais largo. A emulação por CDP mede o layout na largura exata.
"""
import base64
import glob
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request


def _portas_candidatas():
    """Portas baixas sem `bind` prévio: com rede espelhada do WSL, sondar a porta no Linux
    a reserva também no Windows e o Chrome não consegue abri-la."""
    base = 9300 + (os.getpid() * 7) % 380
    return [base + i * 3 for i in range(5)]


def _dir_perfil(chrome):
    """Perfil descartável; Chrome do Windows precisa de um caminho Windows."""
    if chrome.startswith("/mnt/"):
        for base in sorted(glob.glob("/mnt/c/Users/*/AppData/Local/Temp")):
            if os.access(base, os.W_OK):
                d = tempfile.mkdtemp(prefix="biocompiler_cdp_", dir=base)
                win = subprocess.run(["wslpath", "-w", d], capture_output=True, text=True)
                return d, win.stdout.strip()
    d = tempfile.mkdtemp(prefix="biocompiler_cdp_")
    return d, d


class Navegador:
    def __init__(self, chrome):
        for self.porta in _portas_candidatas():
            if self._iniciar(chrome):
                break
        else:
            raise RuntimeError("Chrome não abriu a porta de depuração")
        req = urllib.request.Request(f"http://127.0.0.1:{self.porta}/json/new?about:blank",
                                     method="PUT")
        ws = json.load(urllib.request.urlopen(req, timeout=10))["webSocketDebuggerUrl"]
        self._conectar(ws.split(f":{self.porta}", 1)[1])
        self._id = 0

    def _iniciar(self, chrome):
        self.dir_local, perfil = _dir_perfil(chrome)
        self.proc = subprocess.Popen(
            [chrome, "--headless=new", "--disable-gpu", "--no-first-run",
             "--no-default-browser-check", f"--remote-debugging-port={self.porta}",
             f"--user-data-dir={perfil}", "about:blank"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        prazo = time.time() + 15
        while time.time() < prazo:
            time.sleep(0.5)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.porta}/json/version", timeout=2)
                return True
            except OSError:
                pass
        self._encerrar_proc()
        return False

    def _conectar(self, caminho):
        self.sock = socket.create_connection(("127.0.0.1", self.porta), timeout=30)
        chave = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((
            f"GET {caminho} HTTP/1.1\r\nHost: 127.0.0.1:{self.porta}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {chave}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        self._resto = buf.split(b"\r\n\r\n", 1)[1]

    def _enviar(self, obj):
        dados = json.dumps(obj).encode()
        cab = bytearray([0x81])
        n = len(dados)
        if n < 126:
            cab.append(0x80 | n)
        elif n < 65536:
            cab.append(0x80 | 126)
            cab += struct.pack(">H", n)
        else:
            cab.append(0x80 | 127)
            cab += struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(bytes(cab) + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(dados)))

    def _ler(self, n):
        while len(self._resto) < n:
            self._resto += self.sock.recv(65536)
        d, self._resto = self._resto[:n], self._resto[n:]
        return d

    def _receber(self):
        msg = b""
        while True:
            b1, b2 = self._ler(2)
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._ler(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._ler(8))[0]
            msg += self._ler(n)
            if b1 & 0x80:
                return json.loads(msg)

    def cmd(self, metodo, **params):
        self._id += 1
        self._enviar({"id": self._id, "method": metodo, "params": params})
        while True:
            r = self._receber()
            if r.get("id") == self._id:
                if "error" in r:
                    raise RuntimeError(f"{metodo}: {r['error']}")
                return r.get("result", {})

    def avaliar(self, expressao):
        r = self.cmd("Runtime.evaluate", expression=expressao, returnByValue=True,
                     awaitPromise=True)
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:500])
        return r["result"].get("value")

    def abrir(self, url, largura, altura, espera_js="true", prazo=12):
        self.cmd("Emulation.setDeviceMetricsOverride", width=largura, height=altura,
                 deviceScaleFactor=1, mobile=largura < 700)
        self.cmd("Page.enable")
        self.cmd("Page.navigate", url=url)
        fim = time.time() + prazo
        while time.time() < fim:
            time.sleep(0.25)
            try:
                if self.avaliar(f"document.readyState === 'complete' && ({espera_js})"):
                    time.sleep(0.3)
                    return True
            except RuntimeError:
                pass
        return False

    def captura(self, arquivo):
        img = self.cmd("Page.captureScreenshot", format="png")
        with open(arquivo, "wb") as f:
            f.write(base64.b64decode(img["data"]))

    def fechar(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self._encerrar_proc()

    def _encerrar_proc(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()
