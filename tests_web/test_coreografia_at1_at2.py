"""OS-M10-03 — Coreografias AT1 e AT2 (Frente A; plano §8 e §9).

AT1: cursor científico que acompanha a posição real do evento; trincas surgem a partir
do START; transcrição com correspondência posicional exata (o pré-mRNA nasce da própria
fita); diagnóstico com foco só em posição determinada pela API.
AT2: splicing na MESMA fita (o íntron sai e os éxons se aproximam), CAP encaixada no 5′,
cauda no 3′ e legenda removido/preservado/adicionado com as contagens reais.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz, DNA_INV, DNA_OK, PRE_2INT, PRE_OK  # noqa: E402

from biocompiler import servicos  # noqa: E402

RET = ("(sel) => { const e = document.querySelector(sel); if (!e) return null;"
       " const r = e.getBoundingClientRect(); const c = getComputedStyle(e);"
       " return {x: r.left, y: r.top, w: r.width, h: r.height, op: +c.opacity,"
       " vis: c.visibility, disp: c.display, trans: c.transitionProperty}; }")


class BaseCoreo(BaseViz):
    def caixa(self, sel):
        return self.js(f"({RET})({sel!r})")

    def assentar(self, ms=650):
        self.pausa(ms)


class TestAT1Cursor(BaseCoreo):
    def test_cursor_acompanha_a_posicao_do_evento(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        cur = "[data-viz=at1] [data-cursor]"
        self.assertIsNotNone(self.caixa(cur), "cursor científico [data-cursor] ausente")
        self.assertIn("transform", self.caixa(cur)["trans"] + " all",
                      "o cursor desliza (transição de transform)")
        for k, ev in enumerate(r.eventos, start=1):
            if k > 1:
                self.clicar("proximo")
            if ev.posicao is None:
                continue
            self.assentar()
            c = self.caixa(cur)
            b = self.caixa(f"[data-viz=at1] [data-fita=dna] [data-base][data-indice=\"{ev.posicao}\"]")
            with self.subTest(k=k, evento=ev.tipo):
                self.assertLessEqual(abs(c["x"] - b["x"]), 2, "cursor sobre a posição do evento")
                if ev.tipo in ("CODON_LIDO", "START_ENCONTRADO", "STOP_EM_FASE", "STOP_FORA_DE_FASE"):
                    self.assertTrue(2.5 * b["w"] <= c["w"] <= 4.2 * b["w"], "cursor cobre a trinca")
                else:
                    self.assertLessEqual(c["w"], 1.6 * b["w"], "cursor cobre uma base")

    def test_trincas_surgem_a_partir_do_start(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        self.assertEqual(self.contar("[data-viz=at1] [data-codon]"), 0, "antes do START não há trincas")
        self.clicar("proximo")  # START_ENCONTRADO
        self.assentar()
        self.assertGreaterEqual(self.contar("[data-viz=at1] [data-codon]"), 1)
        self.clicar("fim")
        self.assentar()
        self.assertEqual(self.contar("[data-viz=at1] [data-codon]"), len(r.codons))


class TestAT1Transcricao(BaseCoreo):
    def test_pre_mrna_nasce_da_fita_com_correspondencia_posicional(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        self.ir_para(tipos.index("T_PARA_U"))
        self.assertEqual(self.contar("[data-viz=at1] [data-fita=pre-mrna] [data-base]"), 0,
                         "antes de T_PARA_U não há pré-mRNA")
        self.clicar("proximo")  # T_PARA_U
        self.assentar(900)
        xs = self.js("(() => { const d = Array.from(document.querySelectorAll('[data-viz=at1] "
                     "[data-fita=dna] [data-base]')).map(e => [+e.getAttribute('data-indice'),"
                     " e.getBoundingClientRect().left]); const p = Array.from(document.querySelectorAll("
                     "'[data-viz=at1] [data-fita=pre-mrna] [data-base]')).map(e => "
                     "[+e.getAttribute('data-indice'), e.getBoundingClientRect().left,"
                     " e.textContent.trim()]); return [d, p]; })()")
        dna, pre = xs
        self.assertEqual(len(pre), len(r.pre_mrna))
        pos = {i: x for i, x in dna}
        for i, x, letra in pre:
            self.assertLessEqual(abs(x - pos[i]), 1.5, f"base {i} desalinhada")
            self.assertEqual(letra, r.pre_mrna[i])


class TestAT1Diagnostico(BaseCoreo):
    def test_foco_so_em_posicao_determinada(self):
        r = servicos.processar_lote("at1", [DNA_INV])[0]
        self.executar("/at1", {"seq": DNA_INV, "modo": "rapido"})
        diag = self.texto("[data-viz=at1] [data-regiao=diagnostico]")
        self.assertIn(r.resultado, diag)
        foco = self.js("Array.from(document.querySelectorAll('[data-viz=at1] [data-foco]'))"
                       ".map(e => +e.getAttribute('data-indice'))")
        self.assertEqual(sorted(foco), sorted(i for i, _ in r.bases_invalidas))
        sem_pos = "CCGGCTAAACCGTAAGG"  # START ausente: nenhuma posição a destacar
        r2 = servicos.processar_lote("at1", [sem_pos])[0]
        self.executar("/at1", {"seq": sem_pos, "modo": "rapido"})
        self.assertIn(r2.resultado, self.texto("[data-viz=at1] [data-regiao=diagnostico]"))
        self.assertEqual(self.contar("[data-viz=at1] [data-foco]"), 0,
                         "sem posição determinada pela API, nada é destacado")


class TestAT2Splicing(BaseCoreo):
    def lacuna(self, i_fim_exon, i_ini_exon):
        a = self.caixa(f"[data-viz=at2] [data-fita=pre-mrna] [data-base][data-indice=\"{i_fim_exon}\"]")
        b = self.caixa(f"[data-viz=at2] [data-fita=pre-mrna] [data-base][data-indice=\"{i_ini_exon}\"]")
        return b["x"] - (a["x"] + a["w"]), a["w"]

    def test_exons_se_aproximam_na_mesma_fita(self):
        r = servicos.processar_lote("at2", [PRE_OK])[0]
        i = r.introns[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at2", {"seq": PRE_OK, "modo": "guiado"})
        antes, w = self.lacuna(i.posicao_gu - 1, i.posicao_ag + 2)
        tam = i.posicao_ag + 2 - i.posicao_gu
        self.assertGreaterEqual(antes, 0.8 * tam * w, "antes do splicing o íntron ocupa a fita")
        self.ir_para(tipos.index("EXONS_UNIDOS") + 1)
        self.assentar(1200)
        depois, w = self.lacuna(i.posicao_gu - 1, i.posicao_ag + 2)
        self.assertLessEqual(depois, 1.5 * w, "os éxons se encostam na mesma fita")
        meio = self.caixa(f"[data-viz=at2] [data-fita=pre-mrna] [data-base]"
                          f"[data-indice=\"{i.posicao_branch}\"]")
        base_exon = self.caixa(f"[data-viz=at2] [data-fita=pre-mrna] [data-base]"
                               f"[data-indice=\"{i.posicao_gu - 1}\"]")
        self.assertTrue(meio["op"] < 0.75 or abs(meio["y"] - base_exon["y"]) > base_exon["h"],
                        "o íntron sai da linha principal (esmaece ou se ergue)")

    def test_cap_no_5_e_cauda_no_3(self):
        r = servicos.processar_lote("at2", [PRE_OK])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at2", {"seq": PRE_OK, "modo": "guiado"})
        cap = "[data-viz=at2] [data-cap]"
        c0 = self.caixa(cap)
        self.assertTrue(c0 is None or c0["op"] < 0.1 or c0["disp"] == "none" or c0["w"] == 0,
                        "a CAP só aparece em CAP_ADICIONADA")
        self.ir_para(tipos.index("CAP_ADICIONADA") + 1)
        self.assentar()
        c = self.caixa(cap)
        primeira = self.js("(() => { const b = Array.from(document.querySelectorAll('[data-viz=at2] "
                           "[data-fita=pre-mrna] [data-base]')).filter(e => +getComputedStyle(e).opacity > 0.75)"
                           ".sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left)[0];"
                           " const q = b.getBoundingClientRect(); return [q.left, q.top, q.height]; })()")
        self.assertGreater(c["op"], 0.9)
        self.assertLessEqual(abs((c["x"] + c["w"]) - primeira[0]), 12, "CAP encostada na extremidade 5′")
        self.clicar("fim")
        self.assentar()
        cauda = self.caixa("[data-viz=at2] [data-cauda]")
        ultima = self.js("(() => { const b = Array.from(document.querySelectorAll('[data-viz=at2] "
                         "[data-fita=pre-mrna] [data-base]')).filter(e => +getComputedStyle(e).opacity > 0.75)"
                         ".sort((a, b) => b.getBoundingClientRect().right - a.getBoundingClientRect().right)[0];"
                         " return b.getBoundingClientRect().right; })()")
        self.assertLessEqual(abs(cauda["x"] - ultima), 12, "cauda encostada na extremidade 3′")

    def test_legenda_removido_preservado_adicionado(self):
        r = servicos.processar_lote("at2", [PRE_2INT])[0]
        self.executar("/at2", {"seq": PRE_2INT, "modo": "rapido"})
        leg = self.js("Object.fromEntries(Array.from(document.querySelectorAll('[data-viz=at2] "
                      "[data-legenda-maturacao] [data-categoria]')).map(e => "
                      "[e.getAttribute('data-categoria'), e.textContent.replace(/\\s+/g, ' ')]))")
        removido = sum(i.posicao_ag + 2 - i.posicao_gu for i in r.introns)
        self.assertIn(f"{removido} nt", leg.get("removido", ""))
        self.assertIn(f"{len(r.rna_processado)} nt", leg.get("preservado", ""))
        self.assertIn("m7Gppp", leg.get("adicionado", ""))
        self.assertIn(str(len(r.cauda_adicionada)), leg.get("adicionado", ""))


if __name__ == "__main__":
    unittest.main()
