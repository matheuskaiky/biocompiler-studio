"""Testes de aceite da AT3 — Ribossomo (OS-M3-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: enunciado "Ribossomo.pdf" §§2–14 (exemplos extraídos do PDF com contagem
exata de adeninas); docs/SPEC.md §4.3, §5.3, §5.4; docs/DECISIONS.md D012
(STOP na fase +1) e D013 (ordem, extras, código genético).
Somente biblioteca padrão.
"""

import dataclasses
import random
import time
import typing
import unittest

from biocompiler.core.at3 import traduzir_mrna
from biocompiler.core.genetic_code import CODIGO_GENETICO, CODONS_STOP
from biocompiler.modelos import Evento, ResultadoAT3

CORRETO = "CORRETO"
CAP_ERR = "BUG - CAP 5'"
START_AUSENTE = "BUG - START ausente"
STOP_AUSENTE = "BUG - STOP ausente"
QUADRO = "BUG - quadro de leitura"
CAUDA_ERR = "BUG - cauda poli-A"
VAZIA = "BUG - entrada vazia"
INVALIDA = "BUG - base inválida"
CAP = "m7Gppp"
CAUDA = "A" * 100

# Tabela padrão escrita pelo CTO, independente de core/genetic_code.py.
_REF = {}
for prefixo, aa in [("GC", "Ala"), ("CG", "Arg"), ("GG", "Gly"), ("CC", "Pro"),
                    ("AC", "Thr"), ("GU", "Val"), ("UC", "Ser"), ("CU", "Leu")]:
    for b in "UCAG":
        _REF[prefixo + b] = aa
_REF.update({
    "UUU": "Phe", "UUC": "Phe", "UUA": "Leu", "UUG": "Leu",
    "AUU": "Ile", "AUC": "Ile", "AUA": "Ile", "AUG": "Met",
    "UAU": "Tyr", "UAC": "Tyr", "UAA": "STOP", "UAG": "STOP",
    "CAU": "His", "CAC": "His", "CAA": "Gln", "CAG": "Gln",
    "AAU": "Asn", "AAC": "Asn", "AAA": "Lys", "AAG": "Lys",
    "GAU": "Asp", "GAC": "Asp", "GAA": "Glu", "GAG": "Glu",
    "UGU": "Cys", "UGC": "Cys", "UGA": "STOP", "UGG": "Trp",
    "AGU": "Ser", "AGC": "Ser", "AGA": "Arg", "AGG": "Arg",
})
STOPS = ("UAA", "UAG", "UGA")


def mrna(regiao, cauda=100):
    return CAP + regiao + "A" * cauda


def _oraculo(seq):
    """Implementação independente de SPEC §4.3/§5.3 + D012/D013."""
    if seq == "":
        return VAZIA, None
    if not seq.startswith(CAP):
        return CAP_ERR, None
    corpo = seq[6:]
    n = len(corpo) - len(corpo.rstrip("A"))
    if n != 100:
        return CAUDA_ERR, None
    reg = corpo[:-100]
    if any(c not in "AUCG" for c in reg):
        return INVALIDA, None
    ini = next((i for i in range(len(reg) - 2) if reg[i:i + 3] == "AUG"), None)
    if ini is None:
        return START_AUSENTE, None
    aas = []
    for i in range(ini, len(reg) - 2, 3):
        c = reg[i:i + 3]
        if c in STOPS:
            return CORRETO, "-".join(aas)
        aas.append(_REF[c])
    if any(reg[p:p + 3] in STOPS for p in range(ini + 1, len(reg) - 2, 3)):
        return QUADRO, None
    return STOP_AUSENTE, None


class TestCodigoGenetico(unittest.TestCase):
    def test_64_codons_e_tabela_padrao(self):
        self.assertIsInstance(CODIGO_GENETICO, dict)
        todos = {a + b + c for a in "UCAG" for b in "UCAG" for c in "UCAG"}
        self.assertEqual(set(CODIGO_GENETICO), todos)
        self.assertEqual(len(CODIGO_GENETICO), 64)
        for codon in sorted(todos):
            with self.subTest(codon=codon):
                self.assertEqual(CODIGO_GENETICO[codon], _REF[codon])

    def test_stops_e_aminoacidos(self):
        self.assertEqual(CODONS_STOP, frozenset(STOPS))
        self.assertEqual({c for c, a in CODIGO_GENETICO.items() if a == "STOP"}, set(STOPS))
        nomes = set(CODIGO_GENETICO.values()) - {"STOP"}
        self.assertEqual(len(nomes), 20)
        self.assertTrue(all(len(n) == 3 and n[0].isupper() and n[1:].islower() for n in nomes))


class TestCasosDoProfessor(unittest.TestCase):
    """Enunciado §14 — sequências extraídas do PDF (contagem exata de A)."""

    CASOS = [
        (CAP + "CCAUGGCUAAACCGUAAGG" + "A" * 100, CORRETO, "Met-Ala-Lys-Pro"),
        ("CCAUGGCUAAACCGUAAGG" + "A" * 100, CAP_ERR, None),
        (CAP + "CCGCCGCUAAACCGUAAGG" + "A" * 100, START_AUSENTE, None),
        (CAP + "CCAUGGCUAAACCGGGCGG" + "A" * 100, STOP_AUSENTE, None),
        (CAP + "CCAUGGCUAAAACCGUAAGG" + "A" * 100, QUADRO, None),
        (CAP + "CCAUGGCUAAACCGUAAGG" + "A" * 80, CAUDA_ERR, None),
    ]

    def test_seis_casos(self):
        for seq, esperado, proteina in self.CASOS:
            with self.subTest(esperado=esperado):
                r = traduzir_mrna(seq)
                self.assertIsInstance(r, ResultadoAT3)
                self.assertEqual(r.resultado, esperado)
                self.assertEqual(r.proteina, proteina)
                self.assertEqual(r.ok, esperado == CORRETO)
                self.assertEqual(r.status, "OK" if esperado == CORRETO else "ERRO")
                self.assertEqual(r.sequencia, seq)

    def test_detalhes_do_caso_correto(self):
        # Enunciado §9: CAP OK, START AUG, STOP UAA, cauda 100 A.
        r = traduzir_mrna(self.CASOS[0][0])
        self.assertTrue(r.cap_ok)
        self.assertEqual(r.tamanho_cauda, 100)
        self.assertEqual(r.regiao_transcrita, "CCAUGGCUAAACCGUAAGG")
        self.assertEqual((r.posicao_start, r.posicao_stop, r.codon_stop), (2, 14, "UAA"))
        self.assertEqual(r.codons, ("AUG", "GCU", "AAA", "CCG", "UAA"))
        self.assertEqual(r.aminoacidos, ("Met", "Ala", "Lys", "Pro"))
        self.assertEqual((r.utr5, r.utr3), ("CC", "GG"))

    def test_d012_casos_4_e_5(self):
        r4 = traduzir_mrna(self.CASOS[3][0])
        self.assertEqual(r4.stops_fora_de_fase, (7,))      # fase +2, acidental
        r5 = traduzir_mrna(self.CASOS[4][0])
        self.assertEqual(r5.stops_fora_de_fase, (7, 15))   # 15 está na fase +1

    def test_exemplo_integrado_spec(self):
        # SPEC §11.1: saídas da AT2 para Seq1/Seq2.
        self.assertEqual(traduzir_mrna(mrna("CCAUGGCUAAACCGUAAGG")).proteina, "Met-Ala-Lys-Pro")
        self.assertEqual(traduzir_mrna(mrna("CCAUGGCUAAUCCGUAAGG")).proteina, "Met-Ala-Asn-Pro")


class TestCapECauda(unittest.TestCase):
    def test_cap_exata_e_sensivel_a_caixa(self):
        for seq in ("M7Gppp", "m7gppp", "m7GPPP", " m7Gppp", "m7Gpp", "7Gppp", "Gppp", "m7G"):
            with self.subTest(prefixo=seq):
                r = traduzir_mrna(seq + "CCAUGUAAGG" + CAUDA)
                self.assertEqual(r.resultado, CAP_ERR)
                self.assertFalse(r.cap_ok)
                self.assertIsNone(r.tamanho_cauda)

    def test_cauda_99_100_101(self):
        for n, esperado in ((0, CAUDA_ERR), (1, CAUDA_ERR), (99, CAUDA_ERR),
                            (100, CORRETO), (101, CAUDA_ERR), (200, CAUDA_ERR)):
            with self.subTest(n=n):
                r = traduzir_mrna(mrna("CCAUGUAAGG", n))
                self.assertEqual(r.resultado, esperado)
                self.assertEqual(r.tamanho_cauda, n)

    def test_regiao_terminando_em_a_e_ambigua(self):
        # SPEC §5.3: bloco terminal máximo de A deve medir exatamente 100.
        r = traduzir_mrna(mrna("CCAUGUAAGA"))
        self.assertEqual(r.resultado, CAUDA_ERR)
        self.assertEqual(r.tamanho_cauda, 101)

    def test_cauda_interrompida(self):
        r = traduzir_mrna(CAP + "CCAUGUAAGG" + "A" * 50 + "C" + "A" * 50)
        self.assertEqual((r.resultado, r.tamanho_cauda), (CAUDA_ERR, 50))
        self.assertEqual(traduzir_mrna(CAP + "CCAUGUAAGG" + CAUDA + "a").resultado, CAUDA_ERR)

    def test_somente_cap(self):
        r = traduzir_mrna(CAP)
        self.assertEqual((r.resultado, r.tamanho_cauda), (CAUDA_ERR, 0))

    def test_regiao_vazia(self):
        r = traduzir_mrna(mrna(""))
        self.assertEqual(r.resultado, START_AUSENTE)
        self.assertEqual(r.regiao_transcrita, "")


class TestPrecedencia(unittest.TestCase):
    def test_vazia(self):
        r = traduzir_mrna("")
        self.assertEqual((r.ok, r.status, r.resultado, r.proteina), (False, "ERRO", VAZIA, None))
        self.assertFalse(r.cap_ok)

    def test_cap_antes_de_cauda_e_bases(self):
        self.assertEqual(traduzir_mrna("CCXAUG" + "A" * 3).resultado, CAP_ERR)

    def test_cauda_antes_de_bases(self):
        self.assertEqual(traduzir_mrna(mrna("CCXAUGUAAGG", 99)).resultado, CAUDA_ERR)

    def test_base_invalida(self):
        for reg in ("CCAUGXUAAGG", "ccaugcuaagg", "CCAUG UAAGG", "CCATGTAAGG", "CCAUGUAAG\r"):
            with self.subTest(reg=repr(reg)):
                r = traduzir_mrna(mrna(reg))
                self.assertEqual(r.resultado, INVALIDA)
                self.assertIsNone(r.proteina)

    def test_posicoes_invalidas_relativas_a_regiao(self):
        r = traduzir_mrna(mrna("CTXG"))
        self.assertEqual(r.bases_invalidas, ((1, "T"), (2, "X")))
        self.assertEqual(r.regiao_transcrita, "CTXG")

    def test_base_invalida_antes_de_start(self):
        self.assertEqual(traduzir_mrna(mrna("CCCXCC")).resultado, INVALIDA)


class TestTraducao(unittest.TestCase):
    def test_primeiro_aug(self):
        # Primeiro AUG em 1; leitura AUG AUG CCC UAA.
        r = traduzir_mrna(mrna("CAUGAUGCCCUAAGG"))
        self.assertEqual(r.posicao_start, 1)
        self.assertEqual(r.proteina, "Met-Met-Pro")

    def test_primeiro_aug_mesmo_que_outro_desse_certo(self):
        # Primeiro AUG em 0: AUG CAU GAA AUA AGG → sem STOP em fase; UAA em 10 é fase +1.
        r = traduzir_mrna(mrna("AUGCAUGAAAUAAGG"))
        self.assertEqual(r.posicao_start, 0)
        self.assertEqual(r.resultado, QUADRO)

    def test_tres_stops_encerram(self):
        for stop in STOPS:
            with self.subTest(stop=stop):
                r = traduzir_mrna(mrna("AUGCCC" + stop + "GG"))
                self.assertEqual(r.resultado, CORRETO)
                self.assertEqual(r.codon_stop, stop)
                self.assertEqual(r.proteina, "Met-Pro")

    def test_aug_seguido_de_stop(self):
        r = traduzir_mrna(mrna("AUGUAGCC"))
        self.assertEqual((r.proteina, r.aminoacidos), ("Met", ("Met",)))

    def test_para_no_primeiro_stop_em_fase(self):
        # Vários STOPs em fase não são erro na AT3 (D013).
        r = traduzir_mrna(mrna("AUGGCUUAACCGGGCUAAGG"))
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.proteina, "Met-Ala")
        self.assertEqual(r.posicao_stop, 6)
        self.assertEqual(r.utr3, "CCGGGCUAAGG")

    def test_utrs_nao_traduzidas(self):
        r = traduzir_mrna(mrna("GGGAUGUUUUGAUUUGG"))
        self.assertEqual(r.proteina, "Met-Phe")
        self.assertEqual((r.utr5, r.utr3), ("GGG", "UUUGG"))

    def test_todos_os_61_codons_codificadores(self):
        sentido = [c for c in sorted(_REF) if _REF[c] != "STOP"]
        reg = "AUG" + "".join(sentido) + "UAAGG"
        r = traduzir_mrna(mrna(reg))
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(r.aminoacidos, tuple(["Met"] + [_REF[c] for c in sentido]))
        self.assertEqual(r.proteina, "-".join(r.aminoacidos))
        self.assertNotIn("STOP", r.aminoacidos)

    def test_d012_fase_mais_1_quadro(self):
        for stop in STOPS:
            with self.subTest(stop=stop):
                # AUG CC + STOP: STOP em p=5, (5-0)%3 = 2 → fase +2.
                self.assertEqual(traduzir_mrna(mrna("AUGCC" + stop + "GG")).resultado, STOP_AUSENTE)
                # AUG C + STOP: STOP em p=4, (4-0)%3 = 1 → fase +1.
                self.assertEqual(traduzir_mrna(mrna("AUGC" + stop + "GG")).resultado, QUADRO)

    def test_d012_sem_stop_algum_e_stop_ausente(self):
        for reg in ("AUG", "AUGC", "AUGCC", "AUGCCCGG", "CCAUGCCCCCCCCGG"):
            with self.subTest(reg=reg):
                self.assertEqual(traduzir_mrna(mrna(reg)).resultado, STOP_AUSENTE)

    def test_d012_limite_delecao_documentado(self):
        # Caso 1 com uma base removida antes do STOP: UAA vai para a fase +2.
        self.assertEqual(traduzir_mrna(mrna("CCAUGGCUAAACCUAAGG")).resultado, STOP_AUSENTE)

    def test_stops_fora_de_fase_informativos(self):
        r = traduzir_mrna(mrna("AUGCUAAGUGACC"))
        # Em fase: AUG CUA AGU GAC C → sem STOP. Fora: UAA em 4 (fase +1), UGA em 8 (fase +2).
        self.assertEqual(r.stops_fora_de_fase, (4, 8))
        self.assertEqual(r.resultado, QUADRO)

    def test_codons_sem_stop_vao_ate_ultima_trinca(self):
        r = traduzir_mrna(mrna("CAUGCCCGGGC"))
        self.assertEqual(r.codons, ("AUG", "CCC", "GGG"))
        self.assertEqual(r.aminoacidos, ())
        self.assertIsNone(r.posicao_stop)


class TestResultadoEstruturado(unittest.TestCase):
    def test_campos_e_anotacoes(self):
        self.assertEqual([f.name for f in dataclasses.fields(ResultadoAT3)], [
            "sequencia", "ok", "status", "resultado", "proteina", "aminoacidos",
            "cap_ok", "tamanho_cauda", "regiao_transcrita", "bases_invalidas",
            "posicao_start", "posicao_stop", "codon_stop", "stops_fora_de_fase",
            "codons", "utr5", "utr3", "eventos"])
        self.assertEqual(typing.get_type_hints(ResultadoAT3), {
            "sequencia": str, "ok": bool, "status": str, "resultado": str,
            "proteina": str | None, "aminoacidos": tuple[str, ...],
            "cap_ok": bool, "tamanho_cauda": int | None,
            "regiao_transcrita": str | None,
            "bases_invalidas": tuple[tuple[int, str], ...],
            "posicao_start": int | None, "posicao_stop": int | None,
            "codon_stop": str | None, "stops_fora_de_fase": tuple[int, ...],
            "codons": tuple[str, ...], "utr5": str, "utr3": str,
            "eventos": tuple[Evento, ...]})

    def test_imutavel_sem_padroes(self):
        r = traduzir_mrna(mrna("AUGUAA" + "GG"))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.ok = False  # type: ignore[misc]
        for f in dataclasses.fields(ResultadoAT3):
            self.assertIs(f.default, dataclasses.MISSING, f.name)
            self.assertIs(f.default_factory, dataclasses.MISSING, f.name)

    def test_campos_em_erros_iniciais(self):
        casos = {
            "": (False, None, None),
            "CCAUG": (False, None, None),
            mrna("CCAUGUAAGG", 99): (True, 99, None),
            mrna("CCXG"): (True, 100, "CCXG"),
            mrna("CCCGG"): (True, 100, "CCCGG"),
        }
        for seq, (cap_ok, cauda, regiao) in casos.items():
            with self.subTest(seq=seq[:12]):
                r = traduzir_mrna(seq)
                self.assertEqual((r.cap_ok, r.tamanho_cauda, r.regiao_transcrita),
                                 (cap_ok, cauda, regiao))
                self.assertIsNone(r.posicao_start)
                self.assertIsNone(r.posicao_stop)
                self.assertIsNone(r.codon_stop)
                self.assertEqual((r.codons, r.stops_fora_de_fase, r.aminoacidos), ((), (), ()))
                self.assertEqual((r.utr5, r.utr3), ("", ""))
                self.assertIsNone(r.proteina)

    def test_eventos_correto(self):
        E = Evento
        self.assertEqual(list(traduzir_mrna(mrna("CCAUGGCUAAACCGUAAGG")).eventos), [
            E("CAP_VALIDADA", None, "m7Gppp"),
            E("POLIA_VALIDADA", None, "100"),
            E("BASES_VALIDADAS", None, ""),
            E("AUG_ENCONTRADO", 2, "AUG"),
            E("CODON_TRADUZIDO", 2, "AUG:Met"),
            E("CODON_TRADUZIDO", 5, "GCU:Ala"),
            E("CODON_TRADUZIDO", 8, "AAA:Lys"),
            E("CODON_TRADUZIDO", 11, "CCG:Pro"),
            E("STOP_ENCONTRADO", 14, "UAA"),
            E("STOP_FORA_DE_FASE", 7, "UAA"),
            E("PROTEINA_GERADA", None, "Met-Ala-Lys-Pro"),
            E("RESULTADO", None, CORRETO)])

    def test_stop_fora_de_fase_depois_do_stop_em_fase(self):
        # Pré-revisão P1: coleta na região inteira, sem entrar na tradução.
        E = Evento
        r = traduzir_mrna(mrna("AUGUAAGUAAGG"))
        self.assertEqual((r.resultado, r.proteina, r.posicao_stop), (CORRETO, "Met", 3))
        self.assertEqual(r.stops_fora_de_fase, (7,))
        self.assertEqual(r.codons, ("AUG", "UAA"))
        self.assertEqual(list(r.eventos), [
            E("CAP_VALIDADA", None, "m7Gppp"), E("POLIA_VALIDADA", None, "100"),
            E("BASES_VALIDADAS", None, ""), E("AUG_ENCONTRADO", 0, "AUG"),
            E("CODON_TRADUZIDO", 0, "AUG:Met"), E("STOP_ENCONTRADO", 3, "UAA"),
            E("STOP_FORA_DE_FASE", 7, "UAA"),
            E("PROTEINA_GERADA", None, "Met"), E("RESULTADO", None, CORRETO)])

    def test_eventos_erros(self):
        E = Evento
        self.assertEqual(list(traduzir_mrna("").eventos), [E("RESULTADO", None, VAZIA)])
        self.assertEqual(list(traduzir_mrna("CCAUG").eventos), [E("RESULTADO", None, CAP_ERR)])
        self.assertEqual(list(traduzir_mrna(mrna("CCAUG", 7)).eventos), [
            E("CAP_VALIDADA", None, "m7Gppp"), E("RESULTADO", None, CAUDA_ERR)])
        self.assertEqual(list(traduzir_mrna(mrna("CTG")).eventos), [
            E("CAP_VALIDADA", None, "m7Gppp"), E("POLIA_VALIDADA", None, "100"),
            E("BASE_INVALIDA", 1, "T"), E("RESULTADO", None, INVALIDA)])
        self.assertEqual(list(traduzir_mrna(mrna("CCCGG")).eventos), [
            E("CAP_VALIDADA", None, "m7Gppp"), E("POLIA_VALIDADA", None, "100"),
            E("BASES_VALIDADAS", None, ""), E("RESULTADO", None, START_AUSENTE)])
        # Quadro: lê todas as trincas completas; STOPs fora de fase ao final.
        self.assertEqual(list(traduzir_mrna(mrna("AUGCUAAGG")).eventos), [
            E("CAP_VALIDADA", None, "m7Gppp"), E("POLIA_VALIDADA", None, "100"),
            E("BASES_VALIDADAS", None, ""), E("AUG_ENCONTRADO", 0, "AUG"),
            E("CODON_TRADUZIDO", 0, "AUG:Met"), E("CODON_TRADUZIDO", 3, "CUA:Leu"),
            E("CODON_TRADUZIDO", 6, "AGG:Arg"),
            E("STOP_FORA_DE_FASE", 4, "UAA"),
            E("RESULTADO", None, QUADRO)])


class TestPropriedades(unittest.TestCase):
    def test_aleatorio_contra_oraculo(self):
        rnd = random.Random(20261117)
        for _ in range(3000):
            reg = "".join(rnd.choice("ACGU") for _ in range(rnd.randint(0, 30)))
            if rnd.random() < 0.5:
                reg = rnd.choice(["", "C", "GG"]) + "AUG" + reg
            reg = reg + rnd.choice(["G", "C", "U", "GG", ""])
            cauda = rnd.choice([100] * 8 + [99, 101, 0])
            cap = rnd.choice([CAP] * 9 + ["m7gppp", ""])
            seq = cap + reg + "A" * cauda
            if rnd.random() < 0.03 and reg:
                k = 6 + rnd.randrange(len(reg))
                seq = seq[:k] + rnd.choice("TNx") + seq[k + 1:]
            r = traduzir_mrna(seq)
            rotulo, prot = _oraculo(seq)
            self.assertEqual((r.resultado, r.proteina), (rotulo, prot), seq)
            if r.ok:
                self.assertEqual(len(r.aminoacidos), len(r.codons) - 1)
                self.assertIn(r.codon_stop, STOPS)
                self.assertEqual(r.utr5 + "".join(r.codons) + r.utr3, r.regiao_transcrita)
                self.assertEqual(seq, CAP + r.regiao_transcrita + CAUDA)

    def test_sequencia_longa(self):
        reg = "CC" + "AUG" + "GCU" * 100_000 + "UAA" + "GG"
        t0 = time.perf_counter()
        r = traduzir_mrna(mrna(reg))
        self.assertLess(time.perf_counter() - t0, 5.0)
        self.assertEqual(r.resultado, CORRETO)
        self.assertEqual(len(r.aminoacidos), 100_001)


if __name__ == "__main__":
    unittest.main()
