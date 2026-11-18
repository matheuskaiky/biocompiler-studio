"""OS-M10-02 — Motor de reprodução e componentes científicos (Frente B; plano §5, §7, §10).

Player em vidro com ícones SVG, linha do tempo arrastável e acessível (slider) com
marcos por tipo de evento, cancelamento imediato de animações e seleção sincronizada
aminoácido ↔ códon na AT3 (barramento de estado + conexão SVG).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, DNA_LONGO, DNA_OK, MRNA_OK  # noqa: E402

from biocompiler import servicos  # noqa: E402

LINHA = "[data-componente=player] [data-componente=linha-tempo]"


class TestPlayerVidro(BaseViz):
    def test_player_em_vidro_com_icones_svg(self):
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        p = self.js("(() => { const p = document.querySelector('[data-componente=player]');"
                    " return [p.getAttribute('data-superficie'), getComputedStyle(p).backdropFilter]; })()")
        self.assertEqual(p[0], "vidro")
        self.assertIn("blur", p[1])
        botoes = self.js("Array.from(document.querySelectorAll('[data-componente=player] button'))"
                         ".map(b => [b.getAttribute('data-acao'), !!b.querySelector('svg'),"
                         " (b.getAttribute('aria-label') || '').trim()])")
        for acao in ("inicio", "anterior", "reproduzir", "proximo", "fim"):
            item = [b for b in botoes if b[0] == acao]
            with self.subTest(acao=acao):
                self.assertTrue(item and item[0][1], "ícone SVG")
                self.assertTrue(item[0][2], "aria-label")
        icone = ("document.querySelector('[data-componente=player] [data-acao=reproduzir] svg')"
                 ".getAttribute('data-icone')")
        antes = self.js(icone)
        self.clicar("reproduzir")
        self.assertNotEqual(self.js(icone), antes, "o ícone alterna entre reproduzir e pausar")
        self.clicar("reproduzir")


class TestLinhaDoTempo(BaseViz):
    def estado_linha(self):
        return self.js(f"(() => {{ const s = document.querySelector({LINHA!r});"
                       " return s && [s.getAttribute('role'), +s.getAttribute('aria-valuemin'),"
                       " +s.getAttribute('aria-valuemax'), +s.getAttribute('aria-valuenow'),"
                       " s.tabIndex]; })()")

    def test_slider_acessivel_sincronizado(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        n = len(r.eventos)
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        self.assertEqual(self.estado_linha(), ["slider", 1, n, 1, 0])
        self.clicar("proximo")
        self.assertEqual(self.estado_linha()[3], 2)
        self.js(f"document.querySelector({LINHA!r}).focus(), true")
        for tecla, esperado in (("ArrowRight", 3), ("End", n), ("Home", 1)):
            self.tecla(tecla)
            self.assertEqual(self.estado()["k"], esperado, tecla)
            self.assertEqual(self.estado_linha()[3], esperado)

    def test_clique_e_arraste_levam_ao_passo(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        n = len(r.eventos)
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        caixa = self.js(f"(() => {{ const q = document.querySelector({LINHA!r})"
                        ".getBoundingClientRect(); return [q.left, q.top, q.width, q.height]; })()")
        x0, y0, w, h = caixa
        alvo_x = x0 + w * 0.75
        self.nav.cmd("Input.dispatchMouseEvent", type="mousePressed", x=alvo_x, y=y0 + h / 2,
                     button="left", clickCount=1)
        self.nav.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=alvo_x, y=y0 + h / 2,
                     button="left", clickCount=1)
        self.pausa(250)
        k = self.estado()["k"]
        esperado = 1 + round(0.75 * (n - 1))
        self.assertLessEqual(abs(k - esperado), 1, f"clique a 75%: k={k}, esperado≈{esperado}")
        # arrastar do início até perto do fim
        self.nav.cmd("Input.dispatchMouseEvent", type="mousePressed", x=x0 + 1, y=y0 + h / 2,
                     button="left", clickCount=1)
        for f in (0.3, 0.6, 0.98):
            self.nav.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=x0 + w * f,
                         y=y0 + h / 2, button="left")
        self.nav.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=x0 + w * 0.98,
                     y=y0 + h / 2, button="left", clickCount=1)
        self.pausa(250)
        self.assertGreaterEqual(self.estado()["k"], n - 1)

    def test_marcos_por_tipo_de_evento(self):
        for caminho, at, seq in (("/at1", "at1", DNA_OK), ("/at3", "at3", MRNA_OK),
                                 ("/at1", "at1", DNA_LONGO)):
            r = servicos.processar_lote(at, [seq])[0]
            primeiros = {}
            for k, e in enumerate(r.eventos, start=1):
                primeiros.setdefault(e.tipo, k)
            self.executar(caminho, {"seq": seq, "modo": "rapido"})
            marcos = self.js(f"Array.from(document.querySelectorAll('{LINHA} [data-marco]'))"
                             ".map(m => [m.getAttribute('data-tipo'), +m.getAttribute('data-passo')])")
            with self.subTest(at=at, n=len(r.eventos)):
                self.assertEqual(sorted(marcos), sorted([t, k] for t, k in primeiros.items()),
                                 "um marco por tipo de evento, no primeiro passo daquele tipo")


class TestCancelamento(BaseViz):
    def test_pular_cancela_animacoes_imediatamente(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "animado"})
        self.js("(() => { const s = document.querySelector('[data-componente=player] "
                "select[data-campo=velocidade]'); if (s) { s.value = '0.5';"
                " s.dispatchEvent(new Event('change', {bubbles: true})); } return true; })()")
        self.pausa(700)
        self.js("document.querySelector('[data-componente=player] [data-acao=fim]').click(), true")
        self.pausa(120)
        e = self.estado()
        self.assertEqual((e["k"], e["n"]), (len(r.eventos), len(r.eventos)))
        self.assertEqual(e["tocando"], "false")
        rodando = self.js("document.getAnimations().filter(a => a.playState === 'running'"
                          " && (a.effect && a.effect.getTiming().iterations !== Infinity)).length")
        self.assertEqual(rodando, 0, "pular deve encerrar as animações em andamento")
        aa = self.js("Array.from(document.querySelectorAll('[data-viz=at3] [data-cadeia] "
                     "[data-aminoacido]')).map(e => e.textContent.trim())")
        self.assertEqual(aa, list(r.aminoacidos), "o estado final real aparece de imediato")


class TestSelecaoSincronizada(BaseViz):
    def test_aminoacido_e_codon_se_destacam_juntos(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "rapido"})
        codons = self.js("Array.from(document.querySelectorAll('[data-viz=at3] [data-codon-mrna]'))"
                         ".map(c => [+c.getAttribute('data-ordem'), +c.getAttribute('data-indice'),"
                         " c.textContent.replace(/\\s/g, '')])")
        traduzidos = [e for e in r.eventos if e.tipo == "CODON_TRADUZIDO"]
        self.assertEqual([c[:2] for c in codons][:len(traduzidos)],
                         [[i, e.posicao] for i, e in enumerate(traduzidos)])
        for i, e in enumerate(traduzidos):
            self.assertEqual(codons[i][2], e.detalhe.split(":")[0])
        # aminoácido → códon
        self.js("document.querySelector('[data-viz=at3] [data-aminoacido][data-ordem=\"2\"]')"
                ".dispatchEvent(new MouseEvent('click', {bubbles: true})), true")
        self.pausa(250)
        sel = self.js("[Array.from(document.querySelectorAll('[data-viz=at3] [data-codon-mrna]"
                      "[data-selecionado]')).map(c => +c.getAttribute('data-ordem')),"
                      " Array.from(document.querySelectorAll('[data-viz=at3] [data-aminoacido]"
                      "[data-selecionado]')).map(c => +c.getAttribute('data-ordem')),"
                      " document.querySelectorAll('[data-viz=at3] [data-conexao]').length]")
        self.assertEqual(sel, [[2], [2], 1], "códon 2, aminoácido 2 e uma conexão SVG")
        # códon → aminoácido
        self.js("document.querySelector('[data-viz=at3] [data-codon-mrna][data-ordem=\"0\"]')"
                ".dispatchEvent(new MouseEvent('click', {bubbles: true})), true")
        self.pausa(250)
        self.assertEqual(self.js("Array.from(document.querySelectorAll('[data-viz=at3] "
                                 "[data-aminoacido][data-selecionado]')).map(c => +c.getAttribute('data-ordem'))"),
                         [0])


if __name__ == "__main__":
    unittest.main()
