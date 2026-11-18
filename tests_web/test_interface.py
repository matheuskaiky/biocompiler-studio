"""Testes de aceite da interface web (OS-M7-02; D018/D019).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Três famílias:
1. Estrutura e acessibilidade do HTML servido (landmarks, abas ARIA, rótulos).
2. Regras dos estáticos (temas, cores semânticas, movimento reduzido, JS sem
   recálculo nem injeção de HTML).
3. Ponta a ponta num navegador real (Chrome headless): links profundos executam
   a atividade e o DOM final mostra o resultado vindo da API. Ignorada se não
   houver Chrome/Edge disponível.
Executar: python -m unittest discover -s tests_web -v
"""

import html.parser
import os
import re
import shutil
import subprocess
import sys
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

try:
    import jinja2  # noqa: F401
    TEM_JINJA = True
except ModuleNotFoundError:
    TEM_JINJA = False

WEB = RAIZ / "biocompiler" / "web"
JS = WEB / "static" / "js"
CSS = WEB / "static" / "css"
SEQ1 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG"
SEQ2 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG"

PAGINAS = {"/": "lab", "/at1": "at1", "/at2": "at2", "/at3": "at3", "/at4": "at4",
           "/casos": "casos", "/historico": "historico", "/sobre": "sobre"}
ABAS_AT = ["Entrada", "Etapas", "Visualização", "Resultados", "Exportação"]
ABAS_LAB = ["Montar experimento", "Mapa da expressão gênica", "Comparador molecular",
            "Relatório final"]
VARIAVEIS = ["--cor-dna", "--cor-pre-mrna", "--cor-splicing", "--cor-mrna", "--cor-traducao",
             "--cor-alinhamento", "--cor-erro", "--cor-ok", "--fundo", "--superficie", "--texto"]


def _chrome():
    for c in (os.environ.get("BIOCOMPILER_CHROME"),
              "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
              "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
              shutil.which("google-chrome"), shutil.which("chromium"),
              shutil.which("chromium-browser")):
        if c and Path(c).exists():
            return c
    return None


class Arvore(html.parser.HTMLParser):
    """Coleta elementos (tag, atributos, texto direto) do HTML servido."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elementos = []
        self._pilha = []

    def handle_starttag(self, tag, attrs):
        el = {"tag": tag, "attrs": dict(attrs), "texto": ""}
        self.elementos.append(el)
        if tag not in ("input", "meta", "link", "br", "img", "hr", "source"):
            self._pilha.append(el)

    def handle_endtag(self, tag):
        while self._pilha:
            el = self._pilha.pop()
            if el["tag"] == tag:
                break

    def handle_data(self, data):
        for el in self._pilha:
            el["texto"] += data

    def todos(self, tag=None, **attrs):
        return [e for e in self.elementos if (tag is None or e["tag"] == tag)
                and all(e["attrs"].get(k.replace("_", "-")) == v for k, v in attrs.items())]


@unittest.skipUnless(TEM_JINJA, "Jinja2 não instalado (suíte web opcional)")
class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from biocompiler import webserver
        cls.srv = webserver.criar_servidor("127.0.0.1", 0)
        cls.porta = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def pagina(self, caminho):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.porta}{caminho}", timeout=30) as r:
            texto = r.read().decode("utf-8")
        a = Arvore()
        a.feed(texto)
        return texto, a


class TestEstrutura(Base):
    def test_landmarks_e_navegacao(self):
        for caminho, nome in PAGINAS.items():
            with self.subTest(pagina=caminho):
                texto, a = self.pagina(caminho)
                (html_el,) = a.todos("html")
                self.assertEqual(html_el["attrs"].get("lang"), "pt-BR")
                self.assertEqual(html_el["attrs"].get("data-tema"), "escuro")
                (body,) = a.todos("body")
                self.assertEqual(body["attrs"].get("data-pagina"), nome)
                self.assertEqual(len(a.todos("h1")), 1)
                self.assertEqual(len(a.todos("main")), 1)
                self.assertEqual(a.todos("main")[0]["attrs"].get("id"), "conteudo")
                pular = [e for e in a.todos("a") if e["attrs"].get("href") == "#conteudo"]
                self.assertEqual(len(pular), 1)
                self.assertIn("Pular para o conteúdo", pular[0]["texto"])
                navs = [e for e in a.todos("nav")
                        if e["attrs"].get("aria-label") == "Navegação principal"]
                self.assertEqual(len(navs), 1)
                atuais = [e for e in a.todos("a") if e["attrs"].get("aria-current") == "page"]
                self.assertEqual([e["attrs"]["href"] for e in atuais], [caminho])
                tema = a.todos("button", data_acao="tema")
                self.assertEqual(len(tema), 1)
                self.assertTrue(tema[0]["attrs"].get("aria-label"))
                vivas = [e for e in a.elementos if e["attrs"].get("aria-live") == "polite"
                         and e["attrs"].get("data-regiao") == "status"]
                self.assertEqual(len(vivas), 1)
                self.assertIn('name="viewport"', texto)
                self.assertIn('<link rel="icon"', texto)

    def test_abas_aria(self):
        esperado = {"/": ABAS_LAB, "/at1": ABAS_AT, "/at2": ABAS_AT, "/at3": ABAS_AT,
                    "/at4": ABAS_AT}
        for caminho, rotulos in esperado.items():
            with self.subTest(pagina=caminho):
                _, a = self.pagina(caminho)
                listas = [e for e in a.elementos if e["attrs"].get("role") == "tablist"]
                self.assertEqual(len(listas), 1)
                abas = [e for e in a.elementos if e["attrs"].get("role") == "tab"]
                self.assertEqual([" ".join(e["texto"].split()) for e in abas], rotulos)
                paineis = {e["attrs"].get("id"): e for e in a.elementos
                           if e["attrs"].get("role") == "tabpanel"}
                self.assertEqual(len(paineis), len(rotulos))
                selecionadas = [e for e in abas if e["attrs"].get("aria-selected") == "true"]
                self.assertEqual(len(selecionadas), 1)
                self.assertIs(abas[0], selecionadas[0])
                for aba in abas:
                    alvo = aba["attrs"].get("aria-controls")
                    self.assertIn(alvo, paineis)
                    self.assertEqual(paineis[alvo]["attrs"].get("aria-labelledby"),
                                     aba["attrs"].get("id"))
                    self.assertEqual(aba["tag"], "button")

    def test_campos_rotulados_e_ganchos(self):
        ganchos = {
            "/at1": ["sequencias"], "/at2": ["sequencias"], "/at3": ["sequencias"],
            "/at4": ["seq1", "seq2", "metodo", "match", "mismatch", "gap"],
            "/": ["seq1", "seq2", "metodo", "match", "mismatch", "gap"],
        }
        for caminho in PAGINAS:
            with self.subTest(pagina=caminho):
                _, a = self.pagina(caminho)
                rotulos = {e["attrs"].get("for") for e in a.todos("label")}
                for e in a.elementos:
                    if e["tag"] in ("input", "textarea", "select") and \
                            e["attrs"].get("type") != "hidden":
                        self.assertTrue(e["attrs"].get("id") in rotulos
                                        or e["attrs"].get("aria-label"), e)
                for campo in ganchos.get(caminho, []):
                    els = [e for e in a.elementos if e["attrs"].get("data-campo") == campo]
                    self.assertEqual(len(els), 1, campo)
                if caminho in ganchos:
                    self.assertEqual(len(a.todos("button", data_acao="executar")), 1)
                    self.assertEqual(len(a.todos("button", data_acao="exportar")), 1)
                    arquivos = [e for e in a.todos("input") if e["attrs"].get("type") == "file"]
                    self.assertGreaterEqual(len(arquivos), 1)
                    for f in arquivos:
                        self.assertIn(".txt", f["attrs"].get("accept", ""))
                    regioes = [e for e in a.elementos
                               if e["attrs"].get("data-regiao") == "resultados"]
                    self.assertEqual(len(regioes), 1)
        _, a = self.pagina("/at4")
        padroes = {e["attrs"]["data-campo"]: e["attrs"].get("value") for e in a.elementos
                   if e["attrs"].get("data-campo") in ("match", "mismatch", "gap")}
        self.assertEqual(padroes, {"match": "2", "mismatch": "-1", "gap": "-2"})


@unittest.skipUnless(TEM_JINJA, "Jinja2 não instalado (suíte web opcional)")
class TestEstaticos(unittest.TestCase):
    def _css(self):
        return "\n".join(p.read_text(encoding="utf-8") for p in sorted(CSS.rglob("*.css")))

    def _js(self):
        return {p: p.read_text(encoding="utf-8") for p in sorted(JS.rglob("*.js"))}

    def test_css_temas_cores_movimento_foco(self):
        css = self._css()
        blocos = {"escuro": re.search(r":root\s*\{(.*?)\}", css, re.S),
                  "claro": re.search(r'\[data-tema="claro"\]\s*\{(.*?)\}', css, re.S)}
        for tema, m in blocos.items():
            self.assertIsNotNone(m, tema)
            for var in VARIAVEIS:
                self.assertRegex(m.group(1), re.escape(var) + r"\s*:", (tema, var))
        self.assertRegex(css, r"@media\s*\(prefers-reduced-motion:\s*reduce\)")
        self.assertIn(":focus-visible", css)
        self.assertRegex(css, r"@media\s*\(max-width:\s*\d+px\)")
        self.assertRegex(css, r"font-family:[^;]*system-ui")
        self.assertRegex(css, r"font-family:[^;]*ui-monospace")
        self.assertNotRegex(css, r"@font-face")

    def test_js_seguro_e_via_api(self):
        arquivos = self._js()
        self.assertTrue(arquivos)
        tudo = "\n".join(arquivos.values())
        for proibido in (r"\.innerHTML\b", r"\.outerHTML\b", r"insertAdjacentHTML",
                         r"document\.write", r"\beval\s*\(", r"new\s+Function\b",
                         r"setTimeout\s*\(\s*['\"]", r"https?://"):
            self.assertNotRegex(tudo, proibido, proibido)
        for rota in ("/api/at1", "/api/at2", "/api/at3", "/api/at4", "/api/all",
                     "/api/exportar", "/api/exemplos", "/api/at4/celula",
                     "/api/codigo-genetico"):
            self.assertIn(rota, tudo)

    def test_js_sem_regra_biologica(self):
        # O JS apresenta resultados; não carrega tabela genética nem rótulos de
        # diagnóstico próprios (vêm da API), nem implementa a recorrência da AT4.
        tudo = "\n".join(self._js().values())
        for proibido in (r"['\"]UUU['\"]", r"['\"]GCU['\"]", r"BUG - ", r"ERRO - ",
                         r"Math\.max\([^)]*gap", r"['\"]m7Gppp['\"]"):
            self.assertNotRegex(tudo, proibido, proibido)

    def test_templates_por_pagina(self):
        for nome in ("lab", "at1", "at2", "at3", "at4", "casos", "historico", "sobre"):
            self.assertTrue((WEB / "templates" / "paginas" / f"{nome}.html").is_file(), nome)


CHROME = _chrome()


@unittest.skipUnless(TEM_JINJA and CHROME, "Jinja2 ou Chrome/Edge indisponível")
class TestPontaAPonta(Base):
    """Links profundos: ?...&executar=1 preenche, executa via API e mostra o resultado."""

    def dom(self, caminho, params):
        url = f"http://127.0.0.1:{self.porta}{caminho}?{urllib.parse.urlencode(params)}"
        proc = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                               "--no-default-browser-check", "--virtual-time-budget=8000",
                               "--dump-dom", url], capture_output=True, timeout=120)
        dom = proc.stdout.decode("utf-8", "replace")
        self.assertIn("</html>", dom, proc.stderr[-500:])
        i = dom.find('data-regiao="resultados"')
        self.assertGreater(i, 0)
        return dom[i:]

    def test_at1_link_profundo(self):
        r = self.dom("/at1", {"seq": "ATGGCTAAACCGTAA\nATGGCTXAACCGTAA", "executar": "1"})
        self.assertIn("AUGGCUAAACCGUAA", r)
        self.assertIn("CORRETO", r)
        self.assertIn("BUG - base inválida", r)

    def test_at3_link_profundo(self):
        r = self.dom("/at3", {"seq": "m7GpppCCAUGGCUAAACCGUAAGG" + "A" * 100, "executar": "1"})
        self.assertIn("Met-Ala-Lys-Pro", r)

    def test_at4_link_profundo(self):
        r = self.dom("/at4", {"seq1": "ACGTAC", "seq2": "ACGTTC", "metodo": "global",
                              "executar": "1"})
        self.assertRegex(r, r'data-campo="score"[^>]*>\s*9\s*<')
        self.assertIn("ACGTAC", r)

    def test_lab_link_profundo(self):
        r = self.dom("/", {"seq1": SEQ1, "seq2": SEQ2, "executar": "1"})
        self.assertIn("Met-Ala-Lys-Pro", r)
        self.assertIn("Met-Ala-Asn-Pro", r)

    def test_tema_claro_por_parametro(self):
        url = f"http://127.0.0.1:{self.porta}/sobre?tema=claro"
        proc = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
                               "--virtual-time-budget=3000", "--dump-dom", url],
                              capture_output=True, timeout=120)
        self.assertRegex(proc.stdout.decode("utf-8", "replace"), r'<html[^>]*data-tema="claro"')


if __name__ == "__main__":
    unittest.main()
