"""OS-M10-07 — Polimento do Laboratório (entrada) e extras da AT4 (plano §6, §11).

- "Montar experimento": importação por zona de soltar com botão próprio acessível (sem o
  botão nativo de arquivo visível), seletor de método segmentado e exemplo a um clique.
- AT4: arraste (pan) da área matricial e vista lado a lado Local × Global coordenada.
"""
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz  # noqa: E402

from biocompiler import servicos  # noqa: E402
from biocompiler.exemplos import ALL_EXEMPLO  # noqa: E402


class TestMontarExperimento(BaseViz):
    def abrir_lab(self):
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/?tema=escuro", 1440, 900))
        self.pausa(400)

    def test_importacao_com_controle_proprio_e_zona_de_soltar(self):
        self.abrir_lab()
        nativo = self.js("(() => { const i = document.querySelector('#painel-montar input[type=file]');"
                         " if (!i) return null; const r = i.getBoundingClientRect(), c = getComputedStyle(i);"
                         " return {w: r.width, h: r.height, op: +c.opacity, clip: c.clipPath}; })()")
        self.assertIsNotNone(nativo, "o input de arquivo continua existindo (acessível)")
        self.assertTrue(nativo["w"] <= 1 or nativo["op"] == 0 or nativo["clip"] not in ("none", ""),
                        "o botão nativo do navegador não fica visível")
        botao = self.js("(() => { const b = document.querySelector('#painel-montar [data-acao=importar]');"
                        " return b ? [b.tagName, b.tabIndex, (b.getAttribute('aria-label') || b.textContent).trim()] : null; })()")
        self.assertIsNotNone(botao, "botão próprio [data-acao=importar]")
        self.assertGreaterEqual(botao[1], 0)
        self.assertTrue(botao[2])
        self.assertTrue(self.js("!!document.querySelector('#painel-montar [data-zona-soltar]')"),
                        "zona de soltar arquivo")

    def test_soltar_arquivo_preenche_as_duas_sequencias(self):
        self.abrir_lab()
        conteudo = ">s1\\n" + ALL_EXEMPLO[0] + "\\n>s2\\n" + ALL_EXEMPLO[1] + "\\n"
        self.js("(() => { const z = document.querySelector('#painel-montar [data-zona-soltar]');"
                f" const f = new File([{conteudo!r}], 'par.fasta', {{type: 'text/plain'}});"
                " const dt = new DataTransfer(); dt.items.add(f);"
                " z.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true}));"
                " return true; })()")
        for _ in range(20):
            self.pausa(150)
            v = self.js("[document.querySelector('[data-campo=seq1]').value.trim(),"
                        " document.querySelector('[data-campo=seq2]').value.trim()]")
            if v[0]:
                break
        self.assertEqual(v, [ALL_EXEMPLO[0], ALL_EXEMPLO[1]])

    def test_metodo_segmentado_sincronizado(self):
        self.abrir_lab()
        opcoes = self.js("Array.from(document.querySelectorAll('#painel-montar [data-segmento-metodo] "
                         "[data-valor]')).map(b => b.getAttribute('data-valor'))")
        self.assertEqual(opcoes, ["local", "global", "both"])
        self.js("document.querySelector('#painel-montar [data-segmento-metodo] [data-valor=global]').click(), true")
        self.pausa(150)
        self.assertEqual(self.js("document.querySelector('[data-campo=metodo]').value"), "global",
                         "o segmentado atualiza o campo [data-campo=metodo] usado pela execução")


class TestAT4Extras(BaseViz):
    def abrir_at4(self, a, b, metodo="both"):
        self.executar("/at4", {"seq1": a, "seq2": b, "metodo": metodo, "modo": "rapido"})

    def test_arraste_desloca_a_area_matricial(self):
        import random
        rnd = random.Random(9)
        a = "".join(rnd.choice("ACGT") for _ in range(60))
        b = "".join(rnd.choice("ACGT") for _ in range(60))
        self.abrir_at4(a, b, "global")
        caixa = self.js("(() => { const s = document.querySelector('[data-viz=at4] .matriz-scroll');"
                        " const r = s.getBoundingClientRect(); return [r.left, r.top, r.width, r.height,"
                        " s.scrollLeft, s.scrollWidth > s.clientWidth]; })()")
        x, y, w, h, sl0, transborda = caixa
        self.assertTrue(transborda, "a matriz 61×61 transborda a área visível")
        cx, cy = x + w * 0.6, y + h * 0.6
        self.nav.cmd("Input.dispatchMouseEvent", type="mousePressed", x=cx, y=cy, button="left",
                     clickCount=1)
        for k in range(1, 6):
            self.nav.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=cx - 40 * k, y=cy,
                         button="left")
        self.nav.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=cx - 200, y=cy,
                     button="left", clickCount=1)
        self.pausa(200)
        sl1 = self.js("document.querySelector('[data-viz=at4] .matriz-scroll').scrollLeft")
        self.assertGreater(sl1, sl0 + 100, "arrastar para a esquerda rola a matriz para a direita")

    def test_vista_lado_a_lado_coordenada(self):
        rl = servicos.alinhar_par("ACGTAC", "ACGTTC", "local", 2, -1, -2)[0]
        rg = servicos.alinhar_par("ACGTAC", "ACGTTC", "global", 2, -1, -2)[0]
        self.abrir_at4("ACGTAC", "ACGTTC")
        self.js("document.querySelector('[data-viz=at4] [data-acao=lado-a-lado]').click(), true")
        self.pausa(500)
        grades = self.js("Array.from(document.querySelectorAll('[data-viz=at4] [data-grade-metodo]'))"
                         ".map(g => [g.getAttribute('data-grade-metodo'), Array.from(g.querySelectorAll("
                         "'[data-celula]')).map(c => c.textContent.trim().split(/\\s+/)[0])])")
        self.assertEqual([g[0] for g in grades], ["local", "global"])
        self.assertEqual(grades[0][1], [str(v) for linha in rl.matriz for v in linha])
        self.assertEqual(grades[1][1], [str(v) for linha in rg.matriz for v in linha])
        # inspeção coordenada: selecionar (3,4) numa grade destaca (3,4) na outra
        self.js("document.querySelector('[data-viz=at4] [data-grade-metodo=local] [data-celula]"
                "[data-i=\"3\"][data-j=\"4\"]').dispatchEvent(new MouseEvent('click', {bubbles: true})), true")
        self.pausa(400)
        sel = self.js("Array.from(document.querySelectorAll('[data-viz=at4] [data-grade-metodo] "
                      "[data-celula][data-coordenada-ativa]')).map(c => [c.closest('[data-grade-metodo]')"
                      ".getAttribute('data-grade-metodo'), c.getAttribute('data-i'), c.getAttribute('data-j')])")
        self.assertEqual(sorted(sel), [["global", "3", "4"], ["local", "3", "4"]])

    def test_lado_a_lado_indisponivel_acima_do_limite(self):
        """Premissa da OS: acima de 10 000 células por método, avisar (laudo A1, R1)."""
        a = "ACGT" * 25  # 101 × 101 = 10 201 células por método
        self.executar("/at4", {"seq1": a, "seq2": a, "metodo": "both", "modo": "rapido"}, prazo=90)
        for _ in range(20):
            aviso = self.js("(() => { const e = document.querySelector('[data-viz=at4] [data-aviso=lado-a-lado]');"
                            " if (!e) return null; const r = e.getBoundingClientRect();"
                            " return [r.width > 0 && r.height > 0, e.textContent]; })()")
            if aviso:
                break
            self.pausa(150)
        self.assertIsNotNone(aviso, "aviso [data-aviso=lado-a-lado] ausente acima do limite")
        self.assertTrue(aviso[0], "aviso visível")
        self.assertIn("lado a lado", aviso[1].lower())
        self.assertRegex(aviso[1], r"10[\s.  ]?000", "o aviso informa o limite")
        self.assertEqual(self.js("document.querySelectorAll('[data-viz=at4] [data-grade-metodo]').length"), 0,
                         "nenhuma grade lado a lado é montada acima do limite")
        botao = self.js("(() => { const b = document.querySelector('[data-viz=at4] [data-acao=lado-a-lado]');"
                        " return b ? b.disabled || b.getAttribute('aria-disabled') === 'true' : null; })()")
        self.assertIn(botao, (None, True), "se o botão existir, fica desabilitado")


if __name__ == "__main__":
    unittest.main()
