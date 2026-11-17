"""Testes do ponto de entrada na raiz `main.py` (OS-M0-02).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

`python main.py <args>` deve ser equivalente a `python -m biocompiler <args>`
(mesmo stdout, stderr e código de saída), funcionar de qualquer diretório
atual e preservar o despacho preguiçoso (sem web/ATs no --help).
Somente biblioteca padrão.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MAIN = RAIZ / "main.py"
ATS = ("at1", "at2", "at3", "at4")


def _env():
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return env


def _rodar(args, cwd):
    return subprocess.run([sys.executable, "-S", *args], cwd=cwd, env=_env(),
                          capture_output=True, text=True, encoding="utf-8", timeout=60)


SONDA = r'''
import io, json, runpy, sys, contextlib
for nome in {bloquear!r}:
    sys.modules[nome] = None
sys.argv = [{main!r}] + {argv!r}
saida, erro = io.StringIO(), io.StringIO()
codigo = None
with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
    try:
        runpy.run_path({main!r}, run_name={run_name!r})
    except SystemExit as e:
        codigo = e.code
carregados = sorted(n for n, m in sys.modules.items()
                    if m is not None and (n == "jinja2" or n.startswith("jinja2.")
                                          or n == "biocompiler" or n.startswith("biocompiler.")))
print(json.dumps({{"codigo": codigo, "stdout": saida.getvalue(),
                  "stderr": erro.getvalue(), "carregados": carregados}}))
'''


def _sondar(argv, bloquear=("jinja2",), run_name="__main__"):
    codigo = SONDA.format(bloquear=list(bloquear), main=str(MAIN), argv=list(argv),
                          run_name=run_name)
    # sys.path[0] de "-c" é o diretório atual: rodar na raiz para achar o pacote,
    # como acontece quando o script main.py é executado.
    proc = _rodar(["-c", codigo], cwd=RAIZ)
    if proc.returncode != 0:
        raise AssertionError(f"sonda falhou (rc={proc.returncode}):\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestMainRaiz(unittest.TestCase):
    def test_main_py_existe_na_raiz(self):
        self.assertTrue(MAIN.is_file())

    def test_importacoes_de_topo_somente_sys(self):
        arvore = ast.parse(MAIN.read_text(encoding="utf-8"))
        topo = []
        for no in arvore.body:
            if isinstance(no, ast.Import):
                topo += [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom):
                topo.append(no.module or "")
        self.assertTrue(set(topo) <= {"sys", "__future__"}, topo)

    def test_nao_importa_web_nem_ats_nem_terceiros(self):
        arvore = ast.parse(MAIN.read_text(encoding="utf-8"))
        alvos = []
        for no in ast.walk(arvore):
            if isinstance(no, ast.Import):
                alvos += [a.name for a in no.names]
            elif isinstance(no, ast.ImportFrom):
                alvos.append(no.module or "")
        for alvo in alvos:
            raiz = alvo.split(".")[0]
            self.assertTrue(raiz in sys.stdlib_module_names or raiz == "biocompiler", alvo)
            self.assertFalse(alvo.startswith(("biocompiler.webserver", "biocompiler.web",
                                              "biocompiler.core", "biocompiler.cli")), alvo)

    def test_importar_main_py_nao_executa_nada(self):
        r = _sondar(["--help"], run_name="main")
        self.assertIsNone(r["codigo"])
        self.assertEqual(r["stdout"], "")
        self.assertEqual(r["stderr"], "")
        self.assertEqual(r["carregados"], [])

    def test_help_sem_web_nem_ats(self):
        r = _sondar(["--help"])
        self.assertEqual(r["codigo"], 0)
        self.assertIn("serve", r["stdout"])
        for proibido in ["jinja2", "biocompiler.webserver", "biocompiler.core.pipeline"] + [
                f"biocompiler.core.{a}" for a in ATS]:
            self.assertNotIn(proibido, r["carregados"])

    def test_serve_sem_jinja2_orienta_instalacao(self):
        r = _sondar(["serve"])
        self.assertEqual(r["codigo"], 1)
        self.assertIn("python -m pip install -r requirements-web.txt", r["stderr"])
        self.assertNotIn("biocompiler.cli", r["carregados"])

    def test_equivalente_a_python_m_biocompiler(self):
        casos = [["--help"], [], ["serve", "--help"], ["at1"], ["at4", "--help"],
                 ["comando-inexistente"]]
        for args in casos:
            with self.subTest(args=args):
                via_main = _rodar([str(MAIN), *args], cwd=RAIZ)
                via_m = _rodar(["-m", "biocompiler", *args], cwd=RAIZ)
                self.assertEqual(via_main.returncode, via_m.returncode)
                self.assertEqual(via_main.stdout, via_m.stdout)
                self.assertEqual(via_main.stderr, via_m.stderr)

    def test_funciona_a_partir_de_outro_diretorio(self):
        with tempfile.TemporaryDirectory() as outro:
            proc = _rodar([str(MAIN), "--help"], cwd=outro)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("serve", proc.stdout)
            self.assertEqual(os.listdir(outro), [])

    def test_caminho_relativo_na_raiz(self):
        proc = _rodar(["main.py", "--help"], cwd=RAIZ)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("at1", proc.stdout)


if __name__ == "__main__":
    unittest.main()
