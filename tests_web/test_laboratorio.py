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
        self.tecla(" ")
        self.assertIn(self.estado()["tocando"], ("false", "true"))
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


class TestSemInterpretacaoNoJS(unittest.TestCase):
    def test_js_sem_rotulos_de_mutacao(self):
        raiz = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "js"
        for arq in raiz.rglob("*.js"):
            t = arq.read_text(encoding="utf-8").lower()
            for termo in ("missense", "nonsense", "frameshift", "silenciosa"):
                self.assertNotIn(termo, t, f"{arq.name}: {termo}")


if __name__ == "__main__":
    unittest.main()
