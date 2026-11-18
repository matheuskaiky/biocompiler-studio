"""Testes de aceite de `candidatos_celula` (OS-M7-01; D018).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

O inspetor de célula da interface pede ao núcleo os candidatos da recorrência
(D014) para uma célula já calculada. A função lê ``r.matriz`` e os parâmetros do
resultado; os testes amarram cada candidato aos vizinhos e à direção gravada.
Somente biblioteca padrão.
"""

import random
import unittest

from biocompiler.core.at4 import alinhar_dna, candidatos_celula

SETA = {"diagonal": "↖", "vertical": "↑", "horizontal": "←"}


class TestCandidatos(unittest.TestCase):
    def test_exemplo_global_celula_5_1(self):
        # D014: em (5,1), diagonal = vertical = -6 → ↖ pelo desempate.
        r = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        self.assertEqual(candidatos_celula(r, 5, 1),
                         (("diagonal", -6), ("vertical", -6), ("horizontal", -12)))
        self.assertEqual((r.matriz[5][1], r.direcoes[5][1]), (-6, "↖"))

    def test_local_inclui_zero(self):
        r = alinhar_dna("acgta", "TCATG", "local", 3, -2, -4)
        cand = candidatos_celula(r, 1, 1)
        self.assertEqual([n for n, _ in cand], ["diagonal", "vertical", "horizontal", "zero"])
        self.assertEqual(cand[-1], ("zero", 0))
        self.assertEqual(cand[0], ("diagonal", -2))  # A×T: 0 + mismatch

    def test_bordas_sem_candidatos(self):
        for metodo in ("local", "global"):
            r = alinhar_dna("ACG", "AG", metodo, 2, -1, -2)
            for i, j in ((0, 0), (0, 1), (0, 2), (1, 0), (3, 0)):
                with self.subTest(metodo=metodo, celula=(i, j)):
                    self.assertEqual(candidatos_celula(r, i, j), ())

    def test_fora_da_matriz_e_resultado_com_erro(self):
        r = alinhar_dna("ACG", "AG", "global", 2, -1, -2)
        for i, j in ((4, 0), (0, 3), (-1, 0), (0, -1)):
            with self.subTest(celula=(i, j)):
                with self.assertRaises(ValueError):
                    candidatos_celula(r, i, j)
        with self.assertRaises(ValueError):
            candidatos_celula(alinhar_dna("ACX", "AG", "global", 2, -1, -2), 1, 1)

    def test_propriedade_contra_matriz_e_direcoes(self):
        rnd = random.Random(18)
        for _ in range(150):
            s1 = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 9)))
            s2 = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 9)))
            p = (rnd.randint(-2, 4), rnd.randint(-4, 2), rnd.randint(-5, 1))
            for metodo in ("local", "global"):
                r = alinhar_dna(s1, s2, metodo, *p)
                for i in range(1, len(s1) + 1):
                    for j in range(1, len(s2) + 1):
                        cand = dict(candidatos_celula(r, i, j))
                        s = p[0] if r.seq1[i - 1] == r.seq2[j - 1] else p[1]
                        self.assertEqual(cand["diagonal"], r.matriz[i - 1][j - 1] + s)
                        self.assertEqual(cand["vertical"], r.matriz[i - 1][j] + p[2])
                        self.assertEqual(cand["horizontal"], r.matriz[i][j - 1] + p[2])
                        self.assertEqual(r.matriz[i][j], max(cand.values()))
                        melhor = max(cand["diagonal"], cand["vertical"], cand["horizontal"])
                        if metodo == "local" and melhor <= 0:
                            self.assertEqual(r.direcoes[i][j], "·")
                        else:
                            nome = next(n for n in ("diagonal", "vertical", "horizontal")
                                        if cand[n] == melhor)
                            self.assertEqual(r.direcoes[i][j], SETA[nome])


if __name__ == "__main__":
    unittest.main()
