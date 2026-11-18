"""OS-M10-09 — Ribossomo memorável (plano §10.1–§10.3; diretriz do CEO: "uma das animações
mais memoráveis do projeto", forma vetorial estilizada, elegante e reconhecível).

Estrutura testável: duas subunidades preenchidas (maior acima da fita, menor abaixo), a
fita de mRNA passando entre elas, um túnel de saída de onde cada aminoácido novo emerge
antes de se encaixar na cadeia. As garantias de posição e passo (OS-M10-04) continuam.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, MRNA_OK  # noqa: E402

from biocompiler import servicos  # noqa: E402


class TestRibossomo(BaseViz):
    def forma(self):
        return self.js("""(() => {
          const r = document.querySelector('[data-viz=at3] [data-ribossomo]');
          const sub = n => r && r.querySelector(`[data-subunidade=${n}]`);
          const info = e => { if (!e) return null; const q = e.getBoundingClientRect(), c = getComputedStyle(e);
            return {top: q.top, bottom: q.bottom, w: q.width, h: q.height, fill: c.fill,
                    dash: c.strokeDasharray, op: +c.fillOpacity}; };
          const fita = document.querySelector('[data-viz=at3] [data-fita=mrna] [data-base]');
          const fq = fita.getBoundingClientRect();
          return {maior: info(sub('maior')), menor: info(sub('menor')),
                  fita: {top: fq.top, bottom: fq.bottom},
                  tunel: !!(r && r.querySelector('[data-tunel-saida]'))};
        })()""")

    def test_duas_subunidades_preenchidas_envolvendo_a_fita(self):
        self.executar("/at3", {"seq": MRNA_OK, "modo": "rapido"})
        self.pausa(400)
        f = self.forma()
        for nome in ("maior", "menor"):
            s = f[nome]
            with self.subTest(subunidade=nome):
                self.assertIsNotNone(s, f"[data-subunidade={nome}] ausente")
                self.assertNotIn(s["fill"], ("none", "rgba(0, 0, 0, 0)"), "subunidade preenchida")
                self.assertGreater(s["op"], 0.1)
                self.assertIn(s["dash"], ("none", ""), "contorno contínuo, não tracejado")
        self.assertLessEqual(f["maior"]["bottom"], f["fita"]["top"] + 4, "subunidade maior acima da fita")
        self.assertGreaterEqual(f["menor"]["top"], f["fita"]["bottom"] - 4, "subunidade menor abaixo da fita")
        self.assertGreater(f["maior"]["w"] * f["maior"]["h"], f["menor"]["w"] * f["menor"]["h"],
                           "a subunidade maior é maior")
        self.assertTrue(f["tunel"], "túnel de saída [data-tunel-saida]")

    def test_aminoacido_novo_emerge_do_ribossomo(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        self.ir_para(tipos.index("CODON_TRADUZIDO") + 1)
        self.pausa(600)
        self.js("document.querySelector('[data-componente=player] [data-acao=proximo]').click(), true")
        self.pausa(40)
        dist = self.js("""(() => {
          const rib = document.querySelector('[data-viz=at3] [data-tunel-saida]').getBoundingClientRect();
          const aas = document.querySelectorAll('[data-viz=at3] [data-cadeia] [data-aminoacido]');
          const novo = aas[aas.length - 1].getBoundingClientRect();
          const cx = r => r.left + r.width / 2, cy = r => r.top + r.height / 2;
          return Math.hypot(cx(novo) - cx(rib), cy(novo) - cy(rib));
        })()""")
        self.pausa(900)
        dist_fim = self.js("""(() => {
          const rib = document.querySelector('[data-viz=at3] [data-tunel-saida]').getBoundingClientRect();
          const aas = document.querySelectorAll('[data-viz=at3] [data-cadeia] [data-aminoacido]');
          const novo = aas[aas.length - 1].getBoundingClientRect();
          const cx = r => r.left + r.width / 2, cy = r => r.top + r.height / 2;
          return Math.hypot(cx(novo) - cx(rib), cy(novo) - cy(rib));
        })()""")
        self.assertLess(dist, dist_fim - 20,
                        f"o aminoácido nasce perto do túnel ({dist:.0f}px) e depois se encaixa na cadeia ({dist_fim:.0f}px)")

    def test_movimento_reduzido_sem_trajeto(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"}, reduzir_movimento=True)
        self.ir_para(tipos.index("CODON_TRADUZIDO") + 2)
        self.pausa(60)
        rodando = self.js("document.getAnimations().filter(a => a.playState === 'running'"
                          " && a.effect && a.effect.getTiming().duration > 10).length")
        self.assertEqual(rodando, 0)


if __name__ == "__main__":
    unittest.main()
