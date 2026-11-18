"""OS-M10-01 — Fundação visual (D021, docs/FRONTEND_DESIGN_PLAN.md §3, §4, §6).

Tokens nos dois temas, contraste AA medido, ausência de gradientes decorativos,
Liquid Glass seletivo (só em controles, nunca envolvendo dados) com fallback para
transparência reduzida, navegação renomeada, ícones SVG, sem emoji e foco visível.
"""
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, ESPERA  # noqa: E402

ESPERA_LAB = ("(() => { const s = document.querySelector('[data-regiao=status]');"
              " return !!s && /conclu/i.test(s.textContent); })()")

CSS = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "css"
ROTAS = ["/", "/at1", "/at2", "/at3", "/at4", "/casos", "/historico", "/sobre"]
TOKENS = [
    "--fundo", "--superficie", "--superficie-elevada", "--texto", "--texto-secundario",
    "--texto-terciario", "--separador", "--acento",
    "--esp-1", "--esp-2", "--esp-3", "--esp-4", "--esp-6", "--esp-8",
    "--raio-pequeno", "--raio-medio", "--raio-grande", "--raio-pilula",
    "--elevacao-1", "--elevacao-2", "--elevacao-3",
    "--tipo-titulo-grande", "--tipo-titulo", "--tipo-corpo", "--tipo-legenda", "--tipo-dado",
    "--dur-micro", "--dur-curta", "--dur-media", "--dur-longa",
    "--curva-padrao", "--curva-entrada", "--curva-saida",
    "--vidro-fundo", "--vidro-desfoque", "--vidro-borda", "--vidro-fundo-opaco",
    "--cor-dna", "--cor-pre-mrna", "--cor-splicing", "--cor-mrna", "--cor-traducao",
    "--cor-alinhamento", "--cor-erro", "--cor-ok",
    "--base-a", "--base-c", "--base-g", "--base-t", "--base-u",
]
DADOS = "[data-fita], [data-celula], table, canvas[data-matriz], [data-nivel], [data-cadeia]"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✨\U0001F000-\U0001F2FF]")

COR = r"""(v) => { const e = document.createElement('span'); e.style.color = v;
  document.body.appendChild(e); const c = getComputedStyle(e).color; e.remove(); return c; }"""


def rgb(texto):
    m = re.match(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,/\s]+([\d.]+))?", texto)
    if not m:
        raise AssertionError(f"cor não resolvida para sRGB: {texto!r}")
    return [float(m.group(k)) for k in (1, 2, 3)], float(m.group(4) or 1)


def luminancia(c):
    def canal(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(x) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TestTokensEContraste(BaseViz):
    def abrir_pagina(self, caminho, tema="escuro", extra=None):
        q = {"tema": tema}
        q.update(extra or {})
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}{caminho}?"
                                       + urllib.parse.urlencode(q), 1440, 900))

    def token(self, nome):
        return self.js(f"getComputedStyle(document.documentElement).getPropertyValue("
                       f"{nome!r}).trim()")

    def cor(self, nome):
        return rgb(self.js(f"({COR})('var({nome})')"))

    def test_tokens_definidos_nos_dois_temas(self):
        valores = {}
        for tema in ("escuro", "claro"):
            self.abrir_pagina("/", tema)
            valores[tema] = {t: self.token(t) for t in TOKENS}
            faltando = [t for t, v in valores[tema].items() if not v]
            self.assertEqual(faltando, [], f"tema {tema}: tokens ausentes")
        for t in ("--fundo", "--texto", "--superficie", "--vidro-fundo"):
            self.assertNotEqual(valores["escuro"][t], valores["claro"][t], t)

    def test_contraste_aa_dos_tokens(self):
        for tema in ("escuro", "claro"):
            self.abrir_pagina("/", tema)
            for t in ("--fundo", "--superficie", "--texto", "--texto-secundario",
                      "--texto-terciario", "--base-a", "--base-c", "--base-g", "--base-t", "--base-u"):
                self.assertTrue(self.token(t), f"{t} indefinido (contraste não mensurável)")
            fundo, superficie = self.cor("--fundo")[0], self.cor("--superficie")[0]
            for txt, minimo in (("--texto", 7.0), ("--texto-secundario", 4.5),
                                ("--texto-terciario", 3.0)):
                c = self.cor(txt)[0]
                for nome_fundo, f in (("--fundo", fundo), ("--superficie", superficie)):
                    with self.subTest(tema=tema, texto=txt, fundo=nome_fundo):
                        self.assertGreaterEqual(round(contraste(c, f), 2), minimo)
            for base in ("--base-a", "--base-c", "--base-g", "--base-t", "--base-u"):
                with self.subTest(tema=tema, base=base):
                    self.assertGreaterEqual(round(contraste(self.cor(base)[0], superficie), 2),
                                            3.0, "cor de base precisa ser distinguível (≥ 3:1)")


class TestSuperficies(BaseViz):
    def test_sem_gradientes_decorativos(self):
        for arq in CSS.glob("*.css"):
            if arq.name == "vidro.css":
                continue
            with self.subTest(arquivo=arq.name):
                self.assertNotRegex(arq.read_text(encoding="utf-8"), r"(?:linear|radial|conic)-gradient\(",
                                    "gradientes só no realce do material de vidro (vidro.css)")

    def test_fallback_estatico_do_vidro(self):
        vidro = (CSS / "vidro.css").read_text(encoding="utf-8")
        self.assertRegex(vidro, r"@supports\s+not\s*\(\s*(?:-webkit-)?backdrop-filter")
        self.assertIn("prefers-reduced-transparency", vidro)

    def _paginas_com_dados(self):
        yield "/at1", {"seq": "CCATGGCTAAACCGTAAGG", "executar": "1", "modo": "rapido"}
        yield "/at4", {"seq1": "ACGTAC", "seq2": "ACGTTC", "executar": "1", "modo": "rapido"}
        yield "/", {"seq1": "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG",
                    "seq2": "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG", "executar": "1"}

    def _medir(self):
        return self.js(f"""(() => {{
          const todos = Array.from(document.querySelectorAll('body *'));
          const comBlur = todos.filter(e => {{ const b = getComputedStyle(e).backdropFilter ||
             getComputedStyle(e).webkitBackdropFilter || 'none'; return b !== 'none'; }});
          const vidros = Array.from(document.querySelectorAll('[data-superficie=vidro]'));
          return {{
            semMarca: comBlur.filter(e => e.getAttribute('data-superficie') !== 'vidro')
              .map(e => e.tagName + '.' + e.className).slice(0, 5),
            envolveDados: vidros.filter(v => v.querySelector({DADOS!r}))
              .map(e => e.tagName + '.' + e.className).slice(0, 5),
            dentroDeDados: vidros.filter(v => v.parentElement && v.parentElement.closest({DADOS!r}))
              .map(e => e.tagName + '.' + e.className).slice(0, 5),
            cabecalho: (() => {{ const h = document.querySelector('header');
              return h ? [h.getAttribute('data-superficie'), getComputedStyle(h).backdropFilter] : null; }})(),
            player: (() => {{ const p = document.querySelector('[data-componente=player]');
              return p ? [p.getAttribute('data-superficie'), getComputedStyle(p).backdropFilter] : null; }})(),
            vidros: vidros.map(v => [getComputedStyle(v).backdropFilter, getComputedStyle(v).backgroundColor]),
          }};
        }})()""")

    def test_vidro_seletivo(self):
        for caminho, q in self._paginas_com_dados():
            url = f"http://127.0.0.1:{self.porta}{caminho}?" + urllib.parse.urlencode(q)
            self.nav.cmd("Emulation.setEmulatedMedia", features=[
                {"name": "prefers-reduced-transparency", "value": ""}])
            self.assertTrue(self.nav.abrir(url, 1440, 900, ESPERA_LAB if caminho == "/" else ESPERA))
            if caminho != "/":
                self.aba("Visualização")
            self.pausa(500)
            m = self._medir()
            with self.subTest(pagina=caminho):
                self.assertEqual(m["semMarca"], [], "desfoque só em [data-superficie=vidro]")
                self.assertEqual(m["envolveDados"], [], "vidro não pode envolver fitas/matrizes/tabelas")
                self.assertEqual(m["dentroDeDados"], [], "vidro não pode ficar dentro de áreas de dados")
                self.assertEqual(m["cabecalho"][0], "vidro", "barra superior é de vidro")
                self.assertIn("blur", m["cabecalho"][1])

    def test_transparencia_reduzida_vira_opaco(self):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-transparency", "value": "reduce"}])
        try:
            for caminho, q in self._paginas_com_dados():
                url = f"http://127.0.0.1:{self.porta}{caminho}?" + urllib.parse.urlencode(q)
                self.assertTrue(self.nav.abrir(url, 1440, 900,
                                               ESPERA_LAB if caminho == "/" else ESPERA))
                self.pausa(400)
                vidros = self._medir()["vidros"]
                self.assertGreaterEqual(len(vidros), 1, "a barra superior deve existir como vidro")
                for blur, fundo in vidros:
                    with self.subTest(pagina=caminho):
                        self.assertEqual(blur, "none")
                        self.assertEqual(rgb(fundo)[1], 1.0, "fundo opaco com transparência reduzida")
        finally:
            self.nav.cmd("Emulation.setEmulatedMedia", features=[
                {"name": "prefers-reduced-transparency", "value": ""}])


class TestNavegacaoEIcones(BaseViz):
    def test_nomes_da_navegacao(self):
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/", 1440, 900))
        nav = self.texto("nav[aria-label='Navegação principal']")
        for nome in ("Laboratório Completo", "BioCompiler 1.0", "BioCompiler 2.0", "Ribossomo",
                     "Alinhamento", "Casos de Teste", "Histórico", "Sobre"):
            self.assertIn(nome, nav)
        link = self.js("(() => { const a = Array.from(document.querySelectorAll("
                       "\"nav[aria-label='Navegação principal'] a\")).find(x => /Comparador molecular/"
                       ".test(x.textContent)); return a ? a.getAttribute('href') : null; })()")
        self.assertIsNotNone(link, "item 'Comparador molecular' na navegação")
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}{link}", 1440, 900))
        self.pausa(400)
        self.assertEqual(self.js("(document.querySelector('[role=tab][aria-selected=true]') || {})"
                                 ".textContent.trim()"), "Comparador molecular")

    def test_sem_emoji_em_nenhuma_pagina(self):
        for caminho in ROTAS:
            self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}{caminho}", 1440, 900))
            texto = self.js("document.body.innerText")
            with self.subTest(pagina=caminho):
                self.assertIsNone(EMOJI.search(texto), EMOJI.findall(texto)[:5])

    def test_foco_visivel_e_tipografia(self):
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/at1", 1440, 900))
        self.js("document.activeElement && document.activeElement.blur(), true")
        for _ in range(4):
            for tipo in ("rawKeyDown", "keyUp"):
                self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key="Tab", code="Tab",
                             windowsVirtualKeyCode=9)
            self.pausa(120)
            f = self.js("(() => { const e = document.activeElement, c = getComputedStyle(e);"
                        " return [e.tagName, c.outlineStyle, c.outlineWidth, c.boxShadow]; })()")
            with self.subTest(foco=f[0]):
                self.assertTrue((f[1] != "none" and f[2] != "0px") or f[3] != "none",
                                f"foco sem indicador visível: {f}")
        tipo = self.js("[getComputedStyle(document.body).fontFamily,"
                       " parseFloat(getComputedStyle(document.querySelector('h1')).fontSize)]")
        self.assertRegex(tipo[0], r"system-ui|-apple-system")
        self.assertGreaterEqual(tipo[1], 26)


if __name__ == "__main__":
    unittest.main()
