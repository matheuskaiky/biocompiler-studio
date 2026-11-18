"""OS-M8-02 — AT4 animada: preenchimento da matriz, inspetor de célula e traceback (CDP).

O preenchimento é uma **projeção** da matriz já calculada pela API (ordem de leitura),
e o traceback reproduz os eventos TRACEBACK_PASSO. O JS não aplica a recorrência.
"""
import random
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz  # noqa: E402

from biocompiler import servicos  # noqa: E402

S1, S2 = "ACGTAC", "ACGTTC"
CELULAS = ("(() => Array.from(document.querySelectorAll("
           "'[data-viz=at4] [data-celula]')).map(e => ({i: +e.getAttribute('data-i'),"
           " j: +e.getAttribute('data-j'), rev: e.getAttribute('data-revelada'),"
           " txt: e.textContent.trim(), caminho: e.hasAttribute('data-caminho'),"
           " inicio: e.hasAttribute('data-traceback-inicio')})))()")


def alinhar(metodo, s1=S1, s2=S2, ma=2, mi=-1, g=-2):
    return servicos.alinhar_par(s1, s2, metodo, ma, mi, g)[0]


class BaseAT4(BaseViz):
    def abrir_at4(self, modo, metodo="both", s1=S1, s2=S2, reduzir=False, alinhamento=None):
        self.executar("/at4", {"seq1": s1, "seq2": s2, "metodo": metodo, "match": "2",
                               "mismatch": "-1", "gap": "-2", "modo": modo},
                      reduzir_movimento=reduzir)
        if alinhamento:
            self.js("(() => { const s = document.querySelector('[data-componente=player] "
                    f"select[data-campo=registro]'); s.value = {alinhamento!r};"
                    " s.dispatchEvent(new Event('change', {bubbles: true})); return true; })()")
            self.pausa(300)

    def celulas(self):
        return {(c["i"], c["j"]): c for c in self.js(CELULAS)}

    def sub(self, acao):
        ok = self.js("(() => { const b = document.querySelector("
                     f"'[data-componente=preenchimento] [data-acao={acao}]');"
                     " if (!b || b.disabled) return false; b.click(); return true; })()")
        self.assertTrue(ok, f"[data-componente=preenchimento] [data-acao={acao}] ausente")
        self.pausa(200)


class TestPlayerAT4(BaseAT4):
    def test_registro_escolhe_local_ou_global(self):
        self.abrir_at4("rapido")
        opcoes = self.js("Array.from(document.querySelectorAll('[data-componente=player] "
                         "select[data-campo=registro] option')).map(o => o.value)")
        self.assertEqual(opcoes, ["local", "global"])
        for met in ("global", "local"):
            r = alinhar(met)
            self.abrir_at4("rapido", alinhamento=met)
            e = self.estado()
            self.assertEqual((e["k"], e["n"]), (len(r.eventos), len(r.eventos)))
            self.assertEqual(self.js("document.querySelector('[data-viz=at4]')"
                                     ".getAttribute('data-alinhamento')"), met)

    def test_metodo_unico_sem_seletor_ambiguo(self):
        r = alinhar("global")
        self.abrir_at4("guiado", metodo="global")
        e = self.estado()
        self.assertEqual((e["k"], e["n"]), (1, len(r.eventos)))
        self.assertEqual(e["tipo"], "BORDA_INICIALIZADA")


class TestPreenchimento(BaseAT4):
    def test_bordas_no_passo_1(self):
        r = alinhar("global")
        self.abrir_at4("guiado", metodo="global")
        cel = self.celulas()
        self.assertEqual(len(cel), (len(S1) + 1) * (len(S2) + 1))
        for (i, j), c in cel.items():
            borda = i == 0 or j == 0
            self.assertEqual(c["rev"], "true" if borda else "false", (i, j))
            if borda:
                self.assertEqual(c["txt"], str(r.matriz[i][j]), (i, j))
            else:
                self.assertNotIn(str(r.matriz[i][j]), c["txt"].split(), (i, j))

    def test_celula_a_celula_em_ordem_de_leitura_com_candidatos(self):
        r = alinhar("local")
        self.abrir_at4("guiado", metodo="local")
        self.clicar("proximo")  # MATRIZ_PREENCHIDA
        self.assertEqual(self.estado()["tipo"], "MATRIZ_PREENCHIDA")
        ordem = [(i, j) for i in range(1, len(S1) + 1) for j in range(1, len(S2) + 1)]
        for n, (i, j) in enumerate(ordem[:8], start=1):
            self.sub("celula-proxima")
            cel = self.celulas()
            reveladas = [(a, b) for (a, b), c in cel.items()
                         if a > 0 and b > 0 and c["rev"] == "true"]
            self.assertEqual(sorted(reveladas), sorted(ordem[:n]), f"após {n} células")
            self.assertEqual(cel[(i, j)]["txt"].split()[0], str(r.matriz[i][j]))
            self.assertIn(f"({i}, {j})", self.texto("[data-regiao=celula-atual]"))
            self.pausa(250)
            insp = self.texto("[data-regiao=inspetor-celula]")
            for nome, valor in servicos.inspecionar_celula(r, i, j):
                self.assertIn(nome, insp)
                self.assertIn(str(valor), insp)
            self.assertIn(str(r.matriz[i][j]), insp)
        self.sub("linha-proxima")
        cel = self.celulas()
        linha2 = [cel[(2, j)]["rev"] for j in range(1, len(S2) + 1)]
        self.assertEqual(linha2, ["true"] * len(S2), "linha-proxima completa a linha atual")
        self.sub("preencher-tudo")
        cel = self.celulas()
        self.assertTrue(all(c["rev"] == "true" for c in cel.values()))
        self.assertTrue(all(c["txt"].split()[0] == str(r.matriz[i][j])
                            for (i, j), c in cel.items()))

    def test_avancar_o_player_completa_a_matriz(self):
        self.abrir_at4("guiado", metodo="global")
        self.clicar("proximo")
        self.clicar("proximo")  # INICIO_TRACEBACK
        self.assertTrue(all(c["rev"] == "true" for c in self.celulas().values()))

    def test_direcoes_mostradas_sao_as_da_api(self):
        r = alinhar("global")
        self.abrir_at4("rapido", metodo="global")
        for (i, j), c in self.celulas().items():
            if r.direcoes[i][j] and r.direcoes[i][j] not in (" ", "·"):
                self.assertIn(r.direcoes[i][j], c["txt"], (i, j))


class TestTraceback(BaseAT4):
    def test_caminho_cresce_com_os_eventos(self):
        r = alinhar("global")
        self.abrir_at4("guiado", metodo="global")
        tipos = [e.tipo for e in r.eventos]
        self.ir_para(tipos.index("INICIO_TRACEBACK") + 1)
        cel = self.celulas()
        self.assertEqual([k for k, c in cel.items() if c["inicio"]], [r.inicio_traceback])
        self.assertEqual([k for k, c in cel.items() if c["caminho"]], [])
        vistos = 0
        for k in range(tipos.index("INICIO_TRACEBACK") + 2, len(tipos) + 1):
            self.clicar("proximo")
            if tipos[k - 1] == "TRACEBACK_PASSO":
                vistos += 1
            cel = self.celulas()
            no_caminho = sorted(kk for kk, c in cel.items() if c["caminho"])
            self.assertEqual(no_caminho, sorted(r.caminho[:vistos]), f"passo {k}")
        self.assertEqual(vistos, len(r.caminho))
        self.assertEqual(self.contar("[data-viz=at4] [data-seta]"), len(r.caminho) - 1)

    def test_alinhamento_reconstruido_sincronizado(self):
        r = alinhar("global")
        self.abrir_at4("guiado", metodo="global")
        col = ("(() => { const c = Array.from(document.querySelectorAll("
               "'[data-viz=at4] [data-regiao=alinhamento-viz] [data-coluna]'));"
               " return [c.map(e => e.getAttribute('data-a')).join(''),"
               " c.map(e => e.getAttribute('data-m')).join(''),"
               " c.map(e => e.getAttribute('data-b')).join('')]; })()")
        self.assertEqual(self.js(col), ["", "", ""], "antes do traceback não há colunas")
        self.clicar("fim")
        self.assertEqual(self.js(col), [r.alinhado1, r.marcadores, r.alinhado2])
        txt = self.texto("[data-viz=at4] [data-regiao=alinhamento-viz]")
        self.assertRegex(txt, rf"Score\D*{r.score}\b")


class TestCanvasGrande(BaseAT4):
    def test_matriz_grande_em_canvas(self):
        rnd = random.Random(42)
        a = "".join(rnd.choice("ACGT") for _ in range(150))
        b = "".join(rnd.choice("ACGT") for _ in range(150))
        r = alinhar("global", a, b)
        self.abrir_at4("rapido", metodo="global", s1=a, s2=b)
        self.assertEqual(self.js("document.querySelectorAll('[data-viz=at4] canvas[data-matriz]')"
                                 ".length"), 1)
        self.assertLessEqual(self.js("document.querySelectorAll('[data-viz=at4] [data-celula]')"
                                     ".length"), 2000)
        self.assertEqual(self.js("document.querySelector('[data-viz=at4] canvas[data-matriz]')"
                                 ".getAttribute('data-linhas')"), str(len(a) + 1))
        self.assertLess(self.js("document.querySelectorAll('main *').length"), 8000)
        # inspecionar por teclado no canvas: foco + setas + Enter consulta a API
        self.js("document.querySelector('[data-viz=at4] canvas[data-matriz]').focus(), true")
        for t in ("ArrowRight", "ArrowRight", "ArrowLeft"):
            self.tecla(t)
        self.tecla("Enter")
        self.pausa(400)
        insp = self.texto("[data-regiao=inspetor-celula]")
        m = re.search(r"\((\d+), (\d+)\)", insp)
        self.assertIsNotNone(m, insp)
        i, j = int(m.group(1)), int(m.group(2))
        self.assertIn(str(r.matriz[i][j]), insp)


class TestParidadeAT4(BaseAT4):
    def test_pares_aleatorios(self):
        rnd = random.Random(31337)
        for _ in range(3):
            a = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(3, 12)))
            b = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(3, 12)))
            for met in ("local", "global"):
                r = alinhar(met, a, b)
                self.abrir_at4("rapido", metodo=met, s1=a, s2=b)
                with self.subTest(a=a, b=b, met=met):
                    cel = self.celulas()
                    self.assertTrue(all(c["txt"].split()[0] == str(r.matriz[i][j])
                                        for (i, j), c in cel.items()))
                    self.assertEqual(sorted(k for k, c in cel.items() if c["caminho"]),
                                     sorted(r.caminho))


class TestMovimentoAT4(BaseAT4):
    def test_animado_com_movimento_reduzido_nao_reproduz(self):
        self.abrir_at4("animado", metodo="global", reduzir=True)
        self.pausa(1800)
        self.assertEqual(self.estado()["k"], 1)


class TestSemRecorrenciaNoJS(unittest.TestCase):
    def test_js_nao_aplica_a_recorrencia(self):
        raiz = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "js"
        proibidos = [r"Math\.max\([^)]*(?:diag|diagonal)[^)]*(?:cima|vertical|up)",
                     r"\[\s*i\s*-\s*1\s*\]\s*\[\s*j\s*-\s*1\s*\]\s*\+",
                     r"(?:match|mismatch)\s*:\s*(?:mismatch|match)\s*\)?\s*;?\s*$"]
        for arq in raiz.rglob("*.js"):
            texto = arq.read_text(encoding="utf-8")
            for p in proibidos:
                self.assertIsNone(re.search(p, texto, re.M), f"{arq.name}: padrão proibido {p}")


if __name__ == "__main__":
    unittest.main()
