"""OS-M8-03 — Laboratório: Mapa da expressão gênica, comparador, mutações e modo apresentação.

Fonte da verdade: `servicos.fluxo_completo` (mesmo resultado de /api/all). O JS só compara
para destacar diferenças e reenvia a entrada editada à API; não interpreta biologia.
"""
import re
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz  # noqa: E402

from biocompiler import servicos  # noqa: E402
from biocompiler.exemplos import ALL_EXEMPLO  # noqa: E402

SEQ1, SEQ2 = ALL_EXEMPLO[0], ALL_EXEMPLO[1]
FALHA1 = "CCGGCTAAACCGTAAGG"      # sem ATG → falha em AT1
FALHA2 = "CCATGGCTAAACCGTAAGG"    # sem íntron → falha em AT2
ESPERA = ("(() => { const s = document.querySelector('[data-regiao=status]');"
          " return !!s && /conclu/i.test(s.textContent) && !/Executando/.test(s.textContent); })()")


def fluxo(s1, s2):
    return servicos.fluxo_completo(s1, s2, "both", 2, -1, -2)


class BaseLab(BaseViz):
    def abrir_lab(self, s1, s2, aba=None, largura=1366):
        url = (f"http://127.0.0.1:{self.porta}/?"
               + urllib.parse.urlencode({"seq1": s1, "seq2": s2, "metodo": "both",
                                         "executar": "1", "modo": "rapido"}))
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": ""}])
        self.assertTrue(self.nav.abrir(url, largura, 900, ESPERA), "laboratório não executou")
        if aba:
            self.aba(aba)

    def valor(self, campo):
        return self.js(f"document.querySelector('[data-campo={campo}]').value")


class TestMapa(BaseLab):
    def test_trilhas_e_fases_com_status_da_api(self):
        rf = fluxo(SEQ1, SEQ2)
        self.abrir_lab(SEQ1, SEQ2, "Mapa da expressão gênica")
        for nome, cad in (("seq1", rf.seq1), ("seq2", rf.seq2)):
            fases = self.js(f"Array.from(document.querySelectorAll('[data-trilha={nome}] "
                            "[data-fase]')).map(e => [e.getAttribute('data-fase'),"
                            " e.getAttribute('data-status')])")
            self.assertEqual(fases, [["at1", "ok"], ["at2", "ok"], ["at3", "ok"]])
            prod = self.js(f"Array.from(document.querySelectorAll('[data-trilha={nome}] "
                           "[data-fase] [data-campo=produto]')).map(e => e.getAttribute('data-valor'))")
            self.assertEqual(prod, [cad.at1.pre_mrna, cad.at2.mrna_maduro, cad.at3.proteina])
            self.assertIn(cad.at3.proteina, self.texto(f"[data-trilha={nome}]"))
        scores = self.js("Array.from(document.querySelectorAll('[data-trilha=alinhamento] "
                         "[data-campo=score]')).map(e => [e.getAttribute('data-metodo'),"
                         " e.textContent.trim()])")
        self.assertEqual(sorted(scores), sorted([[r.metodo, str(r.score)]
                                                 for r in rf.alinhamentos]))

    def test_ponto_de_falha_e_nao_executado(self):
        rf = fluxo(FALHA1, FALHA2)
        self.abrir_lab(FALHA1, FALHA2, "Mapa da expressão gênica")
        st = ("Array.from(document.querySelectorAll('[data-trilha=%s] [data-fase]'))"
              ".map(e => e.getAttribute('data-status'))")
        self.assertEqual(self.js(st % "seq1"), ["erro", "nao-executado", "nao-executado"])
        self.assertEqual(self.js(st % "seq2"), ["ok", "erro", "nao-executado"])
        self.assertIn(rf.seq1.at1.resultado, self.texto("[data-trilha=seq1] [data-fase=at1]"))
        self.assertIn(rf.seq2.at2.resultado, self.texto("[data-trilha=seq2] [data-fase=at2]"))
        self.assertIn("NÃO EXECUTADO", self.texto("[data-trilha=seq1] [data-fase=at3]"))
        # AT4 roda nos DNAs originais mesmo com falhas
        self.assertEqual(len(self.js("Array.from(document.querySelectorAll("
                                     "'[data-trilha=alinhamento] [data-campo=score]'))")), 2)

    def test_marcadores_clicaveis_com_coordenadas(self):
        rf = fluxo(SEQ1, SEQ2)
        self.abrir_lab(SEQ1, SEQ2, "Mapa da expressão gênica")
        alvos = (("at1", "start", rf.seq1.at1.posicao_start),
                 ("at2", "intron", rf.seq1.at2.introns[0].posicao_gu),
                 ("at3", "start", rf.seq1.at3.posicao_start))
        for fase, marca, idx in alvos:
            sel = f"[data-trilha=seq1] [data-fase={fase}] [data-marca={marca}]"
            self.assertEqual(self.js(f"document.querySelector({sel!r})"
                                     ".getAttribute('data-indice')"), str(idx), sel)
            self.js(f"document.querySelector({sel!r}).dispatchEvent("
                    "new MouseEvent('click', {bubbles: true})), true")
            self.pausa(150)
            self.assertIn(f"Posição {idx}", self.texto("[data-regiao=inspetor]"))


class TestComparador(BaseLab):
    def test_diferencas_por_nivel(self):
        rf = fluxo(SEQ1, SEQ2)
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        niveis = {
            "dna": (SEQ1, SEQ2),
            "pre-mrna": (rf.seq1.at1.pre_mrna, rf.seq2.at1.pre_mrna),
            "rna-processado": (rf.seq1.at2.rna_processado, rf.seq2.at2.rna_processado),
            "proteina": (rf.seq1.at3.aminoacidos, rf.seq2.at3.aminoacidos),
        }
        for nivel, (a, b) in niveis.items():
            esperado = [str(i) for i in range(min(len(a), len(b))) if a[i] != b[i]]
            obtido = self.js(f"Array.from(document.querySelectorAll('[data-nivel={nivel}] "
                             "[data-diferenca]')).map(e => e.getAttribute('data-indice'))")
            self.assertEqual(sorted(set(obtido)), esperado, nivel)
        prot = self.texto("[data-nivel=proteina]")
        self.assertIn("Lys", prot)
        self.assertIn("Asn", prot)
        self.assertIn("diferença observada", self.texto("[data-componente=comparador]"))

    def test_sem_diagnostico_categorico(self):
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        txt = self.texto("[data-componente=comparador]").lower()
        for termo in ("missense", "nonsense", "silenciosa", "sinônima", "frameshift"):
            self.assertNotIn(termo, txt)

    def test_nivel_ausente_quando_um_percurso_falha(self):
        self.abrir_lab(SEQ1, FALHA2, "Comparador molecular")
        txt = self.texto("[data-nivel=proteina]")
        self.assertIn("indisponível", txt.lower())
        self.assertEqual(self.js("document.querySelectorAll('[data-nivel=proteina] "
                                 "[data-diferenca]').length"), 0)


class TestMutacoes(BaseLab):
    def aplicar(self, alvo, op, pos, base=None):
        self.js("(() => { const set = (c, v) => { const e = document.querySelector("
                "`[data-componente=mutacoes] [data-campo=${c}]`); e.value = v;"
                " e.dispatchEvent(new Event('change', {bubbles: true})); };"
                f" set('mut-alvo', {alvo!r}); set('mut-operacao', {op!r});"
                f" set('mut-posicao', {str(pos)!r});"
                + (f" set('mut-base', {base!r});" if base else "")
                + " document.querySelector('[data-componente=mutacoes] "
                "[data-acao=aplicar-mutacao]').click(); return true; })()")
        for _ in range(40):
            self.pausa(250)
            if self.js(ESPERA):
                break
        self.pausa(300)

    def test_substituir_reexecuta_e_reverter(self):
        i = next(k for k in range(len(SEQ1)) if SEQ1[k] != SEQ2[k])
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        self.aplicar("seq1", "substituir", i, SEQ2[i])
        self.assertEqual(self.valor("seq1"), SEQ2)
        rf = fluxo(SEQ2, SEQ2)
        self.aba("Mapa da expressão gênica")
        self.assertIn(rf.seq1.at3.proteina, self.texto("[data-trilha=seq1]"))
        self.assertEqual(self.js("document.querySelector('[data-trilha=seq1] [data-fase=at3] "
                                 "[data-campo=produto]').getAttribute('data-valor')"),
                         rf.seq1.at3.proteina)
        self.aba("Comparador molecular")
        hist = self.texto("[data-regiao=mutacoes-historico]")
        self.assertIn(f"{SEQ1[i]}→{SEQ2[i]}", hist.replace(" ", ""))
        self.assertIn(str(i), hist)
        self.js("document.querySelector('[data-componente=mutacoes] [data-acao=reverter]')"
                ".click(), true")
        for _ in range(40):
            self.pausa(250)
            if self.js(ESPERA) and self.valor("seq1") == SEQ1:
                break
        self.assertEqual(self.valor("seq1"), SEQ1)
        self.aba("Mapa da expressão gênica")
        self.assertIn(fluxo(SEQ1, SEQ2).seq1.at3.proteina, self.texto("[data-trilha=seq1]"))

    def test_inserir_e_remover_editam_so_a_entrada(self):
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        self.aplicar("seq2", "inserir", 5, "G")
        self.assertEqual(self.valor("seq2"), SEQ2[:5] + "G" + SEQ2[5:])
        self.aplicar("seq2", "remover", 5)
        self.assertEqual(self.valor("seq2"), SEQ2)
        txt = self.texto("[data-componente=comparador]").lower()
        self.assertNotIn("frameshift", txt)

    def test_alinhar_variante_com_origem(self):
        i = next(k for k in range(len(SEQ1)) if SEQ1[k] != SEQ2[k])
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        self.aplicar("seq1", "substituir", i, "G")
        href = self.js("document.querySelector('[data-componente=mutacoes] "
                       "a[data-acao=alinhar-com-origem]').getAttribute('href')")
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        self.assertEqual(urllib.parse.urlparse(href).path, "/at4")
        self.assertEqual(q["seq1"], [SEQ1])
        self.assertEqual(q["seq2"], [SEQ1[:i] + "G" + SEQ1[i + 1:]])


class TestApresentacao(BaseViz):
    def entrar(self):
        self.js("document.querySelector('[data-acao=apresentacao]').click(), true")
        self.pausa(300)

    def test_atalhos_e_tipografia(self):
        self.executar("/at1", {"seq": "CCATGGCTAAACCGTAAGG", "modo": "guiado"})
        h1 = "parseFloat(getComputedStyle(document.querySelector('h1')).fontSize)"
        normal = self.js(h1)
        self.entrar()
        self.assertEqual(self.js("document.documentElement.getAttribute('data-apresentacao')"),
                         "true")
        self.assertGreater(self.js(h1), normal * 1.15, "tipografia ampliada")
        self.js("document.activeElement && document.activeElement.blur(), true")
        self.tecla("ArrowRight")
        self.tecla("ArrowRight")
        self.assertEqual(self.estado()["k"], 3, "→ avança o player em modo apresentação")
        self.tecla("ArrowLeft")
        self.assertEqual(self.estado()["k"], 2)
        n = self.estado()["n"]
        self.tecla_letra("f")
        self.assertEqual(self.estado()["k"], n, "F leva ao resultado final")
        self.tecla_esc()
        self.assertNotEqual(self.js("document.documentElement.getAttribute('data-apresentacao')"),
                            "true", "Esc sai do modo apresentação")

    def tecla_letra(self, ch):
        for tipo in ("rawKeyDown", "char", "keyUp"):
            extra = {"text": ch} if tipo == "char" else {}
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key=ch, code=f"Key{ch.upper()}",
                         windowsVirtualKeyCode=ord(ch.upper()), **extra)
        self.pausa(150)

    def tecla_esc(self):
        for tipo in ("rawKeyDown", "keyUp"):
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key="Escape", code="Escape",
                         windowsVirtualKeyCode=27)
        self.pausa(200)

    def test_botao_em_todas_as_paginas(self):
        for caminho in ("/", "/at1", "/at2", "/at3", "/at4", "/casos", "/historico", "/sobre"):
            self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}{caminho}", 1366, 900))
            self.assertEqual(self.js("document.querySelectorAll('[data-acao=apresentacao]')"
                                     ".length"), 1, caminho)


ESPIAO = r"""(() => {
  const orig = window.fetch.bind(window);
  window.__reqs = []; window.__erros = 0;
  window.addEventListener('error', () => { window.__erros += 1; });
  window.fetch = async (u, o) => {
    const url = String(u);
    window.__reqs.push([url, o && o.body && typeof o.body === 'string' ? o.body : '']);
    const resp = await orig(u, o);
    if (window.__adulterar && url.endsWith('/api/all')) {
      const j = await resp.clone().json();
      return new Response(JSON.stringify(window.__adulterar(j)), {status: resp.status,
        headers: {'Content-Type': 'application/json; charset=utf-8'}});
    }
    return resp;
  };
})();"""


class BaseLabEspiao(BaseLab):
    def com_espiao(self, extra=""):
        return self.nav.cmd("Page.addScriptToEvaluateOnNewDocument",
                            source=ESPIAO + extra)["identifier"]

    def sem_espiao(self, sid):
        self.nav.cmd("Page.removeScriptToEvaluateOnNewDocument", identifier=sid)

    def reqs_all(self):
        return self.js("window.__reqs.filter(r => r[0].endsWith('/api/all'))"
                       ".map(r => JSON.parse(r[1]))")


class TestMapaCompleto(BaseLabEspiao):
    """Pré-revisão 1/2/7: trilha AT4 com alinhamentos e diferenças; marcadores das duas
    trilhas apontam para a base certa; falhas sem produto; teclado; dados da API."""

    def test_trilha_de_alinhamento_completa(self):
        rf = fluxo(SEQ1, SEQ2)
        self.abrir_lab(SEQ1, SEQ2, "Mapa da expressão gênica")
        for r in rf.alinhamentos:
            base = f"[data-trilha=alinhamento] [data-alinhamento={r.metodo}]"
            got = self.js("(() => { const q = c => document.querySelector("
                          f"'{base} [data-campo=' + c + ']'); return ['alinhado1', 'marcadores',"
                          " 'alinhado2'].map(c => q(c) && q(c).getAttribute('data-valor')); })()")
            self.assertEqual(got, [r.alinhado1, r.marcadores, r.alinhado2], r.metodo)
            dif = self.js(f"Array.from(document.querySelectorAll('{base} [data-diferenca]'))"
                          ".map(e => +e.getAttribute('data-indice'))")
            self.assertEqual(dif, [i for i, m in enumerate(r.marcadores) if m != "|"], r.metodo)

    def test_todos_os_marcadores_das_duas_trilhas(self):
        rf = fluxo(SEQ1, SEQ2)
        self.abrir_lab(SEQ1, SEQ2, "Mapa da expressão gênica")
        for nome, cad in (("seq1", rf.seq1), ("seq2", rf.seq2)):
            alvos = [("at1", "start", cad.at1.posicao_start, cad.at1.sequencia, cad.at1.eventos),
                     ("at1", "stop", cad.at1.posicao_stop, cad.at1.sequencia, cad.at1.eventos),
                     ("at3", "start", cad.at3.posicao_start, cad.at3.regiao_transcrita,
                      cad.at3.eventos),
                     ("at3", "stop", cad.at3.posicao_stop, cad.at3.regiao_transcrita,
                      cad.at3.eventos)]
            alvos += [("at2", "intron", i.posicao_gu, cad.at2.sequencia, cad.at2.eventos)
                      for i in cad.at2.introns]
            for fase, marca, idx, fita, eventos in alvos:
                with self.subTest(trilha=nome, fase=fase, marca=marca):
                    sel = f"[data-trilha={nome}] [data-fase={fase}] [data-marca={marca}]"
                    self.assertEqual(self.js(f"document.querySelectorAll({sel!r}).length"), 1)
                    self.assertEqual(self.js(f"document.querySelector({sel!r})"
                                             ".getAttribute('data-indice')"), str(idx))
                    foco = self.js(f"(() => {{ const m = document.querySelector({sel!r});"
                                   " m.focus(); return document.activeElement === m; })()")
                    self.assertTrue(foco, "marcador deve ser focável (botão)")
                    self.tecla("Enter")
                    insp = self.texto("[data-regiao=inspetor]")
                    self.assertIn(f"Posição {idx}", insp)
                    self.assertIn(f"Base {fita[idx]}", insp)
                    for ev in eventos:
                        if ev.posicao == idx:
                            self.assertIn(ev.tipo, insp)

    def test_falhas_sem_produto_e_etapa_de_falha(self):
        rf = fluxo(FALHA1, FALHA2)
        self.abrir_lab(FALHA1, FALHA2, "Mapa da expressão gênica")
        for nome, cad in (("seq1", rf.seq1), ("seq2", rf.seq2)):
            self.assertEqual(self.js(f"document.querySelector('[data-trilha={nome}]')"
                                     ".getAttribute('data-etapa-falha')"), cad.etapa_falha)
            prod = self.js(f"Array.from(document.querySelectorAll('[data-trilha={nome}] "
                           "[data-fase]')).map(f => f.querySelector('[data-campo=produto]') ?"
                           " f.querySelector('[data-campo=produto]').getAttribute('data-valor') :"
                           " null)")
            fases = [cad.at1, cad.at2, cad.at3]
            esperado = [None if (f is None or not f.ok) else v for f, v in zip(
                fases, [getattr(cad.at1, "pre_mrna", None),
                        getattr(cad.at2, "mrna_maduro", None) if cad.at2 else None,
                        getattr(cad.at3, "proteina", None) if cad.at3 else None])]
            self.assertEqual(prod, esperado, nome)

    def test_dados_do_mapa_vem_da_api(self):
        sid = self.com_espiao("window.__adulterar = j => { j.dados.seq1.at3.proteina = "
                              "'Xaa-Yaa'; return j; };")
        try:
            self.abrir_lab(SEQ1, SEQ2, "Mapa da expressão gênica")
            self.assertEqual(self.js("document.querySelector('[data-trilha=seq1] [data-fase=at3] "
                                     "[data-campo=produto]').getAttribute('data-valor')"),
                             "Xaa-Yaa")
            q = self.reqs_all()
            self.assertEqual((q[-1]["seq1"], q[-1]["seq2"]), (SEQ1, SEQ2))
        finally:
            self.sem_espiao(sid)

    def test_movimento_reduzido_no_mapa(self):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": "reduce"}])
        url = (f"http://127.0.0.1:{self.porta}/?" + urllib.parse.urlencode(
            {"seq1": SEQ1, "seq2": SEQ2, "executar": "1", "modo": "animado"}))
        self.assertTrue(self.nav.abrir(url, 1366, 900, ESPERA))
        self.aba("Mapa da expressão gênica")
        durs = self.js("""(() => {
          const s = v => Math.max(...v.split(',').map(x => parseFloat(x) * (x.trim().endsWith('ms') ? 1 : 1000)));
          let m = 0;
          for (const e of document.querySelectorAll('[data-trilha], [data-trilha] *')) {
            const c = getComputedStyle(e); m = Math.max(m, s(c.transitionDuration), s(c.animationDuration));
          }
          const an = document.getAnimations().filter(a => a.playState === 'running')
            .map(a => a.effect && a.effect.getTiming().duration || 0);
          return {css: m, js: an.length ? Math.max(...an) : 0};
        })()""")
        self.assertLessEqual(durs["css"], 10, durs)
        self.assertLessEqual(durs["js"], 10, durs)

    def test_entradas_longas_tem_teto_de_dom(self):
        longo1 = "CC" + "ATG" + "GCT" * 1000 + "TAAGG"
        longo2 = "CC" + "ATG" + "GCA" * 1000 + "TAAGG"
        self.abrir_lab(longo1, longo2)
        for aba in ("Mapa da expressão gênica", "Comparador molecular", "Relatório final"):
            self.aba(aba)
            self.assertLess(self.js("document.querySelectorAll('main *').length"), 8000, aba)


class TestComparadorCompleto(BaseLabEspiao):
    def niveis(self):
        return self.js("Object.fromEntries(Array.from(document.querySelectorAll('[data-nivel]'))"
                       ".map(n => [n.getAttribute('data-nivel'), {"
                       " a: (n.querySelector('[data-lado=seq1]') || {getAttribute: () => null})"
                       ".getAttribute('data-valor'),"
                       " b: (n.querySelector('[data-lado=seq2]') || {getAttribute: () => null})"
                       ".getAttribute('data-valor'),"
                       " dif: Array.from(n.querySelectorAll('[data-diferenca]'))"
                       ".map(e => +e.getAttribute('data-indice')),"
                       " txt: n.textContent}]))")

    def test_valores_dos_dois_lados_e_indices_exatos(self):
        rf = fluxo(SEQ1, SEQ2)
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        nv = self.niveis()
        pares = {"dna": (SEQ1, SEQ2), "pre-mrna": (rf.seq1.at1.pre_mrna, rf.seq2.at1.pre_mrna),
                 "rna-processado": (rf.seq1.at2.rna_processado, rf.seq2.at2.rna_processado),
                 "proteina": (rf.seq1.at3.proteina, rf.seq2.at3.proteina)}
        for nivel, (a, b) in pares.items():
            self.assertEqual((nv[nivel]["a"], nv[nivel]["b"]), (a, b), nivel)
            if nivel == "proteina":
                a, b = a.split("-"), b.split("-")
            self.assertEqual(nv[nivel]["dif"], [i for i in range(min(len(a), len(b)))
                                                if a[i] != b[i]], nivel)

    def test_comprimentos_diferentes_e_indisponibilidade_por_nivel(self):
        ins = SEQ2[:5] + "G" + SEQ2[5:]
        self.abrir_lab(SEQ1, ins, "Comparador molecular")
        nv = self.niveis()
        self.assertIn("comprimentos diferentes", nv["dna"]["txt"].lower())
        rf = fluxo(SEQ1, FALHA2)
        self.abrir_lab(SEQ1, FALHA2, "Comparador molecular")
        nv = self.niveis()
        self.assertEqual((nv["pre-mrna"]["a"], nv["pre-mrna"]["b"]),
                         (rf.seq1.at1.pre_mrna, rf.seq2.at1.pre_mrna))
        for nivel in ("rna-processado", "proteina"):
            self.assertIn("indisponível", nv[nivel]["txt"].lower(), nivel)
            self.assertEqual(nv[nivel]["dif"], [], nivel)


class TestMutacoesCompleto(BaseLabEspiao):
    def mutar(self, alvo, op, pos, base=None):
        self.js("(() => { const set = (c, v) => { const e = document.querySelector("
                "`[data-componente=mutacoes] [data-campo=${c}]`); e.value = v;"
                " e.dispatchEvent(new Event('change', {bubbles: true})); };"
                f" set('mut-alvo', {alvo!r}); set('mut-operacao', {op!r});"
                f" set('mut-posicao', {str(pos)!r});"
                + (f" set('mut-base', {base!r});" if base else "")
                + " document.querySelector('[data-componente=mutacoes] "
                "[data-acao=aplicar-mutacao]').click(); return true; })()")
        for _ in range(40):
            self.pausa(250)
            if self.js(ESPERA):
                break
        self.pausa(300)

    def reverter(self):
        self.js("document.querySelector('[data-componente=mutacoes] [data-acao=reverter]')"
                ".click(), true")
        for _ in range(40):
            self.pausa(250)
            if self.js(ESPERA):
                break
        self.pausa(300)

    def historico(self):
        return self.js("Array.from(document.querySelectorAll('[data-regiao=mutacoes-historico] "
                       "[data-mutacao]')).map(e => e.textContent.replace(/\\s+/g, ' ').trim())")

    def test_encadeadas_reexecutam_pela_api_e_revertem_em_ordem(self):
        sid = self.com_espiao()
        try:
            self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
            self.mutar("seq1", "substituir", 0, "G")
            v1 = "G" + SEQ1[1:]
            self.mutar("seq1", "inserir", len(v1), "A")      # inserir no fim é válido
            v2 = v1 + "A"
            self.assertEqual(self.valor("seq1"), v2)
            q = self.reqs_all()
            self.assertEqual([x["seq1"] for x in q[-2:]], [v1, v2], "cada mutação chama /api/all")
            h = self.historico()
            self.assertEqual(len(h), 2)
            self.assertIn("0", h[0])
            self.assertIn("C→G", h[0].replace(" ", ""))
            self.assertIn("+A", h[1].replace(" ", ""))
            self.reverter()
            self.assertEqual(self.valor("seq1"), v1)
            self.reverter()
            self.assertEqual(self.valor("seq1"), SEQ1)
            self.assertEqual(self.historico(), [])
            self.assertEqual(self.reqs_all()[-1]["seq1"], SEQ1, "reverter reexecuta pela API")
        finally:
            self.sem_espiao(sid)

    def test_alvo_seq2_e_origem_por_alvo(self):
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        self.mutar("seq2", "remover", 3)
        var = SEQ2[:3] + SEQ2[4:]
        self.assertEqual(self.valor("seq2"), var)
        self.assertEqual(self.valor("seq1"), SEQ1)
        href = self.js("document.querySelector('[data-componente=mutacoes] "
                       "a[data-acao=alinhar-com-origem]').getAttribute('href')")
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        self.assertEqual((q["seq1"], q["seq2"]), ([SEQ2], [var]))

    def test_indices_fora_do_intervalo(self):
        self.abrir_lab(SEQ1, SEQ2, "Comparador molecular")
        n = len(SEQ1)
        for op, pos in (("substituir", n), ("remover", n), ("inserir", n + 1), ("remover", -1)):
            with self.subTest(op=op, pos=pos):
                self.mutar("seq1", op, pos, "A")
                self.assertEqual(self.valor("seq1"), SEQ1)
                self.assertIn("fora do intervalo",
                              self.texto("[data-regiao=mutacoes-erro]").lower())


class TestApresentacaoCompleta(BaseLabEspiao):
    def entrar(self):
        self.js("document.querySelector('[data-acao=apresentacao]').click(), true")
        self.pausa(300)

    def esc(self):
        for tipo in ("rawKeyDown", "keyUp"):
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key="Escape", code="Escape",
                         windowsVirtualKeyCode=27)
        self.pausa(200)

    def letra(self, ch):
        for tipo in ("rawKeyDown", "char", "keyUp"):
            extra = {"text": ch} if tipo == "char" else {}
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key=ch, code=f"Key{ch.upper()}",
                         windowsVirtualKeyCode=ord(ch.upper()), **extra)
        self.pausa(200)

    def test_espaco_alterna_e_E_exporta(self):
        sid = self.com_espiao()
        try:
            self.executar("/at1", {"seq": "CCATGGCTAAACCGTAAGG", "modo": "guiado"})
            self.entrar()
            self.js("document.activeElement && document.activeElement.blur(), true")
            self.tecla(" ")
            self.assertEqual(self.estado()["tocando"], "true")
            self.tecla(" ")
            self.assertEqual(self.estado()["tocando"], "false")
            self.letra("e")
            self.pausa(600)
            self.assertTrue(self.js("window.__reqs.some(r => r[0].endsWith('/api/exportar'))"),
                            "E deve exportar pela API")
        finally:
            self.sem_espiao(sid)

    def test_atalhos_ignorados_em_campos_de_texto(self):
        self.executar("/at1", {"seq": "CCATGGCTAAACCGTAAGG", "modo": "guiado"})
        self.entrar()
        self.aba("Entrada")
        self.js("document.querySelector('[data-campo=sequencias]').focus(), true")
        k = self.js("(() => { const p = document.querySelector('[data-componente=player] "
                    "[data-regiao=passo]'); return p ? p.textContent : ''; })()")
        self.js("document.querySelector('[data-campo=sequencias]').focus(), true")
        self.tecla("ArrowRight")
        self.letra("f")
        self.assertEqual(self.js("(() => { const p = document.querySelector("
                                 "'[data-componente=player] [data-regiao=passo]');"
                                 " return p ? p.textContent : ''; })()"), k)

    def test_entra_e_sai_em_todas_as_paginas_sem_erros(self):
        sid = self.com_espiao()
        try:
            for caminho in ("/", "/at1", "/at2", "/at3", "/at4", "/casos", "/historico",
                            "/sobre"):
                with self.subTest(pagina=caminho):
                    self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}{caminho}",
                                                   1366, 900))
                    self.entrar()
                    self.assertEqual(self.js("document.documentElement.getAttribute("
                                             "'data-apresentacao')"), "true")
                    self.js("document.activeElement && document.activeElement.blur(), true")
                    for t in ("ArrowRight", "ArrowLeft"):
                        self.tecla(t)
                    self.letra("f")
                    self.esc()
                    self.assertNotEqual(self.js("document.documentElement.getAttribute("
                                                "'data-apresentacao')"), "true")
                    self.assertEqual(self.js("window.__erros"), 0, "atalhos sem ação não geram erro")
        finally:
            self.sem_espiao(sid)


class TestSemInterpretacaoNoJS(unittest.TestCase):
    def test_js_sem_rotulos_de_mutacao(self):
        raiz = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "js"
        for arq in raiz.rglob("*.js"):
            t = arq.read_text(encoding="utf-8").lower()
            for termo in ("missense", "nonsense", "frameshift", "silenciosa"):
                self.assertNotIn(termo, t, f"{arq.name}: {termo}")


if __name__ == "__main__":
    unittest.main()
