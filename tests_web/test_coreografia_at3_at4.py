"""OS-M10-04 — Coreografias AT3 (ribossomo) e AT4 (programação dinâmica) — Frente B.

AT3: o ribossomo fica centrado no códon traduzido e avança exatamente 3 bases por
evento; no STOP para e a cadeia se conclui. AT4: dependências da célula inspecionada
como conexões SVG; setas do traceback tipadas pelo movimento real; zoom; alternância
Local ↔ Global preservando o contexto (cabeçalhos das sequências são os mesmos nós).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, MRNA_OK  # noqa: E402

from biocompiler import servicos  # noqa: E402

RET = ("(sel) => { const e = document.querySelector(sel); if (!e) return null;"
       " const r = e.getBoundingClientRect(); return {x: r.left, w: r.width, cx: r.left + r.width / 2}; }")


class Base(BaseViz):
    def caixa(self, sel):
        return self.js(f"({RET})({sel!r})")

    def assentar(self, ms=4000):
        for _ in range(ms // 100):
            n = self.js("document.getAnimations().filter(a => a.playState === 'running'"
                        " && a.effect && a.effect.getTiming().iterations !== Infinity).length")
            if n == 0:
                break
            self.pausa(100)
        self.pausa(60)


class TestAT3Ribossomo(Base):

    def test_ribossomo_centrado_e_passo_de_tres_bases(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        largura_base = self.caixa("[data-viz=at3] [data-fita=mrna] [data-base]")["w"]
        centros = []
        ordem = 0
        for k in range(1, len(tipos) + 1):
            if k > 1:
                self.clicar("proximo")
            parado = self.js("document.querySelector('[data-viz=at3] [data-ribossomo]')"
                             ".getAttribute('data-parado')")
            ja_stop = "STOP_ENCONTRADO" in tipos[:k]
            with self.subTest(k=k, evento=tipos[k - 1]):
                self.assertEqual(parado == "true", ja_stop, "parado só a partir do STOP")
            if tipos[k - 1] != "CODON_TRADUZIDO":
                continue
            self.assentar()
            rib = self.caixa("[data-viz=at3] [data-ribossomo]")
            cod = self.caixa(f"[data-viz=at3] [data-codon-mrna][data-ordem=\"{ordem}\"]")
            with self.subTest(codon=ordem):
                self.assertLessEqual(abs(rib["cx"] - cod["cx"]), largura_base / 2,
                                     "ribossomo centrado no códon traduzido")
            centros.append(rib["cx"])
            ordem += 1
        passos = [b - a for a, b in zip(centros, centros[1:])]
        base_pitch = self.js("(() => { const b = Array.from(document.querySelectorAll("
                             "'[data-viz=at3] [data-fita=mrna] [data-base]')).slice(0, 2)"
                             ".map(e => e.getBoundingClientRect().left); return b[1] - b[0]; })()")
        for d in passos:
            self.assertAlmostEqual(d, 3 * base_pitch, delta=2, msg="avança exatamente 3 bases")

    def test_stop_conclui(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "rapido"})
        self.assentar()
        estado = self.js("[document.querySelector('[data-viz=at3] [data-ribossomo]')"
                         ".getAttribute('data-parado'), document.querySelector('[data-viz=at3] "
                         "[data-cadeia]').getAttribute('data-concluida')]")
        self.assertEqual(estado, ["true", "true"])
        rib = self.caixa("[data-viz=at3] [data-ribossomo]")
        stop = self.caixa("[data-viz=at3] [data-marca=stop]")
        self.assertLessEqual(abs(rib["cx"] - stop["cx"]), stop["w"],
                             "o ribossomo para sobre o STOP")
        aa = self.js("Array.from(document.querySelectorAll('[data-viz=at3] [data-cadeia] "
                     "[data-aminoacido]')).map(e => e.textContent.trim())")
        self.assertEqual(aa, list(r.aminoacidos), "o STOP não entra na proteína")

    def test_movimento_reduzido_ribossomo_instantaneo(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"}, reduzir_movimento=True)
        self.ir_para(tipos.index("CODON_TRADUZIDO") + 2)  # segundo códon
        self.pausa(50)
        rib = self.caixa("[data-viz=at3] [data-ribossomo]")
        cod = self.caixa("[data-viz=at3] [data-codon-mrna][data-ordem=\"1\"]")
        self.assertLessEqual(abs(rib["cx"] - cod["cx"]), cod["w"] / 6, "sem deslize: já no códon")


class TestAT4Dependencias(Base):
    def abrir(self, modo="rapido", metodo="global", s1="ACGTAC", s2="ACGTTC"):
        self.executar("/at4", {"seq1": s1, "seq2": s2, "metodo": metodo, "match": "2",
                               "mismatch": "-1", "gap": "-2", "modo": modo})

    def clicar_celula(self, i, j):
        self.js(f"document.querySelector('[data-viz=at4] [data-celula][data-i=\"{i}\"]"
                f"[data-j=\"{j}\"]').dispatchEvent(new MouseEvent('click', {{bubbles: true}})), true")
        self.pausa(400)
        self.assentar()

    def test_conexoes_svg_para_as_tres_dependencias(self):
        self.abrir()
        self.clicar_celula(3, 4)
        deps = self.js("Array.from(document.querySelectorAll('[data-viz=at4] [data-dependencia]'))"
                       ".map(e => [e.getAttribute('data-dependencia'), e.getAttribute('data-de'),"
                       " e.tagName.toLowerCase()])")
        self.assertEqual(sorted(d[0] for d in deps), ["diagonal", "horizontal", "vertical"])
        self.assertEqual(sorted(d[1] for d in deps), ["2,3", "2,4", "3,3"])
        self.assertTrue(all(d[2] in ("path", "line", "polyline") for d in deps), "conexões SVG")
        geo = self.js("""Array.from(document.querySelectorAll('[data-viz=at4] [data-dependencia]')).map(e => {
          const m = e.getScreenCTM(); let a, b;
          if (e.getTotalLength) { const L = e.getTotalLength(); a = e.getPointAtLength(0); b = e.getPointAtLength(L); }
          else { a = {x: +e.getAttribute('x1'), y: +e.getAttribute('y1')}; b = {x: +e.getAttribute('x2'), y: +e.getAttribute('y2')}; }
          const t = p => ({x: m.a * p.x + m.c * p.y + m.e, y: m.b * p.x + m.d * p.y + m.f});
          return [e.getAttribute('data-de'), t(a), t(b)]; })""")
        def dentro(p, i, j, folga=6):
            q = self.js(f"(() => {{ const r = document.querySelector('[data-viz=at4] [data-celula]"
                        f"[data-i=\"{i}\"][data-j=\"{j}\"]').getBoundingClientRect();"
                        " return [r.left, r.top, r.right, r.bottom]; })()")
            return q[0] - folga <= p["x"] <= q[2] + folga and q[1] - folga <= p["y"] <= q[3] + folga
        for de, pa, pb in geo:
            i0, j0 = (int(x) for x in de.split(","))
            with self.subTest(de=de):
                self.assertTrue((dentro(pa, i0, j0) and dentro(pb, 3, 4)) or
                                (dentro(pb, i0, j0) and dentro(pa, 3, 4)),
                                "a conexão liga a célula de origem à célula inspecionada")
        for borda in ((0, 3), (2, 0)):
            self.clicar_celula(*borda)
            self.assertEqual(self.js("document.querySelectorAll('[data-viz=at4] [data-dependencia]')"
                                     ".length"), 0, f"célula de borda {borda} não tem dependências")

    def test_setas_tipadas_pelo_movimento_real(self):
        r = servicos.alinhar_par("ACGTAC", "ACTAC", "global", 2, -1, -2)[0]
        self.abrir(s1="ACGTAC", s2="ACTAC")
        esperado = []
        for (i1, j1), (i2, j2) in zip(r.caminho, r.caminho[1:]):
            di, dj = i1 - i2, j1 - j2
            esperado.append("diagonal" if (di, dj) == (1, 1) else
                            "vertical" if (di, dj) == (1, 0) else "horizontal")
        setas = self.js("Array.from(document.querySelectorAll('[data-viz=at4] [data-seta]'))"
                        ".map(e => [e.getAttribute('data-de'), e.getAttribute('data-para'),"
                        " e.getAttribute('data-direcao')])")
        pares = [[f"{a[0]},{a[1]}", f"{b[0]},{b[1]}", d]
                 for a, b, d in zip(r.caminho, r.caminho[1:], esperado)]
        self.assertEqual(setas, pares, "cada seta, na ordem do traceback, liga as células reais")
        self.assertIn("vertical", setas, "o caso tem um gap (movimento vertical)")

    def test_zoom(self):
        self.abrir()
        largura = ("document.querySelector('[data-viz=at4] [data-celula][data-i=\"1\"]"
                   "[data-j=\"1\"]').getBoundingClientRect().width")
        w0 = self.js(largura)
        self.js("document.querySelector('[data-viz=at4] [data-acao=zoom-mais]').click(), true")
        self.pausa(400)
        w1 = self.js(largura)
        self.assertGreater(w1, w0 * 1.1)
        self.js("document.querySelector('[data-viz=at4] [data-acao=zoom-menos]').click(), true")
        self.js("document.querySelector('[data-viz=at4] [data-acao=zoom-menos]').click(), true")
        self.pausa(400)
        self.assertLess(self.js(largura), w1)

    def test_local_global_preserva_contexto(self):
        self.abrir(metodo="both")
        self.js("(() => { document.querySelectorAll('[data-viz=at4] [data-cabecalho-seq]')"
                ".forEach((e, k) => { e.__marca = 'm' + k; }); return true; })()")
        n = self.js("document.querySelectorAll('[data-viz=at4] [data-cabecalho-seq]').length")
        self.assertEqual(n, 6 + 6, "cabeçalhos das bases de Seq1 e Seq2 marcados")
        rg = servicos.alinhar_par("ACGTAC", "ACGTTC", "global", 2, -1, -2)[0]
        rl = servicos.alinhar_par("ACGTAC", "ACGTTC", "local", 2, -1, -2)[0]
        ler = ("Array.from(document.querySelectorAll('[data-viz=at4] [data-celula]'))"
               ".map(e => [+e.getAttribute('data-i'), +e.getAttribute('data-j'),"
               " e.textContent.trim().split(/\\s+/)[0]])")
        antes = self.js(ler)
        self.assertTrue(all(v == str(rl.matriz[i][j]) for i, j, v in antes),
                        "antes da troca: matriz local da API")
        self.js("(() => { const s = document.querySelector('[data-componente=player] "
                "select[data-campo=registro]'); s.value = 'global';"
                " s.dispatchEvent(new Event('change', {bubbles: true})); return true; })()")
        for _ in range(10):  # amostra a transição: só valores reais de uma das duas matrizes
            for i, j, v in self.js(ler):
                if v:
                    self.assertIn(v, (str(rl.matriz[i][j]), str(rg.matriz[i][j])), (i, j))
            self.pausa(60)
        self.assentar()
        mantidos = self.js("Array.from(document.querySelectorAll('[data-viz=at4] [data-cabecalho-seq]'))"
                           ".filter(e => e.__marca).length")
        self.assertEqual(mantidos, n, "os cabeçalhos das sequências são preservados (mesmos nós)")
        vals = self.js("Array.from(document.querySelectorAll('[data-viz=at4] [data-celula]'))"
                       ".map(e => [+e.getAttribute('data-i'), +e.getAttribute('data-j'),"
                       " e.textContent.trim().split(/\\s+/)[0]])")
        self.assertTrue(all(v == str(rg.matriz[i][j]) for i, j, v in vals),
                        "após a troca, valores da matriz global da API (sem interpolação)")


if __name__ == "__main__":
    unittest.main()
