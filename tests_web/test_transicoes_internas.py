"""OS-M10-13 — Transições que faltavam dentro das páginas (revisão visual do CTO, 2026-11-18).

Achados da revisão: troca de aba, seletores segmentados, diálogo de ajuda e troca de tema
mudavam de estado instantaneamente; botões não davam retorno ao pressionar; o indicador
da navegação lateral saltava entre páginas. Cada transição é curta (≤ 300 ms, plano §7),
usa os tokens de movimento e desaparece com movimento reduzido.
"""
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, DNA_OK, ESPERA  # noqa: E402

class BaseInterna(BaseViz):
    def abrir_at1(self, reduzir=False):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": "reduce" if reduzir else ""}])
        url = (f"http://127.0.0.1:{self.porta}/at1?"
               + urllib.parse.urlencode({"seq": DNA_OK, "executar": "1", "modo": "rapido"}))
        self.assertTrue(self.nav.abrir(url, 1440, 900, ESPERA, prazo=30))
        self.pausa(500)

    def tearDown(self):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": ""}])


class TestTrocaDeAba(BaseInterna):
    def _trocar(self):
        return self.js("""(() => {
          const aba = Array.from(document.querySelectorAll('[role=tab]'))
            .find(a => a.getAttribute('aria-selected') !== 'true');
          aba.click();
          const p = document.getElementById(aba.getAttribute('aria-controls'));
          const anims = p.getAnimations({subtree: false}).concat(p.getAnimations())
            .filter(a => a.playState === 'running' || a.playState === 'pending')
            .map(a => +a.effect.getTiming().duration);
          const r = p.getBoundingClientRect();
          return {anims, visivel: !p.classList.contains('painel-oculto') && r.height > 0};
        })()""")

    def test_painel_novo_entra_com_transicao_curta(self):
        self.abrir_at1()
        t = self._trocar()
        self.assertTrue(t["visivel"], "o conteúdo aparece imediatamente (sem esperar a animação)")
        self.assertTrue(t["anims"], "a troca de aba não tem transição")
        self.assertTrue(all(80 <= d <= 300 for d in t["anims"]), f"durações fora de 80–300 ms: {t['anims']}")

    def test_sem_transicao_com_movimento_reduzido(self):
        self.abrir_at1(reduzir=True)
        t = self._trocar()
        self.assertTrue(t["visivel"])
        self.assertEqual([d for d in t["anims"] if d > 10], [])


class TestSegmentados(BaseInterna):
    INDICADOR = """((grupo, opcao) => {
      const g = document.querySelector(grupo); if (!g) return null;
      const ind = g.querySelector('[data-indicador-segmento]'); if (!ind) return {ind: false};
      const sel = g.querySelector(opcao);
      const a = ind.getBoundingClientRect(), b = sel.getBoundingClientRect(), c = getComputedStyle(ind);
      return {ind: true, dx: Math.abs(a.left - b.left), dw: Math.abs(a.width - b.width),
              dur: c.transitionDuration, prop: c.transitionProperty};
    })"""

    def _medir(self, grupo, opcao):
        return self.js(f"{self.INDICADOR}({grupo!r}, {opcao!r})")

    def test_indicador_desliza_no_seletor_de_modo(self):
        self.abrir_at1()
        self.js("document.querySelector('.modo-segmentado [data-modo=animado]').click(), true")
        self.pausa(450)
        m = self._medir(".modo-segmentado", "[aria-checked=true]")
        self.assertIsNotNone(m)
        self.assertTrue(m["ind"], "[data-indicador-segmento] ausente no seletor de modo")
        self.assertLessEqual(m["dx"], 3, "o indicador assenta sob a opção escolhida")
        self.assertLessEqual(m["dw"], 3)
        self.assertRegex(m["prop"], r"transform|left|translate|all", "o indicador desliza")
        self.assertNotIn(m["dur"].split(",")[0].strip(), ("0s", ""), "duração da transição do indicador")

    def test_indicador_desliza_no_metodo_do_laboratorio(self):
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/", 1440, 900))
        self.pausa(400)
        self.js("document.querySelector('[data-segmento-metodo] [data-valor=global]').click(), true")
        self.pausa(450)
        m = self._medir("[data-segmento-metodo]", "[aria-pressed=true]")
        self.assertTrue(m and m["ind"], "[data-indicador-segmento] ausente no seletor de método")
        self.assertLessEqual(m["dx"], 3)
        self.assertLessEqual(m["dw"], 3)

    def test_indicador_sem_transicao_com_movimento_reduzido(self):
        self.abrir_at1(reduzir=True)
        m = self._medir(".modo-segmentado", "[aria-checked=true]")
        self.assertTrue(m and m["ind"])
        self.assertTrue(all(d.strip() in ("0s", "1e-05s", "0.01ms", "1e-05ms") or float(d.strip().rstrip("ms") or 0) <= 0.01
                            for d in m["dur"].split(",")), f"transição com movimento reduzido: {m['dur']}")


class TestDialogoETema(BaseInterna):
    def test_dialogo_de_ajuda_abre_com_transicao_e_em_vidro(self):
        self.abrir_at1()
        r = self.js("""(() => { document.querySelector('[data-acao=ajuda]').click();
          const d = document.getElementById('dialogo-ajuda');
          const anims = d.getAnimations().filter(a => a.playState !== 'finished')
            .map(a => +a.effect.getTiming().duration);
          const c = getComputedStyle(d);
          return {aberto: d.open, anims, blur: c.backdropFilter, fundo: c.backgroundColor}; })()""")
        self.assertTrue(r["aberto"])
        self.assertTrue(r["anims"], "o diálogo abre sem transição")
        self.assertTrue(all(80 <= d <= 300 for d in r["anims"]), r["anims"])
        self.assertIn("blur", r["blur"], "o diálogo (data-superficie=vidro) usa o material de vidro")
        alfa = [float(x) for x in r["fundo"].replace("rgba(", "").replace(")", "").split(",")[3:]] or [1]
        self.assertLess(alfa[0], 1.0, "o fundo do diálogo é translúcido, não opaco")
        self.js("document.getElementById('dialogo-ajuda').close(), true")

    def test_troca_de_tema_com_view_transition(self):
        self.abrir_at1()
        r = self.js("""(() => { window.__vt = 0; const o = document.startViewTransition;
          if (o) document.startViewTransition = function (...a) { window.__vt++; return o.apply(document, a); };
          const antes = document.documentElement.getAttribute('data-tema');
          document.querySelector('[data-acao=tema]').click();
          return {antes, vt: window.__vt}; })()""")
        self.pausa(500)
        depois = self.js("document.documentElement.getAttribute('data-tema')")
        self.assertNotEqual(r["antes"], depois, "o tema muda")
        self.assertEqual(r["vt"], 1, "a troca de tema usa document.startViewTransition")

    def test_troca_de_tema_sem_view_transition_com_movimento_reduzido(self):
        self.abrir_at1(reduzir=True)
        r = self.js("""(() => { window.__vt = 0; const o = document.startViewTransition;
          if (o) document.startViewTransition = function (...a) { window.__vt++; return o.apply(document, a); };
          document.querySelector('[data-acao=tema]').click(); return window.__vt; })()""")
        self.assertEqual(r, 0)


class TestRetornoTatil(BaseInterna):
    def test_botao_afunda_levemente_ao_pressionar(self):
        self.abrir_at1()
        b = self.js("(() => { const r = document.querySelector('[data-acao=apresentacao]').getBoundingClientRect();"
                    " return [r.left + r.width / 2, r.top + r.height / 2]; })()")
        self.nav.cmd("Input.dispatchMouseEvent", type="mouseMoved", x=b[0], y=b[1])
        self.nav.cmd("Input.dispatchMouseEvent", type="mousePressed", x=b[0], y=b[1], button="left", clickCount=1)
        self.pausa(250)
        t = self.js("getComputedStyle(document.querySelector('[data-acao=apresentacao]')).transform")
        self.nav.cmd("Input.dispatchMouseEvent", type="mouseReleased", x=b[0], y=b[1], button="left", clickCount=1)
        self.pausa(100)
        self.js("(() => { const b = document.querySelector('[data-acao=apresentacao]');"
                " if (b.getAttribute('aria-pressed') === 'true') b.click(); return 1; })()")
        self.assertNotEqual(t, "none", "sem retorno visual ao pressionar")
        escala = float(t.split("(")[1].split(",")[0])
        self.assertTrue(0.94 <= escala < 1.0, f"escala ao pressionar fora de 0,94–1: {escala}")


class TestIndicadorDeNavegacao(BaseInterna):
    def test_item_ativo_da_navegacao_tem_elemento_compartilhado(self):
        nomes = []
        for caminho in ("/at1", "/at2", "/sobre"):
            self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}{caminho}", 1440, 900))
            self.pausa(300)
            nomes.append(self.js("""Array.from(document.querySelectorAll('#barra-lateral *'))
              .map(e => getComputedStyle(e).viewTransitionName).filter(n => n && n !== 'none')"""))
        for lista in nomes:
            self.assertEqual(lista, ["nav-indicador"],
                             "um único indicador do item ativo com view-transition-name: nav-indicador")


if __name__ == "__main__":
    unittest.main()
