"""Testes de aceite da CLI interativa e de apresentação (OS-M5-02).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: docs/SPEC.md §8.2–8.4 (--interactive, --step, --explain, --ascii,
--format json, granularidade), §10 (eventos); docs/DECISIONS.md D015/D016.
Somente biblioteca padrão. Um terminal é simulado em subprocesso com
``python -S``, trocando ``sys.stdin`` por um objeto cujo ``isatty()`` é True.
"""

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from biocompiler import exports
from biocompiler.core.at1 import transcrever_dna
from biocompiler.core.at2 import maturar_pre_mrna
from biocompiler.core.at3 import traduzir_mrna
from biocompiler.core.at4 import alinhar_dna

RAIZ = Path(__file__).resolve().parent.parent
MAIN = RAIZ / "main.py"
SEP_TRACO = "-" * 40
PROMPT = "[Enter] próximo, p pula, q sai: "
P_LOTE = ("Cole as sequências (uma por linha) ou informe o caminho de um arquivo .txt; "
          "linha vazia encerra:\n")
P_SEQ1 = "Seq1 (ou caminho de arquivo .txt/.fasta): "
P_SEQ2 = "Seq2: "
P_METODO = "Método (local/global/both) [{}]: "
P_PARAM = "Match [{}]: Mismatch [{}]: Gap [{}]: "
P_MENU = "Escolha a atividade: 1) AT1  2) AT2  3) AT3  4) AT4  (q para sair): "
CAP = "m7Gppp"
A100 = "A" * 100

AT1_CASOS = [
    "ATGGCTAAACCGTAA", "ATGGCTXAACCGTAA", "CCCGCTAAACCGTAA",
    "ATGGCTAAACCGGGC", "ATGGCTAAAACCGTAA", "ATGGCTTAACCGGGCTAA",
]
AT2_CASOS = [
    "CCCGUCCCCACCCCCCCCCCAGCCC", "CCCCCCCCACCCCCCCCCCAGCCC",
    "CCCGUCCCCACCCCCCCCCCCCCCC", "CCCGU" + "C" * 16 + "AAGCCC",
]
AT3_CASOS = [
    CAP + "CCAUGGCUAAACCGUAAGG" + A100, "CCAUGGCUAAACCGUAAGG" + A100,
    CAP + "CCGCCGCUAAACCGUAAGG" + A100, CAP + "CCAUGGCUAAACCGGGCGG" + A100,
    CAP + "CCAUGGCUAAAACCGUAAGG" + A100, CAP + "CCAUGGCUAAACCGUAAGG" + "A" * 80,
]
NUCLEO = {"at1": transcrever_dna, "at2": maturar_pre_mrna, "at3": traduzir_mrna}
CHAVES_JSON = ["schema_version", "atividade", "entrada", "configuracao", "status",
               "resultado", "validacoes", "passos", "dados", "saidas", "avisos"]

DRIVER = r'''
import io, sys
class TTY(io.StringIO):
    def isatty(self):
        return True
sys.stdin = TTY({dados!r})
sys.path.insert(0, {raiz!r})
from biocompiler.__main__ import main
sys.exit(main({argv!r}))
'''


def _env():
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return env


def cli(*args, cwd, entrada=None):
    """CLI real sem terminal (stdin é pipe ou /dev/null)."""
    proc = subprocess.run(
        [sys.executable, "-S", str(MAIN), *args], cwd=cwd,
        input=entrada.encode("utf-8") if entrada is not None else None,
        stdin=None if entrada is not None else subprocess.DEVNULL,
        capture_output=True, env=_env(), timeout=120)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def tty(*args, cwd, dados=""):
    """CLI com stdin simulando um terminal interativo que fornece ``dados``."""
    codigo = DRIVER.format(dados=dados, raiz=str(RAIZ), argv=list(args))
    proc = subprocess.run([sys.executable, "-S", "-c", codigo], cwd=cwd,
                          stdin=subprocess.DEVNULL, capture_output=True, env=_env(),
                          timeout=120)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def ler(caminho):
    return Path(caminho).read_bytes().decode("utf-8")


def linha_passo(k, e):
    texto = f"  {k}. {e.tipo}"
    if e.posicao is not None:
        texto += f" (índice {e.posicao})"
    if e.detalhe:
        texto += f": {e.detalhe}"
    return texto


def dados_json(r):
    d = dataclasses.asdict(r)
    d.pop("eventos")
    return json.loads(json.dumps(d, ensure_ascii=False))


class Temp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def escrever(self, nome, texto):
        (self.dir / nome).write_bytes(texto.encode("utf-8"))


# ================================================================ exports

class TestExportsApresentacao(unittest.TestCase):
    def test_relatorio_lote_composto_por_cabecalho_e_blocos(self):
        for at, casos in (("at1", AT1_CASOS), ("at2", AT2_CASOS), ("at3", AT3_CASOS)):
            with self.subTest(at=at):
                res = [NUCLEO[at](s) for s in casos]
                self.assertEqual(
                    exports.relatorio_lote(at, res),
                    exports.cabecalho_lote(at)
                    + "".join(exports.bloco_lote(at, n, r) for n, r in enumerate(res, 1)))
                self.assertTrue(exports.bloco_lote(at, 3, res[2]).startswith("ENTRADA: 3\n"))

    def test_passos_fase_formato(self):
        r = transcrever_dna("CCATGGCTAAACCGTAA")
        linhas = exports.passos(r)
        self.assertEqual(linhas, [linha_passo(k, e) for k, e in enumerate(r.eventos, 1)])
        self.assertEqual(linhas[0], "  1. BASES_VALIDADAS")
        self.assertEqual(linhas[1], "  2. START_ENCONTRADO (índice 2): ATG")
        self.assertEqual(linhas[-1], f"  {len(r.eventos)}. RESULTADO: CORRETO")
        for r in (maturar_pre_mrna(AT2_CASOS[0]), traduzir_mrna(AT3_CASOS[1]),
                  alinhar_dna("ACGTAC", "ACGTTC", "local", 2, -1, -2)):
            self.assertEqual(exports.passos(r, "fase"),
                             [linha_passo(k, e) for k, e in enumerate(r.eventos, 1)])

    def _esperado_at4(self, r, extra):
        base = list(r.eventos)
        itens = [base[0]] + extra + base[1:]
        linhas = []
        for k, item in enumerate(itens, 1):
            linhas.append(item(k) if callable(item) else linha_passo(k, item))
        return linhas

    def test_passos_at4_por_linha_e_celula(self):
        r = alinhar_dna("acgta", "TCATG", "local", 3, -2, -4)
        m, n = len(r.seq1), len(r.seq2)
        por_linha = [
            (lambda i: lambda k: f"  {k}. LINHA {i}: " + " ".join(map(str, r.matriz[i])))(i)
            for i in range(m + 1)]
        self.assertEqual(exports.passos(r, "linha"), self._esperado_at4(r, por_linha))
        por_celula = [
            (lambda i, j: lambda k: f"  {k}. CELULA ({i},{j}): {r.matriz[i][j]} {r.direcoes[i][j]}")(i, j)
            for i in range(m + 1) for j in range(n + 1)]
        linhas = exports.passos(r, "celula")
        self.assertEqual(linhas, self._esperado_at4(r, por_celula))
        self.assertEqual(len(linhas), len(r.eventos) + (m + 1) * (n + 1))
        self.assertEqual(linhas[1], "  2. CELULA (0,0): 0 ·")

    def test_passos_at4_em_erro_so_eventos(self):
        r = alinhar_dna("ACGX", "ACGT", "global", 2, -1, -2)
        for g in ("fase", "linha", "celula"):
            self.assertEqual(exports.passos(r, g), ["  1. RESULTADO: ERRO - base inválida"])

    def test_grades_alinhadas(self):
        r = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        linhas = exports.relatorio_at4(r).split("\n")
        for titulo, valores in (("MATRIZ DE PONTUAÇÃO", r.matriz),
                                ("MATRIZ DE TRACEBACK", r.direcoes)):
            i = linhas.index(titulo)
            grade = linhas[i + 1:i + 9]
            self.assertEqual(len({len(l) for l in grade}), 1, grade)
            self.assertEqual(grade[0].split(), ["-", *r.seq2])
            for k, v in enumerate(valores):
                self.assertEqual(grade[k + 1].split(), [(["-"] + list(r.seq1))[k],
                                                        *map(str, v)])
        self.assertIn("  C -12  -8  -4   0   4   5   9", linhas)

    def test_para_ascii(self):
        self.assertEqual(exports.para_ascii("↖ ↑ ← · × é ã |."), "\\ ^ < * x é ã |.")


# ================================================================== JSON

class TestJson(Temp):
    def test_lote_json_e_paridade_com_api(self):
        self.escrever("e.txt", "\n".join(AT1_CASOS) + "\n")
        rc, out, err = cli("at1", "-i", "e.txt", "--format", "json", "--no-save", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        self.assertTrue(out.endswith("\n"))
        doc = json.loads(out)
        self.assertEqual(len(doc), 6)
        for n, (item, seq) in enumerate(zip(doc, AT1_CASOS), 1):
            r = transcrever_dna(seq)
            self.assertEqual(list(item), CHAVES_JSON)
            self.assertEqual(item["schema_version"], 1)
            self.assertEqual(item["atividade"], "at1")
            self.assertEqual(item["entrada"], {"linha": n, "sequencia": seq})
            self.assertEqual(item["configuracao"], {})
            self.assertEqual((item["status"], item["resultado"]), (r.status, r.resultado))
            self.assertEqual(item["validacoes"], [] if r.ok else [r.resultado])
            self.assertEqual(item["passos"], [{"tipo": e.tipo, "posicao": e.posicao,
                                               "detalhe": e.detalhe} for e in r.eventos])
            self.assertEqual(item["dados"], dados_json(r))
            self.assertEqual((item["saidas"], item["avisos"]), ([], []))
        self.assertIn("BUG - base inválida", out)  # ensure_ascii=False

    def test_json_at2_e_at3(self):
        for at, casos in (("at2", AT2_CASOS), ("at3", AT3_CASOS)):
            with self.subTest(at=at):
                self.escrever(f"{at}.txt", "\n".join(casos) + "\n")
                rc, out, _ = cli(at, "-i", f"{at}.txt", "--format", "json", "--no-save",
                                 cwd=self.dir)
                self.assertEqual(rc, 2)
                doc = json.loads(out)
                self.assertEqual([d["dados"] for d in doc],
                                 [dados_json(NUCLEO[at](s)) for s in casos])

    def test_json_lista_arquivos_gravados(self):
        rc, out, err = cli("at1", "--seq", "ATGGCTAAACCGTAA", "--format", "json",
                           cwd=self.dir)
        self.assertEqual(rc, 0, err)
        (item,) = json.loads(out)
        self.assertEqual(len(item["saidas"]), 1)
        self.assertTrue(item["saidas"][0].endswith("at1_resultados.txt"))
        self.assertEqual(ler(self.dir / item["saidas"][0]),
                         "linha;status;resultado;pre_mRNA\n1;OK;CORRETO;AUGGCUAAACCGUAA\n")

    def test_json_lote_todos_os_objetos_listam_o_arquivo(self):
        self.escrever("e.txt", "ATGGCTAAACCGTAA\nCCCGCTAAACCGTAA\n")
        rc, out, err = cli("at1", "-i", "e.txt", "--format", "json", "--out-dir", "r",
                           cwd=self.dir)
        self.assertEqual(rc, 2, err)
        doc = json.loads(out)
        self.assertEqual(len(doc), 2)
        caminho = str(Path("r") / "at1_resultados.txt")
        self.assertEqual([d["saidas"] for d in doc], [[caminho], [caminho]])

    def test_json_at4(self):
        rc, out, err = cli("at4", "--seq1", "acgtac", "--seq2", "ACGTTC", "--format", "json",
                           "--out-dir", "r", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        doc = json.loads(out)
        self.assertEqual([d["configuracao"]["metodo"] for d in doc], ["local", "global"])
        for item in doc:
            r = alinhar_dna("acgtac", "ACGTTC", item["configuracao"]["metodo"], 2, -1, -2)
            self.assertEqual(list(item), CHAVES_JSON)
            self.assertEqual(item["atividade"], "at4")
            self.assertEqual(item["entrada"], {"seq1": "acgtac", "seq2": "ACGTTC"})
            self.assertEqual(item["configuracao"], {"metodo": r.metodo, "match": 2,
                                                    "mismatch": -1, "gap": -2})
            self.assertEqual(item["dados"], dados_json(r))
            self.assertEqual(item["validacoes"], [])
            self.assertEqual(len(item["saidas"]), 9)
        self.assertEqual(doc[1]["dados"]["score"], 9)

    def test_json_at4_erro(self):
        rc, out, _ = cli("at4", "--seq1", "ACGT", "--seq2", "ACGT", "--match", "abc",
                         "--method", "global", "--format", "json", "--no-save", cwd=self.dir)
        self.assertEqual(rc, 2)
        (item,) = json.loads(out)
        self.assertEqual(item["configuracao"]["match"], "abc")
        self.assertEqual(item["status"], "ERRO")
        self.assertEqual(item["validacoes"], ["match não numérico: 'abc'"])

    def test_at4_format_csv_invalido(self):
        rc, _, err = cli("at4", "--seq1", "A", "--seq2", "A", "--format", "csv", cwd=self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("usage:", err)


# ================================================================ explain

class TestExplain(Temp):
    def test_explain_lote(self):
        rc, out, err = cli("at1", "--seq", "CCATGGCTAAACCGTAA", "--explain", "--no-save",
                           cwd=self.dir)
        self.assertEqual(rc, 0, err)
        r = transcrever_dna("CCATGGCTAAACCGTAA")
        self.assertEqual(out, exports.cabecalho_lote("at1") + exports.bloco_lote("at1", 1, r)
                         + "PASSOS — ENTRADA 1\n" + "\n".join(exports.passos(r)) + "\n"
                         + SEP_TRACO + "\n")

    def test_explain_at4_com_granularidade(self):
        rc, out, err = cli("at4", "--seq1", "ACGTAC", "--seq2", "ACGTTC", "--explain",
                           "--granularidade", "linha", "--no-save", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        rl = alinhar_dna("ACGTAC", "ACGTTC", "local", 2, -1, -2)
        rg = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        esperado = ""
        for r, nome in ((rl, "LOCAL"), (rg, "GLOBAL")):
            esperado += (exports.relatorio_at4(r) + f"PASSOS — {nome}\n"
                         + "\n".join(exports.passos(r, "linha")) + "\n" + SEP_TRACO + "\n")
        esperado += exports.texto_comparacao(rl, rg)
        self.assertEqual(out, esperado)

    def test_combinacoes_invalidas(self):
        casos = [
            (("at1", "--seq", "ATG", "--explain", "--format", "csv"),
             "opções incompatíveis: --explain e --format csv"),
            (("at3", "--seq", "ATG", "--explain", "--format", "json"),
             "opções incompatíveis: --explain e --format json"),
            (("at4", "--seq1", "A", "--seq2", "A", "--granularidade", "linha"),
             "--granularidade exige --step ou --explain"),
            (("at2", "--seq", "AUG", "--ascii", "--format", "json"),
             "opções incompatíveis: --ascii e --format json"),
            (("at4", "--seq1", "A", "--seq2", "A", "--ascii", "--format", "json"),
             "opções incompatíveis: --ascii e --format json"),
        ]
        for args, msg in casos:
            with self.subTest(args=args):
                rc, out, err = cli(*args, "--no-save", cwd=self.dir)
                self.assertEqual((rc, out), (1, ""))
                self.assertIn(f"biocompiler: {msg}", err)


# ================================================================== ascii

class TestAscii(Temp):
    def test_ascii_so_no_terminal(self):
        rc, out, err = cli("at4", "--seq1", "ACGTAC", "--seq2", "ACGTTC", "--method", "both",
                           "--ascii", "--out-dir", "r", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        rl = alinhar_dna("ACGTAC", "ACGTTC", "local", 2, -1, -2)
        rg = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        self.assertEqual(out, exports.para_ascii(exports.relatorio_at4(rl)
                                                 + exports.relatorio_at4(rg)
                                                 + exports.texto_comparacao(rl, rg)))
        for simbolo in "↖↑←·×":
            self.assertNotIn(simbolo, out)
        self.assertIn("↖", ler(self.dir / "r" / "matriz_traceback_global.csv"))
        self.assertIn("↖", ler(self.dir / "r" / "alinhamento_global.txt"))
        self.assertIn("×", ler(self.dir / "r" / "comparacao.txt"))

    def test_ascii_nao_altera_rotulos(self):
        rc, out, _ = cli("at1", "--seq", "ATGGCTXAACCGTAA", "--ascii", "--no-save",
                         cwd=self.dir)
        self.assertEqual(rc, 2)
        self.assertIn("TIPO: BUG - base inválida\npré-mRNA: NÃO GERADO\n", out)


# =================================================================== step

class TestStep(Temp):
    def test_step_lote_com_enter(self):
        r = transcrever_dna("CCATGGCTAAACCGTAA")
        n = len(r.eventos)
        rc, out, err = tty("at1", "--seq", "CCATGGCTAAACCGTAA", "--step", "--no-save",
                           cwd=self.dir, dados="\n" * n)
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.count(PROMPT), n)
        self.assertTrue(out.startswith(exports.cabecalho_lote("at1")
                                       + "PASSO A PASSO — ENTRADA 1\n"))
        esperado = "".join(f"{l}\n{PROMPT}" for l in exports.passos(r))
        self.assertIn(esperado + exports.bloco_lote("at1", 1, r), out)
        self.assertTrue(out.endswith(exports.bloco_lote("at1", 1, r)))

    def test_step_pular_e_sair(self):
        self.escrever("e.txt", "\n".join(AT1_CASOS[:3]) + "\n")
        res = [transcrever_dna(s) for s in AT1_CASOS[:3]]
        rc, out, _ = tty("at1", "-i", "e.txt", "--step", "--no-save", cwd=self.dir,
                         dados="p\n" + "\n" * 50)
        self.assertEqual(rc, 2)
        self.assertEqual(out.count(PROMPT), 1 + len(res[1].eventos) + len(res[2].eventos))
        for k, r in enumerate(res, 1):
            self.assertIn(f"PASSO A PASSO — ENTRADA {k}\n" + "\n".join(exports.passos(r)), out.replace(PROMPT, ""))
            self.assertIn(exports.bloco_lote("at1", k, r), out)
        for dados in ("q\n", ""):
            with self.subTest(dados=dados):
                rc, out, _ = tty("at1", "-i", "e.txt", "--step", "--no-save", cwd=self.dir,
                                 dados=dados)
                self.assertEqual(rc, 2)
                self.assertEqual(out.count(PROMPT), 1)
                self.assertEqual(out.replace(PROMPT, ""), exports.cabecalho_lote("at1") + "".join(
                    f"PASSO A PASSO — ENTRADA {k}\n" + "".join(f"{l}\n" for l in exports.passos(r))
                    + exports.bloco_lote("at1", k, r) for k, r in enumerate(res, 1)))

    def test_step_at4_celula(self):
        r = alinhar_dna("ACGT", "AGT", "global", 2, -1, -2)
        passos = exports.passos(r, "celula")
        rc, out, err = tty("at4", "--seq1", "ACGT", "--seq2", "AGT", "--method", "global",
                           "--step", "--granularidade", "celula", "--no-save", cwd=self.dir,
                           dados="\n" * len(passos))
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.count(PROMPT), len(passos))
        self.assertEqual(out.replace(PROMPT, ""), "PASSO A PASSO — GLOBAL\n"
                         + "".join(f"{l}\n" for l in passos) + exports.relatorio_at4(r))

    def test_step_at4_both_fase_e_ascii(self):
        rl = alinhar_dna("ACGT", "ACGT", "local", 2, -1, -2)
        rg = alinhar_dna("ACGT", "ACGT", "global", 2, -1, -2)
        rc, out, _ = tty("at4", "--seq1", "ACGT", "--seq2", "ACGT", "--step", "--ascii",
                         "--no-save", cwd=self.dir, dados="\n" * 100)
        self.assertEqual(rc, 0)
        self.assertEqual(out.count(PROMPT), len(rl.eventos) + len(rg.eventos))
        corpo = out.replace(PROMPT, "")
        self.assertEqual(corpo, exports.para_ascii(
            "PASSO A PASSO — LOCAL\n" + "".join(f"{l}\n" for l in exports.passos(rl))
            + exports.relatorio_at4(rl)
            + "PASSO A PASSO — GLOBAL\n" + "".join(f"{l}\n" for l in exports.passos(rg))
            + exports.relatorio_at4(rg) + exports.texto_comparacao(rl, rg)))

    def test_step_format_text_explicito_e_valido(self):
        r = transcrever_dna("ATGGCTAAACCGTAA")
        rc, out, err = tty("at1", "--seq", "ATGGCTAAACCGTAA", "--step", "--format", "text",
                           "--no-save", cwd=self.dir, dados="q\n")
        self.assertEqual(rc, 0, err)
        self.assertEqual(out.count(PROMPT), 1)
        self.assertTrue(out.endswith(exports.bloco_lote("at1", 1, r)))

    def test_step_exige_terminal_e_combinacoes(self):
        rc, out, err = cli("at1", "--seq", "ATG", "--step", "--no-save", cwd=self.dir)
        self.assertEqual((rc, out), (1, ""))
        self.assertIn("biocompiler: --step requer um terminal interativo", err)
        casos = [
            (("at1", "--seq", "ATG", "--step", "--quiet"), "opções incompatíveis: --step e --quiet"),
            (("at1", "--seq", "ATG", "--step", "--fast"), "opções incompatíveis: --step e --fast"),
            (("at1", "--seq", "ATG", "--step", "--explain"),
             "opções incompatíveis: --step e --explain"),
            (("at1", "--seq", "ATG", "--step", "--format", "csv"),
             "opções incompatíveis: --step e --format csv"),
            (("at4", "--seq1", "A", "--seq2", "A", "--step", "--format", "json"),
             "opções incompatíveis: --step e --format json"),
            (("at1", "-i", "-", "--step"),
             "--step não pode ser usado com entrada por stdin (--input -)"),
        ]
        for args, msg in casos:
            with self.subTest(args=args):
                rc, out, err = tty(*args, "--no-save", cwd=self.dir, dados="\n" * 20)
                self.assertEqual((rc, out), (1, ""))
                self.assertIn(f"biocompiler: {msg}", err)


# ============================================================ interativo

class TestInterativo(Temp):
    def test_lote_colando_sequencias_automatico_em_tty(self):
        rc, out, err = tty("at1", cwd=self.dir,
                           dados="ATGGCTAAACCGTAA\nATGGCTXAACCGTAA\n\n")
        self.assertEqual(rc, 2, err)
        self.assertTrue(out.startswith(P_LOTE))
        res = [transcrever_dna(AT1_CASOS[0]), transcrever_dna(AT1_CASOS[1])]
        self.assertIn(exports.relatorio_lote("at1", res), out)
        self.assertEqual(ler(self.dir / "saidas" / "at1_resultados.txt"),
                         exports.csv_lote("at1", res))

    def test_lote_por_caminho_de_arquivo(self):
        self.escrever("e.txt", "\n".join(AT3_CASOS) + "\n")
        rc, out, err = tty("at3", "--interactive", "--no-save", "--format", "csv",
                           cwd=self.dir, dados="e.txt\n")
        self.assertEqual(rc, 2, err)
        self.assertEqual(out, P_LOTE + exports.csv_lote("at3", [traduzir_mrna(s) for s in AT3_CASOS]))
        self.assertIn(exports.csv_lote("at3", [traduzir_mrna(s) for s in AT3_CASOS]), out)

    def test_lote_vazio(self):
        rc, _, err = tty("at2", "--no-save", cwd=self.dir, dados="\n")
        self.assertEqual(rc, 1)
        self.assertIn("biocompiler: nenhuma sequência na entrada", err)

    def test_at4_interativo(self):
        rc, out, err = tty("at4", cwd=self.dir, dados="ACGTAC\nACGTTC\nglobal\n\n\n\n")
        self.assertEqual(rc, 0, err)
        r = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        self.assertEqual(out, P_SEQ1 + P_SEQ2 + P_METODO.format("both")
                         + P_PARAM.format(2, -1, -2) + exports.relatorio_at4(r))
        self.assertEqual(sorted(p.name for p in (self.dir / "saidas" / "at4").iterdir()),
                         ["alinhamento_global.csv", "alinhamento_global.txt",
                          "matriz_pontuacao_global.csv", "matriz_traceback_global.csv"])

    def test_at4_metodo_invalido_repergunta_e_parametros(self):
        rc, out, err = tty("at4", "--no-save", cwd=self.dir,
                           dados="ACGT\nACGT\nxyz\nlocal\n3\n\n-5\n")
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith(P_SEQ1 + P_SEQ2 + P_METODO.format("both") * 2
                                       + P_PARAM.format(2, -1, -2)))
        self.assertIn(exports.relatorio_at4(alinhar_dna("ACGT", "ACGT", "local", 3, -1, -5)), out)

    def test_at4_parametro_invalido_vai_ao_nucleo(self):
        rc, out, _ = tty("at4", "--no-save", "--method", "global", cwd=self.dir,
                         dados="ACGT\nACGT\n\nabc\n\n\n")
        self.assertEqual(rc, 2)
        self.assertIn("- match não numérico: 'abc'\n", out)

    def test_at4_arquivo_fasta(self):
        self.escrever("par.fasta", ">a\nACGTAC\n>b\nACGTTC\n")
        rc, out, err = tty("at4", "--no-save", "--method", "local", "--match", "3",
                           cwd=self.dir, dados="par.fasta\nboth\n2\n\n\n")
        self.assertEqual(rc, 0, err)
        # Com arquivo, a Seq2 não é perguntada: logo após Seq1 vem o método.
        self.assertTrue(out.startswith(P_SEQ1 + P_METODO.format("local")
                                       + P_PARAM.format(3, -1, -2) + "=" * 40 + "\n"))
        rl = alinhar_dna("ACGTAC", "ACGTTC", "local", 2, -1, -2)
        rg = alinhar_dna("ACGTAC", "ACGTTC", "global", 2, -1, -2)
        self.assertIn(exports.relatorio_at4(rl) + exports.relatorio_at4(rg)
                      + exports.texto_comparacao(rl, rg), out)

    def test_entrada_interrompida(self):
        for args, dados in ((("at4",), "ACGT\n"), (("at4",), "ACGT\nACGT\nlocal\n2\n")):
            with self.subTest(dados=dados):
                rc, _, err = tty(*args, "--no-save", cwd=self.dir, dados=dados)
                self.assertEqual(rc, 1)
                self.assertIn("biocompiler: entrada interrompida", err)

    def test_interactive_exige_terminal_e_sem_entrada(self):
        rc, out, err = cli("at1", "--interactive", "--no-save", cwd=self.dir)
        self.assertEqual((rc, out), (1, ""))
        self.assertIn("biocompiler: --interactive requer um terminal interativo", err)
        for args in (("at1", "--seq", "ATG"), ("at4", "--seq1", "A", "--seq2", "A"),
                     ("at2", "-i", "x.txt")):
            with self.subTest(args=args):
                rc, out, err = tty(*args, "--interactive", "--no-save", cwd=self.dir)
                self.assertEqual((rc, out), (1, ""))
                self.assertIn("biocompiler: opções incompatíveis: --interactive e entrada informada",
                              err)

    def test_menu_sem_comando(self):
        rc, out, err = tty(cwd=self.dir, dados="9\n1\nATGGCTAAACCGTAA\n\n")
        self.assertEqual(rc, 0, err)
        self.assertTrue(out.startswith(P_MENU * 2 + P_LOTE))
        self.assertIn(exports.bloco_lote("at1", 1, transcrever_dna("ATGGCTAAACCGTAA")), out)
        self.assertTrue((self.dir / "saidas" / "at1_resultados.txt").exists())
        rc, out, err = tty(cwd=self.dir, dados="4\nACGT\nACGT\nlocal\n\n\n\n")
        self.assertEqual(rc, 0, err)
        self.assertIn("ALINHAMENTO LOCAL (SMITH-WATERMAN)", out)
        for dados in ("q\n", ""):
            with self.subTest(dados=dados):
                d = self.dir / "vazio"
                d.mkdir(exist_ok=True)
                rc, out, _ = tty(cwd=d, dados=dados)
                self.assertEqual((rc, out), (0, P_MENU))
                self.assertEqual(list(d.iterdir()), [])

    def test_sem_terminal_mantem_comportamento(self):
        rc, out, _ = cli(cwd=self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("usage:", out)
        rc, _, err = cli("at1", cwd=self.dir)
        self.assertEqual(rc, 1)
        self.assertIn("informe --input ou --seq", err)


if __name__ == "__main__":
    unittest.main()
