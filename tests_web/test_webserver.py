"""Testes de aceite do servidor web e da API (OS-M7-01; D018).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Suíte separada e opcional (SPEC §9.3): exige Jinja2 e se ignora sozinha sem ele.
Executar: python -m unittest discover -s tests_web -v
O servidor sobe numa thread em 127.0.0.1, porta efêmera; nada sai da máquina.
"""

import io
import json
import os
import re
import socket
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

try:
    import jinja2  # noqa: F401
    TEM_JINJA = True
except ModuleNotFoundError:
    TEM_JINJA = False

from biocompiler import exemplos, exports, io_formats, servicos  # noqa: E402
from biocompiler.core.at4 import alinhar_dna, candidatos_celula  # noqa: E402
from biocompiler.core.genetic_code import CODIGO_GENETICO, CODONS_STOP  # noqa: E402

SEQ1 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG"
SEQ2 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG"
PAGINAS = ["/", "/at1", "/at2", "/at3", "/at4", "/casos", "/historico", "/sobre"]
WEB = RAIZ / "biocompiler" / "web"
URL_EXTERNA = re.compile(r"(?:https?:)?//(?!www\.w3\.org/)[a-z0-9.-]+\.[a-z]{2,}", re.I)


@unittest.skipUnless(TEM_JINJA, "Jinja2 não instalado (suíte web opcional)")
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from biocompiler import webserver
        cls.srv = webserver.criar_servidor("127.0.0.1", 0)
        cls.porta = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def req(self, caminho, dados=None, metodo=None, bruto=None):
        corpo = bruto if bruto is not None else (
            json.dumps(dados).encode("utf-8") if dados is not None else None)
        r = urllib.request.Request(f"http://127.0.0.1:{self.porta}{caminho}", data=corpo,
                                   method=metodo or ("POST" if corpo is not None else "GET"))
        if corpo is not None:
            r.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    def json_ok(self, caminho, dados):
        st, h, corpo = self.req(caminho, dados)
        self.assertEqual(st, 200, corpo[:300])
        self.assertEqual(h["Content-Type"], "application/json; charset=utf-8")
        return corpo

    def erro(self, caminho, dados=None, status=400, bruto=None, metodo=None):
        st, h, corpo = self.req(caminho, dados, bruto=bruto, metodo=metodo)
        self.assertEqual(st, status, corpo[:300])
        self.assertEqual(h["Content-Type"], "application/json; charset=utf-8")
        return json.loads(corpo)["erro"]


class TestPaginas(Base):
    def test_paginas_e_navegacao(self):
        for pagina in PAGINAS:
            with self.subTest(pagina=pagina):
                st, h, corpo = self.req(pagina)
                self.assertEqual(st, 200)
                self.assertEqual(h["Content-Type"], "text/html; charset=utf-8")
                html = corpo.decode("utf-8")
                self.assertIn('<html lang="pt-BR"', html)
                self.assertRegex(html, r"<title>[^<]*BioCompiler Studio[^<]*</title>")
                for alvo in PAGINAS:
                    self.assertIn(f'href="{alvo}"', html)
                self.assertIsNone(URL_EXTERNA.search(html), URL_EXTERNA.search(html))

    def test_cabecalhos_de_seguranca(self):
        for caminho in ("/", "/api/saude", "/static/css/app.css"):
            with self.subTest(caminho=caminho):
                _, h, _ = self.req(caminho)
                csp = h["Content-Security-Policy"]
                for diretiva in ("default-src 'self'", "script-src 'self'", "style-src 'self'",
                                 "connect-src 'self'", "frame-ancestors 'none'"):
                    self.assertIn(diretiva, csp)
                self.assertEqual(h["X-Content-Type-Options"], "nosniff")
                self.assertEqual(h["Referrer-Policy"], "no-referrer")

    def _cabecalhos(self, h, corpo):
        self.assertIn("default-src 'self'", h["Content-Security-Policy"])
        self.assertEqual(h["X-Content-Type-Options"], "nosniff")
        self.assertEqual(h["Referrer-Policy"], "no-referrer")
        self.assertEqual(int(h["Content-Length"]), len(corpo))

    def test_cabecalhos_tambem_em_erros(self):
        casos = [("/nao-existe", None, 404), ("/api/nao-existe", None, 404),
                 ("/static/css/nao_existe.css", None, 404), ("/api/at1", None, 405),
                 ("/api/at1", {"sequencias": []}, 400),
                 ("/api/exportar", {"atividade": "at4", "seq1": "ACX", "seq2": "AC",
                                    "metodo": "global"}, 422)]
        for caminho, dados, status in casos:
            with self.subTest(caminho=caminho, status=status):
                st, h, corpo = self.req(caminho, dados, metodo="GET" if status == 405 else None)
                self.assertEqual(st, status)
                self._cabecalhos(h, corpo)

    def test_404_405(self):
        st, h, corpo = self.req("/nao-existe")
        self.assertEqual(st, 404)
        self.assertIn("text/html", h["Content-Type"])
        self.assertIn('href="/"', corpo.decode("utf-8"))
        self.assertEqual(self.erro("/api/nao-existe", status=404), "rota inexistente")
        self.assertEqual(self.erro("/api/at1", metodo="GET", status=405), "método não permitido")
        st, _, _ = self.req("/at1", {"x": 1})
        self.assertEqual(st, 405)


class TestEstaticos(Base):
    def test_css_js_servidos(self):
        for caminho, tipo in (("/static/css/app.css", "text/css; charset=utf-8"),
                              ("/static/js/app.js", "text/javascript; charset=utf-8")):
            with self.subTest(caminho=caminho):
                st, h, corpo = self.req(caminho)
                self.assertEqual(st, 200)
                self.assertEqual(h["Content-Type"], tipo)
                self.assertGreater(len(corpo), 0)

    def test_travessia_bloqueada(self):
        for caminho in ("/static/../webserver.py", "/static/%2e%2e/webserver.py",
                        "/static/..%2fwebserver.py", "/static/css/../../../webserver.py",
                        "/static/", "/static/css/nao_existe.css"):
            with self.subTest(caminho=caminho):
                st, _, corpo = self.req(caminho)
                self.assertEqual(st, 404)
                self.assertNotIn(b"def main", corpo)

    def test_contencao_em_static(self):
        # Arquivo com extensão servível FORA de static/: só vaza se a contenção falhar.
        isca = WEB / "isca_teste_travessia.css"
        isca.write_text("SEGREDO", encoding="utf-8")
        try:
            for caminho in ("/static/../isca_teste_travessia.css",
                            "/static/%2e%2e/isca_teste_travessia.css",
                            "/static/..%2fisca_teste_travessia.css",
                            "/static/css/..%2f..%2fisca_teste_travessia.css",
                            "/static/%2E%2E%2Fisca_teste_travessia.css"):
                with self.subTest(caminho=caminho):
                    st, _, corpo = self.req(caminho)
                    self.assertEqual(st, 404)
                    self.assertNotIn(b"SEGREDO", corpo)
        finally:
            isca.unlink()

    def test_sem_recursos_externos_nem_codigo_inline(self):
        for arq in sorted(WEB.rglob("*")):
            if arq.is_file() and arq.suffix in (".html", ".css", ".js", ".svg"):
                texto = arq.read_text(encoding="utf-8")
                with self.subTest(arquivo=str(arq.relative_to(RAIZ))):
                    self.assertIsNone(URL_EXTERNA.search(texto), URL_EXTERNA.search(texto))
                    self.assertNotRegex(texto, r"@import\s+url\(\s*['\"]?https?:")
                    if arq.suffix == ".html":
                        self.assertNotRegex(texto, r"<style\b")
                        self.assertNotRegex(texto, r"\sstyle\s*=")
                        self.assertNotRegex(texto, r"\son[a-z]+\s*=")
                        for tag in re.findall(r"<script\b[^>]*>", texto):
                            self.assertTrue("src=" in tag or "application/json" in tag, tag)


class TestApiConsulta(Base):
    def test_saude_exemplos_codigo(self):
        st, _, corpo = self.req("/api/saude")
        self.assertEqual((st, json.loads(corpo)), (200, {"ok": True, "nome": "BioCompiler Studio"}))
        _, _, corpo = self.req("/api/exemplos")
        self.assertEqual(json.loads(corpo), {
            "at1": list(exemplos.AT1_EXEMPLOS), "at2": list(exemplos.AT2_EXEMPLOS),
            "at3": list(exemplos.AT3_EXEMPLOS),
            "at4": {"seq1": "ACGTAC", "seq2": "ACGTTC"},
            "all": {"seq1": SEQ1, "seq2": SEQ2}})
        self.assertEqual(exemplos.ALL_EXEMPLO, (SEQ1, SEQ2))
        _, _, corpo = self.req("/api/codigo-genetico")
        doc = json.loads(corpo)
        self.assertEqual(doc["codigos"], CODIGO_GENETICO)
        self.assertEqual(doc["stops"], sorted(CODONS_STOP))


class TestApiAtividades(Base):
    def test_lote_paridade_com_cli(self):
        for at, casos in (("at1", exemplos.AT1_EXEMPLOS), ("at2", exemplos.AT2_EXEMPLOS),
                          ("at3", exemplos.AT3_EXEMPLOS)):
            with self.subTest(at=at):
                seqs = list(casos)
                esperado = exports.json_lote(at, seqs, servicos.processar_lote(at, seqs), [])
                self.assertEqual(self.json_ok(f"/api/{at}", {"sequencias": seqs}),
                                 esperado.encode("utf-8"))
                texto = "\r\n".join(seqs) + "\r\n"
                regs = io_formats.separar_registros(texto)
                self.assertEqual(self.json_ok(f"/api/{at}", {"texto": texto}),
                                 exports.json_lote(at, regs, servicos.processar_lote(at, regs),
                                                   []).encode("utf-8"))

    def test_lote_erros_400_413(self):
        casos = [
            (None, b"{nao json", "JSON inválido"),
            ([1, 2], None, "corpo deve ser um objeto JSON"),
            ({}, None, "informe 'sequencias' ou 'texto'"),
            ({"sequencias": ["A"], "texto": "A"}, None, "informe 'sequencias' ou 'texto'"),
            ({"sequencias": "ATG"}, None, "'sequencias' deve ser uma lista de textos"),
            ({"sequencias": ["ATG", 3]}, None, "'sequencias' deve ser uma lista de textos"),
            ({"texto": 5}, None, "'texto' deve ser um texto"),
            ({"sequencias": []}, None, "nenhuma sequência na entrada"),
            ({"texto": ""}, None, "nenhuma sequência na entrada"),
            ({"sequencias": ["A"] * 1001}, None, "lote acima do limite de 1000 sequências"),
        ]
        for dados, bruto, msg in casos:
            with self.subTest(msg=msg, dados=str(dados)[:40]):
                self.assertEqual(self.erro("/api/at1", dados, bruto=bruto), msg)
        # O limite é checado pelo Content-Length, antes de ler o corpo.
        import http.client
        con = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=30)
        con.putrequest("POST", "/api/at2")
        con.putheader("Content-Type", "application/json")
        con.putheader("Content-Length", str(2 * 1024 * 1024 + 1))
        con.endheaders()
        resp = con.getresponse()
        self.assertEqual(resp.status, 413)
        corpo = resp.read()
        self.assertEqual(json.loads(corpo)["erro"], "requisição acima de 2 MB")
        self._cabecalhos_resp(resp, corpo)
        con.close()

    def _cabecalhos_resp(self, resp, corpo):
        self.assertIn("default-src 'self'", resp.getheader("Content-Security-Policy"))
        self.assertEqual(resp.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(int(resp.getheader("Content-Length")), len(corpo))

    def test_limite_exato_de_2_mib(self):
        # 2 MB = 2 * 1024 * 1024 bytes: exatamente no limite é aceito.
        prefixo, sufixo = b'{"texto": "', b'"}'
        meio = (2 * 1024 * 1024 - len(prefixo) - len(sufixo))
        seq = b"A" * (meio // 2 - 1) + b"\\n" + b"A" * (meio - meio // 2 - 1)  # \\n escapado no JSON
        corpo = prefixo + seq + sufixo
        self.assertEqual(len(corpo), 2 * 1024 * 1024)
        st, _, resp = self.req("/api/at4", bruto=corpo)
        self.assertEqual(st, 200, resp[:200])
        self.assertEqual(json.loads(resp)[0]["resultado"], "ERRO - sequência muito longa")

    def test_content_length_ausente_ou_invalido(self):
        import http.client
        for valor, status, msg in ((None, 411, "Content-Length obrigatório"),
                                   ("abc", 400, "Content-Length inválido"),
                                   ("-5", 400, "Content-Length inválido")):
            with self.subTest(valor=valor):
                con = http.client.HTTPConnection("127.0.0.1", self.porta, timeout=30)
                con.putrequest("POST", "/api/at1", skip_accept_encoding=True)
                if valor is not None:
                    con.putheader("Content-Length", valor)
                con.endheaders()
                resp = con.getresponse()
                corpo = resp.read()
                self.assertEqual(resp.status, status)
                self.assertEqual(json.loads(corpo)["erro"], msg)
                self._cabecalhos_resp(resp, corpo)
                con.close()

    def test_at4_paridade_parametros_e_texto(self):
        casos = [
            ({"seq1": "ACGTAC", "seq2": "ACGTTC"}, ("ACGTAC", "ACGTTC", "both", 2, -1, -2)),
            ({"seq1": "acgta", "seq2": "TCATG", "metodo": "local", "match": 3,
              "mismatch": "-2", "gap": -4}, ("acgta", "TCATG", "local", 3, -2, -4)),
            ({"seq1": "ACGT", "seq2": "ACGT", "metodo": "global", "match": "abc"},
             ("ACGT", "ACGT", "global", "abc", -1, -2)),
            ({"seq1": "ACGT", "seq2": "ACGT", "metodo": "global", "gap": 1.5},
             ("ACGT", "ACGT", "global", 2, -1, 1.5)),
            ({"texto": ">a\nACG\nTAC\n>b\nACGTTC\n", "metodo": "global"},
             ("ACGTAC", "ACGTTC", "global", 2, -1, -2)),
        ]
        for dados, (s1, s2, m, ma, mi, g) in casos:
            with self.subTest(dados=dados):
                res = servicos.alinhar_par(s1, s2, m, ma, mi, g)
                esperado = exports.json_at4(s1, s2, ma, mi, g, res, [])
                self.assertEqual(self.json_ok("/api/at4", dados), esperado.encode("utf-8"))
        doc = json.loads(self.json_ok("/api/at4", casos[2][0]))
        self.assertEqual(doc[0]["status"], "ERRO")

    def test_at4_erros(self):
        casos = [
            ({"seq1": "A"}, "informe 'seq1' e 'seq2' ou 'texto'"),
            ({"seq1": "A", "seq2": "C", "texto": "A\nC\n"}, "informe 'seq1' e 'seq2' ou 'texto'"),
            ({"seq1": "A", "seq2": 3}, "'seq1' e 'seq2' devem ser textos"),
            ({"texto": "A\nC\nG\n"}, "esperadas exatamente 2 sequências, encontradas 3"),
            ({"seq1": "A", "seq2": "C", "metodo": "xyz"},
             "método inválido: 'xyz' (use local, global ou both)"),
        ]
        for dados, msg in casos:
            with self.subTest(msg=msg):
                self.assertEqual(self.erro("/api/at4", dados), msg)

    def test_all_paridade(self):
        for dados, args in (({"seq1": SEQ1, "seq2": SEQ2}, (SEQ1, SEQ2, "both", 2, -1, -2)),
                            ({"texto": f"{SEQ1}\nCCCGCTAAACCGTAA\n", "metodo": "global",
                              "match": "3"}, (SEQ1, "CCCGCTAAACCGTAA", "global", 3, -1, -2))):
            with self.subTest(dados=str(dados)[:50]):
                rf = servicos.fluxo_completo(*args)
                esperado = exports.json_fluxo(args[0], args[1], args[2], args[3], args[4],
                                              args[5], rf, [])
                self.assertEqual(self.json_ok("/api/all", dados), esperado.encode("utf-8"))
        self.assertEqual(self.erro("/api/all", {"seq1": SEQ1}), "informe 'seq1' e 'seq2' ou 'texto'")


class TestApiInspetor(Base):
    def test_celula(self):
        base = {"seq1": "ACGTAC", "seq2": "ACGTTC", "metodo": "both"}
        r = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        doc = json.loads(self.json_ok("/api/at4/celula", {**base, "alinhamento": "global",
                                                           "i": 5, "j": 1}))
        self.assertEqual(doc, {"metodo": "global", "i": 5, "j": 1, "valor": -6, "direcao": "↖",
                               "candidatos": [{"nome": n, "valor": v}
                                              for n, v in candidatos_celula(r, 5, 1)]})
        doc = json.loads(self.json_ok("/api/at4/celula", {**base, "alinhamento": "local",
                                                           "i": 0, "j": 3}))
        self.assertEqual((doc["valor"], doc["direcao"], doc["candidatos"]), (0, "·", []))

    def test_celula_erros(self):
        base = {"seq1": "ACGTAC", "seq2": "ACGTTC"}
        casos = [
            ({**base, "alinhamento": "global", "i": 7, "j": 0}, "célula fora da matriz: (7,0)"),
            ({**base, "alinhamento": "global", "i": "1", "j": 0}, "'i' e 'j' devem ser inteiros"),
            ({**base, "alinhamento": "both", "i": 1, "j": 1},
             "'alinhamento' deve ser 'local' ou 'global'"),
            ({"seq1": "ACX", "seq2": "AC", "alinhamento": "global", "i": 1, "j": 1},
             "alinhamento com erro: ERRO - base inválida"),
            ({**base, "alinhamento": "global", "i": True, "j": 0}, "'i' e 'j' devem ser inteiros"),
            ({**base, "alinhamento": "global", "i": 1, "j": False}, "'i' e 'j' devem ser inteiros"),
            ({**base, "alinhamento": "global", "i": 1, "j": 1, "match": []},
             "alinhamento com erro: ERRO - parâmetro não numérico"),
            ({**base, "alinhamento": "local", "i": 1, "j": 1, "gap": {"x": 1}},
             "alinhamento com erro: ERRO - parâmetro não numérico"),
        ]
        for dados, msg in casos:
            with self.subTest(msg=msg):
                self.assertEqual(self.erro("/api/at4/celula", dados), msg)


class TestExportar(Base):
    def _zip(self, dados):
        st, h, corpo = self.req("/api/exportar", dados)
        self.assertEqual(st, 200, corpo[:300])
        self.assertEqual(h["Content-Type"], "application/zip")
        return h, zipfile.ZipFile(io.BytesIO(corpo))

    def _conferir(self, z, esperado):
        self.assertEqual(z.namelist(), list(esperado))
        for nome, conteudo in esperado.items():
            self.assertEqual(z.read(nome).decode("utf-8"), conteudo, nome)

    def test_exportar_lote(self):
        seqs = list(exemplos.AT1_EXEMPLOS)
        h, z = self._zip({"atividade": "at1", "sequencias": seqs})
        self.assertEqual(h["Content-Disposition"], 'attachment; filename="biocompiler_at1.zip"')
        esperado = exports.artefatos_lote("at1", servicos.processar_lote("at1", seqs))
        self.assertEqual(list(esperado), ["at1_resultados.txt"])
        self._conferir(z, esperado)

    def test_exportar_at4_e_all(self):
        res = servicos.alinhar_par("ACGTAC", "ACGTTC", "both", 2, -1, -2)
        _, z = self._zip({"atividade": "at4", "seq1": "ACGTAC", "seq2": "ACGTTC",
                          "delimitador": "comma"})
        esperado = exports.artefatos_at4(res, ",")
        self.assertEqual(len(esperado), 9)
        self._conferir(z, esperado)
        rf = servicos.fluxo_completo(SEQ1, SEQ2, "global", 2, -1, -2)
        _, z = self._zip({"atividade": "all", "seq1": SEQ1, "seq2": SEQ2, "metodo": "global"})
        esperado = exports.artefatos_fluxo(rf, ";")
        self.assertEqual(list(esperado)[:4], ["relatorio_mestre.txt", "at1_resultados.txt",
                                              "at2_resultados.txt", "at3_resultados.txt"])
        self._conferir(z, esperado)

    def test_exportar_erros(self):
        self.assertEqual(self.erro("/api/exportar", {"atividade": "at4", "seq1": "ACX",
                                                     "seq2": "AC", "metodo": "global"}, status=422),
                         "nada a exportar: ERRO - base inválida")
        self.assertEqual(self.erro("/api/exportar", {"atividade": "x"}),
                         "atividade inválida: 'x'")
        self.assertEqual(self.erro("/api/exportar", {"atividade": "at4", "seq1": "A", "seq2": "C",
                                                     "delimitador": "tab"}),
                         "'delimitador' deve ser 'semicolon' ou 'comma'")


class TestArtefatosIguaisCli(unittest.TestCase):
    """Os artefatos montados em exports são os mesmos que a CLI grava (sem Jinja2)."""

    def test_cli_grava_artefatos(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
            env.pop("PYTHONPATH", None)
            proc = subprocess.run([sys.executable, "-S", str(RAIZ / "main.py"), "all", "--seq1",
                                   SEQ1, "--seq2", SEQ2, "--out-dir", "r", "--quiet"], cwd=d,
                                  env=env, stdin=subprocess.DEVNULL, capture_output=True,
                                  timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            esperado = exports.artefatos_fluxo(servicos.fluxo_completo(SEQ1, SEQ2, "both", 2, -1, -2), ";")
            self.assertEqual(sorted(p.name for p in (Path(d) / "r").iterdir()), sorted(esperado))
            for nome, conteudo in esperado.items():
                self.assertEqual((Path(d) / "r" / nome).read_text(encoding="utf-8"), conteudo)


@unittest.skipUnless(TEM_JINJA, "Jinja2 não instalado (suíte web opcional)")
class TestServeCli(unittest.TestCase):
    def _rodar(self, *args):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run([sys.executable, str(RAIZ / "main.py"), "serve", *args],
                              cwd=RAIZ, env=env, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, encoding="utf-8", timeout=60)

    def test_argumento_invalido(self):
        proc = self._rodar("--port", "abc")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("usage:", proc.stderr)

    def test_host_fora_do_loopback_exige_opcao(self):
        proc = self._rodar("--host", "0.0.0.0", "--port", "0")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("biocompiler: host 0.0.0.0 não é local; use --permitir-rede para expor "
                      "o servidor na rede", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_porta_ocupada(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            s.listen()
            porta = s.getsockname()[1]
            proc = self._rodar("--port", str(porta))
        self.assertEqual(proc.returncode, 1)
        self.assertIn(f"biocompiler: porta {porta} indisponível", proc.stderr)


if __name__ == "__main__":
    unittest.main()
