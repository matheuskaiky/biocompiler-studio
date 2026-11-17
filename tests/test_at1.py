"""Testes de aceite da AT1 — BioCompiler 1.0 (OS-M1-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: enunciado "AT1 - BioCompiler 1.0.pdf" §§2–14; docs/SPEC.md §4.1 e §5.1;
docs/DECISIONS.md D007 (frameshift × STOP ausente) e D008 (entrada vazia).
Somente biblioteca padrão.
"""

import dataclasses
import random
import time
import typing
import unittest

from biocompiler.core.at1 import transcrever_dna
from biocompiler.modelos import Evento, ResultadoAT1

CORRETO = "CORRETO"
BASE_INVALIDA = "BUG - base inválida"
START_AUSENTE = "BUG - START ausente"
STOP_AUSENTE = "BUG - STOP ausente"
FRAMESHIFT = "BUG - frameshift"
NONSENSE = "BUG - nonsense / STOP prematuro"
ENTRADA_VAZIA = "BUG - entrada vazia"
STOPS = ("TAA", "TAG", "TGA")


def _oraculo(seq):
    """Classificação independente, escrita a partir de SPEC §5.1 + D007/D008."""
    if seq == "":
        return ENTRADA_VAZIA
    if any(c not in "ATCG" for c in seq):
        return BASE_INVALIDA
    inicio = next((i for i in range(len(seq) - 2) if seq[i:i + 3] == "ATG"), None)
    if inicio is None:
        return START_AUSENTE
    em_fase = [i for i in range(inicio, len(seq) - 2, 3) if seq[i:i + 3] in STOPS]
    if len(em_fase) >= 2:
        return NONSENSE
    if len(em_fase) == 1:
        return CORRETO
    return FRAMESHIFT if (len(seq) - inicio) % 3 else STOP_AUSENTE


class TestCasosDoProfessor(unittest.TestCase):
    """Enunciado §14: seis linhas, rótulos e pré-mRNA literais."""

    CASOS = [
        ("ATGGCTAAACCGTAA", CORRETO, "AUGGCUAAACCGUAA"),
        ("ATGGCTXAACCGTAA", BASE_INVALIDA, None),
        ("CCCGCTAAACCGTAA", START_AUSENTE, None),
        ("ATGGCTAAACCGGGC", STOP_AUSENTE, None),
        ("ATGGCTAAAACCGTAA", FRAMESHIFT, None),
        ("ATGGCTTAACCGGGCTAA", NONSENSE, None),
    ]

    def test_seis_casos(self):
        for seq, esperado, pre in self.CASOS:
            with self.subTest(seq=seq):
                r = transcrever_dna(seq)
                self.assertIsInstance(r, ResultadoAT1)
                self.assertEqual(r.resultado, esperado)
                self.assertEqual(r.pre_mrna, pre)
                self.assertEqual(r.ok, esperado == CORRETO)
                self.assertEqual(r.status, "OK" if esperado == CORRETO else "ERRO")
                self.assertEqual(r.sequencia, seq)

    def test_exemplo_de_entrada_txt_com_flancos(self):
        # Enunciado §2: arquivo entrada.txt de exemplo; todas válidas.
        for seq in ("CCCATGGCTAAACCGTAA", "GGGATGCCCGGGTAG", "TTTATGAAACCCGGGTGA"):
            with self.subTest(seq=seq):
                r = transcrever_dna(seq)
                self.assertEqual(r.resultado, CORRETO)
                self.assertEqual(r.pre_mrna, seq.replace("T", "U"))

    def test_detalhes_do_caso_correto(self):
        # Enunciado §14.1: "START: ATG - OK", "STOP: TAA - OK".
        r = transcrever_dna("ATGGCTAAACCGTAA")
        self.assertEqual(r.posicao_start, 0)
        self.assertEqual(r.posicao_stop, 12)
        self.assertEqual(r.codon_stop, "TAA")
        self.assertEqual(r.codons, ("ATG", "GCT", "AAA", "CCG", "TAA"))
        self.assertEqual(r.utr5, "")
        self.assertEqual(r.utr3, "")


class TestPrecedenciaEPolitica(unittest.TestCase):
    """SPEC §5.1 (com D007/D008): ordem de verificação e convenções."""

    def test_entrada_vazia(self):
        r = transcrever_dna("")
        self.assertEqual((r.ok, r.status, r.resultado, r.pre_mrna),
                         (False, "ERRO", ENTRADA_VAZIA, None))

    def test_base_invalida_tem_precedencia(self):
        # Sem ATG e com base inválida: base inválida vence.
        self.assertEqual(transcrever_dna("CCCXCC").resultado, BASE_INVALIDA)
        # Base inválida depois de uma ORF correta também invalida a linha.
        self.assertEqual(transcrever_dna("ATGGCTAAACCGTAAN").resultado, BASE_INVALIDA)

    def test_caracteres_invalidos_diversos(self):
        for seq in ("atggctaaaccgtaa", "ATGGCTAAACCGTAa", "ATG GCTAAACCGTAA",
                    " ATGGCTAAACCGTAA", "ATGGCTAAACCGTAA ", "ATGGCTAAACCGTAA\r",
                    "AUGGCUAAACCGUAA", "ATG-GCT", "ATGÇ", "ATG\tGCT"):
            with self.subTest(seq=repr(seq)):
                r = transcrever_dna(seq)
                self.assertEqual(r.resultado, BASE_INVALIDA)
                self.assertIsNone(r.pre_mrna)

    def test_posicoes_de_todas_as_bases_invalidas(self):
        r = transcrever_dna("AXGGCTYAA")
        self.assertEqual(r.bases_invalidas, ((1, "X"), (6, "Y")))
        self.assertEqual(transcrever_dna("ATGGCTAAACCGTAA").bases_invalidas, ())

    def test_start_ausente(self):
        for seq in ("A", "AT", "CCCC", "TAATAGTGA", "ATAGATCGA", "GTA"):
            with self.subTest(seq=seq):
                r = transcrever_dna(seq)
                self.assertEqual(r.resultado, START_AUSENTE)
                self.assertIsNone(r.posicao_start)

    def test_primeiro_atg_e_o_usado(self):
        # Primeiro ATG em 1 (o ATG em 4 é só um códon interno da leitura).
        r = transcrever_dna("CATGATGAAATAA")
        self.assertEqual(r.posicao_start, 1)
        # A partir de 1: ATG ATG AAA TAA → STOP em fase em 10.
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.posicao_stop, 10)

    def test_primeiro_atg_mesmo_sem_stop_enquanto_outro_atg_teria(self):
        # Primeiro ATG em 0: ATG CAT GAA ATA A → sem STOP em fase, resto 1 → frameshift.
        # (Um ATG em 4 teria ATG AAA TAA, mas não é o primeiro.)
        r = transcrever_dna("ATGCATGAAATAA")
        self.assertEqual(r.posicao_start, 0)
        self.assertEqual(r.resultado, FRAMESHIFT)

    def test_atg_sobreposto(self):
        # "AATGATG": primeiro ATG em 1.
        self.assertEqual(transcrever_dna("AATGATGTAA").posicao_start, 1)

    def test_atg_nao_e_stop_e_o_proprio_start_entra_na_leitura(self):
        r = transcrever_dna("ATGTAA")
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.codons, ("ATG", "TAA"))

    def test_tres_stops(self):
        for stop in STOPS:
            with self.subTest(stop=stop):
                r = transcrever_dna("ATGCCC" + stop)
                self.assertEqual(r.resultado, CORRETO)
                self.assertEqual(r.codon_stop, stop)
                self.assertEqual(r.posicao_stop, 6)

    def test_stop_fora_de_fase_nao_conta_como_stop(self):
        # ATG GTA AC: TAA em 4 fora de fase; sem STOP em fase.
        r = transcrever_dna("ATGGTAAC")
        self.assertIsNone(r.posicao_stop)
        self.assertEqual(r.stops_em_fase, ())
        self.assertEqual(r.stops_fora_de_fase, (4,))
        self.assertEqual(r.resultado, FRAMESHIFT)  # resto 2

    def test_d007_stop_fora_de_fase_nao_decide(self):
        # Caso 4 do professor: TAA fora de fase em 5, comprimento múltiplo de 3.
        r = transcrever_dna("ATGGCTAAACCGGGC")
        self.assertEqual(r.stops_fora_de_fase, (5,))
        self.assertEqual(r.resultado, STOP_AUSENTE)
        # Sem nenhum STOP em qualquer fase e resto != 0 → frameshift.
        self.assertEqual(transcrever_dna("ATGCCCG").resultado, FRAMESHIFT)
        self.assertEqual(transcrever_dna("ATGCCCGG").resultado, FRAMESHIFT)
        self.assertEqual(transcrever_dna("ATGCCC").resultado, STOP_AUSENTE)
        self.assertEqual(transcrever_dna("ATG").resultado, STOP_AUSENTE)

    def test_d007_limite_documentado_com_flanco_3(self):
        # Caso 5 + "C": resto 2 → frameshift; caso 5 + "CC": resto 0 → STOP ausente.
        self.assertEqual(transcrever_dna("ATGGCTAAAACCGTAAC").resultado, FRAMESHIFT)
        self.assertEqual(transcrever_dna("ATGGCTAAAACCGTAACC").resultado, STOP_AUSENTE)

    def test_resto_do_quadro(self):
        self.assertEqual(transcrever_dna("ATGGCTAAAACCGTAA").resto_quadro, 1)
        self.assertEqual(transcrever_dna("CCATGCC").resto_quadro, 2)
        self.assertEqual(transcrever_dna("ATGGCTAAACCGGGC").resto_quadro, 0)
        self.assertIsNone(transcrever_dna("CCC").resto_quadro)

    def test_nonsense_dois_ou_mais_stops_em_fase(self):
        r = transcrever_dna("ATGGCTTAACCGGGCTAA")
        self.assertEqual(r.stops_em_fase, (6, 15))
        self.assertEqual(r.posicao_stop, 6)
        self.assertEqual(r.codon_stop, "TAA")
        self.assertEqual(r.codons, ("ATG", "GCT", "TAA"))
        self.assertEqual(transcrever_dna("ATGTAATAGTGA").stops_em_fase, (3, 6, 9))
        self.assertEqual(transcrever_dna("ATGTAATAGTGA").resultado, NONSENSE)
        # Segundo STOP em fase depois de bases que não fecham trinca no fim.
        self.assertEqual(transcrever_dna("ATGTGACCCTAGCC").resultado, NONSENSE)

    def test_correto_com_bases_apos_stop_sem_segundo_stop_em_fase(self):
        # Enunciado §4: bases depois do STOP podem existir.
        for seq in ("ATGAAATAAG", "ATGAAATAAGG", "ATGAAATAAGGGCCC", "ATGAAATAATTAA"):
            with self.subTest(seq=seq):
                r = transcrever_dna(seq)
                self.assertEqual(r.resultado, CORRETO, seq)
                self.assertEqual(r.utr3, seq[9:])
                self.assertEqual(r.pre_mrna, seq.replace("T", "U"))

    def test_utrs(self):
        r = transcrever_dna("GGCATGCCCTAGTT")
        self.assertEqual((r.utr5, r.utr3), ("GGC", "TT"))
        self.assertEqual(r.codons, ("ATG", "CCC", "TAG"))

    def test_codons_sem_stop_vao_ate_ultima_trinca_completa(self):
        r = transcrever_dna("CATGCCCGGGA")
        self.assertEqual(r.codons, ("ATG", "CCC", "GGG"))
        self.assertEqual(r.utr3, "")
        self.assertEqual(r.resultado, FRAMESHIFT)

    def test_campos_de_erro_antes_da_leitura(self):
        for seq in ("", "ATGX"):
            with self.subTest(seq=seq):
                r = transcrever_dna(seq)
                self.assertIsNone(r.posicao_start)
                self.assertIsNone(r.posicao_stop)
                self.assertIsNone(r.codon_stop)
                self.assertIsNone(r.resto_quadro)
                self.assertEqual(r.codons, ())
                self.assertEqual(r.stops_em_fase, ())
                self.assertEqual(r.stops_fora_de_fase, ())
                self.assertEqual((r.utr5, r.utr3), ("", ""))


class TestTranscricao(unittest.TestCase):
    def test_sequencia_inteira_inclusive_flancos(self):
        seq = "TTTATGTTTTAATTT"
        r = transcrever_dna(seq)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.pre_mrna, "UUUAUGUUUUAAUUU")
        self.assertEqual(len(r.pre_mrna), len(seq))

    def test_sem_pre_mrna_em_qualquer_erro(self):
        for seq in ("", "ATGX", "CCC", "ATGCCC", "ATGCCCC", "ATGTAATAA"):
            with self.subTest(seq=seq):
                r = transcrever_dna(seq)
                self.assertFalse(r.ok)
                self.assertIsNone(r.pre_mrna)


class TestResultadoEstruturado(unittest.TestCase):
    def test_imutavel(self):
        r = transcrever_dna("ATGGCTAAACCGTAA")
        self.assertTrue(dataclasses.is_dataclass(r))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.resultado = "x"  # type: ignore[misc]

    def test_campos_exatos(self):
        nomes = [f.name for f in dataclasses.fields(ResultadoAT1)]
        self.assertEqual(nomes, [
            "sequencia", "ok", "status", "resultado", "pre_mrna", "bases_invalidas",
            "posicao_start", "posicao_stop", "codon_stop", "stops_em_fase",
            "stops_fora_de_fase", "codons", "utr5", "utr3", "resto_quadro", "eventos",
        ])
        self.assertEqual([f.name for f in dataclasses.fields(Evento)],
                         ["tipo", "posicao", "detalhe"])

    def test_evento_imutavel(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            Evento("X", None, "").tipo = "Y"  # type: ignore[misc]

    def test_sem_valores_padrao(self):
        for cls in (Evento, ResultadoAT1):
            for f in dataclasses.fields(cls):
                with self.subTest(classe=cls.__name__, campo=f.name):
                    self.assertIs(f.default, dataclasses.MISSING)
                    self.assertIs(f.default_factory, dataclasses.MISSING)

    def test_anotacoes(self):
        self.assertEqual(typing.get_type_hints(Evento),
                         {"tipo": str, "posicao": int | None, "detalhe": str})
        self.assertEqual(typing.get_type_hints(ResultadoAT1), {
            "sequencia": str, "ok": bool, "status": str, "resultado": str,
            "pre_mrna": str | None,
            "bases_invalidas": tuple[tuple[int, str], ...],
            "posicao_start": int | None, "posicao_stop": int | None,
            "codon_stop": str | None,
            "stops_em_fase": tuple[int, ...], "stops_fora_de_fase": tuple[int, ...],
            "codons": tuple[str, ...], "utr5": str, "utr3": str,
            "resto_quadro": int | None, "eventos": tuple[Evento, ...],
        })

    def test_eventos_completos_por_classe_de_erro(self):
        E = Evento
        casos = {
            # nonsense: leitura continua após o 1º STOP; TAA fora de fase não há.
            "ATGGCTTAACCGGGCTAA": [
                E("BASES_VALIDADAS", None, ""), E("START_ENCONTRADO", 0, "ATG"),
                E("CODON_LIDO", 0, "ATG"), E("CODON_LIDO", 3, "GCT"),
                E("CODON_LIDO", 6, "TAA"), E("STOP_EM_FASE", 6, "TAA"),
                E("CODON_LIDO", 9, "CCG"), E("CODON_LIDO", 12, "GGC"),
                E("CODON_LIDO", 15, "TAA"), E("STOP_EM_FASE", 15, "TAA"),
                E("RESULTADO", None, NONSENSE)],
            # frameshift com STOPs fora de fase (5 e 13) e resto 1.
            "ATGGCTAAAACCGTAA": [
                E("BASES_VALIDADAS", None, ""), E("START_ENCONTRADO", 0, "ATG"),
                E("CODON_LIDO", 0, "ATG"), E("CODON_LIDO", 3, "GCT"),
                E("CODON_LIDO", 6, "AAA"), E("CODON_LIDO", 9, "ACC"),
                E("CODON_LIDO", 12, "GTA"),
                E("STOP_FORA_DE_FASE", 5, "TAA"), E("STOP_FORA_DE_FASE", 13, "TAA"),
                E("RESULTADO", None, FRAMESHIFT)],
            # STOP ausente com flanco 5′ e STOP fora de fase em 7.
            "CCATGGCTAAACCGGGC": [
                E("BASES_VALIDADAS", None, ""), E("START_ENCONTRADO", 2, "ATG"),
                E("CODON_LIDO", 2, "ATG"), E("CODON_LIDO", 5, "GCT"),
                E("CODON_LIDO", 8, "AAA"), E("CODON_LIDO", 11, "CCG"),
                E("CODON_LIDO", 14, "GGC"),
                E("STOP_FORA_DE_FASE", 7, "TAA"),
                E("RESULTADO", None, STOP_AUSENTE)],
            "GGCATGTGACC": [
                E("BASES_VALIDADAS", None, ""), E("START_ENCONTRADO", 3, "ATG"),
                E("CODON_LIDO", 3, "ATG"), E("CODON_LIDO", 6, "TGA"),
                E("STOP_EM_FASE", 6, "TGA"),
                E("T_PARA_U", None, "GGCAUGUGACC"),
                E("RESULTADO", None, CORRETO)],
        }
        for seq, esperado in casos.items():
            with self.subTest(seq=seq):
                self.assertEqual(list(transcrever_dna(seq).eventos), esperado)

    def test_eventos_correto(self):
        r = transcrever_dna("CCATGGCTAAACCGTAAGG")
        self.assertTrue(all(isinstance(e, Evento) for e in r.eventos))
        tipos = [e.tipo for e in r.eventos]
        self.assertEqual(tipos[0], "BASES_VALIDADAS")
        self.assertEqual(r.eventos[-1], Evento("RESULTADO", None, CORRETO))
        self.assertIn(Evento("START_ENCONTRADO", 2, "ATG"), r.eventos)
        self.assertEqual([e.posicao for e in r.eventos if e.tipo == "STOP_EM_FASE"], [14])
        self.assertEqual([e.posicao for e in r.eventos if e.tipo == "STOP_FORA_DE_FASE"], [7])
        lidos = [(e.posicao, e.detalhe) for e in r.eventos if e.tipo == "CODON_LIDO"]
        self.assertEqual(lidos, [(2, "ATG"), (5, "GCT"), (8, "AAA"), (11, "CCG"), (14, "TAA")])
        self.assertEqual(tipos[-2], "T_PARA_U")
        self.assertEqual(r.eventos[-2].detalhe, r.pre_mrna)

    def test_eventos_erros(self):
        r = transcrever_dna("AXGY")
        self.assertEqual(list(r.eventos), [
            Evento("BASE_INVALIDA", 1, "X"), Evento("BASE_INVALIDA", 3, "Y"),
            Evento("RESULTADO", None, BASE_INVALIDA)])
        self.assertEqual(list(transcrever_dna("").eventos),
                         [Evento("RESULTADO", None, ENTRADA_VAZIA)])
        self.assertEqual([e.tipo for e in transcrever_dna("CCC").eventos],
                         ["BASES_VALIDADAS", "RESULTADO"])
        tipos = [e.tipo for e in transcrever_dna("ATGTAATAA").eventos]
        self.assertNotIn("T_PARA_U", tipos)
        self.assertEqual(tipos.count("STOP_EM_FASE"), 2)

    def test_leitura_em_fase_continua_ate_o_fim(self):
        # CODON_LIDO cobre todas as trincas completas do START ao fim (para achar 2º STOP).
        r = transcrever_dna("ATGTAACCCGG")
        self.assertEqual([e.detalhe for e in r.eventos if e.tipo == "CODON_LIDO"],
                         ["ATG", "TAA", "CCC"])

    def test_determinismo_e_funcao_pura(self):
        a, b = transcrever_dna("CCATGGCTAAACCGTAAGG"), transcrever_dna("CCATGGCTAAACCGTAAGG")
        self.assertEqual(a, b)


class TestPropriedades(unittest.TestCase):
    def test_aleatorio_contra_oraculo_e_invariantes(self):
        rnd = random.Random(20261117)
        for _ in range(3000):
            n = rnd.randint(0, 40)
            seq = "".join(rnd.choice("ACGT") for _ in range(n))
            if rnd.random() < 0.05 and seq:
                k = rnd.randrange(len(seq))
                seq = seq[:k] + rnd.choice("NXu ") + seq[k + 1:]
            r = transcrever_dna(seq)
            self.assertEqual(r.resultado, _oraculo(seq), seq)
            if r.ok:
                self.assertEqual(r.pre_mrna, seq.replace("T", "U"))
                self.assertEqual(len(r.stops_em_fase), 1)
                self.assertEqual(r.utr5 + "".join(r.codons) + r.utr3, seq)
                self.assertEqual(r.codons[-1], r.codon_stop)
            else:
                self.assertIsNone(r.pre_mrna)
            for p in r.stops_em_fase:
                self.assertEqual((p - r.posicao_start) % 3, 0)
                self.assertIn(seq[p:p + 3], STOPS)
            for p in r.stops_fora_de_fase:
                self.assertNotEqual((p - r.posicao_start) % 3, 0)
                self.assertGreater(p, r.posicao_start)
                self.assertIn(seq[p:p + 3], STOPS)

    def test_sequencia_longa_linear(self):
        seq = "CC" + "ATG" + "GCT" * 200_000 + "TAA" + "GG"
        t0 = time.perf_counter()
        r = transcrever_dna(seq)
        self.assertLess(time.perf_counter() - t0, 5.0)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(len(r.pre_mrna), len(seq))


if __name__ == "__main__":
    unittest.main()
