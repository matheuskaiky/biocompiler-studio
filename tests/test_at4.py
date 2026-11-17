"""Testes de aceite da AT4 — Smith–Waterman e Needleman–Wunsch (OS-M4-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: enunciado "AT4 - Smith-Waterman.pdf" §§2–4 e apêndice; docs/SPEC.md
§4.4 e §11.2; docs/DECISIONS.md D014. Somente biblioteca padrão.
"""

import dataclasses
import random
import time
import typing
import unittest

from biocompiler.core.at4 import alinhar_dna
from biocompiler.modelos import Evento, ResultadoAT4

GLOBAL, LOCAL = "global", "local"


def _oraculo(s1, s2, metodo, ma, mi, g):
    """Implementação independente (força bruta direta da recorrência + D014)."""
    m, n = len(s1), len(s2)
    F = [[0] * (n + 1) for _ in range(m + 1)]
    D = [["·"] * (n + 1) for _ in range(m + 1)]
    if metodo == GLOBAL:
        for i in range(1, m + 1):
            F[i][0], D[i][0] = i * g, "↑"
        for j in range(1, n + 1):
            F[0][j], D[0][j] = j * g, "←"
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cand = [(F[i - 1][j - 1] + (ma if s1[i - 1] == s2[j - 1] else mi), "↖"),
                    (F[i - 1][j] + g, "↑"), (F[i][j - 1] + g, "←")]
            melhor = max(v for v, _ in cand)
            if metodo == LOCAL and melhor <= 0:
                F[i][j], D[i][j] = 0, "·"
            else:
                F[i][j] = melhor
                D[i][j] = next(d for v, d in cand if v == melhor)
    if metodo == GLOBAL:
        inicio, score = (m, n), F[m][n]
    else:
        score = max(max(linha) for linha in F)
        inicio = None if score == 0 else next(
            (i, j) for i in range(m + 1) for j in range(n + 1) if F[i][j] == score)
    caminho, a1, a2 = [], [], []
    if inicio is not None:
        i, j = inicio
        while True:
            caminho.append((i, j))
            d = D[i][j]
            if d == "·":
                break
            if d == "↖":
                a1.append(s1[i - 1]); a2.append(s2[j - 1]); i, j = i - 1, j - 1
            elif d == "↑":
                a1.append(s1[i - 1]); a2.append("-"); i -= 1
            else:
                a1.append("-"); a2.append(s2[j - 1]); j -= 1
    a1, a2 = "".join(reversed(a1)), "".join(reversed(a2))
    marc = "".join(" " if "-" in (x, y) else ("|" if x == y else ".") for x, y in zip(a1, a2))
    return (tuple(map(tuple, F)), tuple(map(tuple, D)), inicio, tuple(caminho),
            a1, marc, a2, score)


class TestExemploGlobalDoProfessor(unittest.TestCase):
    """Enunciado §3.7 e apêndice: ACGTAC × ACGTTC, +2/−1/−2, score 9."""

    def setUp(self):
        self.r = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)

    def test_resultado(self):
        r = self.r
        self.assertIsInstance(r, ResultadoAT4)
        self.assertEqual((r.ok, r.status, r.resultado, r.erros), (True, "OK", "CORRETO", ()))
        self.assertEqual(r.score, 9)
        self.assertEqual((r.alinhado1, r.marcadores, r.alinhado2), ("ACGTAC", "||||.|", "ACGTTC"))
        self.assertEqual((r.matches, r.mismatches, r.gaps, r.tamanho), (5, 1, 0, 6))
        self.assertEqual((r.seq1, r.seq2, r.metodo, r.match, r.mismatch, r.gap),
                         ("ACGTAC", "ACGTTC", "global", 2, -1, -2))
        self.assertEqual(r.observacao, "")

    def test_matriz_de_pontuacao_igual_a_do_enunciado(self):
        self.assertEqual(self.r.matriz, (
            (0, -2, -4, -6, -8, -10, -12),
            (-2, 2, 0, -2, -4, -6, -8),
            (-4, 0, 4, 2, 0, -2, -4),
            (-6, -2, 2, 6, 4, 2, 0),
            (-8, -4, 0, 4, 8, 6, 4),
            (-10, -6, -2, 2, 6, 7, 5),
            (-12, -8, -4, 0, 4, 5, 9)))

    def test_matriz_de_direcoes_pela_regra_de_desempate(self):
        # D014: a imagem do enunciado difere em 9 células fora do caminho; vale o texto §3.6.
        self.assertEqual(tuple("".join(l) for l in self.r.direcoes), (
            "·←←←←←←",
            "↑↖←←←←←",
            "↑↑↖←←←↖",
            "↑↑↑↖←←←",
            "↑↑↑↑↖↖←",
            "↑↖↑↑↑↖↖",
            "↑↑↖↑↑↖↖"))

    def test_caminho(self):
        self.assertEqual(self.r.inicio_traceback, (6, 6))
        self.assertEqual(self.r.caminho, tuple((k, k) for k in range(6, -1, -1)))


class TestExemploLocalDoApendice(unittest.TestCase):
    """Apêndice 2.5: acgta × TCATG, local, +3/−2/−4 (minúsculas normalizadas)."""

    def test_resultado(self):
        r = alinhar_dna("acgta", "TCATG", "local", 3, -2, -4)
        self.assertEqual((r.ok, r.seq1, r.seq2), (True, "ACGTA", "TCATG"))
        self.assertEqual(r.matriz, (
            (0, 0, 0, 0, 0, 0),
            (0, 0, 0, 3, 0, 0),
            (0, 0, 3, 0, 1, 0),
            (0, 0, 0, 1, 0, 4),
            (0, 3, 0, 0, 4, 0),
            (0, 0, 1, 3, 0, 2)))
        self.assertEqual(tuple("".join(l) for l in r.direcoes), (
            "······", "···↖··", "··↖·↖·", "···↖·↖", "·↖··↖·", "··↖↖·↖"))
        # Máximo 4 em (3,5) e (4,4): primeiro em ordem linha/coluna (SPEC §4.4).
        self.assertEqual(r.inicio_traceback, (3, 5))
        self.assertEqual(r.caminho, ((3, 5), (2, 4), (1, 3), (0, 2)))
        self.assertEqual((r.alinhado1, r.marcadores, r.alinhado2), ("ACG", "|.|", "ATG"))
        self.assertEqual((r.score, r.matches, r.mismatches, r.gaps, r.tamanho), (4, 2, 1, 0, 3))


class TestCasosEspeciais(unittest.TestCase):
    def test_local_sem_similaridade_positiva(self):
        r = alinhar_dna("AAA", "CCC", "local", 2, -1, -2)
        self.assertTrue(r.ok)
        self.assertEqual(r.score, 0)
        self.assertEqual(r.matriz, ((0,) * 4,) * 4)
        self.assertEqual(r.direcoes, (("·",) * 4,) * 4)
        self.assertIsNone(r.inicio_traceback)
        self.assertEqual((r.caminho, r.alinhado1, r.marcadores, r.alinhado2), ((), "", "", ""))
        self.assertEqual((r.matches, r.mismatches, r.gaps, r.tamanho), (0, 0, 0, 0))
        self.assertEqual(r.observacao, "sem região de similaridade positiva")

    def test_empate_vertical_horizontal_prefere_vertical(self):
        # F(1,1): diag −5, cima −4, esquerda −4 → ↑; depois ← até a origem.
        r = alinhar_dna("A", "C", "global", 2, -5, -2)
        self.assertEqual(r.direcoes, (("·", "←"), ("↑", "↑")))
        self.assertEqual((r.alinhado1, r.marcadores, r.alinhado2), ("-A", "  ", "C-"))
        self.assertEqual(r.caminho, ((1, 1), (0, 1), (0, 0)))
        self.assertEqual((r.score, r.gaps), (-4, 2))

    def test_global_comprimentos_diferentes(self):
        r = alinhar_dna("ACGT", "AT", "global", 2, -1, -2)
        self.assertEqual(r.alinhado1.replace("-", ""), "ACGT")
        self.assertEqual(r.alinhado2.replace("-", ""), "AT")
        self.assertEqual(r.tamanho, 4)
        self.assertEqual(r.score, _oraculo("ACGT", "AT", GLOBAL, 2, -1, -2)[-1])

    def test_mesmo_par_nos_dois_metodos(self):
        g = alinhar_dna("TTACGTAC", "ACGTTC", "global", 2, -1, -2)
        l = alinhar_dna("TTACGTAC", "ACGTTC", "local", 2, -1, -2)
        self.assertTrue(g.ok and l.ok)
        self.assertGreaterEqual(l.score, g.score)
        self.assertEqual(g.caminho[-1], (0, 0))

    def test_sequencia_unitaria(self):
        r = alinhar_dna("A", "A", "local", 1, -1, -1)
        self.assertEqual((r.score, r.alinhado1, r.alinhado2, r.caminho), (1, "A", "A", ((1, 1), (0, 0))))

    def test_parametros_nao_recomendados_sao_aceitos(self):
        r = alinhar_dna("ACG", "ACG", "global", 0, 1, 3)
        self.assertTrue(r.ok)
        self.assertEqual(r.score, _oraculo("ACG", "ACG", GLOBAL, 0, 1, 3)[-1])


class TestValidacao(unittest.TestCase):
    def _erro(self, r, rotulo, erros):
        self.assertEqual((r.ok, r.status, r.resultado, r.erros), (False, "ERRO", rotulo, erros))
        self.assertIsNone(r.matriz)
        self.assertIsNone(r.direcoes)
        self.assertIsNone(r.score)
        self.assertIsNone(r.inicio_traceback)
        self.assertEqual((r.caminho, r.alinhado1, r.marcadores, r.alinhado2), ((), "", "", ""))
        self.assertEqual((r.matches, r.mismatches, r.gaps, r.tamanho), (0, 0, 0, 0))
        self.assertEqual(list(r.eventos), [Evento("RESULTADO", None, rotulo)])

    def test_metodo_invalido(self):
        for metodo in ("LOCAL", "both", "", "ambos"):
            with self.subTest(metodo=metodo):
                self._erro(alinhar_dna("ACG", "ACG", metodo, 2, -1, -2), "ERRO - método inválido",
                           (f"método inválido: {metodo!r} (use 'local' ou 'global')",))

    def test_parametro_nao_numerico(self):
        r = alinhar_dna("ACG", "ACG", "global", "a", -1.5, True)
        self._erro(r, "ERRO - parâmetro não numérico",
                   ("match não numérico: 'a'", "mismatch não numérico: -1.5",
                    "gap não numérico: True"))
        self.assertEqual((r.match, r.mismatch, r.gap), (None, None, None))
        r = alinhar_dna("ACG", "ACG", "global", 2, None, -2)
        self._erro(r, "ERRO - parâmetro não numérico", ("mismatch não numérico: None",))
        self.assertEqual((r.match, r.mismatch, r.gap), (2, None, -2))

    def test_sequencia_vazia(self):
        self._erro(alinhar_dna("", "ACGTTC", "global", 2, -1, -2),
                   "ERRO - sequência vazia", ("Seq1 vazia",))
        self._erro(alinhar_dna("", "", "local", 2, -1, -2),
                   "ERRO - sequência vazia", ("Seq1 vazia", "Seq2 vazia"))

    def test_base_invalida(self):
        r = alinhar_dna("ACGTB", "ACGTTC", "global", 2, -1, -2)
        self._erro(r, "ERRO - base inválida", ("Seq1, posição 5: B",))
        self.assertEqual(r.seq1, "ACGTB")
        r = alinhar_dna("ACGTAXTG", "AxU", "local", 2, -1, -2)
        self._erro(r, "ERRO - base inválida",
                   ("Seq1, posição 6: X", "Seq2, posição 2: x", "Seq2, posição 3: U"))

    def test_normaliza_somente_acgt(self):
        r = alinhar_dna("acgt", "ACGt", "global", 2, -1, -2)
        self.assertEqual((r.seq1, r.seq2, r.ok), ("ACGT", "ACGT", True))
        self.assertEqual(alinhar_dna("acgn", "A", "global", 2, -1, -2).erros, ("Seq1, posição 4: n",))
        self.assertEqual(alinhar_dna("ac gt", "A", "global", 2, -1, -2).erros, ("Seq1, posição 3:  ",))

    def test_precedencia(self):
        self.assertEqual(alinhar_dna("", "X", "x", "a", -1, -2).resultado, "ERRO - método inválido")
        self.assertEqual(alinhar_dna("", "X", "local", "a", -1, -2).resultado, "ERRO - parâmetro não numérico")
        self.assertEqual(alinhar_dna("", "X", "local", 1, -1, -2).resultado, "ERRO - sequência vazia")
        self.assertEqual(alinhar_dna("A" * 2001, "X", "local", 1, -1, -2).resultado, "ERRO - base inválida")

    def test_limite_de_tamanho(self):
        t0 = time.perf_counter()
        r = alinhar_dna("A" * 2001, "C" * 2500, "global", 2, -1, -2)
        self.assertLess(time.perf_counter() - t0, 1.0)  # recusa antes de alocar
        self._erro(r, "ERRO - sequência muito longa",
                   ("Seq1 com 2001 bases (limite 2000)", "Seq2 com 2500 bases (limite 2000)"))
        self.assertTrue(alinhar_dna("A" * 2000, "A", "local", 2, -1, -2).ok)


class TestResultadoEstruturado(unittest.TestCase):
    def test_campos_e_anotacoes(self):
        self.assertEqual([f.name for f in dataclasses.fields(ResultadoAT4)], [
            "seq1", "seq2", "metodo", "match", "mismatch", "gap", "ok", "status",
            "resultado", "erros", "matriz", "direcoes", "inicio_traceback", "caminho",
            "alinhado1", "marcadores", "alinhado2", "score", "matches", "mismatches",
            "gaps", "tamanho", "observacao", "eventos"])
        self.assertEqual(typing.get_type_hints(ResultadoAT4), {
            "seq1": str, "seq2": str, "metodo": str,
            "match": int | None, "mismatch": int | None, "gap": int | None,
            "ok": bool, "status": str, "resultado": str, "erros": tuple[str, ...],
            "matriz": tuple[tuple[int, ...], ...] | None,
            "direcoes": tuple[tuple[str, ...], ...] | None,
            "inicio_traceback": tuple[int, int] | None,
            "caminho": tuple[tuple[int, int], ...],
            "alinhado1": str, "marcadores": str, "alinhado2": str,
            "score": int | None, "matches": int, "mismatches": int, "gaps": int,
            "tamanho": int, "observacao": str, "eventos": tuple[Evento, ...]})

    def test_imutavel_sem_padroes(self):
        r = alinhar_dna("AC", "AC", "global", 2, -1, -2)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.score = 0  # type: ignore[misc]
        self.assertIsInstance(r.matriz, tuple)
        self.assertIsInstance(r.matriz[0], tuple)
        for f in dataclasses.fields(ResultadoAT4):
            self.assertIs(f.default, dataclasses.MISSING, f.name)
            self.assertIs(f.default_factory, dataclasses.MISSING, f.name)

    def test_eventos_global(self):
        E = Evento
        self.assertEqual(list(alinhar_dna("AC", "A", "global", 2, -1, -2).eventos), [
            E("BORDA_INICIALIZADA", None, "global"),
            E("MATRIZ_PREENCHIDA", None, "3x2"),
            E("INICIO_TRACEBACK", None, "2,1"),
            E("TRACEBACK_PASSO", None, "2,1,↑"),
            E("TRACEBACK_PASSO", None, "1,1,↖"),
            E("TRACEBACK_PASSO", None, "0,0,·"),
            E("ALINHAMENTO_FINAL", None, "0"),
            E("RESULTADO", None, "CORRETO")])

    def test_eventos_local_sem_similaridade(self):
        E = Evento
        self.assertEqual(list(alinhar_dna("A", "C", "local", 2, -1, -2).eventos), [
            E("BORDA_INICIALIZADA", None, "local"),
            E("MATRIZ_PREENCHIDA", None, "2x2"),
            E("ALINHAMENTO_FINAL", None, "0"),
            E("RESULTADO", None, "CORRETO")])

    def test_determinismo(self):
        a = alinhar_dna("GATTACA", "GCATGCU".replace("U", "T"), "local", 2, -1, -2)
        b = alinhar_dna("GATTACA", "GCATGCT", "local", 2, -1, -2)
        self.assertEqual(a, b)


class TestPropriedades(unittest.TestCase):
    def test_aleatorio_contra_oraculo(self):
        rnd = random.Random(20261117)
        for _ in range(600):
            s1 = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 9)))
            s2 = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 9)))
            metodo = rnd.choice((GLOBAL, LOCAL))
            ma, mi, g = rnd.randint(-1, 4), rnd.randint(-3, 1), rnd.randint(-4, 1)
            r = alinhar_dna(s1, s2, metodo, ma, mi, g)
            F, D, ini, cam, a1, marc, a2, score = _oraculo(s1, s2, metodo, ma, mi, g)
            caso = (s1, s2, metodo, ma, mi, g)
            self.assertEqual(r.matriz, F, caso)
            self.assertEqual(r.direcoes, D, caso)
            self.assertEqual((r.inicio_traceback, r.caminho), (ini, cam), caso)
            self.assertEqual((r.alinhado1, r.marcadores, r.alinhado2), (a1, marc, a2), caso)
            self.assertEqual(r.score, score, caso)
            # Score verificável pela soma independente das colunas (SPEC §4.4).
            soma = sum(g if "-" in (x, y) else (ma if x == y else mi) for x, y in zip(a1, a2))
            self.assertEqual(soma, r.score, caso)
            self.assertEqual(r.matches, marc.count("|"))
            self.assertEqual(r.mismatches, marc.count("."))
            self.assertEqual(r.gaps, marc.count(" "))
            self.assertEqual(r.tamanho, len(a1))
            if metodo == GLOBAL:
                self.assertEqual((a1.replace("-", ""), a2.replace("-", "")), (s1, s2), caso)
            else:
                self.assertIn(a1.replace("-", ""), s1)
                self.assertIn(a2.replace("-", ""), s2)

    def test_desempenho_400x400(self):
        rnd = random.Random(7)
        s1 = "".join(rnd.choice("ACGT") for _ in range(400))
        s2 = "".join(rnd.choice("ACGT") for _ in range(400))
        for metodo in (GLOBAL, LOCAL):
            t0 = time.perf_counter()
            r = alinhar_dna(s1, s2, metodo, 2, -1, -2)
            self.assertLess(time.perf_counter() - t0, 10.0)
            self.assertTrue(r.ok)
            self.assertEqual(len(r.matriz), 401)


if __name__ == "__main__":
    unittest.main()
