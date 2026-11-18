"""M9 — propriedades da SPEC §12 com entradas geradas e CLI funcional sem a camada web.

As entradas são construídas pela gramática de cada enunciado (sementes fixas), sem
consultar os exemplos do professor. Só biblioteca padrão.
"""
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
N = 300  # casos por propriedade


def codons_sem_stop(rnd, n, rna=False):
    stops = STOPS_RNA if rna else STOPS_DNA
    alfa = "ACGU" if rna else "ACGT"
    saida = []
    while len(saida) < n:
        c = "".join(rnd.choice(alfa) for _ in range(3))
        if c not in stops:
            saida.append(c)
    return "".join(saida)


class TestPropriedadesAT1(unittest.TestCase):
    def test_transcricao_integral_quando_valida(self):
        rnd = random.Random(101)
        validos = 0
        for _ in range(N):
            if rnd.random() < 0.6:
                dna = ("".join(rnd.choice("ACGT") for _ in range(rnd.randint(0, 8))) + "ATG"
                       + codons_sem_stop(rnd, rnd.randint(0, 15)) + rnd.choice(STOPS_DNA)
                       + "".join(rnd.choice("ACGT") for _ in range(rnd.randint(0, 8))))
            else:
                dna = "".join(rnd.choice("ACGTN") for _ in range(rnd.randint(1, 40)))
            r = transcrever_dna(dna)
            with self.subTest(dna=dna):
                if r.ok:
                    validos += 1
                    self.assertEqual(len(r.pre_mrna), len(dna))
                    self.assertEqual(r.pre_mrna, dna.replace("T", "U"))
                    self.assertEqual(dna[r.posicao_start:r.posicao_start + 3], "ATG")
                    self.assertIn(dna[r.posicao_stop:r.posicao_stop + 3], STOPS_DNA)
                    self.assertEqual((r.posicao_stop - r.posicao_start) % 3, 0)
                else:
                    self.assertIsNone(r.pre_mrna, "entrada inválida não produz pré-mRNA")
        self.assertGreater(validos, N // 3)


class TestPropriedadesAT2(unittest.TestCase):
    def test_maduro_e_remocao_somente_de_introns(self):
        rnd = random.Random(202)
        validos = 0
        for _ in range(N):
            exon = lambda: "".join(rnd.choice("CU") for _ in range(rnd.randint(2, 10)))  # noqa: E731
            d = rnd.randint(10, 30)
            intron = "GU" + "C" * rnd.randint(1, 6) + "A" + "C" * d + "AG"
            pre = exon() + intron + exon()
            if rnd.random() < 0.4:
                pre += "".join(rnd.choice("C") for _ in range(2)) + (
                    "GU" + "C" * 2 + "A" + "C" * rnd.randint(10, 30) + "AG") + exon()
            r = maturar_pre_mrna(pre)
            with self.subTest(pre=pre):
                if not r.ok:
                    continue
                validos += 1
                self.assertEqual(r.mrna_maduro, "m7Gppp" + r.rna_processado + "A" * 100)
                removidas = set()
                for i in r.introns:
                    self.assertEqual(pre[i.posicao_gu:i.posicao_gu + 2], "GU")
                    self.assertEqual(pre[i.posicao_branch], "A")
                    self.assertEqual(pre[i.posicao_ag:i.posicao_ag + 2], "AG")
                    self.assertTrue(10 <= i.posicao_ag - i.posicao_branch - 1 <= 30)  # D009
                    removidas.update(range(i.posicao_gu, i.posicao_ag + 2))
                mantidas = "".join(b for k, b in enumerate(pre) if k not in removidas)
                self.assertEqual(r.rna_processado, mantidas)
        self.assertGreater(validos, N // 2)


class TestPropriedadesAT3(unittest.TestCase):
    def test_aminoacidos_igual_codons_ate_o_stop(self):
        rnd = random.Random(303)
        validos = 0
        for _ in range(N):
            utr5 = "".join(rnd.choice("CG") for _ in range(rnd.randint(0, 6)))
            regiao = (utr5 + "AUG" + codons_sem_stop(rnd, rnd.randint(0, 20), rna=True)
                      + rnd.choice(STOPS_RNA) + "".join(rnd.choice("CG") for _ in range(3)))
            mrna = "m7Gppp" + regiao + "A" * 100
            r = traduzir_mrna(mrna)
            with self.subTest(mrna=regiao):
                self.assertTrue(r.ok, r.resultado)
                validos += 1
                n_codons = (r.posicao_stop - r.posicao_start) // 3
                self.assertEqual(len(r.aminoacidos), n_codons)
                self.assertEqual(r.proteina, "-".join(r.aminoacidos))
                self.assertEqual(r.aminoacidos[0], "Met")
                self.assertTrue(all(len(a) == 3 and "STOP" not in a.upper()
                                    for a in r.aminoacidos))
        self.assertEqual(validos, N)


class TestPropriedadesAT4(unittest.TestCase):
    def test_reconstrucao_e_score(self):
        rnd = random.Random(404)
        for _ in range(N):
            a = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 14)))
            b = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(1, 14)))
            ma, mi, g = rnd.randint(1, 3), rnd.randint(-3, -1), rnd.randint(-3, -1)
            for metodo in ("local", "global"):
                r = alinhar_dna(a, b, metodo, ma, mi, g)
                with self.subTest(a=a, b=b, metodo=metodo, p=(ma, mi, g)):
                    self.assertTrue(r.ok, r.resultado)
                    s1, s2 = r.alinhado1.replace("-", ""), r.alinhado2.replace("-", "")
                    if metodo == "global":
                        self.assertEqual((s1, s2), (a, b))
                    else:
                        self.assertIn(s1, a)
                        self.assertIn(s2, b)
                    soma = 0
                    for x, y in zip(r.alinhado1, r.alinhado2):
                        soma += g if "-" in (x, y) else (ma if x == y else mi)
                    self.assertEqual(soma, r.score)
                    self.assertEqual(r.matches * ma + r.mismatches * mi + r.gaps * g, r.score)
                    self.assertEqual(r.score, r.matriz[r.inicio_traceback[0]][
                        r.inicio_traceback[1]] if r.inicio_traceback else 0)


class TestCLISemWeb(unittest.TestCase):
    """SPEC §12/M9: a CLI funciona com a camada web removida (sem `web/` nem `webserver.py`)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="biocompiler_sem_web_"))
        shutil.copytree(RAIZ / "biocompiler", cls.tmp / "biocompiler",
                        ignore=shutil.ignore_patterns("web", "webserver.py", "__pycache__"))
        shutil.copy(RAIZ / "main.py", cls.tmp / "main.py")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def rodar(self, *args):
        return subprocess.run([sys.executable, "-S", "main.py", *args], cwd=self.tmp,
                              capture_output=True, text=True, stdin=subprocess.DEVNULL,
                              timeout=120)

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

    def test_serve_sem_web_falha_com_orientacao_e_sem_traceback(self):
        p = self.rodar("serve", "--port", "0")
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn("Traceback", p.stderr)


if __name__ == "__main__":
    unittest.main()
