"""OS-M10-14 — Padronização dos controles em pílula e composição menos genérica
(pedido do CEO e revisão visual do CTO em 2026-11-18; D023).

Achados medidos antes da OS (inventário CDP): botões, abas, opções de modo e campos
"arredondados" (raio de cartão) convivendo com chips/selos em pílula e botões circulares;
cartões dentro de cartões nas abas Resultados/Entrada e nas páginas Casos/Sobre; faixas
coloridas decorativas no topo de cartões; bordas tracejadas em painéis; barra de status
ocupando a largura toda mesmo sem nada a dizer.
"""
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, DNA_OK, MRNA_OK, PRE_OK  # noqa: E402

from biocompiler.exemplos import ALL_EXEMPLO  # noqa: E402

ESPERA = ("(() => { const s = document.querySelector('[data-regiao=status]');"
          " return !!s && /conclu/i.test(s.textContent); })()")

PAGINAS = [
    ("/", {"seq1": ALL_EXEMPLO[0], "seq2": ALL_EXEMPLO[1], "executar": "1"}),
    ("/at1", {"seq": DNA_OK, "executar": "1"}), ("/at2", {"seq": PRE_OK, "executar": "1"}),
    ("/at3", {"seq": MRNA_OK, "executar": "1"}),
    ("/at4", {"seq1": "ACGTAC", "seq2": "ACGTTC", "executar": "1"}),
    ("/casos", {}), ("/historico", {}), ("/sobre", {}),
]

# Controles interativos e marcadores curtos. Ficam de fora: glifos de dados (bases, células,
# códons, aminoácidos, marcos da linha do tempo), textareas, sliders e itens altos de lista.
FORMAS = r"""(() => {
  const dados = '[data-celula],[data-base],[data-codon],[data-aminoacido],[data-marco],[data-passo],svg,.celula-btn,[data-fita],[data-matriz]';
  const sel = 'button, a.btn, [role=tab], [role=radio], .chip, .selo, select, '
            + 'input[type=text], input[type=number], input[type=search], input:not([type]), '
            + '[role=tablist], [role=radiogroup], .modo-segmentado, [data-segmento-metodo]';
  const fora = [];
  for (const e of document.querySelectorAll(sel)) {
    if (e.closest(dados)) continue;
    const r = e.getBoundingClientRect(), c = getComputedStyle(e);
    if (!r.width || !r.height || c.visibility === 'hidden' || r.height > 64) continue;
    if (c.opacity === '0' || (r.width <= 2 && r.height <= 2)) continue;
    const rad = Math.min(parseFloat(c.borderTopLeftRadius) || 0, parseFloat(c.borderBottomRightRadius) || 0);
    if (rad < r.height / 2 - 1) fora.push(`${e.tagName}.${String(e.className).split(' ')[0]} "${(e.textContent || e.value || '').trim().slice(0, 14)}" r=${rad} h=${Math.round(r.height)}`);
  }
  return fora;
})()"""

DECORACAO = r"""(() => {
  const main = document.querySelector('main'), ruins = [];
  for (const e of main.querySelectorAll('*')) {
    if (e.offsetParent === null) continue;
    const c = getComputedStyle(e), r = e.getBoundingClientRect();
    if (r.width < 120 || r.height < 40) continue;
    const t = parseFloat(c.borderTopWidth), l = parseFloat(c.borderLeftWidth);
    if (t >= 2 && t > l && c.borderTopColor !== c.borderLeftColor) ruins.push('faixa: ' + e.tagName + '.' + e.className);
    // Separador solto: o primeiro item visível de um grupo não leva linha acima.
    const ant = e.previousElementSibling;
    if (t >= 1 && c.borderTopStyle === 'solid' && l === 0 && (!ant || ant.offsetParent === null) && e.parentElement.closest('[role=tabpanel]'))
      ruins.push('separador solto: ' + e.tagName + '.' + e.className);
    // Estado vazio só é exceção enquanto está vazio de fato (sem elementos filhos).
    const vazioReal = e.matches('.vazio') && e.children.length === 0;
    if ([c.borderTopStyle, c.borderLeftStyle].some(x => x === 'dashed' || x === 'dotted') && !e.matches('[data-zona-soltar], .zona-arquivo') && !vazioReal)
      ruins.push('tracejado: ' + e.tagName + '.' + e.className);
  }
  return ruins;
})()"""


# Mesmo critério de cartão do test_refinamento (raio ≥ 10, fundo ou borda, > 200×80), mas
# campos de formulário, estados vazios, zonas de soltar e blocos de alinhamento (<pre>) não
# são cartões: são controles ou áreas de dados.
CARTOES = r"""(() => {
 const cartao = e => { if (e.matches('textarea, input, select, pre, .vazio, [data-zona-soltar], .zona-arquivo')) return false;
   const c = getComputedStyle(e), r = parseFloat(c.borderTopLeftRadius) || 0;
   const bg = c.backgroundColor, fundo = bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg);
   const b = e.getBoundingClientRect();
   return r >= 10 && (fundo || parseFloat(c.borderTopWidth) > 0) && b.width > 200 && b.height > 80; };
 const main = document.querySelector('main');
 const dados = '[data-fita], [data-celula], .matriz-scroll, .fita-scroll, canvas, table, [data-componente=player], dialog';
 const cs = Array.from(main.querySelectorAll('*')).filter(e => e.offsetParent !== null && cartao(e) && !e.closest(dados));
 return cs.filter(e => { for (let a = e.parentElement; a && a !== main; a = a.parentElement) if (cartao(a)) return true; return false; })
   .map(e => e.tagName + '.' + e.className);
})()"""


class BasePadrao(BaseViz):
    def abrir(self, caminho, q, tema="escuro"):
        url = (f"http://127.0.0.1:{self.porta}{caminho}?"
               + urllib.parse.urlencode(dict(q, tema=tema, modo="rapido")))
        self.assertTrue(self.nav.abrir(url, 1440, 900, ESPERA if q else "true", prazo=30))
        self.pausa(400)

    def abas(self):
        return self.js("Array.from(document.querySelectorAll('[role=tab]')).map(t => t.textContent.trim())")

    def em_cada_aba(self, caminho, q, medir):
        self.abrir(caminho, q)
        abas = self.abas() or [None]
        for aba in abas:
            if aba:
                self.aba(aba)
                self.pausa(250)
            yield aba, self.js(medir)


class TestControlesEmPilula(BasePadrao):
    def test_controles_interativos_em_pilula_em_todas_as_paginas_e_abas(self):
        for caminho, q in PAGINAS:
            for aba, fora in self.em_cada_aba(caminho, q, FORMAS):
                with self.subTest(pagina=caminho, aba=aba):
                    self.assertEqual(fora, [], "controle fora do formato pílula (raio ≥ altura/2)")


class TestComposicaoSemGenericos(BasePadrao):
    def test_sem_cartao_dentro_de_cartao_em_nenhuma_aba(self):
        for caminho, q in PAGINAS:
            for aba, aninhados in self.em_cada_aba(caminho, q, CARTOES):
                with self.subTest(pagina=caminho, aba=aba):
                    self.assertLessEqual(len(aninhados), 1, f"cartões aninhados: {aninhados}")

    def test_sem_faixas_decorativas_nem_paineis_tracejados(self):
        for caminho, q in PAGINAS:
            for aba, ruins in self.em_cada_aba(caminho, q, DECORACAO):
                with self.subTest(pagina=caminho, aba=aba):
                    self.assertEqual(ruins, [])

    def test_status_compacto_fora_do_fluxo(self):
        for caminho, q in (PAGINAS[1], PAGINAS[7]):
            self.abrir(caminho, q)
            s = self.js("""(() => { const e = document.querySelector('[data-regiao=status]');
              const r = e.getBoundingClientRect(), c = getComputedStyle(e);
              const main = document.querySelector('main').getBoundingClientRect();
              return {w: r.width, h: r.height, wmain: main.width, pos: c.position,
                      live: e.getAttribute('aria-live'), rad: parseFloat(c.borderTopLeftRadius) || 0}; })()""")
            with self.subTest(pagina=caminho):
                self.assertEqual(s["live"], "polite", "a região continua anunciando o status")
                self.assertIn(s["pos"], ("fixed", "sticky", "absolute"),
                              "o status não empurra o conteúdo (fora do fluxo)")
                self.assertLessEqual(s["w"], min(520, s["wmain"] * 0.6), "status compacto, não uma faixa")
                self.assertGreaterEqual(s["rad"], s["h"] / 2 - 1, "status em pílula")


if __name__ == "__main__":
    unittest.main()
