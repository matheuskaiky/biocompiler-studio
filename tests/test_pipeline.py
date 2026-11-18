"""Testes de aceite do orquestrador `executar_fluxo` (OS-M6-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: docs/SPEC.md §2.1, §9.4, §11.1, §12 (Integração); docs/DECISIONS.md D017.
Somente biblioteca padrão.
"""

import dataclasses
import random
import typing
import unittest

from biocompiler.core.at1 import transcrever_dna
from biocompiler.core.at2 import maturar_pre_mrna
from biocompiler.core.at3 import traduzir_mrna
from biocompiler.core.at4 import alinhar_dna
from biocompiler.core.pipeline import executar_fluxo
from biocompiler.modelos import (CadeiaFluxo, ResultadoAT1, ResultadoAT2, ResultadoAT3,
                                 ResultadoAT4, ResultadoFluxo)

SEQ1 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG"
SEQ2 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG"


def cadeia_esperada(origem, dna):
    """Oráculo: composição explícita das funções públicas (SPEC §2.1)."""
    r1 = transcrever_dna(dna)
    r2 = maturar_pre_mrna(r1.pre_mrna) if r1.ok else None
    r3 = traduzir_mrna(r2.mrna_maduro) if r2 is not None and r2.ok else None
    if not r1.ok:
        falha = "AT1"
    elif not r2.ok:
        falha = "AT2"
    elif not r3.ok:
        falha = "AT3"
    else:
        falha = None
    return CadeiaFluxo(origem, dna, r1, r2, r3, falha is None, falha)


def fluxo_esperado(s1, s2, metodo="both", match=2, mismatch=-1, gap=-2):
    metodos = ("local", "global") if metodo == "both" else (metodo,)
    alin = tuple(alinhar_dna(s1, s2, m, match, mismatch, gap) for m in metodos)
    c1, c2 = cadeia_esperada("Seq1", s1), cadeia_esperada("Seq2", s2)
    return ResultadoFluxo(c1, c2, alin, c1.ok and c2.ok and all(r.ok for r in alin))


class TestEstrutura(unittest.TestCase):
    def test_dataclasses(self):
        esperado = {
            CadeiaFluxo: [("origem", str), ("dna", str), ("at1", ResultadoAT1),
                          ("at2", ResultadoAT2 | None), ("at3", ResultadoAT3 | None),
                          ("ok", bool), ("etapa_falha", str | None)],
            ResultadoFluxo: [("seq1", CadeiaFluxo), ("seq2", CadeiaFluxo),
                             ("alinhamentos", tuple[ResultadoAT4, ...]), ("ok", bool)],
        }
        for cls, campos in esperado.items():
            with self.subTest(cls=cls.__name__):
                self.assertTrue(dataclasses.is_dataclass(cls))
                self.assertTrue(cls.__dataclass_params__.frozen)
                fs = dataclasses.fields(cls)
                self.assertEqual([f.name for f in fs], [n for n, _ in campos])
                for f in fs:
                    self.assertIs(f.default, dataclasses.MISSING)
                    self.assertIs(f.default_factory, dataclasses.MISSING)
                dicas = typing.get_type_hints(cls)
                for nome, tipo in campos:
                    self.assertEqual(dicas[nome], tipo, nome)

    def test_assinatura(self):
        import inspect
        sig = inspect.signature(executar_fluxo)
        self.assertEqual(list(sig.parameters),
                         ["seq1", "seq2", "metodo", "match", "mismatch", "gap"])
        self.assertEqual([sig.parameters[p].default for p in ("metodo", "match", "mismatch", "gap")],
                         ["both", 2, -1, -2])


class TestExemploIntegrado(unittest.TestCase):
    """SPEC §11.1: o exemplo atravessa as três fases nas duas sequências."""

    def test_spec_11_1(self):
        rf = executar_fluxo(SEQ1, SEQ2)
        self.assertIsInstance(rf, ResultadoFluxo)
        self.assertEqual(rf, fluxo_esperado(SEQ1, SEQ2))
        self.assertTrue(rf.ok)
        self.assertEqual((rf.seq1.origem, rf.seq2.origem), ("Seq1", "Seq2"))
        self.assertEqual(rf.seq1.at2.rna_processado, "CCAUGGCUAAACCGUAAGG")
        self.assertEqual(rf.seq2.at2.rna_processado, "CCAUGGCUAAUCCGUAAGG")
        self.assertEqual(rf.seq1.at3.proteina, "Met-Ala-Lys-Pro")
        self.assertEqual(rf.seq2.at3.proteina, "Met-Ala-Asn-Pro")
        self.assertEqual([r.metodo for r in rf.alinhamentos], ["local", "global"])
        # AT4 compara os DNAs originais, não pré-mRNA nem proteína.
        for r in rf.alinhamentos:
            self.assertEqual((r.seq1, r.seq2), (SEQ1, SEQ2))
        self.assertEqual(rf.alinhamentos[1].mismatches, 1)

    def test_metodo_unico_e_parametros(self):
        rf = executar_fluxo(SEQ1, SEQ2, "global", 3, -2, -4)
        self.assertEqual(rf, fluxo_esperado(SEQ1, SEQ2, "global", 3, -2, -4))
        self.assertEqual(len(rf.alinhamentos), 1)
        self.assertEqual(rf.alinhamentos[0].match, 3)


class TestFalhasIsoladas(unittest.TestCase):
    def test_erro_at1_nao_gera_etapas_artificiais(self):
        rf = executar_fluxo("CCCGCTAAACCGTAA", SEQ2)
        self.assertEqual(rf, fluxo_esperado("CCCGCTAAACCGTAA", SEQ2))
        c = rf.seq1
        self.assertEqual((c.ok, c.etapa_falha, c.at1.resultado), (False, "AT1", "BUG - START ausente"))
        self.assertIsNone(c.at2)
        self.assertIsNone(c.at3)
        self.assertTrue(rf.seq2.ok)
        self.assertTrue(all(r.ok for r in rf.alinhamentos))
        self.assertFalse(rf.ok)

    def test_falha_at2_bloqueia_so_at3_daquela_amostra(self):
        sem_intron = "ATGGCTAAACCGTAA"  # AT1 ok; pré-mRNA sem GU → AT2 falha
        rf = executar_fluxo(SEQ1, sem_intron)
        self.assertEqual(rf, fluxo_esperado(SEQ1, sem_intron))
        self.assertTrue(rf.seq2.at1.ok)
        self.assertFalse(rf.seq2.at2.ok)
        self.assertIsNone(rf.seq2.at3)
        self.assertEqual(rf.seq2.etapa_falha, "AT2")
        self.assertTrue(rf.seq1.ok)

    def test_falha_at3(self):
        # AT1 e AT2 corretas; o DNA termina em A, então a cauda do mRNA maduro
        # fica com 101 A e a AT3 acusa a cauda (convenção SPEC §5.3).
        dna = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGGGCTAA"
        rf = executar_fluxo(dna, SEQ2)
        self.assertEqual(rf, fluxo_esperado(dna, SEQ2))
        c = rf.seq1
        self.assertTrue(c.at1.ok and c.at2.ok)
        self.assertEqual((c.at3.resultado, c.etapa_falha, c.ok),
                         ("BUG - cauda poli-A", "AT3", False))

    def test_at4_independe_das_cadeias(self):
        rf = executar_fluxo("CCCGCTAAACCGTAA", "GGGGGGGG")
        self.assertFalse(rf.seq1.ok)
        self.assertFalse(rf.seq2.ok)
        self.assertTrue(all(r.ok for r in rf.alinhamentos))
        self.assertEqual(rf.alinhamentos, (alinhar_dna("CCCGCTAAACCGTAA", "GGGGGGGG", "local", 2, -1, -2),
                                           alinhar_dna("CCCGCTAAACCGTAA", "GGGGGGGG", "global", 2, -1, -2)))

    def test_dna_invalido_at4_responde_erro(self):
        rf = executar_fluxo("ATGXTAA", SEQ2)
        self.assertEqual(rf, fluxo_esperado("ATGXTAA", SEQ2))
        self.assertEqual({r.resultado for r in rf.alinhamentos}, {"ERRO - base inválida"})
        self.assertEqual(rf.seq1.etapa_falha, "AT1")

    def test_metodo_invalido_vai_ao_nucleo(self):
        rf = executar_fluxo(SEQ1, SEQ2, "xyz")
        self.assertEqual(len(rf.alinhamentos), 1)
        self.assertEqual(rf.alinhamentos[0].resultado, "ERRO - método inválido")
        self.assertTrue(rf.seq1.ok and rf.seq2.ok)
        self.assertFalse(rf.ok)

    def test_minusculas_seguem_regras_de_cada_at(self):
        rf = executar_fluxo(SEQ1.lower(), SEQ2)
        self.assertEqual(rf.seq1.at1.resultado, "BUG - base inválida")
        self.assertTrue(all(r.ok for r in rf.alinhamentos))

    def test_modo_individual_inalterado(self):
        executar_fluxo(SEQ1, SEQ2)
        self.assertEqual(transcrever_dna(SEQ1), fluxo_esperado(SEQ1, SEQ2).seq1.at1)


class TestPropriedades(unittest.TestCase):
    def test_aleatorio_contra_composicao(self):
        rnd = random.Random(2026)
        blocos = ["ATG", "TAA", "TGA", "GT", "AG", "A", "C" * 12, "CC", "G", "T", "ACC"]
        for _ in range(300):
            s1 = "".join(rnd.choice(blocos) for _ in range(rnd.randint(0, 12)))
            s2 = "".join(rnd.choice(blocos) for _ in range(rnd.randint(1, 12)))
            metodo = rnd.choice(["both", "local", "global"])
            with self.subTest(s1=s1, s2=s2, metodo=metodo):
                self.assertEqual(executar_fluxo(s1, s2, metodo),
                                 fluxo_esperado(s1, s2, metodo))


if __name__ == "__main__":
    unittest.main()
