"""Testes de aceite da CLI, leitura e exportações (OS-M5-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: enunciados AT1 §§9/11/14, AT2 §§9/11/14, Ribossomo §§9/11/14, AT4
§§2.1/2.4/3.9/4.1/4.2; docs/SPEC.md §8; docs/DECISIONS.md D014/D015.
Somente biblioteca padrão. A CLI é exercitada por subprocesso com ``python -S``
a partir de diretórios temporários (nada é gravado no repositório).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from biocompiler import exports, io_formats, servicos
from biocompiler.core.at1 import transcrever_dna
from biocompiler.core.at2 import maturar_pre_mrna
from biocompiler.core.at3 import traduzir_mrna
from biocompiler.core.at4 import alinhar_dna

RAIZ = Path(__file__).resolve().parent.parent
MAIN = RAIZ / "main.py"

CAP = "m7Gppp"
A100 = "A" * 100
SEP_IGUAL = "=" * 40
SEP_TRACO = "-" * 40

AT1_CASOS = [
    "ATGGCTAAACCGTAA", "ATGGCTXAACCGTAA", "CCCGCTAAACCGTAA",
    "ATGGCTAAACCGGGC", "ATGGCTAAAACCGTAA", "ATGGCTTAACCGGGCTAA",
]
AT1_CSV = (
    "linha;status;resultado;pre_mRNA\n"
    "1;OK;CORRETO;AUGGCUAAACCGUAA\n"
    "2;ERRO;BUG - base inválida;NÃO GERADO\n"
    "3;ERRO;BUG - START ausente;NÃO GERADO\n"
    "4;ERRO;BUG - STOP ausente;NÃO GERADO\n"
    "5;ERRO;BUG - frameshift;NÃO GERADO\n"
    "6;ERRO;BUG - nonsense / STOP prematuro;NÃO GERADO\n"
)
AT2_CASOS = [
    "CCCGUCCCCACCCCCCCCCCAGCCC", "CCCCCCCCACCCCCCCCCCAGCCC",
    "CCCGUCCCCACCCCCCCCCCCCCCC", "CCCGU" + "C" * 16 + "AAGCCC",
]
AT2_CSV = (
    "linha;status;resultado;mRNA_maduro\n"
    f"1;OK;CORRETO;{CAP}CCCCCC{A100}\n"
    "2;ERRO;BUG - sítio 5' ausente;NÃO GERADO\n"
    "3;ERRO;BUG - sítio 3' ausente;NÃO GERADO\n"
    "4;ERRO;BUG - branch point;NÃO GERADO\n"
)
AT3_CASOS = [
    CAP + "CCAUGGCUAAACCGUAAGG" + A100,
    "CCAUGGCUAAACCGUAAGG" + A100,
    CAP + "CCGCCGCUAAACCGUAAGG" + A100,
    CAP + "CCAUGGCUAAACCGGGCGG" + A100,
    CAP + "CCAUGGCUAAAACCGUAAGG" + A100,
    CAP + "CCAUGGCUAAACCGUAAGG" + "A" * 80,
]
AT3_CSV = (
    "linha;status;resultado;proteina\n"
    "1;OK;CORRETO;Met-Ala-Lys-Pro\n"
    "2;ERRO;BUG - CAP 5';NÃO GERADA\n"
    "3;ERRO;BUG - START ausente;NÃO GERADA\n"
    "4;ERRO;BUG - STOP ausente;NÃO GERADA\n"
    "5;ERRO;BUG - quadro de leitura;NÃO GERADA\n"
    "6;ERRO;BUG - cauda poli-A;NÃO GERADA\n"
)
NUCLEO = {"at1": transcrever_dna, "at2": maturar_pre_mrna, "at3": traduzir_mrna}
ARQ_AT4 = ("alinhamento_{m}.txt", "matriz_pontuacao_{m}.csv",
           "matriz_traceback_{m}.csv", "alinhamento_{m}.csv")


def _env(**extra):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    env.update(extra)
    return env


def cli(*args, cwd, entrada=None, env=None):
    """Executa ``python -S main.py <args>`` e devolve (rc, stdout, stderr) em texto UTF-8."""
    proc = subprocess.run(
        [sys.executable, "-S", str(MAIN), *args], cwd=cwd,
        input=(entrada.encode("utf-8") if isinstance(entrada, str) else entrada),
        stdin=None if entrada is not None else subprocess.DEVNULL,
        capture_output=True, env=env or _env(), timeout=120,
    )
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def ler(caminho):
    return Path(caminho).read_bytes().decode("utf-8")


def escrever(pasta, nome, texto):
    caminho = Path(pasta) / nome
    caminho.write_bytes(texto.encode("utf-8") if isinstance(texto, str) else texto)
    return caminho


def tokens_grade(linhas_relatorio, titulo, m):
    """Tokens das m+2 linhas que seguem o título de uma matriz no relatório."""
    i = linhas_relatorio.index(titulo)
    return [linha.split() for linha in linhas_relatorio[i + 1:i + 3 + m]]


class Temp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# ======================================================== io_formats (texto)

class TestSepararRegistros(unittest.TestCase):
    def test_linhas_fisicas(self):
        casos = {
            "A\nB\n": ["A", "B"],
            "A\nB": ["A", "B"],
            "A\n\nB\n": ["A", "", "B"],
            "A\r\nB\r\n": ["A", "B"],
            "": [],
            "\n": [""],
            " A \n": [" A "],
            "A\n\n": ["A", ""],
        }
        for texto, esperado in casos.items():
            with self.subTest(texto=texto):
                self.assertEqual(io_formats.separar_registros(texto), esperado)


class TestLerPar(unittest.TestCase):
    def test_txt_duas_linhas(self):
        self.assertEqual(io_formats.ler_par("acgt\nTTGA\n"), ("acgt", "TTGA"))
        self.assertEqual(io_formats.ler_par("ACGT\r\nTTGA"), ("ACGT", "TTGA"))
        self.assertEqual(io_formats.ler_par("\nTTGA\n"), ("", "TTGA"))

    def test_txt_quantidade_errada(self):
        for texto, n in [("A\nC\nG\n", 3), ("ACGT\n", 1), ("", 0), ("A\nC\n\n", 3)]:
            with self.subTest(texto=texto):
                with self.assertRaises(io_formats.ErroEntrada) as cm:
                    io_formats.ler_par(texto)
                self.assertEqual(str(cm.exception),
                                 f"esperadas exatamente 2 sequências, encontradas {n}")

    def test_fasta_multilinha_e_cabecalhos(self):
        texto = "\n>Seq1 descrição livre\nACG  \r\nTAC\n\n>Seq2\nacgttc\n"
        self.assertEqual(io_formats.ler_par(texto), ("ACGTAC", "acgttc"))

    def test_fasta_registro_vazio(self):
        self.assertEqual(io_formats.ler_par(">S1\n>S2\nACGT\n"), ("", "ACGT"))

    def test_fasta_quantidade_errada(self):
        for texto, n in [(">a\nA\n>b\nC\n>c\nG\n", 3), (">a\nACGT\n", 1)]:
            with self.subTest(texto=texto):
                with self.assertRaises(io_formats.ErroEntrada) as cm:
                    io_formats.ler_par(texto)
                self.assertEqual(str(cm.exception),
                                 f"esperadas exatamente 2 sequências, encontradas {n}")

    def test_erro_entrada_e_exception(self):
        self.assertTrue(issubclass(io_formats.ErroEntrada, Exception))


class TestLerTexto(Temp):
    def test_utf8_com_e_sem_bom(self):
        a = escrever(self.dir, "a.txt", "ACGT\nTTGA\n")
        b = escrever(self.dir, "b.txt", b"\xef\xbb\xbfACGT\n")
        self.assertEqual(io_formats.ler_texto(str(a)), "ACGT\nTTGA\n")
        self.assertEqual(io_formats.ler_texto(str(b)), "ACGT\n")

    def test_inexistente_ilegivel_e_pasta(self):
        faltando = str(self.dir / "nao_existe.txt")
        with self.assertRaises(io_formats.ErroEntrada) as cm:
            io_formats.ler_texto(faltando)
        self.assertEqual(str(cm.exception), f"arquivo não encontrado: {faltando}")
        ruim = escrever(self.dir, "ruim.txt", b"ACGT\xff\xfe\n")
        for caminho in (str(ruim), str(self.dir)):
            with self.subTest(caminho=caminho):
                with self.assertRaises(io_formats.ErroEntrada) as cm:
                    io_formats.ler_texto(caminho)
                self.assertEqual(str(cm.exception), f"arquivo ilegível: {caminho}")


# ============================================================== servicos

class TestServicos(unittest.TestCase):
    def test_processar_lote_preserva_ordem_e_igual_ao_nucleo(self):
        for at, casos in (("at1", AT1_CASOS), ("at2", AT2_CASOS), ("at3", AT3_CASOS)):
            with self.subTest(at=at):
                res = servicos.processar_lote(at, casos + [""])
                self.assertIsInstance(res, tuple)
                self.assertEqual(res, tuple(NUCLEO[at](s) for s in casos + [""]))

    def test_processar_lote_rejeita_outras(self):
        for nome in ("at4", "all", "xyz"):
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    servicos.processar_lote(nome, ["ACGT"])

    def test_alinhar_par(self):
        args = ("ACGTAC", "ACGTTC")
        self.assertEqual(servicos.alinhar_par(*args, "both", 2, -1, -2),
                         (alinhar_dna(*args, "local", 2, -1, -2),
                          alinhar_dna(*args, "global", 2, -1, -2)))
        self.assertEqual(servicos.alinhar_par(*args, "global", 2, -1, -2),
                         (alinhar_dna(*args, "global", 2, -1, -2),))
        r = servicos.alinhar_par(*args, "xyz", 2, -1, -2)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].resultado, "ERRO - método inválido")


# ================================================================ exports

class TestExportsLote(unittest.TestCase):
    def test_csv_canonico_dos_professores(self):
        for at, casos, esperado in (("at1", AT1_CASOS, AT1_CSV), ("at2", AT2_CASOS, AT2_CSV),
                                    ("at3", AT3_CASOS, AT3_CSV)):
            with self.subTest(at=at):
                res = [NUCLEO[at](s) for s in casos]
                self.assertEqual(exports.csv_lote(at, res), esperado)

    def test_csv_ponto_e_virgula_no_campo_e_escapado(self):
        r = transcrever_dna("AT;G")
        texto = exports.csv_lote("at1", [r])
        self.assertEqual(texto.splitlines()[1], "1;ERRO;BUG - base inválida;NÃO GERADO")

    def test_relatorio_at1(self):
        res = [transcrever_dna(AT1_CASOS[0]), transcrever_dna(AT1_CASOS[1])]
        esperado = (
            f"{SEP_IGUAL}\nBIOCOMPILER 1.0 - DNA TRANSCRIBER\n{SEP_IGUAL}\n"
            "ENTRADA: 1\nSTATUS: CORRETO\nBases: OK\nSTART: ATG - OK\n"
            "Quadro de leitura: OK\nSTOP: TAA - OK\nTranscrição: OK\n"
            f"pré-mRNA: AUGGCUAAACCGUAA\n{SEP_TRACO}\n"
            "ENTRADA: 2\nSTATUS: ERRO\nTIPO: BUG - base inválida\n"
            f"pré-mRNA: NÃO GERADO\n{SEP_TRACO}\n"
        )
        self.assertEqual(exports.relatorio_lote("at1", res), esperado)

    def test_relatorio_at2(self):
        res = [maturar_pre_mrna(AT2_CASOS[0]), maturar_pre_mrna(AT2_CASOS[3])]
        esperado = (
            f"{SEP_IGUAL}\nBIOCOMPILER 2.0 - RNA PROCESSOR\n{SEP_IGUAL}\n"
            "ENTRADA: 1\nSTATUS: CORRETO\nSítio 5': OK\nBranch point: OK\n"
            "Sítio 3': OK\nSplicing: OK\nCAP 5': ADICIONADA\nCauda poli-A: 100 A\n"
            f"mRNA MADURO: {CAP}CCCCCC{A100}\n{SEP_TRACO}\n"
            "ENTRADA: 2\nSTATUS: ERRO\nTIPO: BUG - branch point\n"
            f"mRNA MADURO: NÃO GERADO\n{SEP_TRACO}\n"
        )
        self.assertEqual(exports.relatorio_lote("at2", res), esperado)

    def test_relatorio_at3(self):
        res = [traduzir_mrna(AT3_CASOS[0]), traduzir_mrna(AT3_CASOS[1])]
        esperado = (
            f"{SEP_IGUAL}\nRIBOSSOMO - PROTEIN TRANSLATOR\n{SEP_IGUAL}\n"
            "ENTRADA: 1\nSTATUS: CORRETO\nCAP 5': OK\nSTART: AUG - OK\n"
            "Quadro de leitura: OK\nSTOP: UAA - OK\nCauda poli-A: 100 A - OK\n"
            f"Tradução: OK\nPROTEÍNA: Met-Ala-Lys-Pro\n{SEP_TRACO}\n"
            "ENTRADA: 2\nSTATUS: ERRO\nTIPO: BUG - CAP 5'\n"
            f"PROTEÍNA: NÃO GERADA\n{SEP_TRACO}\n"
        )
        self.assertEqual(exports.relatorio_lote("at3", res), esperado)

    def test_stop_variavel_no_relatorio(self):
        r1 = transcrever_dna("CCATGTGACC")
        self.assertIn("STOP: TGA - OK\n", exports.relatorio_lote("at1", [r1]))
        r3 = traduzir_mrna(CAP + "AUGUAG" + A100)
        self.assertIn("STOP: UAG - OK\n", exports.relatorio_lote("at3", [r3]))


class TestExportsAT4(unittest.TestCase):
    def setUp(self):
        self.g = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        self.l = alinhar_dna("ACGTAC", "ACGTTC", "local", 2, -1, -2)

    def _csv_esperado(self, r, valores, d=";"):
        linhas = [d.join(["", "-", *r.seq2])]
        rotulos = ["-", *r.seq1]
        for i, linha in enumerate(valores):
            linhas.append(d.join([rotulos[i], *map(str, linha)]))
        return "\n".join(linhas) + "\n"

    def test_csv_matrizes_completas(self):
        for r in (self.g, self.l):
            with self.subTest(metodo=r.metodo):
                self.assertEqual(exports.csv_matriz_pontuacao(r),
                                 self._csv_esperado(r, r.matriz))
                self.assertEqual(exports.csv_matriz_traceback(r),
                                 self._csv_esperado(r, r.direcoes))
        self.assertEqual(exports.csv_matriz_pontuacao(self.g).splitlines()[:2],
                         [";-;A;C;G;T;T;C", "-;0;-2;-4;-6;-8;-10;-12"])
        self.assertEqual(exports.csv_matriz_pontuacao(self.g, ",").splitlines()[0],
                         ",-,A,C,G,T,T,C")

    def test_csv_alinhamento_exemplo(self):
        esperado = (
            "posicao;seq1;marcador;seq2;contribuicao_score\n"
            "1;A;|;A;2\n2;C;|;C;2\n3;G;|;G;2\n4;T;|;T;2\n5;A;.;T;-1\n6;C;|;C;2\n"
        )
        self.assertEqual(exports.csv_alinhamento(self.g), esperado)

    def test_csv_alinhamento_com_gaps_soma_score(self):
        r = alinhar_dna("ACGTTGCA", "ACGCA", "global", 2, -1, -2)
        self.assertGreater(r.gaps, 0)
        linhas = exports.csv_alinhamento(r, ",").splitlines()
        self.assertEqual(linhas[0], "posicao,seq1,marcador,seq2,contribuicao_score")
        corpo = [l.split(",") for l in linhas[1:]]
        self.assertEqual(len(corpo), r.tamanho)
        self.assertEqual(sum(int(c[4]) for c in corpo), r.score)
        for k, (pos, a, m, b, c) in enumerate(corpo):
            self.assertEqual((int(pos), a, m, b), (k + 1, r.alinhado1[k], r.marcadores[k],
                                                    r.alinhado2[k]))
            if "-" in (a, b):
                self.assertEqual((m, int(c)), (" ", -2))

    def test_relatorio_sucesso(self):
        texto = exports.relatorio_at4(self.g)
        linhas = texto.split("\n")
        self.assertEqual(linhas[:7], [
            SEP_IGUAL, "ALINHAMENTO GLOBAL (NEEDLEMAN-WUNSCH)", SEP_IGUAL,
            "Seq1 original: ACGTAC", "Seq2 original: ACGTTC",
            "Match: +2   Mismatch: -1   Gap: -2", "STATUS: CORRETO"])
        for linha in ("Início do traceback: (6,6)",
                      "Caminho: (6,6) (5,5) (4,4) (3,3) (2,2) (1,1) (0,0)",
                      "Seq1: A C G T A C", "      | | | | . |", "Seq2: A C G T T C",
                      "Score: 9", "Matches: 5   Mismatches: 1   Gaps: 0   Tamanho: 6"):
            self.assertIn(linha, linhas)
        i = linhas.index("Seq1: A C G T A C")
        self.assertEqual(linhas[i + 1:i + 4],
                         ["      | | | | . |", "Seq2: A C G T T C", "Score: 9"])
        self.assertTrue(texto.endswith(SEP_TRACO + "\n"))
        self.assertEqual(linhas[-2], SEP_TRACO)
        self.assertEqual(exports.relatorio_at4(self.l).split("\n")[1],
                         "ALINHAMENTO LOCAL (SMITH-WATERMAN)")

    def test_relatorio_mostra_matrizes_inteiras(self):
        r = alinhar_dna("acgta", "TCATG", "local", 3, -2, -4)
        linhas = exports.relatorio_at4(r).split("\n")
        rotulos = ["-", *r.seq1]
        pont = tokens_grade(linhas, "MATRIZ DE PONTUAÇÃO", len(r.seq1))
        trac = tokens_grade(linhas, "MATRIZ DE TRACEBACK", len(r.seq1))
        self.assertEqual(pont[0], ["-", *r.seq2])
        self.assertEqual(trac[0], ["-", *r.seq2])
        for i in range(len(r.seq1) + 1):
            self.assertEqual(pont[i + 1], [rotulos[i], *map(str, r.matriz[i])])
            self.assertEqual(trac[i + 1], [rotulos[i], *r.direcoes[i]])
        self.assertIn("Match: +3   Mismatch: -2   Gap: -4", linhas)
        self.assertIn("Início do traceback: (3,5)", linhas)

    def test_relatorio_marcador_de_gap(self):
        r = alinhar_dna("ACGTTGCA", "ACGCA", "global", 2, -1, -2)
        linhas = exports.relatorio_at4(r).split("\n")
        i = linhas.index("Seq1: " + " ".join(r.alinhado1))
        self.assertEqual(linhas[i + 1], ("      " + " ".join(r.marcadores)).rstrip())
        self.assertEqual(linhas[i + 2], "Seq2: " + " ".join(r.alinhado2))

    def test_relatorio_local_sem_similaridade(self):
        r = alinhar_dna("AAAA", "CCCC", "local", 2, -1, -2)
        linhas = exports.relatorio_at4(r).split("\n")
        self.assertIn("Início do traceback: nenhum (sem região de similaridade positiva)", linhas)
        self.assertIn("Score: 0", linhas)
        self.assertFalse(any(l.startswith("Caminho:") for l in linhas))
        self.assertFalse(any(l.startswith("Seq1: ") for l in linhas))

    def test_relatorio_erro(self):
        r = alinhar_dna("ACGTAX", "ACGTTC", "global", 2, -1, -2)
        esperado = (
            f"{SEP_IGUAL}\nALINHAMENTO GLOBAL (NEEDLEMAN-WUNSCH)\n{SEP_IGUAL}\n"
            "Seq1 original: ACGTAX\nSeq2 original: ACGTTC\n"
            "Match: +2   Mismatch: -1   Gap: -2\n"
            "STATUS: ERRO\nTIPO: ERRO - base inválida\n- Seq1, posição 6: X\n"
            f"{SEP_TRACO}\n"
        )
        self.assertEqual(exports.relatorio_at4(r), esperado)

    def test_relatorio_erro_parametro_e_metodo(self):
        r = alinhar_dna("ACGT", "ACGT", "global", "abc", -1, -2)
        texto = exports.relatorio_at4(r)
        self.assertNotIn("Match:", texto)
        self.assertIn("TIPO: ERRO - parâmetro não numérico\n- match não numérico: 'abc'\n", texto)
        r = alinhar_dna("ACGT", "ACGT", "xyz", 2, -1, -2)
        self.assertEqual(exports.relatorio_at4(r).split("\n")[1], "ALINHAMENTO")

    def test_comparacao(self):
        esperado = (
            "COMPARAÇÃO LOCAL × GLOBAL\n"
            "Seq1 original: ACGTAC\nSeq2 original: ACGTTC\n"
            "Match: +2   Mismatch: -1   Gap: -2\n"
            f"LOCAL: score={self.l.score} tamanho={self.l.tamanho} matches={self.l.matches} "
            f"mismatches={self.l.mismatches} gaps={self.l.gaps}\n"
            "GLOBAL: score=9 tamanho=6 matches=5 mismatches=1 gaps=0\n"
        )
        self.assertEqual(exports.texto_comparacao(self.l, self.g), esperado)


# ===================================================== CLI — AT1 a AT3

class TestCliLote(Temp):
    def _entrada(self, casos, nome="entrada.txt"):
        return escrever(self.dir, nome, "\n".join(casos) + "\n")

    def test_at1_arquivo_padrao(self):
        self._entrada(AT1_CASOS)
        rc, out, err = cli("at1", "--input", "entrada.txt", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        res = [transcrever_dna(s) for s in AT1_CASOS]
        self.assertEqual(out, exports.relatorio_lote("at1", res))
        destino = self.dir / "saidas" / "at1_resultados.txt"
        self.assertEqual(ler(destino), AT1_CSV)
        self.assertIn("at1_resultados.txt", err)
        self.assertFalse(destino.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", destino.read_bytes())

    def test_at2_e_at3_arquivos_do_professor(self):
        for at, casos, esperado in (("at2", AT2_CASOS, AT2_CSV), ("at3", AT3_CASOS, AT3_CSV)):
            with self.subTest(at=at):
                self._entrada(casos, f"{at}.txt")
                rc, out, err = cli(at, "-i", f"{at}.txt", cwd=self.dir)
                self.assertEqual(rc, 2, err)
                self.assertEqual(ler(self.dir / "saidas" / f"{at}_resultados.txt"), esperado)
                self.assertEqual(out, exports.relatorio_lote(at, [NUCLEO[at](s) for s in casos]))

    def test_tudo_correto_retorna_0(self):
        self._entrada(["ATGGCTAAACCGTAA", "CCCATGGCTAAACCGTAA"])
        rc, _, err = cli("at1", "-i", "entrada.txt", "--fast", cwd=self.dir)
        self.assertEqual(rc, 0, err)

    def test_padrao_nao_sobrescreve_numerando(self):
        self._entrada(AT1_CASOS[:1])
        cli("at1", "-i", "entrada.txt", cwd=self.dir)
        self._entrada(AT1_CASOS[1:2])
        rc, _, err = cli("at1", "-i", "entrada.txt", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        saidas = self.dir / "saidas"
        self.assertIn("1;OK;CORRETO", ler(saidas / "at1_resultados.txt"))
        self.assertIn("1;ERRO;BUG - base inválida", ler(saidas / "at1_resultados_2.txt"))
        cli("at1", "-i", "entrada.txt", cwd=self.dir)
        self.assertTrue((saidas / "at1_resultados_3.txt").exists())

    def test_output_explicito_e_force(self):
        self._entrada(AT1_CASOS)
        rc, _, err = cli("at1", "-i", "entrada.txt", "-o", "resultados.txt", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        self.assertEqual(ler(self.dir / "resultados.txt"), AT1_CSV)
        self.assertFalse((self.dir / "saidas").exists())
        escrever(self.dir, "resultados.txt", "antigo\n")
        rc, out, err = cli("at1", "-i", "entrada.txt", "-o", "resultados.txt", cwd=self.dir)
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("arquivo já existe: resultados.txt (use --force para sobrescrever)", err)
        self.assertEqual(ler(self.dir / "resultados.txt"), "antigo\n")
        rc, _, err = cli("at1", "-i", "entrada.txt", "-o", "resultados.txt", "--force",
                         cwd=self.dir)
        self.assertEqual(rc, 2, err)
        self.assertEqual(ler(self.dir / "resultados.txt"), AT1_CSV)

    def test_output_cria_pastas(self):
        self._entrada(AT1_CASOS)
        rc, _, err = cli("at1", "-i", "entrada.txt", "-o", "x/y/r.csv", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        self.assertEqual(ler(self.dir / "x" / "y" / "r.csv"), AT1_CSV)

    def test_out_dir(self):
        self._entrada(AT1_CASOS)
        rc, _, err = cli("at1", "-i", "entrada.txt", "--out-dir", "res", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        self.assertEqual(ler(self.dir / "res" / "at1_resultados.txt"), AT1_CSV)
        rc, _, err = cli("at1", "-i", "entrada.txt", "--out-dir", "res", cwd=self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("arquivo já existe:", err)
        self.assertFalse((self.dir / "res" / "at1_resultados_2.txt").exists())

    def test_no_save_format_csv_e_quiet(self):
        self._entrada(AT1_CASOS)
        rc, out, err = cli("at1", "-i", "entrada.txt", "--no-save", "--format", "csv",
                           cwd=self.dir)
        self.assertEqual((rc, out, err), (2, AT1_CSV, ""))
        self.assertFalse((self.dir / "saidas").exists())
        rc, out, err = cli("at1", "-i", "entrada.txt", "--quiet", cwd=self.dir)
        self.assertEqual((rc, out, err), (2, "", ""))
        self.assertEqual(ler(self.dir / "saidas" / "at1_resultados.txt"), AT1_CSV)

    def test_seq_direta(self):
        rc, out, err = cli("at1", "--seq", "ATGGCTAAACCGTAA", "--no-save", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        self.assertIn("ENTRADA: 1\nSTATUS: CORRETO\n", out)
        self.assertIn("pré-mRNA: AUGGCUAAACCGUAA\n", out)
        rc, out, _ = cli("at3", "--seq", AT3_CASOS[0], "--no-save", "--format", "csv",
                         cwd=self.dir)
        self.assertEqual((rc, out), (0, "linha;status;resultado;proteina\n"
                                        "1;OK;CORRETO;Met-Ala-Lys-Pro\n"))

    def test_linhas_vazias_intermediarias_mantem_numeracao(self):
        escrever(self.dir, "e.txt", "ATGGCTAAACCGTAA\n\nATGGCTAAACCGTAA\r\n")
        rc, out, _ = cli("at1", "-i", "e.txt", "--no-save", "--format", "csv", cwd=self.dir)
        self.assertEqual(rc, 2)
        self.assertEqual(out.splitlines()[1:], [
            "1;OK;CORRETO;AUGGCUAAACCGUAA",
            "2;ERRO;BUG - entrada vazia;NÃO GERADO",
            "3;OK;CORRETO;AUGGCUAAACCGUAA"])

    def test_stdin(self):
        rc, out, err = cli("at1", "--input", "-", "--no-save", "--format", "csv",
                           cwd=self.dir, entrada="\r\n".join(AT1_CASOS) + "\r\n")
        self.assertEqual((rc, out), (2, AT1_CSV), err)
        rc, out, err = cli("at2", "-i", "-", "--no-save", cwd=self.dir, entrada="")
        self.assertEqual((rc, out), (1, ""))
        self.assertIn("nenhuma sequência na entrada", err)

    def test_bom_aceito(self):
        escrever(self.dir, "e.txt", b"\xef\xbb\xbfATGGCTAAACCGTAA\n")
        rc, out, err = cli("at1", "-i", "e.txt", "--no-save", "--format", "csv", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.splitlines()[1], "1;OK;CORRETO;AUGGCUAAACCGUAA")

    def test_erros_de_entrada_retorno_1_sem_gravar(self):
        self._entrada(AT1_CASOS)
        escrever(self.dir, "ruim.txt", b"ACGT\xff\n")
        casos = [
            (("at1",), "informe --input ou --seq"),
            (("at1", "-i", "entrada.txt", "--seq", "ATG"), "use apenas um entre --input e --seq"),
            (("at1", "-i", "nao_existe.txt"), "arquivo não encontrado: nao_existe.txt"),
            (("at2", "-i", "ruim.txt"), "arquivo ilegível: ruim.txt"),
            (("at1", "-i", "entrada.txt", "-o", "r.txt", "--no-save"),
             "opções incompatíveis: --output e --no-save"),
            (("at1", "-i", "entrada.txt", "-o", "r.txt", "--out-dir", "d"),
             "opções incompatíveis: --output e --out-dir"),
        ]
        for args, mensagem in casos:
            with self.subTest(args=args):
                rc, out, err = cli(*args, cwd=self.dir)
                self.assertEqual(rc, 1)
                self.assertEqual(out, "")
                self.assertIn(f"biocompiler: {mensagem}", err)
                self.assertEqual(sorted(p.name for p in self.dir.iterdir()),
                                 ["entrada.txt", "ruim.txt"])

    def test_erros_de_argparse_retornam_1(self):
        for args in (("at1", "--formato", "x"), ("at1", "--format", "xml"),
                     ("at1", "--seq1", "A"), ("comando-inexistente",)):
            with self.subTest(args=args):
                rc, out, err = cli(*args, cwd=self.dir)
                self.assertEqual(rc, 1)
                self.assertIn("usage:", err)

    def test_saida_utf8_independente_do_locale(self):
        env = _env(LANG="C", LC_ALL="C", PYTHONUTF8="0")
        env.pop("PYTHONIOENCODING")
        rc, out, err = cli("at1", "--seq", "ATGGCTXAACCGTAA", "--no-save", cwd=self.dir, env=env)
        self.assertEqual(rc, 2, err)
        self.assertIn("TIPO: BUG - base inválida\npré-mRNA: NÃO GERADO\n", out)


# ============================================================ CLI — AT4

class TestCliAT4(Temp):
    def _esperados(self, metodos, s1="ACGTAC", s2="ACGTTC", p=(2, -1, -2), d=";"):
        res = {m: alinhar_dna(s1, s2, m, *p) for m in metodos}
        arquivos = {}
        for m, r in res.items():
            arquivos[f"alinhamento_{m}.txt"] = exports.relatorio_at4(r)
            arquivos[f"matriz_pontuacao_{m}.csv"] = exports.csv_matriz_pontuacao(r, d)
            arquivos[f"matriz_traceback_{m}.csv"] = exports.csv_matriz_traceback(r, d)
            arquivos[f"alinhamento_{m}.csv"] = exports.csv_alinhamento(r, d)
        return res, arquivos

    def _conferir_pasta(self, pasta, arquivos):
        self.assertEqual(sorted(p.name for p in Path(pasta).iterdir()), sorted(arquivos))
        for nome, conteudo in arquivos.items():
            with self.subTest(arquivo=nome):
                self.assertEqual(ler(Path(pasta) / nome), conteudo)

    def test_global_com_out_dir(self):
        rc, out, err = cli("at4", "--seq1", "ACGTAC", "--seq2", "ACGTTC", "--method", "global",
                           "--out-dir", "res", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        res, arquivos = self._esperados(["global"])
        self.assertEqual(out, exports.relatorio_at4(res["global"]))
        self.assertIn("Score: 9\n", out)
        self._conferir_pasta(self.dir / "res", arquivos)
        self.assertFalse((self.dir / "saidas").exists())

    def test_both_padrao_e_colisao(self):
        rc, out, err = cli("at4", "--seq1", "ACGTAC", "--seq2", "ACGTTC", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        res, arquivos = self._esperados(["local", "global"])
        comp = exports.texto_comparacao(res["local"], res["global"])
        arquivos["comparacao.txt"] = comp
        self.assertEqual(out, exports.relatorio_at4(res["local"])
                         + exports.relatorio_at4(res["global"]) + comp)
        self._conferir_pasta(self.dir / "saidas" / "at4", arquivos)
        rc, _, err = cli("at4", "--seq1", "ACGTAC", "--seq2", "ACGTTC", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        self._conferir_pasta(self.dir / "saidas" / "at4_2", arquivos)

    def test_out_dir_existente_exige_force(self):
        args = ("at4", "--seq1", "ACGT", "--seq2", "ACGT", "--method", "local", "--out-dir", "r")
        self.assertEqual(cli(*args, cwd=self.dir)[0], 0)
        escrever(self.dir / "r", "matriz_pontuacao_local.csv", "antigo\n")
        rc, out, err = cli(*args, cwd=self.dir)
        self.assertEqual((rc, out), (1, ""))
        self.assertIn("arquivo já existe:", err)
        self.assertEqual(ler(self.dir / "r" / "matriz_pontuacao_local.csv"), "antigo\n")
        self.assertEqual(cli(*args, "--force", cwd=self.dir)[0], 0)
        self.assertNotEqual(ler(self.dir / "r" / "matriz_pontuacao_local.csv"), "antigo\n")

    def test_entrada_fasta_e_txt(self):
        escrever(self.dir, "par.fasta", ">Seq1\nacg\ntac\n>Seq2\nACGTTC\n")
        escrever(self.dir, "par.txt", "acgtac\r\nACGTTC\r\n")
        for nome in ("par.fasta", "par.txt"):
            with self.subTest(arquivo=nome):
                rc, out, err = cli("at4", "-i", nome, "--method", "global", "--no-save",
                                   cwd=self.dir)
                self.assertEqual(rc, 0, err)
                self.assertEqual(out, exports.relatorio_at4(
                    alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)))

    def test_stdin_fasta(self):
        rc, out, err = cli("at4", "-i", "-", "--method", "local", "--no-save", cwd=self.dir,
                           entrada=">a\nacgta\n>b\nTCATG\n")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out, exports.relatorio_at4(
            alinhar_dna("acgta", "TCATG", "local", 2, -1, -2)))

    def test_parametros_e_delimitador(self):
        rc, _, err = cli("at4", "--seq1", "acgta", "--seq2", "TCATG", "--method", "local",
                         "--match", "3", "--mismatch", "-2", "--gap", "-4",
                         "--delimiter", "comma", "--out-dir", "r", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        _, arquivos = self._esperados(["local"], "acgta", "TCATG", (3, -2, -4), ",")
        self._conferir_pasta(self.dir / "r", arquivos)
        self.assertIn("Score: 4", ler(self.dir / "r" / "alinhamento_local.txt"))

    def test_erro_do_nucleo_retorna_2_sem_artefatos(self):
        rc, out, err = cli("at4", "--seq1", "ACGTAX", "--seq2", "ACGTTC", "--method", "global",
                           cwd=self.dir)
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, exports.relatorio_at4(
            alinhar_dna("ACGTAX", "ACGTTC", "global", 2, -1, -2)))
        self.assertEqual(list(self.dir.iterdir()), [])
        rc, out, _ = cli("at4", "--seq1", "ACGT", "--seq2", "ACGT", "--match", "abc",
                         "--no-save", cwd=self.dir)
        self.assertEqual(rc, 2)
        self.assertIn("TIPO: ERRO - parâmetro não numérico\n- match não numérico: 'abc'\n", out)

    def test_quantidade_e_combinacoes_invalidas(self):
        escrever(self.dir, "tres.txt", "ACGT\nACGT\nACGT\n")
        escrever(self.dir, "um.fasta", ">a\nACGT\n")
        casos = [
            (("-i", "tres.txt"), "esperadas exatamente 2 sequências, encontradas 3"),
            (("-i", "um.fasta"), "esperadas exatamente 2 sequências, encontradas 1"),
            (("-i", "nao_existe.fasta"), "arquivo não encontrado: nao_existe.fasta"),
            ((), "informe --input ou --seq1 e --seq2"),
            (("--seq1", "ACGT"), "--seq1 e --seq2 devem ser informados juntos"),
            (("-i", "tres.txt", "--seq1", "A", "--seq2", "C"),
             "use apenas um entre --input e --seq1/--seq2"),
        ]
        for args, mensagem in casos:
            with self.subTest(args=args):
                rc, out, err = cli("at4", *args, cwd=self.dir)
                self.assertEqual((rc, out), (1, ""))
                self.assertIn(f"biocompiler: {mensagem}", err)
        self.assertFalse((self.dir / "saidas").exists())

    def test_argparse_at4(self):
        for args in (("--method", "xyz"), ("-o", "r.txt"), ("--delimiter", "tab"),
                     ("--seq", "ACGT")):
            with self.subTest(args=args):
                rc, _, err = cli("at4", "--seq1", "A", "--seq2", "A", *args, cwd=self.dir)
                self.assertEqual(rc, 1)
                self.assertIn("usage:", err)

    def test_quiet(self):
        rc, out, err = cli("at4", "--seq1", "ACGT", "--seq2", "ACGT", "--quiet", cwd=self.dir)
        self.assertEqual((rc, out, err), (0, "", ""))
        self.assertEqual(len(list((self.dir / "saidas" / "at4").iterdir())), 9)


# ================================================== ajuda, exemplos, test

class TestAjudaExemplos(Temp):
    def test_ajuda_por_comando(self):
        for sub in ("at1", "at2", "at3", "at4", "examples", "test"):
            with self.subTest(sub=sub):
                rc, out, _ = cli(sub, "--help", cwd=self.dir)
                self.assertEqual(rc, 0)
                if sub.startswith("at"):
                    self.assertIn("Códigos de saída", out)
                    self.assertIn("Exemplo", out)
                    self.assertIn(f"python -m biocompiler {sub}", out)
        _, out, _ = cli("at4", "--help", cwd=self.dir)
        for opcao in ("--seq1", "--seq2", "--method", "--match", "--mismatch", "--gap",
                      "--delimiter", "--out-dir", "--force", "--no-save", "--quiet"):
            self.assertIn(opcao, out)
        _, out, _ = cli("at1", "--help", cwd=self.dir)
        for opcao in ("--input", "--seq", "--output", "--out-dir", "--format", "--fast",
                      "--quiet", "--no-save", "--force"):
            self.assertIn(opcao, out)

    def test_examples_lista(self):
        rc, out, err = cli("examples", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        for seq in AT1_CASOS + AT2_CASOS + AT3_CASOS + ["ACGTAC", "ACGTTC"]:
            self.assertIn(seq, out)
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_examples_write_e_execucao_ponta_a_ponta(self):
        rc, _, err = cli("examples", "--write", "ex", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        ex = self.dir / "ex"
        self.assertEqual(sorted(p.name for p in ex.iterdir()),
                         ["at1_exemplos.txt", "at2_exemplos.txt", "at3_exemplos.txt",
                          "at4_exemplo.fasta"])
        self.assertEqual(ler(ex / "at1_exemplos.txt"), "\n".join(AT1_CASOS) + "\n")
        self.assertEqual(ler(ex / "at2_exemplos.txt"), "\n".join(AT2_CASOS) + "\n")
        self.assertEqual(ler(ex / "at3_exemplos.txt"), "\n".join(AT3_CASOS) + "\n")
        self.assertEqual(ler(ex / "at4_exemplo.fasta"), ">Seq1\nACGTAC\n>Seq2\nACGTTC\n")
        for at, esperado in (("at1", AT1_CSV), ("at2", AT2_CSV), ("at3", AT3_CSV)):
            with self.subTest(at=at):
                rc, out, _ = cli(at, "-i", f"ex/{at}_exemplos.txt", "--no-save", "--format",
                                 "csv", cwd=self.dir)
                self.assertEqual((rc, out), (2, esperado))
        rc, out, _ = cli("at4", "-i", "ex/at4_exemplo.fasta", "--method", "global",
                         "--no-save", cwd=self.dir)
        self.assertEqual(rc, 0)
        self.assertIn("Score: 9\n", out)
        rc, _, err = cli("examples", "--write", "ex", cwd=self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("arquivo já existe:", err)
        self.assertEqual(cli("examples", "--write", "ex", "--force", cwd=self.dir)[0], 0)


# ============================================================ isolamento

SONDA_CLI = r'''
import io, json, sys, contextlib
for nome in {bloquear!r}:
    sys.modules[nome] = None
saida, erro = io.StringIO(), io.StringIO()
with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
    from biocompiler.__main__ import main
    codigo = main({argv!r})
carregados = sorted(n for n in sys.modules if sys.modules[n] is not None
                    and (n.startswith("biocompiler") or n.startswith("jinja2")))
print(json.dumps({{"codigo": codigo, "stdout": saida.getvalue(), "carregados": carregados}}))
'''


class TestIsolamentoCli(unittest.TestCase):
    def _sondar(self, argv, bloquear):
        proc = subprocess.run(
            [sys.executable, "-S", "-c", SONDA_CLI.format(argv=argv, bloquear=bloquear)],
            cwd=RAIZ, env=_env(), capture_output=True, text=True, encoding="utf-8",
            timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def test_cada_atividade_sem_as_outras(self):
        mods = {a: f"biocompiler.core.{a}" for a in ("at1", "at2", "at3", "at4")}
        web = ["biocompiler.webserver", "jinja2", "biocompiler.core.pipeline"]
        casos = {
            "at1": ["at1", "--seq", "ATGGCTAAACCGTAA", "--no-save"],
            "at2": ["at2", "--seq", AT2_CASOS[0], "--no-save"],
            "at3": ["at3", "--seq", AT3_CASOS[0], "--no-save"],
            "at4": ["at4", "--seq1", "ACGTAC", "--seq2", "ACGTTC", "--no-save"],
        }
        for at, argv in casos.items():
            with self.subTest(at=at):
                outras = [m for a, m in mods.items() if a != at]
                r = self._sondar(argv, outras + web)
                self.assertEqual(r["codigo"], 0, r["stdout"])
                self.assertIn(mods[at], r["carregados"])
                for proibido in outras + web:
                    self.assertNotIn(proibido, r["carregados"])


if __name__ == "__main__":
    unittest.main()
