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

    def test_sem_link_quando_a_etapa_falha(self):
        self.executar("/at1", {"seq": "CCGGCTAAACCGTAAGG", "modo": "rapido"})  # START ausente
        self.assertIsNone(self.link(), "não se envia produto inexistente")

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

    def test_detalhe_da_fase_no_lugar_e_retorno_com_foco(self):
        self.abrir_lab()
        url0 = self.js("location.href")
        alvo = "[data-trilha=seq1] [data-fase=at2] [data-acao=detalhar]"
        self.js(f"document.querySelector({alvo!r}).focus(), true")
        self.tecla("Enter")
        self.pausa(600)
        self.assertEqual(self.js("location.href"), url0, "o detalhe abre no lugar, sem navegar")
        det = "[data-detalhe-fase=at2][data-trilha-origem=seq1]"
        self.assertTrue(self.js(f"!!document.querySelector({det!r})"))
        self.assertTrue(self.js(f"!!document.querySelector('{det} [data-viz=at2]')"),
                        "o detalhe mostra a visualização real da AT2")
        for tipo in ("rawKeyDown", "keyUp"):
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key="Escape", code="Escape",
                         windowsVirtualKeyCode=27)
        self.pausa(500)
        self.assertFalse(self.js(f"!!document.querySelector({det!r})"), "Esc fecha o detalhe")
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


if __name__ == "__main__":
    unittest.main()
