"""M9 — propriedades da SPEC §12 com entradas geradas e oráculos independentes,
e CLI funcional sem a camada web.

As entradas são construídas pela gramática de cada enunciado (sementes fixas), sem
consultar os exemplos do professor. Os oráculos (tabela genética e programação dinâmica)
são escritos aqui, de forma independente do núcleo. Só biblioteca padrão.
"""
import itertools
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from biocompiler.core.at1 import transcrever_dna  # noqa: E402
from biocompiler.core.at2 import maturar_pre_mrna  # noqa: E402
from biocompiler.core.at3 import traduzir_mrna  # noqa: E402
from biocompiler.core.at4 import alinhar_dna  # noqa: E402

STOPS_DNA = ("TAA", "TAG", "TGA")
STOPS_RNA = ("UAA", "UAG", "UGA")
N = 300

# Oráculo independente: código genético padrão (ordem UCAG × UCAG × UCAG).
_AA = ("Phe Phe Leu Leu Ser Ser Ser Ser Tyr Tyr STOP STOP Cys Cys STOP Trp "
       "Leu Leu Leu Leu Pro Pro Pro Pro His His Gln Gln Arg Arg Arg Arg "
       "Ile Ile Ile Met Thr Thr Thr Thr Asn Asn Lys Lys Ser Ser Arg Arg "
       "Val Val Val Val Ala Ala Ala Ala Asp Asp Glu Glu Gly Gly Gly Gly").split()
CODIGO = {"".join(c): aa for c, aa in zip(itertools.product("UCAG", repeat=3), _AA)}


def codons_sem_stop(rnd, n, rna=False):
    stops = STOPS_RNA if rna else STOPS_DNA
    alfa = "ACGU" if rna else "ACGT"
    saida = []
    while len(saida) < n:
        c = "".join(rnd.choice(alfa) for _ in range(3))
        if c not in stops:
            saida.append(c)
    return "".join(saida)


def flanco_cg(rnd, a, b):
    """Flancos só com C/G: não formam ATG/AUG nem STOP, e não criam GU/AG."""
    return "".join(rnd.choice("CG") for _ in range(rnd.randint(a, b)))


def dp(a, b, metodo, ma, mi, g):
    """Oráculo independente: matriz de pontuação de SW (local) ou NW (global)."""
    m, n = len(a), len(b)
    F = [[0] * (n + 1) for _ in range(m + 1)]
    if metodo == "global":
        for i in range(1, m + 1):
            F[i][0] = i * g
        for j in range(1, n + 1):
            F[0][j] = j * g
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            s = ma if a[i - 1] == b[j - 1] else mi
            v = max(F[i - 1][j - 1] + s, F[i - 1][j] + g, F[i][j - 1] + g)
            F[i][j] = max(v, 0) if metodo == "local" else v
    return F


class TestPropriedadesAT1(unittest.TestCase):
    def test_orf_construido_sempre_valido_e_transcrito_integralmente(self):
        rnd = random.Random(101)
        for _ in range(N):
            utr5 = flanco_cg(rnd, 0, 8)
            corpo = codons_sem_stop(rnd, rnd.randint(0, 15))
            stop = rnd.choice(STOPS_DNA)
            dna = utr5 + "ATG" + corpo + stop + flanco_cg(rnd, 0, 8)
            r = transcrever_dna(dna)
            with self.subTest(dna=dna):
                # O primeiro ATG é o construído; um STOP em fase anterior ao construído
                # só pode vir do corpo, que não tem STOP em fase.
                self.assertTrue(r.ok, r.resultado)
                self.assertEqual(r.posicao_start, len(utr5))
                self.assertEqual(r.posicao_stop, len(utr5) + 3 + len(corpo))
                self.assertEqual(r.pre_mrna, dna.replace("T", "U"))
                self.assertEqual(len(r.pre_mrna), len(dna))

    def test_base_invalida_nunca_produz_pre_mrna(self):
        rnd = random.Random(102)
        for _ in range(N):
            base = "ATG" + codons_sem_stop(rnd, rnd.randint(1, 8)) + "TAA"
            k = rnd.randrange(len(base))
            dna = base[:k] + rnd.choice("NXBZ") + base[k:]
            r = transcrever_dna(dna)
            with self.subTest(dna=dna):
                self.assertFalse(r.ok)
                self.assertIsNone(r.pre_mrna)
                self.assertTrue(any(i == k for i, _ in r.bases_invalidas))


class TestPropriedadesAT2(unittest.TestCase):
    def _intron(self, rnd, d):
        return "GU" + "C" * rnd.randint(1, 6) + "A" + "C" * d + "AG"

    def test_um_ou_dois_introns_construidos_sao_todos_encontrados(self):
        rnd = random.Random(202)
        exon = lambda: "".join(rnd.choice("CU") for _ in range(rnd.randint(2, 10)))  # noqa: E731
        for _ in range(N):
            partes, esperados = [exon()], []
            for _ in range(rnd.choice((1, 2))):
                inicio = sum(len(p) for p in partes)
                intron = self._intron(rnd, rnd.randint(10, 30))
                esperados.append((inicio, inicio + intron.index("A"),
                                  inicio + len(intron) - 2))
                partes += [intron, exon()]
            pre = "".join(partes)
            r = maturar_pre_mrna(pre)
            with self.subTest(pre=pre):
                self.assertTrue(r.ok, r.resultado)
                self.assertEqual([(i.posicao_gu, i.posicao_branch, i.posicao_ag)
                                  for i in r.introns], esperados)
                mantidas = "".join(p for k, p in enumerate(partes) if k % 2 == 0)
                self.assertEqual(r.rna_processado, mantidas)
                self.assertEqual(r.mrna_maduro, "m7Gppp" + mantidas + "A" * 100)

    def test_limites_do_branch_point(self):
        rnd = random.Random(203)
        for d, valido in ((9, False), (10, True), (30, True), (31, False)):
            for _ in range(20):
                pre = "CUCU" + self._intron(rnd, d) + "CUUC"
                r = maturar_pre_mrna(pre)
                with self.subTest(d=d, pre=pre):
                    self.assertEqual(r.ok, valido, r.resultado)
                    if valido:
                        i = r.introns[0]
                        self.assertEqual(i.posicao_ag - i.posicao_branch - 1, d)  # D009
                    else:
                        self.assertEqual(r.resultado, "BUG - branch point")


class TestPropriedadesAT3(unittest.TestCase):
    def test_traducao_confere_com_tabela_independente(self):
        rnd = random.Random(303)
        for _ in range(N):
            utr5 = flanco_cg(rnd, 0, 6)
            corpo = codons_sem_stop(rnd, rnd.randint(0, 20), rna=True)
            stop = rnd.choice(STOPS_RNA)
            # 3′ UTR com ≥ 1 base C/G: um STOP terminado em A colado à cauda mudaria a
            # contagem de A (ambiguidade da SPEC §5.3), o que não é o objeto desta propriedade.
            regiao = utr5 + "AUG" + corpo + stop + flanco_cg(rnd, 1, 4)
            r = traduzir_mrna("m7Gppp" + regiao + "A" * 100)
            with self.subTest(regiao=regiao):
                self.assertTrue(r.ok, r.resultado)
                esperado = [CODIGO[c] for c in ["AUG"] + [corpo[k:k + 3]
                                                          for k in range(0, len(corpo), 3)]]
                self.assertEqual(list(r.aminoacidos), esperado)
                self.assertNotIn("STOP", r.aminoacidos)
                self.assertEqual(r.posicao_start, len(utr5))
                self.assertEqual(r.posicao_stop, len(utr5) + 3 + len(corpo))
                self.assertEqual(r.proteina, "-".join(esperado))

    def test_tabela_do_oraculo_tem_64_codons_e_3_stops(self):
        self.assertEqual(len(CODIGO), 64)
        self.assertEqual(sorted(c for c, a in CODIGO.items() if a == "STOP"),
                         sorted(STOPS_RNA))


class TestPropriedadesAT4(unittest.TestCase):
    def test_matriz_score_e_traceback_contra_oraculo(self):
        rnd = random.Random(404)
        for _ in range(N):
            a = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 12)))
            b = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 12)))
            ma, mi, g = rnd.randint(1, 3), rnd.randint(-3, -1), rnd.randint(-3, -1)
            for metodo in ("local", "global"):
                r = alinhar_dna(a, b, metodo, ma, mi, g)
                F = dp(a, b, metodo, ma, mi, g)
                with self.subTest(a=a, b=b, metodo=metodo, p=(ma, mi, g)):
                    self.assertTrue(r.ok, r.resultado)
                    self.assertEqual([list(l) for l in r.matriz], F, "matriz ≠ oráculo")
                    esperado = F[-1][-1] if metodo == "global" else max(max(l) for l in F)
                    self.assertEqual(r.score, esperado, "score ≠ oráculo")
                    self.assertEqual(len(r.alinhado1), len(r.alinhado2))
                    self.assertEqual(len(r.marcadores), len(r.alinhado1))
                    self.assertFalse(any(x == "-" and y == "-"
                                         for x, y in zip(r.alinhado1, r.alinhado2)))
                    s1, s2 = r.alinhado1.replace("-", ""), r.alinhado2.replace("-", "")
                    soma = sum(g if "-" in (x, y) else (ma if x == y else mi)
                               for x, y in zip(r.alinhado1, r.alinhado2))
                    self.assertEqual(soma, r.score)
                    if metodo == "global":
                        self.assertEqual((s1, s2), (a, b))
                    elif esperado > 0:
                        self.assertTrue(s1 and s2, "local com score > 0 não pode ser vazio")
                        self.assertIn(s1, a)
                        self.assertIn(s2, b)
                        # início do traceback = primeiro máximo em ordem de leitura
                        primeiro = next((i, j) for i in range(len(F)) for j in range(len(F[0]))
                                        if F[i][j] == esperado)
                        self.assertEqual(tuple(r.inicio_traceback), primeiro)
                    else:
                        self.assertEqual((r.alinhado1, r.alinhado2), ("", ""))


class TestCLISemWeb(unittest.TestCase):
    """SPEC §12/M9: a CLI funciona com a camada web removida (sem `web/` nem `webserver.py`).

    Os demais caminhos da CLI (stdin, interativo, passos, lotes, arquivos, exportações,
    rótulos, códigos de saída) já são cobertos por `test_cli.py`, `test_cli_interativo.py`
    e `test_cli_all.py`, que importam apenas a CLI. Aqui se prova que eles não dependem
    dos arquivos da web.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="biocompiler_sem_web_"))
        shutil.copytree(RAIZ / "biocompiler", cls.tmp / "biocompiler",
                        ignore=shutil.ignore_patterns("web", "webserver.py", "__pycache__"))
        shutil.copy(RAIZ / "main.py", cls.tmp / "main.py")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rodar(self, *args, entrada=None):
        return subprocess.run([sys.executable, "-S", "main.py", *args], cwd=self.tmp,
                              capture_output=True, text=True, timeout=120,
                              input=entrada, stdin=None if entrada is not None
                              else subprocess.DEVNULL)

    def test_copia_nao_tem_web(self):
        self.assertFalse((self.tmp / "biocompiler" / "web").exists())
        self.assertFalse((self.tmp / "biocompiler" / "webserver.py").exists())

    def test_help_e_comandos(self):
        self.assertEqual(self.rodar("--help").returncode, 0)
        for args, chave in ((("at1", "--seq", "CCATGGCTAAACCGTAAGG"), "at1"),
                            (("at2", "--seq", "CCAUGGCUGUCCCCCCCCCCACCCCCCCCCCCCCCCCAGAAACCGUAAGG"),
                             "at2"),
                            (("at3", "--seq", "m7GpppCCAUGGCUAAACCGUAAGG" + "A" * 100), "at3")):
            p = self.rodar(*args, "--format", "json", "--no-save")
            with self.subTest(cmd=args[0]):
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(json.loads(p.stdout)[0]["atividade"], chave)
        p = self.rodar("at4", "--seq1", "ACGTAC", "--seq2", "ACGTTC", "--format", "json",
                       "--no-save")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('"score": 9', p.stdout)
        p = self.rodar("all", "--seq1", "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG",
                       "--seq2", "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG",
                       "--format", "json", "--no-save")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Met-Ala-Asn-Pro", p.stdout)

    def test_lote_por_stdin_e_exportacao_sem_web(self):
        p = self.rodar("at1", "--input", "-", "--out-dir", "saida_teste", "--quiet",
                       entrada="CCATGGCTAAACCGTAAGG\nATGCCC\n")
        self.assertEqual(p.returncode, 2, p.stderr)  # um registro com diagnóstico (D015)
        csv = (self.tmp / "saida_teste" / "at1_resultados.txt").read_text(encoding="utf-8")
        self.assertIn("CORRETO", csv)
        self.assertIn("BUG - STOP ausente", csv)

    def test_serve_sem_web_orienta_sem_traceback(self):
        p = self.rodar("serve", "--port", "0")
        self.assertEqual(p.returncode, 1)
        self.assertNotIn("Traceback", p.stderr)
        self.assertIn("interface web", p.stderr)
        self.assertIn("não está disponível", p.stderr)


if __name__ == "__main__":
    unittest.main()
