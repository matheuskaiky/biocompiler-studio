"""OS-M10-15 — Botões com material e abas alinhadas ao conteúdo (pedido do CEO, 2026-11-18).

Pedido: a barra de abas não tinha a largura do cartão logo abaixo (438 px contra 1086 px em
/at3) e encostava nele (0 px de respiro). Os botões tinham cor chapada e "simples"; o CEO pediu
acabamento de designer sênior, como ícones de app do iOS: degradê, sombreamento e reação ao
passar o ponteiro, em todos os botões interativos. Referência de ideias (não de código):
variantes e estados de botão do shadcn/ui. O seletor nativo de arquivo também ficava sem estilo.
Precisão do CEO: o degradê é leve, com cores semelhantes à cor base — nada contrastante.
"""
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, DNA_OK, MRNA_OK  # noqa: E402

from biocompiler.exemplos import ALL_EXEMPLO  # noqa: E402

ESPERA = ("(() => { const s = document.querySelector('[data-regiao=status]');"
          " return !!s && /conclu/i.test(s.textContent); })()")

PAGINAS = [
    ("/", {}),
    ("/", {"seq1": ALL_EXEMPLO[0], "seq2": ALL_EXEMPLO[1], "executar": "1"}),
    ("/at1", {"seq": DNA_OK, "executar": "1"}),
    ("/at3", {}),
    ("/at4", {"seq1": "ACGTAC", "seq2": "ACGTTC", "executar": "1"}),
    ("/casos", {}),
]

# Botões de ação (não glifos de dados, não opções de grupos segmentados/abas).
BOTOES = r"""(() => {
  const dados = '[data-celula],[data-base],[data-codon],[data-aminoacido],[data-marco],[data-passo],svg,[data-fita],[data-matriz]';
  const lista = [];
  document.querySelectorAll('button.btn, a.btn, .btn-icone').forEach((e, i) => {
    if (e.closest(dados)) return;
    const r = e.getBoundingClientRect(), c = getComputedStyle(e);
    if (!r.width || !r.height || c.visibility === 'hidden' || c.display === 'none' || e.disabled) return;
    const sombras = c.boxShadow === 'none' ? [] : c.boxShadow.split(/,(?![^(]*\))/);
    const grads = c.backgroundImage.match(/gradient\((?:[^()]|\([^()]*\))*\)/g) || [];
    let salto = 0, brilho = 0;
    for (const g of grads) {
      const cores = (g.match(/rgba?\([^)]*\)/g) || []).map(x => x.match(/[\d.]+/g).map(Number));
      const opacas = cores.filter(v => (v.length < 4 ? 1 : v[3]) >= 0.9);
      for (const a of opacas) for (const b of opacas)
        salto = Math.max(salto, Math.abs(a[0] - b[0]), Math.abs(a[1] - b[1]), Math.abs(a[2] - b[2]));
      for (const v of cores) if (v.length === 4 && v[3] < 0.9) brilho = Math.max(brilho, v[3]);
    }
    lista.push({id: i, salto, brilho, nome: (e.className + ' "' + (e.textContent || '').trim().slice(0, 18) + '"'),
                gradiente: /gradient\(/.test(c.backgroundImage),
                inset: sombras.filter(s => /inset/.test(s)).length,
                externas: sombras.filter(s => !/inset/.test(s)).length,
                x: r.left + r.width / 2, y: r.top + r.height / 2,
                visivel: r.top >= 0 && r.bottom <= innerHeight});
  });
  return lista;
})()"""

ESTADO = r"""((i) => { const e = document.querySelectorAll('button.btn, a.btn, .btn-icone')[i];
  const c = getComputedStyle(e);
  return [c.backgroundImage, c.boxShadow, c.transform, c.filter, c.backgroundColor].join(' | '); })"""

ABAS = r"""(() => {
  const l = document.querySelector('.abas-lista'); if (!l) return null;
  const p = document.querySelector('[role=tabpanel]:not(.painel-oculto)');
  const a = l.getBoundingClientRect(), b = p.getBoundingClientRect(), c = getComputedStyle(l);
  const interna = a.width - parseFloat(c.paddingLeft) - parseFloat(c.paddingRight);
  const soma = Array.from(l.querySelectorAll('[role=tab]')).reduce((s, t) => s + t.getBoundingClientRect().width, 0);
  return {la: a.left, wa: a.width, lp: b.left, wp: b.width, respiro: b.top - a.bottom, ocupacao: soma / interna};
})()"""


class BaseBotoes(BaseViz):
    def abrir(self, caminho, q, tema="escuro", reduzir=False):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": "reduce" if reduzir else ""}])
        url = (f"http://127.0.0.1:{self.porta}{caminho}?"
               + urllib.parse.urlencode(dict(q, tema=tema, modo="rapido")))
        self.assertTrue(self.nav.abrir(url, 1440, 900, ESPERA if q else "true", prazo=30))
        self.pausa(400)

    def tearDown(self):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": ""}])

    def pairar(self, x, y):
        self.nav.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
        self.pausa(350)

    def sair(self):
        self.nav.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=2, y=898)
        self.pausa(350)


class TestAbasAlinhadas(BaseBotoes):
    def test_barra_de_abas_com_a_largura_do_conteudo_e_respiro(self):
        for caminho, q in PAGINAS:
            if caminho == "/casos":
                continue
            self.abrir(caminho, q)
            m = self.js(ABAS)
            if m is None:
                continue
            with self.subTest(pagina=caminho, executado=bool(q)):
                self.assertLessEqual(abs(m["la"] - m["lp"]), 2, f"abas e painel alinhados à esquerda: {m}")
                self.assertLessEqual(abs(m["wa"] - m["wp"]), 2, f"abas com a largura do painel: {m}")
                self.assertGreaterEqual(m["ocupacao"], 0.9, "as abas preenchem a barra (sem faixa vazia)")
                self.assertTrue(12 <= m["respiro"] <= 32, f"respiro entre abas e painel: {m['respiro']} px")

    def test_seletor_de_metodo_sem_espaco_morto(self):
        self.abrir("/", {})
        m = self.js("""(() => { const g = document.querySelector('[data-segmento-metodo]');
          const gw = g.getBoundingClientRect().width, c = getComputedStyle(g);
          const interna = gw - parseFloat(c.paddingLeft) - parseFloat(c.paddingRight);
          const soma = Array.from(g.querySelectorAll('button')).reduce((s, b) => s + b.getBoundingClientRect().width, 0);
          return soma / interna; })()""")
        self.assertGreaterEqual(m, 0.9, "as opções do seletor de método preenchem o grupo")


class TestBotoesComMaterial(BaseBotoes):
    def test_degrade_brilho_e_sombra_em_todos_os_botoes(self):
        for tema in ("escuro", "claro"):
            for caminho, q in PAGINAS:
                self.abrir(caminho, q, tema)
                for b in self.js(BOTOES):
                    with self.subTest(tema=tema, pagina=caminho, botao=b["nome"]):
                        self.assertTrue(b["gradiente"], "superfície com degradê")
                        self.assertLessEqual(b["salto"], 36, "degradê leve: cores opacas semelhantes entre si")
                        self.assertLessEqual(b["brilho"], 0.3, "camadas de brilho translúcidas e discretas")
                        self.assertGreaterEqual(b["inset"], 1, "brilho interno (borda superior iluminada)")
                        self.assertGreaterEqual(b["externas"], 1, "sombra de elevação")

    def test_botoes_reagem_ao_ponteiro(self):
        for tema in ("escuro", "claro"):
            for caminho, q in (PAGINAS[0], PAGINAS[2], PAGINAS[4]):
                self.abrir(caminho, q, tema)
                vis = [b for b in self.js(BOTOES) if b["visivel"]]
                prim = [b for b in vis if "primario" in b["nome"]][:1]
                for b in prim + [b for b in vis if b not in prim][:3]:
                    self.sair()
                    antes = self.js(f"{ESTADO}({b['id']})")
                    self.pairar(b["x"], b["y"])
                    depois = self.js(f"{ESTADO}({b['id']})")
                    with self.subTest(tema=tema, pagina=caminho, botao=b["nome"]):
                        self.assertNotEqual(antes, depois, "sem reação ao passar o ponteiro")
                self.sair()

    def test_transicao_curta_e_sem_deslocamento_com_movimento_reduzido(self):
        self.abrir("/at3", {})
        t = self.js("""(() => { const c = getComputedStyle(document.querySelector('.btn-primario'));
          return [c.transitionProperty, c.transitionDuration]; })()""")
        self.assertRegex(t[0], r"all|box-shadow|transform|background|filter", "o hover é animado")
        for d in t[1].split(","):
            d = d.strip()
            ms = float(d[:-2]) if d.endswith("ms") else float(d[:-1]) * 1000
            self.assertLessEqual(ms, 300, f"duração do hover: {t[1]}")
        self.abrir("/at3", {}, reduzir=True)
        b = self.js("(() => { const r = document.querySelector('.btn-primario').getBoundingClientRect();"
                    " return [r.left + r.width / 2, r.top + r.height / 2]; })()")
        self.pairar(*b)
        tr = self.js("getComputedStyle(document.querySelector('.btn-primario')).transform")
        self.sair()
        self.assertEqual(tr, "none", "com movimento reduzido o botão não se desloca no hover")

    def test_seletor_de_arquivo_estilizado_como_botao(self):
        for tema in ("escuro", "claro"):
            self.abrir("/at3", {}, tema)
            f = self.js("""(() => { const i = document.querySelector('input[type=file]');
              const c = getComputedStyle(i, '::file-selector-button');
              return {grad: /gradient\\(/.test(c.backgroundImage), raio: parseFloat(c.borderTopLeftRadius) || 0,
                      h: parseFloat(c.height) || (parseFloat(c.fontSize) * 2), sombra: c.boxShadow}; })()""")
            with self.subTest(tema=tema):
                self.assertTrue(f["grad"], "botão de arquivo com o mesmo material dos botões")
                self.assertGreaterEqual(f["raio"], 12, "botão de arquivo em pílula")
                self.assertNotEqual(f["sombra"], "none")


if __name__ == "__main__":
    unittest.main()
