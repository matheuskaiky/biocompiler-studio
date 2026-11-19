"""OS-M10-06 — Refinamento (fases 6+7): contraste real, composição sem cartões aninhados,
tablet e desempenho medido (plano §13, §14, §16).

Linhas de base medidas pelo CTO às 11:55 (antes da OS):
- contraste: selos OK/erro no tema claro (3,81 e 4,33:1), células do mapa de calor da AT4
  no claro (1,24:1 medido), botão "Enviar para…" (2,38:1);
- cartões aninhados: AT1 4, AT4 5, Laboratório 9;
- 820 px: sem rolagem horizontal; reprodução a 4×: p95 de 16,8 ms por quadro.
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
    ("/", {"seq1": ALL_EXEMPLO[0], "seq2": ALL_EXEMPLO[1], "executar": "1"}, "Mapa da expressão gênica"),
    ("/at1", {"seq": DNA_OK, "executar": "1"}, "Visualização"),
    ("/at2", {"seq": PRE_OK, "executar": "1"}, "Visualização"),
    ("/at3", {"seq": MRNA_OK, "executar": "1"}, "Visualização"),
    ("/at4", {"seq1": "ACGTAC", "seq2": "ACGTTC", "executar": "1"}, "Visualização"),
    ("/casos", {}, None), ("/historico", {}, None), ("/sobre", {}, None),
]

CONTRASTE = r"""(() => {
 // color-mix() é serializado como color(srgb r g b [/ a]) com canais em 0–1: converter para 0–255.
 const rgb = s => { const m = s.match(/[\d.]+/g); if (!m) return null; const v = m.map(Number);
   return /^color\(srgb/.test(s) ? v.map((x, i) => i < 3 ? x * 255 : x) : v; };
 const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
   return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2]); };
 const fundo = e => { for (let a = e; a; a = a.parentElement) { const c = rgb(getComputedStyle(a).backgroundColor);
   if (c && (c.length < 4 || c[3] > .9)) return c; } return rgb(getComputedStyle(document.body).backgroundColor); };
 const ruins = [];
 const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
 while (w.nextNode()) {
   const t = w.currentNode, e = t.parentElement;
   if (!e || !t.textContent.trim() || e.offsetParent === null || e.closest('svg,[aria-hidden=true],.pular-conteudo')) continue;
   const c = getComputedStyle(e); if (+c.opacity < .5 || c.visibility === 'hidden') continue;
   const fg = rgb(c.color), bg = fundo(e), l1 = lum(fg), l2 = lum(bg);
   const cr = (Math.max(l1, l2) + .05) / (Math.min(l1, l2) + .05);
   const tam = parseFloat(c.fontSize), grande = tam >= 24 || (tam >= 18.66 && +c.fontWeight >= 700);
   if (cr < (grande ? 3 : 4.5)) ruins.push(e.tagName + '.' + e.className + ' "' + t.textContent.trim().slice(0, 18) + '" ' + cr.toFixed(2));
 }
 return ruins;
})()"""

CARTOES = r"""(() => {
 const cartao = e => { const c = getComputedStyle(e), r = parseFloat(c.borderTopLeftRadius) || 0;
   const bg = c.backgroundColor, fundo = bg && !/rgba\(0, 0, 0, 0\)|transparent/.test(bg);
   const b = e.getBoundingClientRect();
   return r >= 10 && (fundo || parseFloat(c.borderTopWidth) > 0) && b.width > 200 && b.height > 80; };
 const main = document.querySelector('main');
 const dados = '[data-fita], [data-celula], .matriz-scroll, .fita-scroll, canvas, table, [data-componente=player], dialog';
 const cs = Array.from(main.querySelectorAll('*')).filter(e => e.offsetParent !== null && cartao(e) && !e.closest(dados));
 return cs.filter(e => { for (let a = e.parentElement; a && a !== main; a = a.parentElement) if (cartao(a)) return true; return false; })
   .map(e => e.tagName + '.' + e.className);
})()"""


class BaseRefino(BaseViz):
    def abrir(self, caminho, q, aba, tema, largura=1440, altura=900):
        url = (f"http://127.0.0.1:{self.porta}{caminho}?"
               + urllib.parse.urlencode(dict(q, tema=tema, modo="rapido")))
        self.assertTrue(self.nav.abrir(url, largura, altura, ESPERA if q else "true", prazo=30))
        if aba:
            self.aba(aba)
        self.pausa(500)


class TestContrasteReal(BaseRefino):
    def test_texto_visivel_aa_em_todas_as_paginas_e_temas(self):
        for tema in ("escuro", "claro"):
            for caminho, q, aba in PAGINAS:
                self.abrir(caminho, q, aba, tema)
                with self.subTest(tema=tema, pagina=caminho):
                    ruins = self.js(CONTRASTE)
                    self.assertEqual(ruins, [], "texto visível abaixo de AA (4,5:1; 3:1 se grande)")


class TestComposicao(BaseRefino):
    def test_sem_cartao_dentro_de_cartao(self):
        for caminho, q, aba in PAGINAS[:5]:
            self.abrir(caminho, q, aba, "escuro")
            with self.subTest(pagina=caminho):
                aninhados = self.js(CARTOES)
                self.assertLessEqual(len(aninhados), 1,
                                     f"no máximo 1 cartão aninhado fora das áreas de dados: {aninhados}")


class TestTabletEDesempenho(BaseRefino):
    def test_tablet_820_sem_rolagem_horizontal(self):
        for caminho, q, aba in PAGINAS:
            self.abrir(caminho, q, aba, "claro", 820, 1180)
            with self.subTest(pagina=caminho):
                sw = self.js("[document.documentElement.scrollWidth, innerWidth]")
                self.assertLessEqual(sw[0], sw[1])

    def test_quadros_durante_reproducao_animada(self):
        for caminho, q in (("/at3", {"seq": MRNA_OK, "executar": "1"}),
                           ("/at4", {"seq1": "ACGTAC", "seq2": "ACGTTC", "executar": "1"})):
            url = (f"http://127.0.0.1:{self.porta}{caminho}?"
                   + urllib.parse.urlencode(dict(q, modo="guiado")))
            self.assertTrue(self.nav.abrir(url, 1440, 900, ESPERA, prazo=30))
            self.aba("Visualização")
            self.js("(() => { const s = document.querySelector('[data-componente=player] "
                    "select[data-campo=velocidade]'); if (s) { s.value = '4';"
                    " s.dispatchEvent(new Event('change', {bubbles: true})); }"
                    " window.__q = []; let t0 = performance.now();"
                    " const f = t => { window.__q.push(t - t0); t0 = t;"
                    " if (window.__q.length < 150) requestAnimationFrame(f); };"
                    " requestAnimationFrame(f); document.querySelector('[data-componente=player] "
                    "[data-acao=reproduzir]').click(); return true; })()")
            self.pausa(3500)
            m = self.js("(() => { const q = window.__q.slice(5).sort((a, b) => a - b);"
                        " return {n: q.length, p95: q[Math.floor(q.length * .95)]}; })()")
            with self.subTest(pagina=caminho):
                self.assertGreaterEqual(m["n"], 100)
                self.assertLessEqual(m["p95"], 34, f"p95 de quadro acima de 34 ms: {m}")


if __name__ == "__main__":
    unittest.main()
