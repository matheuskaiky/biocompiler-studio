"""Testes de aceite do comando `all` e do relatório mestre (OS-M6-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Fontes: docs/SPEC.md §2.1, §8.3 (modo `all`), §11.1; docs/DECISIONS.md D015–D017.
Somente biblioteca padrão; CLI real por subprocesso com ``python -S``.
"""

import dataclasses
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from biocompiler import exports, servicos
from biocompiler.core.at1 import transcrever_dna
from biocompiler.core.at4 import alinhar_dna
from biocompiler.core.pipeline import executar_fluxo

RAIZ = Path(__file__).resolve().parent.parent
MAIN = RAIZ / "main.py"
SEQ1 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG"
SEQ2 = "CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG"
IGUAL, TRACO = "=" * 40, "-" * 40
A100 = "A" * 100
NAO_EXEC = "NÃO EXECUTADO — dependência inválida"
ARQ_ETAPAS = ["at1_resultados.txt", "at2_resultados.txt", "at3_resultados.txt",
              "relatorio_mestre.txt"]


def _env():
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return env


def cli(*args, cwd, entrada=None):
    proc = subprocess.run(
        [sys.executable, "-S", str(MAIN), *args], cwd=cwd,
        input=entrada.encode("utf-8") if entrada is not None else None,
        stdin=None if entrada is not None else subprocess.DEVNULL,
        capture_output=True, env=_env(), timeout=120)
    return proc.returncode, proc.stdout.decode("utf-8"), proc.stderr.decode("utf-8")


def ler(caminho):
    return Path(caminho).read_bytes().decode("utf-8")


class Temp(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# ============================================================ exports

class TestExportsFluxo(unittest.TestCase):
    def test_csv_lote_com_etapa_nao_executada(self):
        r = transcrever_dna("ATGGCTAAACCGTAA")
        self.assertEqual(exports.csv_lote("at1", [r, None]),
                         "linha;status;resultado;pre_mRNA\n"
                         "1;OK;CORRETO;AUGGCUAAACCGUAA\n"
                         f"2;NÃO EXECUTADO;{NAO_EXEC};NÃO GERADO\n")
        self.assertEqual(exports.csv_lote("at3", [None]).splitlines()[1],
                         f"1;NÃO EXECUTADO;{NAO_EXEC};NÃO GERADA")

    def test_relatorio_mestre_exemplo_spec(self):
        rf = executar_fluxo(SEQ1, SEQ2)
        cadeias = ""
        for k, (dna, proc, prot, cods) in enumerate((
                (SEQ1, "CCAUGGCUAAACCGUAAGG", "Met-Ala-Lys-Pro", "AUG GCU AAA CCG UAA"),
                (SEQ2, "CCAUGGCUAAUCCGUAAGG", "Met-Ala-Asn-Pro", "AUG GCU AAU CCG UAA")), 1):
            cadeias += (
                f"SEQ{k}\nDNA: {dna}\n"
                f"AT1: CORRETO\n  pré-mRNA: {dna.replace('T', 'U')}\n"
                "AT2: CORRETO\n"
                "  Íntron 1: GU no índice 8, branch A no índice 20, AG no índice 36\n"
                f"  mRNA maduro: m7Gppp{proc}{A100}\n"
                f"AT3: CORRETO\n  Códons: {cods}\n  Proteína: {prot}\n"
                f"CADEIA: OK\n{TRACO}\n")
        esperado = (f"{IGUAL}\nLABORATÓRIO COMPLETO (AT1 → AT2 → AT3 + AT4)\n{IGUAL}\n"
                    + cadeias
                    + exports.relatorio_at4(rf.alinhamentos[0])
                    + exports.relatorio_at4(rf.alinhamentos[1])
                    + exports.texto_comparacao(*rf.alinhamentos))
        self.assertEqual(exports.relatorio_fluxo(rf), esperado)

    def test_relatorio_mestre_com_falhas(self):
        rf = executar_fluxo("CCCGCTAAACCGTAA", "ATGGCTAAACCGTAA", "global")
        texto = exports.relatorio_fluxo(rf)
        self.assertIn("SEQ1\nDNA: CCCGCTAAACCGTAA\nAT1: BUG - START ausente\n"
                      f"AT2: {NAO_EXEC}\nAT3: {NAO_EXEC}\nCADEIA: ERRO (falha em AT1)\n{TRACO}\n",
                      texto)
        self.assertIn("SEQ2\nDNA: ATGGCTAAACCGTAA\nAT1: CORRETO\n  pré-mRNA: AUGGCUAAACCGUAA\n"
                      f"AT2: BUG - sítio 3' ausente\nAT3: {NAO_EXEC}\n"
                      f"CADEIA: ERRO (falha em AT2)\n{TRACO}\n", texto)
        self.assertTrue(texto.endswith(exports.relatorio_at4(rf.alinhamentos[0])))
        self.assertNotIn("COMPARAÇÃO", texto)


class TestServicoFluxo(unittest.TestCase):
    def test_servico_delega_ao_pipeline(self):
        self.assertEqual(servicos.fluxo_completo(SEQ1, SEQ2, "both", 2, -1, -2),
                         executar_fluxo(SEQ1, SEQ2, "both", 2, -1, -2))


# ================================================================= CLI

class TestCliAll(Temp):
    def _arquivos_at4(self, rf, d=";"):
        arq = {}
        for r in rf.alinhamentos:
            m = r.metodo
            arq[f"alinhamento_{m}.txt"] = exports.relatorio_at4(r)
            arq[f"matriz_pontuacao_{m}.csv"] = exports.csv_matriz_pontuacao(r, d)
            arq[f"matriz_traceback_{m}.csv"] = exports.csv_matriz_traceback(r, d)
            arq[f"alinhamento_{m}.csv"] = exports.csv_alinhamento(r, d)
        if len(rf.alinhamentos) == 2:
            arq["comparacao.txt"] = exports.texto_comparacao(*rf.alinhamentos)
        return arq

    def _etapas(self, rf):
        return {
            "relatorio_mestre.txt": exports.relatorio_fluxo(rf),
            "at1_resultados.txt": exports.csv_lote("at1", [rf.seq1.at1, rf.seq2.at1]),
            "at2_resultados.txt": exports.csv_lote("at2", [rf.seq1.at2, rf.seq2.at2]),
            "at3_resultados.txt": exports.csv_lote("at3", [rf.seq1.at3, rf.seq2.at3]),
        }

    def _conferir(self, pasta, arquivos):
        self.assertEqual(sorted(p.name for p in Path(pasta).iterdir()), sorted(arquivos))
        for nome, conteudo in arquivos.items():
            with self.subTest(arquivo=nome):
                self.assertEqual(ler(Path(pasta) / nome), conteudo)

    def test_exemplo_spec_padrao(self):
        rc, out, err = cli("all", "--seq1", SEQ1, "--seq2", SEQ2, cwd=self.dir)
        self.assertEqual(rc, 0, err)
        rf = executar_fluxo(SEQ1, SEQ2)
        self.assertEqual(out, exports.relatorio_fluxo(rf))
        self._conferir(self.dir / "saidas" / "all", {**self._etapas(rf), **self._arquivos_at4(rf)})
        self.assertIn("1;OK;CORRETO;Met-Ala-Lys-Pro", ler(self.dir / "saidas" / "all" / "at3_resultados.txt"))
        self.assertIn("2;OK;CORRETO;Met-Ala-Asn-Pro", ler(self.dir / "saidas" / "all" / "at3_resultados.txt"))
        rc, _, _ = cli("all", "--seq1", SEQ1, "--seq2", SEQ2, cwd=self.dir)
        self.assertEqual(rc, 0)
        self._conferir(self.dir / "saidas" / "all_2", {**self._etapas(rf), **self._arquivos_at4(rf)})

    def test_falhas_gravam_etapas_e_retornam_2(self):
        rc, out, err = cli("all", "--seq1", "CCCGCTAAACCGTAA", "--seq2", SEQ2, "--method",
                           "global", "--out-dir", "r", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        rf = executar_fluxo("CCCGCTAAACCGTAA", SEQ2, "global")
        self.assertEqual(out, exports.relatorio_fluxo(rf))
        self._conferir(self.dir / "r", {**self._etapas(rf), **self._arquivos_at4(rf)})
        self.assertEqual(ler(self.dir / "r" / "at2_resultados.txt").splitlines()[1],
                         f"1;NÃO EXECUTADO;{NAO_EXEC};NÃO GERADO")

    def test_at4_com_erro_nao_gera_artefatos_at4(self):
        rc, _, _ = cli("all", "--seq1", "ATGXTAA", "--seq2", SEQ2, "--out-dir", "r",
                       cwd=self.dir)
        self.assertEqual(rc, 2)
        rf = executar_fluxo("ATGXTAA", SEQ2)
        self._conferir(self.dir / "r", self._etapas(rf))

    def test_entrada_fasta_txt_stdin_e_parametros(self):
        (self.dir / "par.fasta").write_text(f">Seq1\n{SEQ1[:20]}\n{SEQ1[20:]}\n>Seq2\n{SEQ2}\n",
                                            encoding="utf-8")
        (self.dir / "par.txt").write_text(f"{SEQ1}\n{SEQ2}\n", encoding="utf-8")
        rf = executar_fluxo(SEQ1, SEQ2, "local", 3, -2, -4)
        for args, entrada in ((("-i", "par.fasta"), None), (("-i", "par.txt"), None),
                              (("-i", "-"), f"{SEQ1}\r\n{SEQ2}\r\n")):
            with self.subTest(args=args):
                rc, out, err = cli("all", *args, "--method", "local", "--match", "3",
                                   "--mismatch", "-2", "--gap", "-4", "--no-save",
                                   cwd=self.dir, entrada=entrada)
                self.assertEqual(rc, 0, err)
                self.assertEqual(out, exports.relatorio_fluxo(rf))
        self.assertFalse((self.dir / "saidas").exists())

    def test_delimitador_e_ascii(self):
        rc, out, err = cli("all", "--seq1", SEQ1, "--seq2", SEQ2, "--method", "global",
                           "--delimiter", "comma", "--ascii", "--out-dir", "r", cwd=self.dir)
        self.assertEqual(rc, 0, err)
        rf = executar_fluxo(SEQ1, SEQ2, "global")
        self.assertEqual(out, exports.para_ascii(exports.relatorio_fluxo(rf)))
        self.assertNotIn("↖", out)
        self._conferir(self.dir / "r", {**self._etapas(rf), **self._arquivos_at4(rf, ",")})
        self.assertIn("→", ler(self.dir / "r" / "relatorio_mestre.txt"))

    def test_json(self):
        rc, out, err = cli("all", "--seq1", SEQ1, "--seq2", "CCCGCTAAACCGTAA", "--format",
                           "json", "--out-dir", "r", cwd=self.dir)
        self.assertEqual(rc, 2, err)
        doc = json.loads(out)
        rf = executar_fluxo(SEQ1, "CCCGCTAAACCGTAA")
        self.assertEqual(list(doc), ["schema_version", "atividade", "entrada", "configuracao",
                                     "status", "dados", "saidas", "avisos"])
        self.assertEqual(doc["atividade"], "all")
        self.assertEqual(doc["entrada"], {"seq1": SEQ1, "seq2": "CCCGCTAAACCGTAA"})
        self.assertEqual(doc["configuracao"], {"metodo": "both", "match": 2, "mismatch": -1,
                                               "gap": -2})
        self.assertEqual(doc["status"], "ERRO")
        self.assertEqual(doc["dados"], json.loads(json.dumps(dataclasses.asdict(rf),
                                                             ensure_ascii=False)))
        self.assertIsNone(doc["dados"]["seq2"]["at2"])
        ordem = (["relatorio_mestre.txt"] + ARQ_ETAPAS[:3]
                 + [n.format(m=m) for m in ("local", "global") for n in (
                     "alinhamento_{m}.txt", "matriz_pontuacao_{m}.csv",
                     "matriz_traceback_{m}.csv", "alinhamento_{m}.csv")]
                 + ["comparacao.txt"])
        self.assertEqual(doc["saidas"], [str(Path("r") / n) for n in ordem])
        for caminho in doc["saidas"]:
            self.assertTrue((self.dir / caminho).is_file(), caminho)
        self.assertEqual(doc["avisos"], [])

    def test_quiet(self):
        rc, out, err = cli("all", "--seq1", "CCCGCTAAACCGTAA", "--seq2", "ATGGCTAAACCGTAA",
                           "--method", "global", "--quiet", "--no-save", cwd=self.dir)
        self.assertEqual((rc, out), (2, ""))
        self.assertEqual(err, "biocompiler: Seq1: AT1: BUG - START ausente\n"
                              "biocompiler: Seq2: AT2: BUG - sítio 3' ausente\n")
        rc, out, err = cli("all", "--seq1", "ACGX", "--seq2", "ACGT", "--method", "global",
                           "--quiet", "--no-save", cwd=self.dir)
        self.assertEqual(err, "biocompiler: Seq1: AT1: BUG - base inválida\n"
                              "biocompiler: Seq2: AT1: BUG - START ausente\n"
                              "biocompiler: global: ERRO - base inválida\n")
        rc, out, err = cli("all", "--seq1", SEQ1, "--seq2", SEQ2, "--quiet", cwd=self.dir)
        self.assertEqual((rc, out, err), (0, "", ""))

    def test_quiet_com_falha_grava_mesmo_assim(self):
        rc, out, err = cli("all", "--seq1", "CCCGCTAAACCGTAA", "--seq2", SEQ2, "--method",
                           "global", "--quiet", cwd=self.dir)
        self.assertEqual((rc, out, err), (2, "", "biocompiler: Seq1: AT1: BUG - START ausente\n"))
        rf = executar_fluxo("CCCGCTAAACCGTAA", SEQ2, "global")
        self._conferir(self.dir / "saidas" / "all", {**self._etapas(rf), **self._arquivos_at4(rf)})

    def test_erros_de_entrada(self):
        (self.dir / "tres.txt").write_text("A\nC\nG\n", encoding="utf-8")
        casos = [
            ((), "informe --input ou --seq1 e --seq2"),
            (("--seq1", SEQ1), "--seq1 e --seq2 devem ser informados juntos"),
            (("-i", "tres.txt"), "esperadas exatamente 2 sequências, encontradas 3"),
            (("-i", "tres.txt", "--seq1", "A", "--seq2", "C"),
             "use apenas um entre --input e --seq1/--seq2"),
            (("-i", "nao_existe.txt"), "arquivo não encontrado: nao_existe.txt"),
            (("--seq1", "A", "--seq2", "C", "--out-dir", "d", "--no-save"),
             "opções incompatíveis: --out-dir e --no-save"),
            (("--seq1", "A", "--seq2", "C", "--ascii", "--format", "json"),
             "opções incompatíveis: --ascii e --format json"),
        ]
        for args, msg in casos:
            with self.subTest(args=args):
                rc, out, err = cli("all", *args, cwd=self.dir)
                self.assertEqual((rc, out), (1, ""))
                self.assertIn(f"biocompiler: {msg}", err)
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["tres.txt"])

    def test_out_dir_existente_exige_force(self):
        args = ("all", "--seq1", SEQ1, "--seq2", SEQ2, "--method", "local", "--out-dir", "r")
        self.assertEqual(cli(*args, cwd=self.dir)[0], 0)
        (self.dir / "r" / "at2_resultados.txt").write_text("antigo\n", encoding="utf-8")
        (self.dir / "r" / "relatorio_mestre.txt").unlink()
        (self.dir / "r" / "matriz_pontuacao_local.csv").unlink()
        antes = {p.name: p.read_bytes() for p in (self.dir / "r").iterdir()}
        rc, out, err = cli(*args, cwd=self.dir)
        self.assertEqual((rc, out), (1, ""))
        self.assertIn("arquivo já existe:", err)
        # Nada gravado: nem os ausentes recriados, nem os demais sobrescritos.
        self.assertEqual({p.name: p.read_bytes() for p in (self.dir / "r").iterdir()}, antes)
        self.assertEqual(cli(*args, "--force", cwd=self.dir)[0], 0)

    def test_argparse_e_ajuda(self):
        for args in (("--step",), ("--explain",), ("--interactive",), ("--format", "csv"),
                     ("--seq", "A"), ("-o", "x.txt")):
            with self.subTest(args=args):
                rc, _, err = cli("all", "--seq1", "A", "--seq2", "C", *args, cwd=self.dir)
                self.assertEqual(rc, 1)
                self.assertIn("usage:", err)
        rc, out, _ = cli("all", "--help", cwd=self.dir)
        self.assertEqual(rc, 0)
        for trecho in ("Códigos de saída", "Exemplo", "python -m biocompiler all", "--seq1",
                       "--method", "--format", "--ascii", "--delimiter", "--out-dir"):
            self.assertIn(trecho, out)

    def test_erros_de_argumento_e_leitura_antes_de_carregar_ats(self):
        sonda = r'''
import io, json, sys, contextlib
for nome in ["biocompiler.core.pipeline", "biocompiler.core.at1", "biocompiler.core.at2",
             "biocompiler.core.at3", "biocompiler.core.at4"]:
    sys.modules[nome] = None
erro = io.StringIO()
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(erro):
    from biocompiler.__main__ import main
    codigo = main({argv!r})
print(json.dumps({{"codigo": codigo, "stderr": erro.getvalue(),
                  "core": sorted(n for n in sys.modules if n.startswith("biocompiler.core")
                                 and sys.modules[n] is not None)}}))
'''
        casos = [(["all", "-i", "nao_existe.txt"], "arquivo não encontrado"),
                 (["all", "--seq1", "A"], "--seq1 e --seq2 devem ser informados juntos"),
                 (["all", "--seq1", "A", "--seq2", "C", "--out-dir", "d", "--no-save"],
                  "opções incompatíveis")]
        for argv, msg in casos:
            with self.subTest(argv=argv):
                proc = subprocess.run([sys.executable, "-S", "-c", sonda.format(argv=argv)],
                                      cwd=RAIZ, env=_env(), capture_output=True, text=True,
                                      encoding="utf-8", timeout=60, stdin=subprocess.DEVNULL)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                r = json.loads(proc.stdout.strip().splitlines()[-1])
                self.assertEqual(r["codigo"], 1, r["stderr"])
                self.assertIn(msg, r["stderr"])
                # Os módulos bloqueados estão em sys.modules como None: importá-los
                # levantaria ImportError (código 3). Nenhuma AT/pipeline carregada.
                for nome in ("pipeline", "at1", "at2", "at3", "at4"):
                    self.assertNotIn(f"biocompiler.core.{nome}", r["core"])

    def test_individual_nao_carrega_pipeline(self):
        rc, out, _ = cli("at1", "--seq", "ATGGCTAAACCGTAA", "--no-save", "--format", "csv",
                         cwd=self.dir)
        self.assertEqual((rc, out), (0, "linha;status;resultado;pre_mRNA\n"
                                        "1;OK;CORRETO;AUGGCUAAACCGUAA\n"))


if __name__ == "__main__":
    unittest.main()
