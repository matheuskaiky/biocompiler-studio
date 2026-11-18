"""OS-M10-12 — Liquid Glass com materialidade (pedido do CEO em 2026-11-18; D023).

Revisão do CTO: o vidro funciona (translúcido nos dois temas), mas parece genérico e, no
tema claro, quase não se distingue (interior ≈ branco puro, contorno fraco). Referências
estudadas: ybouane/liquidglass (WebGL + captura do DOM — não adotável: dependência e um
contexto WebGL por painel) e a técnica de refração por SVG (feDisplacementMap com mapa
gerado a partir de um perfil de bisel e da lei de Snell). Adota-se uma versão nativa:
- contorno de luz em camadas (Fresnel na borda + brilho especular), sombra de contato;
- tema claro com tinta, contorno e profundidade próprios;
- lente de refração na borda (backdrop-filter: url(#…) com feDisplacementMap e mapa gerado
  em canvas pelo próprio projeto) como aprimoramento progressivo nas barras flutuantes; o
  centro do mapa é neutro, então o texto sobre o vidro não é deslocado.
"""
import base64
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, MRNA_OK  # noqa: E402
from png_simples import ler  # noqa: E402

VIDROS = r"""(() => Array.from(document.querySelectorAll('[data-superficie=vidro]'))
  .filter(e => { const r = e.getBoundingClientRect(), c = getComputedStyle(e);
                 return r.width > 0 && r.height > 0 && c.display !== 'none' && c.backdropFilter !== 'none'; })
  .map(e => { const c = getComputedStyle(e);
    const sombras = c.boxShadow === 'none' ? [] : c.boxShadow.split(/,(?![^(]*\))/);
    return {nome: e.tagName + '.' + e.className, inset: sombras.filter(s => /inset/.test(s)).length,
            externas: sombras.filter(s => !/inset/.test(s)).length,
            gradientes: (c.backgroundImage.match(/gradient\(/g) || []).length,
            borda: c.borderTopColor, fundo: c.backgroundColor}; }))()"""

LENTE = r"""((sel) => {
  const e = document.querySelector(sel); if (!e) return null;
  const c = getComputedStyle(e), r = e.getBoundingClientRect();
  const m = c.backdropFilter.match(/url\(["']?#([^"')]+)["']?\)/);
  const f = m && document.getElementById(m[1]);
  const img = f && f.querySelector('feImage');
  const href = img && (img.getAttribute('href') || img.getAttribute('xlink:href') || '');
  return {lente: e.hasAttribute('data-lente'), filtro: c.backdropFilter, w: r.width, h: r.height,
          temFiltro: !!f, desloc: !!(f && f.querySelector('feDisplacementMap')),
          imgW: img ? +img.getAttribute('width') : null, imgH: img ? +img.getAttribute('height') : null,
          href: href ? href.slice(0, 40) : null, dados: href || null};
})"""


def lum(rgb):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])


def contraste(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def rgba(s):
    v = [float(x) for x in re.findall(r"[\d.]+", s)]
    return v + [1.0] if len(v) == 3 else v


class TestMaterialEmCamadas(BaseViz):
    def test_contorno_fresnel_especular_e_sombra_nos_dois_temas(self):
        for tema in ("escuro", "claro"):
            self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado", "tema": tema})
            vidros = self.js(VIDROS)
            self.assertGreaterEqual(len(vidros), 2, "barra superior e player, ao menos")
            for v in vidros:
                with self.subTest(tema=tema, vidro=v["nome"]):
                    self.assertGreaterEqual(v["inset"], 2, "luz na borda superior e sombra interna inferior")
                    self.assertGreaterEqual(v["externas"], 1, "sombra de contato")
                    self.assertGreaterEqual(v["gradientes"], 2, "camadas de Fresnel e brilho especular")

    def test_tema_claro_com_tinta_e_contorno_perceptivel(self):
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/sobre?tema=claro", 1440, 900))
        self.pausa(300)
        fundo = rgba(self.js("getComputedStyle(document.body).backgroundColor"))[:3]
        h = self.js("(() => { const c = getComputedStyle(document.querySelector('header.barra-topo'));"
                    " return [c.backgroundColor, c.borderBottomColor, c.borderBottomWidth]; })()")
        bg = rgba(h[0])
        self.assertFalse(all(x >= 252 for x in bg[:3]) and bg[3] > 0.3,
                         f"o véu do tema claro não pode ser branco puro: {h[0]}")
        borda = rgba(h[1])
        composta = [borda[i] * borda[3] + fundo[i] * (1 - borda[3]) for i in range(3)]
        self.assertGreater(float(h[2].rstrip("px") or 0), 0, "contorno inferior presente")
        self.assertGreaterEqual(contraste(composta, fundo), 1.25,
                                f"contorno do vidro no tema claro imperceptível: {h[1]}")


class TestLenteDeRefracao(BaseViz):
    def test_barras_flutuantes_com_lente_de_refracao(self):
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        for sel in ("header.barra-topo", "[data-componente=player]"):
            le = self.js(f"{LENTE}({sel!r})")
            with self.subTest(elemento=sel):
                self.assertIsNotNone(le)
                self.assertTrue(le["lente"], f"{sel} sem [data-lente]")
                self.assertIn("url(", le["filtro"], "backdrop-filter referencia o filtro SVG da lente")
                self.assertTrue(le["temFiltro"] and le["desloc"], "filtro com feDisplacementMap")
                self.assertTrue(le["href"] and le["href"].startswith("data:image/png"),
                                "mapa de deslocamento gerado localmente (data:image/png)")
                self.assertLessEqual(abs(le["imgW"] - le["w"]), 2, "mapa na largura do elemento")
                self.assertLessEqual(abs(le["imgH"] - le["h"]), 2, "mapa na altura do elemento")

    def test_mapa_neutro_no_centro_e_ativo_na_borda(self):
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        le = self.js(f"{LENTE}('header.barra-topo')")
        self.assertTrue(le and le["dados"], "mapa da lente ausente")
        w, h, bpp, img = ler(base64.b64decode(le["dados"].split(",", 1)[1]))
        cy, cx = h // 2, w // 2
        r, g = img[cy][cx * bpp], img[cy][cx * bpp + 1]
        self.assertLessEqual(abs(r - 128), 2, "centro sem deslocamento horizontal (texto legível)")
        self.assertLessEqual(abs(g - 128), 2, "centro sem deslocamento vertical")
        borda = [abs(img[y][x * bpp] - 128) + abs(img[y][x * bpp + 1] - 128)
                 for y in range(h) for x in (0, 1, 2, w - 3, w - 2, w - 1)]
        self.assertGreater(max(borda), 20, "a borda refrata (deslocamento ≠ 0 junto ao contorno)")

    def test_mapa_acompanha_o_tamanho(self):
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        antes = self.js(f"{LENTE}('header.barra-topo')")
        self.assertTrue(antes and antes["imgW"], "mapa da lente ausente")
        self.nav.cmd("Emulation.setDeviceMetricsOverride", width=1100, height=900, deviceScaleFactor=1,
                     mobile=False)
        try:
            for _ in range(20):
                self.pausa(150)
                depois = self.js(f"{LENTE}('header.barra-topo')")
                if depois["imgW"] != antes["imgW"]:
                    break
            self.assertLessEqual(abs(depois["imgW"] - depois["w"]), 2, "mapa regenerado ao redimensionar")
            self.assertNotEqual(depois["imgW"], antes["imgW"])
        finally:
            self.nav.cmd("Emulation.setDeviceMetricsOverride", width=1366, height=900, deviceScaleFactor=1,
                         mobile=False)

    def test_lente_desligada_com_transparencia_reduzida(self):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-transparency", "value": "reduce"}])
        try:
            self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}/sobre", 1440, 900))
            self.pausa(300)
            f = self.js("getComputedStyle(document.querySelector('header.barra-topo')).backdropFilter")
            self.assertEqual(f, "none")
        finally:
            self.nav.cmd("Emulation.setEmulatedMedia", features=[
                {"name": "prefers-reduced-transparency", "value": ""}])


if __name__ == "__main__":
    unittest.main()
