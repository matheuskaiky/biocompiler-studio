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
    def abrir_at4(self, modo, metodo="both", s1=S1, s2=S2, reduzir=False, alinhamento=None,
                  params=(2, -1, -2), prazo=12):
        ma, mi, g = params
        self.executar("/at4", {"seq1": s1, "seq2": s2, "metodo": metodo, "match": str(ma),
                               "mismatch": str(mi), "gap": str(g), "modo": modo},
                      reduzir_movimento=reduzir, prazo=prazo)
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


ADULTERAR = r"""(() => {
  const orig = window.fetch.bind(window);
  window.__reqs = [];
  window.fetch = async (u, o) => {
    const url = String(u);
    window.__reqs.push([url, o && o.body ? String(o.body) : '']);
    const resp = await orig(u, o);
    if (!window.__adulterar) return resp;
    if (url.endsWith('/api/at4') || url.endsWith('/api/at4/celula')) {
      const j = await resp.clone().json();
      const k = window.__adulterar(url, j);
      return new Response(JSON.stringify(k), {status: resp.status,
        headers: {'Content-Type': 'application/json; charset=utf-8'}});
    }
    return resp;
  };
})();"""


class TestFonteDosDados(BaseAT4):
    """Pré-revisão A2/A3: a tela mostra o que a API devolve (inclusive adulterado no teste)."""

    def _com_script(self, fonte, corpo):
        sid = self.nav.cmd("Page.addScriptToEvaluateOnNewDocument", source=fonte)["identifier"]
        try:
            corpo()
        finally:
            self.nav.cmd("Page.removeScriptToEvaluateOnNewDocument", identifier=sid)

    def test_matriz_e_candidatos_vem_da_api(self):
        fonte = ADULTERAR + r"""
window.__adulterar = (url, j) => {
  if (url.endsWith('/api/at4')) { for (const env of j) { env.dados.matriz[1][1] = 999; } return j; }
  j.candidatos = j.candidatos.map(c => ({nome: c.nome, valor: c.valor + 7000})); return j;
};"""

        def corpo():
            self.abrir_at4("guiado", metodo="local")
            self.clicar("proximo")
            self.sub("celula-proxima")  # (1,1)
            self.assertEqual(self.celulas()[(1, 1)]["txt"].split()[0], "999",
                             "o valor exibido deve ser o da API, não recalculado")
            self.pausa(300)
            r = alinhar("local")
            insp = self.texto("[data-regiao=inspetor-celula]")
            for nome, valor in servicos.inspecionar_celula(r, 1, 1):
                self.assertIn(str(valor + 7000), insp, "candidatos devem vir de /api/at4/celula")
            reqs = self.js("window.__reqs.filter(r => r[0].endsWith('/api/at4/celula'))"
                           ".map(r => JSON.parse(r[1]))")
            self.assertTrue(any(q.get("i") == 1 and q.get("j") == 1
                                and q.get("alinhamento") == "local" for q in reqs), reqs)
        self._com_script(fonte, corpo)

    def test_celula_de_borda_sem_candidatos(self):
        self.abrir_at4("rapido", metodo="local")
        self.js("(() => { const c = document.querySelector('[data-viz=at4] [data-celula]"
                "[data-i=\"0\"][data-j=\"3\"]'); c.dispatchEvent(new MouseEvent('click',"
                " {bubbles: true})); return true; })()")
        self.pausa(400)
        insp = self.texto("[data-regiao=inspetor-celula]")
        self.assertIn("(0, 3)", insp)
        self.assertIn("Célula de borda", insp)
        self.assertNotIn("diagonal", insp.lower())


class TestCasosEspeciais(BaseAT4):
    def test_local_sem_regiao_positiva(self):
        r = alinhar("local", "AAAA", "CCCC")
        self.assertEqual(r.caminho, ())
        self.abrir_at4("rapido", metodo="local", s1="AAAA", s2="CCCC")
        e = self.estado()
        self.assertEqual((e["k"], e["n"]), (len(r.eventos), len(r.eventos)))
        cel = self.celulas()
        self.assertFalse(any(c["inicio"] or c["caminho"] for c in cel.values()),
                         "não inventar início nem caminho")
        self.assertEqual(self.contar("[data-viz=at4] [data-seta]"), 0)
        self.assertEqual(self.js("document.querySelectorAll('[data-viz=at4] "
                                 "[data-regiao=alinhamento-viz] [data-coluna]').length"), 0)
        self.assertIn(r.observacao, self.texto("[data-viz=at4]"))

    def test_empates_e_desempate_exibido(self):
        a, b = "ACGT", "TGCA"
        r = alinhar("global", a, b, 1, -1, -1)
        self.abrir_at4("rapido", metodo="global", s1=a, s2=b, params=(1, -1, -1))
        cel = self.celulas()
        for (i, j), c in cel.items():
            if i and j:
                self.assertIn(r.direcoes[i][j], c["txt"], (i, j))
        # célula (3,3): empate vertical × horizontal → vertical (API)
        self.assertEqual(r.direcoes[3][3], "↑")
        self.js("(() => { const c = document.querySelector('[data-viz=at4] [data-celula]"
                "[data-i=\"3\"][data-j=\"3\"]'); c.dispatchEvent(new MouseEvent('click',"
                " {bubbles: true})); return true; })()")
        self.pausa(400)
        insp = self.texto("[data-regiao=inspetor-celula]")
        self.assertIn("empate", insp.lower())
        self.assertIn("diagonal > vertical > horizontal", insp)

    def test_local_primeiro_maximo_em_ordem_de_leitura(self):
        r = alinhar("local", "AC", "CA", 1, -1, -1)
        self.assertEqual(r.inicio_traceback, (1, 2))
        self.abrir_at4("rapido", metodo="local", s1="AC", s2="CA", params=(1, -1, -1))
        cel = self.celulas()
        self.assertEqual([k for k, c in cel.items() if c["inicio"]], [r.inicio_traceback])


class TestAlinhamentoProgressivo(BaseAT4):
    def test_colunas_crescem_do_fim_para_o_inicio(self):
        a, b = "ACGTAC", "ACTAC"
        r = alinhar("global", a, b)
        self.abrir_at4("guiado", metodo="global", s1=a, s2=b)
        tipos = [e.tipo for e in r.eventos]
        self.ir_para(tipos.index("INICIO_TRACEBACK") + 1)
        col = ("(() => { const c = Array.from(document.querySelectorAll("
               "'[data-viz=at4] [data-regiao=alinhamento-viz] [data-coluna]'));"
               " return [c.map(e => e.getAttribute('data-a')).join(''),"
               " c.map(e => e.getAttribute('data-m')).join(''),"
               " c.map(e => e.getAttribute('data-b')).join('')]; })()")
        t = 0
        for k in range(tipos.index("INICIO_TRACEBACK") + 2, len(tipos) + 1):
            self.clicar("proximo")
            ev = r.eventos[k - 1]
            if ev.tipo == "TRACEBACK_PASSO" and not ev.detalhe.endswith("·"):
                t += 1
            if ev.tipo == "TRACEBACK_PASSO":
                esperado = [r.alinhado1[len(r.alinhado1) - t:], r.marcadores[len(r.marcadores) - t:],
                            r.alinhado2[len(r.alinhado2) - t:]] if t else ["", "", ""]
                self.assertEqual(self.js(col), esperado, f"passo {k} ({ev.detalhe})")
        self.assertIn("-", r.alinhado2)


class TestTecladoGrade(BaseAT4):
    def test_grade_pequena_roving(self):
        self.abrir_at4("rapido", metodo="global")
        self.assertEqual(self.js("document.querySelector('[data-viz=at4] [role=grid]') !== null"),
                         True)
        self.js("(() => { const c = document.querySelector('[data-viz=at4] [data-celula]"
                "[data-i=\"1\"][data-j=\"1\"]'); c.focus(); return true; })()")
        self.tecla_seta("ArrowDown")
        self.tecla_seta("ArrowRight")
        a = self.js("[document.activeElement.getAttribute('data-i'),"
                    " document.activeElement.getAttribute('data-j'),"
                    " document.activeElement.getAttribute('role')]")
        self.assertEqual(a, ["2", "2", "gridcell"])

    def tecla_seta(self, nome):
        cod = {"ArrowDown": 40, "ArrowUp": 38, "ArrowRight": 39, "ArrowLeft": 37}[nome]
        for tipo in ("rawKeyDown", "keyUp"):
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key=nome, code=nome,
                         windowsVirtualKeyCode=cod)
        self.pausa(120)

    def test_canvas_cursor_preciso_e_anunciado(self):
        rnd = random.Random(7)
        a = "".join(rnd.choice("ACGT") for _ in range(120))
        b = "".join(rnd.choice("ACGT") for _ in range(110))
        r = alinhar("global", a, b)
        self.abrir_at4("rapido", metodo="global", s1=a, s2=b)
        cv = "document.querySelector('[data-viz=at4] canvas[data-matriz]')"
        self.assertTrue(self.js(f"!!{cv}.getAttribute('aria-label') && {cv}.tabIndex >= 0"))
        self.js(f"{cv}.focus(), true")
        for t in ("ArrowRight", "ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "ArrowUp",
                  "ArrowUp"):
            self.tecla_seta(t)
        anuncio = self.texto("[data-viz=at4] [data-regiao=cursor-matriz]")
        self.assertIn("Linha 0", anuncio)
        self.assertIn("coluna 1", anuncio)
        self.assertIn(f"valor {r.matriz[0][1]}", anuncio)
        self.assertEqual(self.js(f"{cv}.closest('[aria-live]') !== null || document.querySelector("
                                 "'[data-viz=at4] [data-regiao=cursor-matriz]')"
                                 ".getAttribute('aria-live')"), "polite")
        self.tecla("Enter")
        self.pausa(400)
        self.assertIn("(0, 1)", self.texto("[data-regiao=inspetor-celula]"))


class TestMovimentoELimites(BaseAT4):
    def test_movimento_reduzido_sem_animacoes_na_matriz(self):
        self.abrir_at4("guiado", metodo="global", reduzir=True)
        self.clicar("proximo")
        self.sub("celula-proxima")
        self.clicar("fim")
        durs = self.js("""(() => {
          const s = v => Math.max(...v.split(',').map(x => parseFloat(x) * (x.trim().endsWith('ms') ? 1 : 1000)));
          let m = 0;
          for (const e of document.querySelectorAll('[data-viz=at4], [data-viz=at4] *')) {
            const c = getComputedStyle(e);
            m = Math.max(m, s(c.transitionDuration), s(c.animationDuration));
          }
          const an = document.getAnimations().filter(a => a.playState === 'running')
            .map(a => a.effect && a.effect.getTiming().duration || 0);
          return {css: m, js: an.length ? Math.max(...an) : 0};
        })()""")
        self.assertLessEqual(durs["css"], 10, durs)
        self.assertLessEqual(durs["js"], 10, durs)

    def test_matriz_muito_grande_tem_limite_honesto(self):
        rnd = random.Random(3)
        a = "".join(rnd.choice("ACGT") for _ in range(1100))
        b = "".join(rnd.choice("ACGT") for _ in range(1000))
        r = alinhar("global", a, b)
        self.abrir_at4("rapido", metodo="global", s1=a, s2=b, prazo=90)  # resposta de ~34 MB
        for _ in range(60):  # resposta de ~34 MB: aguarda a renderização (asserção inalterada)
            aviso = self.texto("[data-viz=at4] [data-regiao=aviso-matriz]")
            if aviso:
                break
            self.pausa(500)
        self.assertIn(str(1101 * 1001), aviso.replace(".", "").replace(" ", "").replace(" ", ""))
        self.assertIn(f"Score", self.texto("[data-viz=at4]"))
        self.assertIn(str(r.score), self.texto("[data-viz=at4]"))
        self.assertLess(self.js("document.querySelectorAll('main *').length"), 8000)

    def test_matriz_grande_renderiza_no_canvas(self):
        rnd = random.Random(5)
        a = "".join(rnd.choice("ACGT") for _ in range(600))
        b = "".join(rnd.choice("ACGT") for _ in range(600))
        self.abrir_at4("rapido", metodo="global", s1=a, s2=b)
        self.assertEqual(self.js("document.querySelectorAll('[data-viz=at4] canvas[data-matriz]')"
                                 ".length"), 1)
        self.assertEqual(self.js("document.querySelectorAll('[data-viz=at4] "
                                 "[data-regiao=aviso-matriz]').length"), 0)


class TestAcabamentoVisual(BaseAT4):
    """R1 (CTO): grade com células em caixas, mapa de calor e rótulo de estado coerente."""

    def test_celulas_em_caixas_com_mapa_de_calor(self):
        self.abrir_at4("rapido", metodo="global")
        est = self.js("""(() => Array.from(document.querySelectorAll('[data-viz=at4] [data-celula]'))
          .filter(e => !e.hasAttribute('data-caminho')).map(e => {
            const c = getComputedStyle(e), r = e.getBoundingClientRect();
            return {raio: parseFloat(c.borderTopLeftRadius) || 0, fundo: c.backgroundColor,
                    w: r.width, h: r.height};
          }))()""")
        self.assertTrue(est)
        self.assertTrue(all(x["raio"] >= 3 for x in est), "células com cantos arredondados")
        self.assertTrue(all(x["w"] >= 34 and x["h"] >= 30 for x in est),
                        "células com área legível (≥ 34×30 px)")
        self.assertGreaterEqual(len({x["fundo"] for x in est}), 4,
                                "mapa de calor: fundos variam conforme o valor")

    def test_rotulo_do_preenchimento_acompanha_o_passo(self):
        self.abrir_at4("guiado", metodo="global")
        rot = "[data-regiao=celula-atual]"
        self.assertIn("Bordas", self.texto(rot))
        self.clicar("proximo")
        self.sub("preencher-tudo")
        self.clicar("proximo")  # INICIO_TRACEBACK
        t = self.texto(rot)
        self.assertNotIn("Bordas", t)
        self.assertIn("Matriz completa", t)


class TestVisibilidadePreenchimento(BaseAT4):
    """R2: o subcontrole de preenchimento só aparece no passo MATRIZ_PREENCHIDA."""

    def visivel(self):
        return self.js("(() => { const e = document.querySelector("
                       "'[data-componente=preenchimento]'); if (!e) return false;"
                       " const r = e.getBoundingClientRect(); const c = getComputedStyle(e);"
                       " return c.display !== 'none' &&"
                       " c.visibility !== 'hidden' && r.width > 0 && r.height > 0; })()")

    def test_aparece_somente_no_passo_de_preenchimento(self):
        self.abrir_at4("guiado", metodo="global")
        self.assertFalse(self.visivel(), "passo 1 (BORDA_INICIALIZADA)")
        self.clicar("proximo")
        self.assertTrue(self.visivel(), "passo MATRIZ_PREENCHIDA")
        self.clicar("proximo")
        self.assertFalse(self.visivel(), "passo INICIO_TRACEBACK")
        self.clicar("fim")
        self.assertFalse(self.visivel(), "passo final")


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
