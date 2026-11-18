"""OS-M10-05 — Fluxo integrado e transições entre atividades (plano §12).

AT1 → AT2 → AT3: o produto de uma etapa é enviado como entrada da próxima (link profundo
com os valores exatos da API), com elemento compartilhado (`view-transition-name`) para
continuidade visual e indicação de origem. Laboratório: drill-down de fase no lugar,
com retorno preservando o foco. AT4 ligada explicitamente aos DNAs originais.
"""
import sys
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, DNA_OK, PRE_OK  # noqa: E402

from biocompiler import servicos  # noqa: E402
from biocompiler.exemplos import ALL_EXEMPLO  # noqa: E402

CSS = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "css"
ESPERA_LAB = ("(() => { const s = document.querySelector('[data-regiao=status]');"
              " return !!s && /conclu/i.test(s.textContent); })()")


REGISTRO_VT = r"""(() => {
  window.addEventListener('pagereveal', e => {
    window.__vt = !!e.viewTransition;
    window.__vtPulada = false;
    if (e.viewTransition) e.viewTransition.finished.catch(() => {}).then(() => {});
    if (e.viewTransition) {
      const orig = e.viewTransition.skipTransition.bind(e.viewTransition);
      e.viewTransition.skipTransition = () => { window.__vtPulada = true; return orig(); };
    }
  });
})();"""
ESPERA_EXEC = ("(() => { const s = document.querySelector('[data-regiao=status]');"
               " return !!s && /Conclu/i.test(s.textContent); })()")


class TestEnviarParaProxima(BaseViz):
    def link(self):
        return self.js("(() => { const a = document.querySelector('a[data-acao=enviar-proxima]');"
                       " return a ? a.getAttribute('href') : null; })()")

    def test_at1_envia_pre_mrna_para_at2(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        href = self.link()
        self.assertIsNotNone(href, "AT1 com resultado correto oferece 'enviar para BioCompiler 2.0'")
        u = urllib.parse.urlparse(href)
        q = urllib.parse.parse_qs(u.query)
        self.assertEqual(u.path, "/at2")
        self.assertEqual(q["seq"], [r.pre_mrna])
        self.assertEqual(q.get("origem"), ["at1"])
        self.assertEqual(q.get("executar"), ["1"])

    def test_at2_envia_mrna_maduro_para_at3_e_mostra_origem(self):
        r = servicos.processar_lote("at2", [PRE_OK])[0]
        self.executar("/at2", {"seq": PRE_OK, "modo": "rapido", "origem": "at1"})
        self.assertIn("BioCompiler 1.0", self.texto("[data-regiao=origem]"),
                      "chegada pela AT1 é indicada")
        href = self.link()
        q = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        self.assertEqual(urllib.parse.urlparse(href).path, "/at3")
        self.assertEqual(q["seq"], [r.mrna_maduro])
        self.assertEqual(q.get("origem"), ["at2"])
        self.assertEqual(q.get("executar"), ["1"])

    def test_sem_link_quando_a_etapa_falha(self):
        self.executar("/at1", {"seq": "CCGGCTAAACCGTAAGG", "modo": "rapido"})  # START ausente
        self.assertIsNone(self.link(), "não se envia produto inexistente")
        self.executar("/at2", {"seq": "CCAUGGCUAAACCGUAAGG", "modo": "rapido"})  # sem íntron
        self.assertIsNone(self.link(), "AT2 com falha não envia para o Ribossomo")

    def seguir(self, reduzir=False):
        """Clica no link real e espera a página seguinte executar."""
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": "reduce" if reduzir else ""}])
        sid = self.nav.cmd("Page.addScriptToEvaluateOnNewDocument", source=REGISTRO_VT)["identifier"]
        try:
            self.js("document.querySelector('a[data-acao=enviar-proxima]').click(), true")
            for _ in range(80):
                self.pausa(150)
                try:
                    if self.js(ESPERA_EXEC) and self.js("window.__vt !== undefined"):
                        break
                except RuntimeError:
                    pass
            self.pausa(300)
            return self.js("[location.pathname, window.__vt === true, window.__vtPulada === true]")
        finally:
            self.nav.cmd("Page.removeScriptToEvaluateOnNewDocument", identifier=sid)

    def test_navegacao_real_at1_at2_at3_com_transicao(self):
        r1 = servicos.processar_lote("at1", [DNA_OK])[0]
        r2 = servicos.processar_lote("at2", [r1.pre_mrna])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        self.assertIn("BioCompiler 2.0", self.texto("a[data-acao=enviar-proxima]"))
        caminho, vt, _ = self.seguir()
        self.assertEqual(caminho, "/at2")
        self.assertTrue(vt, "a navegação AT1 → AT2 executa uma view transition")
        self.assertIn("Recebido do BioCompiler 1.0", self.texto("[data-regiao=origem]"))
        self.assertEqual(self.js("document.querySelector('[data-campo=sequencias]').value.trim()"),
                         r1.pre_mrna)
        if r2.ok:
            self.assertIn("Ribossomo", self.texto("a[data-acao=enviar-proxima]"))
            caminho, vt, _ = self.seguir()
            self.assertEqual(caminho, "/at3")
            self.assertTrue(vt)
            self.assertIn("Recebido do BioCompiler 2.0", self.texto("[data-regiao=origem]"))

    def test_transicao_curta_e_pulada_com_movimento_reduzido(self):
        css = (CSS / "transicoes.css").read_text(encoding="utf-8")
        import re as _re
        for valor, unidade in _re.findall(r"animation-duration\s*:\s*([\d.]+)(ms|s)", css):
            ms = float(valor) * (1000 if unidade == "s" else 1)
            self.assertLessEqual(ms, 450, "transições entre páginas ≤ 450 ms")
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        caminho, vt, pulada = self.seguir(reduzir=True)
        self.assertEqual(caminho, "/at2")
        self.assertTrue((not vt) or pulada, "com movimento reduzido a transição é pulada")

    def test_elemento_compartilhado_entre_paginas(self):
        self.assertRegex((CSS / "transicoes.css").read_text(encoding="utf-8"),
                         r"@view-transition\s*\{\s*navigation\s*:\s*auto")
        nomes = {}
        for caminho, q in (("/at1", {"seq": DNA_OK}), ("/at2", {"seq": PRE_OK}),
                           ("/at3", {"seq": "m7GpppCCAUGGCUAAACCGUAAGG" + "A" * 100})):
            self.executar(caminho, dict(q, modo="rapido"))
            nomes[caminho] = self.js("Array.from(document.querySelectorAll('[data-viz] [data-fita]'))"
                                     ".map(e => getComputedStyle(e).viewTransitionName)"
                                     ".filter(n => n && n !== 'none')")
        self.assertIn("fita-produto", nomes["/at1"], "AT1: a fita do pré-mRNA é o elemento compartilhado")
        self.assertIn("fita-produto", nomes["/at2"])
        self.assertIn("fita-produto", nomes["/at3"])
        for k, v in nomes.items():
            self.assertEqual(v.count("fita-produto"), 1, f"{k}: nome único por página")


class TestLaboratorioDrillDown(BaseViz):
    def abrir_lab(self):
        url = (f"http://127.0.0.1:{self.porta}/?" + urllib.parse.urlencode(
            {"seq1": ALL_EXEMPLO[0], "seq2": ALL_EXEMPLO[1], "executar": "1", "modo": "rapido"}))
        self.assertTrue(self.nav.abrir(url, 1440, 900, ESPERA_LAB))
        self.aba("Mapa da expressão gênica")

    def test_detalhe_das_seis_fases_no_lugar_com_retorno_de_foco(self):
        rf = servicos.fluxo_completo(ALL_EXEMPLO[0], ALL_EXEMPLO[1], "both", 2, -1, -2)
        self.abrir_lab()
        url0 = self.js("location.href")
        for k, (trilha, cad) in enumerate((("seq1", rf.seq1), ("seq2", rf.seq2))):
            for fase, n_bases in (("at1", len(cad.at1.sequencia)), ("at2", len(cad.at2.sequencia)),
                                  ("at3", len(cad.at3.regiao_transcrita))):
                with self.subTest(trilha=trilha, fase=fase):
                    alvo = f"[data-trilha={trilha}] [data-fase={fase}] [data-acao=detalhar]"
                    self.js(f"document.querySelector({alvo!r}).focus(), true")
                    self.tecla("Enter")
                    self.pausa(600)
                    self.assertEqual(self.js("location.href"), url0, "abre no lugar")
                    det = f"[data-detalhe-fase={fase}][data-trilha-origem={trilha}]"
                    fita = "pre-mrna" if fase == "at2" else ("mrna" if fase == "at3" else "dna")
                    n = self.js(f"document.querySelectorAll('{det} [data-viz={fase}] "
                                f"[data-fita={fita}] [data-base]').length")
                    self.assertTrue(0 < n <= 600 and (n == n_bases or n == 600),
                                    f"visualização real da fase ({n} bases, esperado {n_bases})")
                    if (k + len(fase)) % 2 == 0:
                        for tipo in ("rawKeyDown", "keyUp"):
                            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key="Escape",
                                         code="Escape", windowsVirtualKeyCode=27)
                    else:
                        self.js(f"document.querySelector('{det} [data-acao=fechar-detalhe]').click(), true")
                    self.pausa(500)
                    self.assertFalse(self.js(f"!!document.querySelector({det!r})"), "fecha")
                    self.assertTrue(self.js(f"document.activeElement === document.querySelector({alvo!r})"),
                                    "o foco volta ao botão de origem")

    def test_alinhamento_ligado_aos_dnas_originais(self):
        self.abrir_lab()
        origens = self.js("Array.from(document.querySelectorAll('[data-trilha=alinhamento] "
                          "[data-origem-dna]')).map(e => [e.getAttribute('data-origem-dna'),"
                          " e.getAttribute('data-valor')])")
        self.assertEqual(sorted(origens), sorted([["seq1", ALL_EXEMPLO[0]], ["seq2", ALL_EXEMPLO[1]]]))
        txt = self.texto("[data-trilha=alinhamento]").lower()
        self.assertIn("dna original", txt)
        vis = self.js("Array.from(document.querySelectorAll('[data-trilha=alinhamento] "
                      "[data-origem-dna]')).map(e => { const r = e.getBoundingClientRect();"
                      " return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; })")
        self.assertEqual(vis, [True, True], "origens visíveis")
        for n in ("seq1", "seq2"):
            self.assertTrue(self.js(f"(() => {{ const c = document.querySelector('[data-conexao-dna={n}]');"
                                    " if (!c) return false; const r = c.getBoundingClientRect();"
                                    " return r.width > 0 || r.height > 0; })()"),
                            f"conexão visível entre a trilha AT4 e o DNA original de {n}")


if __name__ == "__main__":
    unittest.main()
