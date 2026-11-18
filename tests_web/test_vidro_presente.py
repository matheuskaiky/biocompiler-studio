"""OS-M10-10 — Vidro mais presente (pedido do CEO em 2026-11-18; D022; plano §4).

O Liquid Glass continua seletivo (R-4.1/R-4.2; `test_fundacao.TestSuperficies` segue
valendo), mas fica perceptível:
- material mais translúcido, com borda especular interna (box-shadow inset);
- um fundo ambiente sutil e fixo atrás do conteúdo, para que o vidro tenha o que refratar;
- mais superfícies previstas no plano: inspetor "Por que este resultado?" e gaveta lateral
  no celular;
- o texto sobre o vidro mantém AA mesmo com conteúdo médio por trás;
- com transparência reduzida, tudo volta a ser opaco e o fundo ambiente some.
"""
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, DNA_OK, ESPERA, MRNA_OK  # noqa: E402

CSS = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "css"

MATERIAL = r"""(() => {
  const h = document.querySelector('header.barra-topo'), c = getComputedStyle(h);
  const a = (c.backgroundColor.match(/[\d.]+/g) || []).map(Number);
  const blur = (c.backdropFilter.match(/blur\(([\d.]+)px\)/) || [0, 0])[1];
  const sat = (c.backdropFilter.match(/saturate\(([\d.]+)\)/) || [0, 0])[1];
  return {alfa: a.length > 3 ? a[3] : 1, blur: +blur, sat: +sat, sombra: c.boxShadow};
})()"""

AMBIENTE = r"""(() => {
  const e = document.querySelector('[data-fundo-ambiente]');
  if (!e) return null;
  const c = getComputedStyle(e), r = e.getBoundingClientRect();
  return {aria: e.getAttribute('aria-hidden'), pos: c.position, ptr: c.pointerEvents,
          img: c.backgroundImage, disp: c.display, vis: c.visibility, z: c.zIndex,
          cobre: r.width >= innerWidth - 1 && r.height >= innerHeight - 1};
})()"""

# Contraste de cada texto visível dentro de [data-superficie=vidro]: a cor do vidro é composta
# sobre (a) o --fundo do tema e (b) um cinza médio #808080, que representa o pior caso
# plausível de conteúdo desfocado passando por trás. Exige AA (4,5:1; 3:1 se texto grande).
CONTRASTE_VIDRO = r"""(() => {
  const rgb = s => (s.match(/[\d.]+/g) || []).map(Number);
  const lum = c => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; };
    return .2126 * f(c[0]) + .7152 * f(c[1]) + .0722 * f(c[2]); };
  const cr = (x, y) => { const a = lum(x), b = lum(y); return (Math.max(a, b) + .05) / (Math.min(a, b) + .05); };
  const sobre = (top, base) => { const al = top.length > 3 ? top[3] : 1;
    return [0, 1, 2].map(i => top[i] * al + base[i] * (1 - al)); };
  const fundoTema = rgb(getComputedStyle(document.body).backgroundColor);
  const ruins = [];
  for (const v of document.querySelectorAll('[data-superficie=vidro]')) {
    if (v.offsetParent === null && getComputedStyle(v).position !== 'fixed') continue;
    const w = document.createTreeWalker(v, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      const t = w.currentNode, e = t.parentElement;
      if (!t.textContent.trim() || !e || e.closest('svg,[aria-hidden=true]')) continue;
      const r = e.getBoundingClientRect(); if (!r.width || !r.height) continue;
      const c = getComputedStyle(e); if (c.visibility === 'hidden' || +c.opacity < .5) continue;
      // fundo próprio opaco (botão, chip) entre o texto e o vidro
      let camada = null;
      for (let a = e; a && a !== v.parentElement; a = a.parentElement) {
        const b = rgb(getComputedStyle(a).backgroundColor);
        if (b.length && (b.length < 4 || b[3] > .9)) { camada = b; break; }
        if (a === v) break;
      }
      const vidro = rgb(getComputedStyle(v).backgroundColor), fg = rgb(c.color);
      const tam = parseFloat(c.fontSize), grande = tam >= 24 || (tam >= 18.66 && +c.fontWeight >= 700);
      const min = grande ? 3 : 4.5;
      for (const [nome, base] of [['fundo', fundoTema], ['cinza', [128, 128, 128]]]) {
        const bg = camada || sobre(vidro, base), x = cr(fg, bg);
        if (x < min) ruins.push(`${nome}: ${e.tagName}.${e.className} "${t.textContent.trim().slice(0, 16)}" ${x.toFixed(2)}`);
      }
    }
  }
  return ruins;
})()"""


class TestMaterial(BaseViz):
    def test_material_translucido_com_borda_especular(self):
        for tema in ("escuro", "claro"):
            self.executar("/at1", {"seq": DNA_OK, "modo": "rapido", "tema": tema})
            m = self.js(MATERIAL)
            with self.subTest(tema=tema):
                self.assertGreaterEqual(m["alfa"], 0.45, "véu mínimo para leitura")
                self.assertLessEqual(m["alfa"], 0.62, f"vidro perceptível: alfa {m['alfa']} > 0,62")
                self.assertGreaterEqual(m["blur"], 16)
                self.assertGreaterEqual(m["sat"], 1.6)
                self.assertIn("inset", m["sombra"], "borda especular interna (box-shadow inset)")


class TestFundoAmbiente(BaseViz):
    def test_fundo_ambiente_sutil_fixo_e_inerte(self):
        for caminho, q in (("/at1", {"seq": DNA_OK}), ("/at3", {"seq": MRNA_OK}), ("/sobre", {})):
            for tema in ("escuro", "claro"):
                if q:
                    self.executar(caminho, dict(q, modo="rapido", tema=tema))
                else:
                    self.assertTrue(self.nav.abrir(
                        f"http://127.0.0.1:{self.porta}{caminho}?tema={tema}", 1440, 900))
                a = self.js(AMBIENTE)
                with self.subTest(pagina=caminho, tema=tema):
                    self.assertIsNotNone(a, "camada [data-fundo-ambiente] ausente")
                    self.assertEqual(a["aria"], "true")
                    self.assertEqual(a["pos"], "fixed")
                    self.assertEqual(a["ptr"], "none")
                    self.assertTrue(a["cobre"], "cobre a janela")
                    self.assertRegex(a["img"], r"gradient\(", "tinta ambiente com gradiente suave")

    def test_fundo_ambiente_visivel_nos_pixels(self):
        """Estilo computado não basta: a camada precisa aparecer na tela (não ficar sob o fundo
        opaco do body) e continuar discreta. Mede-se a diferença de pixels com e sem a camada
        numa página de texto (/sobre), amostrando a janela inteira."""
        import base64
        from png_simples import ler
        for tema in ("escuro", "claro"):
            self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/sobre?tema={tema}", 800, 600))
            self.pausa(400)
            def foto():
                return ler(base64.b64decode(self.nav.cmd("Page.captureScreenshot", format="png")["data"]))
            w, h, bpp, com = foto()
            self.js("document.querySelector('[data-fundo-ambiente]').style.display = 'none', true")
            self.pausa(250)
            _, _, _, sem = foto()
            self.js("document.querySelector('[data-fundo-ambiente]').style.display = '', true")
            difs = [max(abs(com[y][x + k] - sem[y][x + k]) for k in range(3))
                    for y in range(0, h, 6) for x in range(0, w * bpp, bpp * 6)]
            with self.subTest(tema=tema):
                perceptivel = sum(d >= 3 for d in difs) / len(difs)
                self.assertGreaterEqual(perceptivel, 0.05,
                                        f"ambiente imperceptível: {perceptivel:.1%} dos pixels mudam ≥ 3 níveis")
                self.assertLessEqual(max(difs), 48, "ambiente discreto: nenhum pixel muda mais de 48 níveis")

    def test_gradiente_ambiente_so_em_vidro_css_e_discreto(self):
        css = (CSS / "vidro.css").read_text(encoding="utf-8")
        bloco = re.search(r"\[data-fundo-ambiente\][^{]*\{([^}]*)\}", css)
        self.assertIsNotNone(bloco, "[data-fundo-ambiente] é estilizado em vidro.css")
        self.assertIn("var(--ambiente-", bloco.group(1), "cores do ambiente vêm de tokens --ambiente-*")
        tokens = (CSS / "tokens.css").read_text(encoding="utf-8")
        for nome, alfa in re.findall(r"(--ambiente-[\w-]+)\s*:\s*rgba\([^)]*,\s*([\d.]+)\s*\)", tokens):
            with self.subTest(token=nome):
                    self.assertLessEqual(float(alfa), 0.14, f"{nome} acima de 0,14 de opacidade")

    def test_transparencia_reduzida_remove_o_ambiente(self):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-transparency", "value": "reduce"}])
        try:
            # executar() redefine as mídias emuladas; aqui a página é aberta diretamente
            self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/at1?"
                                           + urllib.parse.urlencode({"seq": DNA_OK, "modo": "rapido",
                                                                     "executar": "1"}), 1366, 900, ESPERA))
            a = self.js(AMBIENTE)
            self.assertTrue(a is None or a["img"] == "none" or a["disp"] == "none"
                            or a["vis"] == "hidden", f"ambiente ainda visível: {a}")
        finally:
            self.nav.cmd("Emulation.setEmulatedMedia", features=[
                {"name": "prefers-reduced-transparency", "value": ""}])


class TestNovasSuperficies(BaseViz):
    def test_inspetor_em_vidro_nas_atividades(self):
        for caminho, q in (("/at1", {"seq": DNA_OK}), ("/at3", {"seq": MRNA_OK})):
            self.executar(caminho, dict(q, modo="rapido"))
            i = self.js("(() => { const e = document.querySelector('[data-regiao=inspetor]');"
                        " if (!e) return null; const c = getComputedStyle(e);"
                        " return [e.getAttribute('data-superficie'), c.backdropFilter]; })()")
            with self.subTest(pagina=caminho):
                self.assertIsNotNone(i, "[data-regiao=inspetor] ausente")
                self.assertEqual(i[0], "vidro", "inspetor temporário é de vidro (R-4.1)")
                self.assertIn("blur", i[1])

    def test_gaveta_lateral_em_vidro_no_celular(self):
        self.nav.cmd("Emulation.setDeviceMetricsOverride", width=390, height=844,
                     deviceScaleFactor=1, mobile=True)
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/at1", 390, 844))
        self.pausa(300)
        self.js("document.querySelector('[aria-controls=barra-lateral]').click(), true")
        self.pausa(500)
        g = self.js("(() => { const e = document.getElementById('barra-lateral'), c = getComputedStyle(e);"
                    " const r = e.getBoundingClientRect();"
                    " return [e.getAttribute('data-superficie'), c.backdropFilter, r.right > 100]; })()")
        self.assertTrue(g[2], "gaveta aberta")
        self.assertEqual(g[0], "vidro", "gaveta sobre o conteúdo é de vidro (R-4.1)")
        self.assertIn("blur", g[1])


class TestLeituraSobreVidro(BaseViz):
    def test_texto_sobre_vidro_aa_com_conteudo_por_tras(self):
        for tema in ("escuro", "claro"):
            for caminho, q in (("/at1", {"seq": DNA_OK}), ("/at3", {"seq": MRNA_OK})):
                self.executar(caminho, dict(q, modo="guiado", tema=tema))
                self.js("window.scrollTo(0, 300), true")
                self.pausa(300)
                with self.subTest(tema=tema, pagina=caminho):
                    self.assertEqual(self.js(CONTRASTE_VIDRO), [])


if __name__ == "__main__":
    unittest.main()
