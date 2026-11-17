"""Testes de aceite da AT2 — BioCompiler 2.0 (OS-M2-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: enunciado "4.2 Especificacao_BioCompiler_2_0 2026.2_VERSION 2.docx"
§§2–14; docs/SPEC.md §4.2 e §5.2; docs/DECISIONS.md D009 (distância do
branch point), D010 (precedência dos erros), D011 (diagnósticos extras).
Somente biblioteca padrão.
"""

import dataclasses
import random
import time
import typing
import unittest

from biocompiler.core.at2 import maturar_pre_mrna
from biocompiler.modelos import Evento, Intron, ResultadoAT2

CORRETO = "CORRETO"
SITIO5 = "BUG - sítio 5' ausente"
SITIO3 = "BUG - sítio 3' ausente"
BRANCH = "BUG - branch point"
VAZIA = "BUG - entrada vazia"
INVALIDA = "BUG - base inválida"
SEM_INTRON = "BUG - íntron ausente"
CAP = "m7Gppp"
CAUDA = "A" * 100


def intron(gap, antes=4):
    """GU + C*antes + A + C*gap + AG: `gap` bases entre o A e o AG."""
    return "GU" + "C" * antes + "A" + "C" * gap + "AG"


def _oraculo(s):
    """Implementação independente de SPEC §4.2/§5.2 + D009–D011 (força bruta)."""
    if s == "":
        return VAZIA, None, ()
    if any(c not in "AUCG" for c in s):
        return INVALIDA, None, ()
    gus = [i for i in range(len(s) - 1) if s[i:i + 2] == "GU"]
    ags = [i for i in range(len(s) - 1) if s[i:i + 2] == "AG"]
    introns, cursor = [], 0
    while True:
        achou = None
        for g in (g for g in gus if g >= cursor):
            for j in (j for j in ags if j >= g + 2):
                ks = [k for k in range(g + 2, j) if s[k] == "A" and 10 <= j - k - 1 <= 30]
                if ks:
                    achou = (g, max(ks), j)
                    break
            if achou:
                break
        if not achou:
            break
        introns.append(achou)
        cursor = achou[2] + 2
    if introns:
        rna, p = "", 0
        for g, _, j in introns:
            rna, p = rna + s[p:g], j + 2
        return CORRETO, rna + s[p:], tuple(introns)
    if any(j >= g + 2 for g in gus for j in ags):
        return BRANCH, None, ()
    if ags:
        return SITIO5, None, ()
    if gus:
        return SITIO3, None, ()
    return SEM_INTRON, None, ()


class TestCasosDoProfessor(unittest.TestCase):
    """Enunciado §14: quatro exemplos (espaços e marcadores removidos)."""

    def test_caso1_correto(self):
        seq = "CCCGUCCCCACCCCCCCCCCAGCCC"
        r = maturar_pre_mrna(seq)
        self.assertIsInstance(r, ResultadoAT2)
        self.assertEqual((r.ok, r.status, r.resultado), (True, "OK", CORRETO))
        self.assertEqual(r.rna_processado, "CCCCCC")
        self.assertEqual(r.mrna_maduro, CAP + "CCCCCC" + CAUDA)
        self.assertEqual(r.cap, CAP)
        self.assertEqual(r.cauda_adicionada, CAUDA)
        self.assertEqual(r.introns, (Intron(3, 9, 20),))

    def test_casos_de_erro(self):
        casos = [
            ("CCCCCCCCACCCCCCCCCCAGCCC", SITIO5),
            ("CCCGUCCCCACCCCCCCCCCCCCCC", SITIO3),
            ("CCCGU" + "C" * 16 + "AAGCCC", BRANCH),
        ]
        for seq, esperado in casos:
            with self.subTest(seq=seq):
                r = maturar_pre_mrna(seq)
                self.assertEqual((r.ok, r.status, r.resultado), (False, "ERRO", esperado))
                self.assertIsNone(r.mrna_maduro)
                self.assertIsNone(r.rna_processado)
                self.assertIsNone(r.cap)
                self.assertIsNone(r.cauda_adicionada)
                self.assertEqual(r.introns, ())

    def test_entrada_txt_do_enunciado(self):
        # Enunciado §2 (sem respostas no documento; conferido à mão pelo CTO).
        r = maturar_pre_mrna("CCUAUGGCUGUAACCUUUAACUAACAAGAUGGCCUAC")
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.introns, (Intron(9, 12, 26),))
        self.assertEqual(r.rna_processado, "CCUAUGGCUAUGGCCUAC")
        self.assertEqual(maturar_pre_mrna("CCUAUGGCUCUAACCUUUAAACCUAACAGGAUGGCCUAC").resultado, SITIO5)
        self.assertEqual(maturar_pre_mrna("CCUAUGGCUGUCCUUUCCUUCCUUCCAGGAUGGCCUAC").resultado, BRANCH)

    def test_exemplo_integrado_da_spec(self):
        # SPEC §11.1: pré-mRNA da Seq1 → CCAUGGCUAAACCGUAAGG.
        seq = "CCAUGGCUGUCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGUAAGG"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.rna_processado, "CCAUGGCUAAACCGUAAGG")
        self.assertEqual(r.mrna_maduro, CAP + "CCAUGGCUAAACCGUAAGG" + CAUDA)


class TestBranchPointD009(unittest.TestCase):
    def test_limites_9_10_30_31(self):
        for gap, esperado in ((9, BRANCH), (10, CORRETO), (30, CORRETO), (31, BRANCH)):
            with self.subTest(gap=gap):
                seq = "CC" + intron(gap) + "CC"
                self.assertEqual(maturar_pre_mrna(seq).resultado, esperado)

    def test_posicao_do_branch_no_limite(self):
        r = maturar_pre_mrna("CC" + intron(10) + "CC")
        self.assertEqual(r.introns, (Intron(2, 8, 19),))
        self.assertEqual(r.introns[0].posicao_ag - r.introns[0].posicao_branch - 1, 10)
        r = maturar_pre_mrna("CC" + intron(30) + "CC")
        self.assertEqual(r.introns[0].posicao_ag - r.introns[0].posicao_branch - 1, 30)

    def test_a_imediatamente_apos_gu_e_valido(self):
        seq = "CCGUA" + "C" * 10 + "AGCC"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.introns, (Intron(2, 4, 15),))

    def test_a_antes_do_gu_nao_conta(self):
        # A em 0, GU em 2, AG em 16: 15 entre, mas o A está fora do íntron.
        self.assertEqual(maturar_pre_mrna("ACGU" + "C" * 12 + "AGCC").resultado, BRANCH)

    def test_varios_a_escolhe_o_mais_proximo_do_ag(self):
        seq = "GU" + "A" + "C" * 5 + "A" + "C" * 12 + "AGC"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.introns, (Intron(0, 8, 21),))

    def test_a_proximo_demais_e_a_distante_valido(self):
        # A a 3 do AG (inválido) e A a 20 do AG (válido): escolhe o válido.
        seq = "GU" + "C" + "A" + "C" * 16 + "A" + "CCC" + "AG"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.introns[0].posicao_branch, 3)

    def test_a_do_proprio_ag_nao_e_branch(self):
        self.assertEqual(maturar_pre_mrna("GU" + "C" * 12 + "AG").resultado, BRANCH)


class TestPrecedenciaD010D011(unittest.TestCase):
    def test_vazia(self):
        r = maturar_pre_mrna("")
        self.assertEqual((r.ok, r.status, r.resultado), (False, "ERRO", VAZIA))

    def test_base_invalida_tem_precedencia(self):
        for seq in ("CCCGUCCCCACCCCCCCCCCAGCCT", "cccgu", "CCC GU", "CCGU\r", "CCXAG", "ATG"):
            with self.subTest(seq=repr(seq)):
                r = maturar_pre_mrna(seq)
                self.assertEqual(r.resultado, INVALIDA)
                self.assertIsNone(r.mrna_maduro)

    def test_posicoes_invalidas(self):
        self.assertEqual(maturar_pre_mrna("ATGT").bases_invalidas, ((1, "T"), (3, "T")))
        self.assertEqual(maturar_pre_mrna("CCC").bases_invalidas, ())

    def test_sem_sinal_algum(self):
        for seq in ("C", "CCCCAAAUUU", "UGCA", "A"):
            with self.subTest(seq=seq):
                self.assertEqual(maturar_pre_mrna(seq).resultado, SEM_INTRON)

    def test_ag_somente_antes_de_gu_e_sitio5(self):
        # Linhas do arquivo "40 casos modelo oficial" (D010): AG em j e GU em j+1.
        for seq in ("UCUCCCCCCCCACCCCCCCCCCCCCCAGUCUCCC",
                    "UCCUCCCCCCCACCCCCCCCCCCCCCCCCAGUCCUCC",
                    "UCCCUCCCCCCACCCCCCCCCCCAGUCCCUC",
                    "CCAGCCCCGUCC"):
            with self.subTest(seq=seq):
                self.assertEqual(maturar_pre_mrna(seq).resultado, SITIO5)

    def test_par_gu_ag_sem_branch_vence_sitios_orfaos(self):
        # AG órfão antes, par GU→AG sem A válido depois → branch point.
        self.assertEqual(maturar_pre_mrna("CAGCGU" + "C" * 12 + "AGGU").resultado, BRANCH)

    def test_gu_ag_sobrepostos_nao_formam_par(self):
        # "GUAG": AG em 2 = g+2 forma par; "AGU": AG em 0 antes do GU em 1 não.
        self.assertEqual(maturar_pre_mrna("GUAG").resultado, BRANCH)
        self.assertEqual(maturar_pre_mrna("AGU").resultado, SITIO5)
        self.assertEqual(maturar_pre_mrna("CCGUCC").resultado, SITIO3)

    def test_sitios_informativos(self):
        r = maturar_pre_mrna("CAGUCCAGU")
        self.assertEqual(r.sitios_gu, (2, 7))
        self.assertEqual(r.sitios_ag, (1, 6))
        self.assertEqual(maturar_pre_mrna("").sitios_gu, ())
        self.assertEqual(maturar_pre_mrna("GUX").sitios_ag, ())


class TestSelecaoESplicing(unittest.TestCase):
    def test_primeiro_gu_e_escolhido(self):
        seq = "CCGUCGU" + "CC" + "A" + "C" * 10 + "AGCC"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.introns[0].posicao_gu, 2)
        self.assertEqual(r.rna_processado, "CCCC")

    def test_menor_ag_que_satisfaz_branch(self):
        # Primeiro AG válido termina o íntron; o segundo AG fica no éxon.
        seq = "CC" + intron(10) + "CCCCCAGCC"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.introns, (Intron(2, 8, 19),))
        self.assertEqual(r.rna_processado, "CC" + "CCCCCAGCC")

    def test_ag_cedo_demais_e_pulado(self):
        # AG em 6 sem A elegível; AG seguinte com A a 12 entre → íntron até ele.
        seq = "GUCCCCAG" + "A" + "C" * 12 + "AGUU"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.introns, (Intron(0, 8, 21),))
        self.assertEqual(r.rna_processado, "UU")

    def test_dois_introns(self):
        seq = "CC" + intron(10) + "UU" + intron(12) + "GG"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(len(r.introns), 2)
        self.assertEqual(r.rna_processado, "CCUUGG")

    def test_remocao_inclusiva_sem_tocar_vizinhos(self):
        seq = "GGG" + intron(10) + "UUU"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.rna_processado, "GGGUUU")

    def test_juncao_nova_nao_e_reinterpretada(self):
        # Após remover o íntron, "G"+"UCCA..." forma GU…A…AG na junção; não é re-splicado.
        seq = "CCG" + intron(10) + "UCCA" + "C" * 10 + "AGCC"
        r = maturar_pre_mrna(seq)
        self.assertEqual(len(r.introns), 1)
        self.assertEqual(r.rna_processado, "CCGUCCA" + "C" * 10 + "AGCC")

    def test_gu_residual_nao_invalida(self):
        seq = "CC" + intron(10) + "CCGUCC"
        r = maturar_pre_mrna(seq)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.rna_processado, "CCCCGUCC")

    def test_intron_ocupa_tudo(self):
        r = maturar_pre_mrna(intron(10))
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.rna_processado, "")
        self.assertEqual(r.mrna_maduro, CAP + CAUDA)

    def test_cauda_exata_e_cap_literal(self):
        r = maturar_pre_mrna("CC" + intron(15) + "GG")
        self.assertTrue(r.mrna_maduro.startswith("m7Gppp"))
        self.assertEqual(r.mrna_maduro[-101:], "G" + "A" * 100)
        self.assertEqual(len(r.mrna_maduro), len("m7Gppp") + len(r.rna_processado) + 100)


class TestResultadoEstruturado(unittest.TestCase):
    def test_campos_e_anotacoes(self):
        self.assertEqual([f.name for f in dataclasses.fields(Intron)],
                         ["posicao_gu", "posicao_branch", "posicao_ag"])
        self.assertEqual([f.name for f in dataclasses.fields(ResultadoAT2)], [
            "sequencia", "ok", "status", "resultado", "mrna_maduro", "rna_processado",
            "cap", "cauda_adicionada", "bases_invalidas", "sitios_gu", "sitios_ag",
            "introns", "eventos"])
        self.assertEqual(typing.get_type_hints(Intron),
                         {"posicao_gu": int, "posicao_branch": int, "posicao_ag": int})
        self.assertEqual(typing.get_type_hints(ResultadoAT2), {
            "sequencia": str, "ok": bool, "status": str, "resultado": str,
            "mrna_maduro": str | None, "rna_processado": str | None,
            "cap": str | None, "cauda_adicionada": str | None,
            "bases_invalidas": tuple[tuple[int, str], ...],
            "sitios_gu": tuple[int, ...], "sitios_ag": tuple[int, ...],
            "introns": tuple[Intron, ...], "eventos": tuple[Evento, ...]})

    def test_imutaveis_sem_padroes(self):
        r = maturar_pre_mrna("CC" + intron(10))
        for obj in (r, r.introns[0]):
            with self.assertRaises(dataclasses.FrozenInstanceError):
                obj.ok = False  # type: ignore[misc]
        for cls in (Intron, ResultadoAT2):
            for f in dataclasses.fields(cls):
                self.assertIs(f.default, dataclasses.MISSING, f.name)
                self.assertIs(f.default_factory, dataclasses.MISSING, f.name)

    def test_eventos_correto(self):
        seq = "CCCGUCCCCACCCCCCCCCCAGCCC"
        E = Evento
        self.assertEqual(list(maturar_pre_mrna(seq).eventos), [
            E("BASES_VALIDADAS", None, ""),
            E("GU_CANDIDATO", 3, "GU"),
            E("AG_CANDIDATO", 20, "AG"),
            E("INTRON_SELECIONADO", 3, "GUCCCCACCCCCCCCCCAG"),
            E("BRANCH_POINT", 9, "A"),
            E("EXONS_UNIDOS", None, "CCCCCC"),
            E("CAP_ADICIONADA", None, "m7Gppp"),
            E("POLIA_ADICIONADA", None, "100"),
            E("RESULTADO", None, CORRETO)])

    def test_eventos_erros(self):
        E = Evento
        self.assertEqual(list(maturar_pre_mrna("").eventos), [E("RESULTADO", None, VAZIA)])
        self.assertEqual(list(maturar_pre_mrna("CTX").eventos), [
            E("BASE_INVALIDA", 1, "T"), E("BASE_INVALIDA", 2, "X"),
            E("RESULTADO", None, INVALIDA)])
        self.assertEqual(list(maturar_pre_mrna("AGUCCAG").eventos), [
            E("BASES_VALIDADAS", None, ""),
            E("GU_CANDIDATO", 1, "GU"),
            E("AG_CANDIDATO", 0, "AG"), E("AG_CANDIDATO", 5, "AG"),
            E("RESULTADO", None, BRANCH)])

    def test_eventos_dois_introns(self):
        seq = "CC" + intron(10) + "UU" + intron(12) + "GG"
        tipos = [e.tipo for e in maturar_pre_mrna(seq).eventos]
        self.assertEqual(tipos.count("INTRON_SELECIONADO"), 2)
        i = tipos.index("INTRON_SELECIONADO")
        self.assertEqual(tipos[i:i + 4], ["INTRON_SELECIONADO", "BRANCH_POINT",
                                          "INTRON_SELECIONADO", "BRANCH_POINT"])

    def test_determinismo(self):
        seq = "CC" + intron(10) + "UU" + intron(12) + "GG"
        self.assertEqual(maturar_pre_mrna(seq), maturar_pre_mrna(seq))


class TestPropriedades(unittest.TestCase):
    def test_aleatorio_contra_oraculo(self):
        rnd = random.Random(20261117)
        pedacos = ["GU", "AG", "A", "C", "U", "G", "CC", "CCCCC", "CCCCCCCCCC"]
        for _ in range(2500):
            if rnd.random() < 0.5:
                seq = "".join(rnd.choice(pedacos) for _ in range(rnd.randint(0, 20)))
            else:
                seq = ("".join(rnd.choice("CU") for _ in range(rnd.randint(0, 6)))
                       + intron(rnd.randint(5, 35), rnd.randint(0, 6))
                       + "".join(rnd.choice("ACGU") for _ in range(rnd.randint(0, 8))))
            if rnd.random() < 0.03 and seq:
                k = rnd.randrange(len(seq))
                seq = seq[:k] + rnd.choice("TNa") + seq[k + 1:]
            r = maturar_pre_mrna(seq)
            rotulo, rna, introns = _oraculo(seq)
            self.assertEqual(r.resultado, rotulo, seq)
            self.assertEqual(r.rna_processado, rna, seq)
            self.assertEqual(tuple((i.posicao_gu, i.posicao_branch, i.posicao_ag)
                                   for i in r.introns), introns, seq)
            if r.ok:
                self.assertEqual(r.mrna_maduro, CAP + r.rna_processado + CAUDA)
                fim = -1
                for i in r.introns:
                    self.assertGreater(i.posicao_gu, fim)
                    self.assertEqual(seq[i.posicao_gu:i.posicao_gu + 2], "GU")
                    self.assertEqual(seq[i.posicao_ag:i.posicao_ag + 2], "AG")
                    self.assertEqual(seq[i.posicao_branch], "A")
                    self.assertTrue(10 <= i.posicao_ag - i.posicao_branch - 1 <= 30)
                    fim = i.posicao_ag + 1
            else:
                self.assertIsNone(r.mrna_maduro)

    def test_sequencia_longa_sem_intron_valido(self):
        # 40 kb com 1000 pares GU/AG e nenhum A a 10–30 de um AG: pior caso de busca.
        bloco = "GU" + "C" * 36 + "AG"
        seq = bloco * 1000
        t0 = time.perf_counter()
        r = maturar_pre_mrna(seq)
        self.assertLess(time.perf_counter() - t0, 10.0)
        self.assertEqual(r.resultado, BRANCH)

    def test_sequencia_longa_com_muitos_introns(self):
        seq = ("CC" + intron(12)) * 2000 + "GG"
        t0 = time.perf_counter()
        r = maturar_pre_mrna(seq)
        self.assertLess(time.perf_counter() - t0, 10.0)
        self.assertEqual(len(r.introns), 2000)
        self.assertEqual(r.rna_processado, "CC" * 2000 + "GG")


if __name__ == "__main__":
    unittest.main()
