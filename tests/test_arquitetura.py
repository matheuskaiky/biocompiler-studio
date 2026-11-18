"""Testes de arquitetura e isolamento (OS-M0-01).

Autor: CTO. Testes de aceite: o pedreiro não edita este arquivo.

Duas famílias de verificação:
1. Estáticas (AST): regras de importação por camada, aplicadas a todos os
   arquivos .py presentes em biocompiler/ e tests/, inclusive os criados
   em marcos futuros.
2. Dinâmicas (subprocesso com ``python -S``): o que efetivamente é carregado
   em ``sys.modules`` ao executar --help, despacho por atividade e ``serve``.

Somente biblioteca padrão. Nenhum teste aqui importa Jinja2.
"""

import ast
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PACOTE = RAIZ / "biocompiler"
TESTES = RAIZ / "tests"

ATS = ("at1", "at2", "at3", "at4")
FUNCOES_AT = {
    "at1": ("transcrever_dna", ["sequencia"]),
    "at2": ("maturar_pre_mrna", ["sequencia"]),
    "at3": ("traduzir_mrna", ["sequencia"]),
    "at4": ("alinhar_dna", ["seq1", "seq2", "metodo", "match", "mismatch", "gap"]),
}

# Stdlib permitida em biocompiler/core/ (D005): computação pura, sem I/O,
# ambiente, processos, importação dinâmica ou expressões regulares.
STDLIB_CORE = {
    "__future__", "dataclasses", "typing", "enum", "collections",
    "itertools", "math", "functools",
}
CHAMADAS_PROIBIDAS_CORE = {
    "print", "input", "open", "eval", "exec", "compile", "__import__",
    "breakpoint",
}
WEB = ("biocompiler.webserver", "biocompiler.web", "jinja2")


# ---------------------------------------------------------------- utilitários

def _nome_modulo(caminho: Path) -> str:
    partes = list(caminho.relative_to(RAIZ).with_suffix("").parts)
    if partes[-1] == "__init__":
        partes = partes[:-1]
    return ".".join(partes)


def _pacote_de(caminho: Path) -> str:
    nome = _nome_modulo(caminho)
    return nome if caminho.name == "__init__.py" else nome.rpartition(".")[0]


def _importacoes(caminho: Path):
    """Retorna [(alvo, linha, nivel_modulo)] para cada importação do arquivo.

    ``alvo`` é o nome absoluto. Para ``from X import y`` são registrados
    ``X`` e ``X.y`` (y pode ser submódulo). ``nivel_modulo`` é True quando a
    instrução está no corpo do módulo (fora de def/class), inclusive dentro
    de if/try no topo.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    resultado = []

    def visitar(no, no_topo):
        for filho in ast.iter_child_nodes(no):
            topo = no_topo and not isinstance(
                filho, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
            )
            if isinstance(filho, ast.Import):
                for alias in filho.names:
                    resultado.append((alias.name, filho.lineno, no_topo))
            elif isinstance(filho, ast.ImportFrom):
                if filho.level:
                    base = _pacote_de(caminho).split(".")
                    if filho.level > 1:
                        base = base[: -(filho.level - 1)]
                    modulo = ".".join(base + ([filho.module] if filho.module else []))
                else:
                    modulo = filho.module
                resultado.append((modulo, filho.lineno, no_topo))
                for alias in filho.names:
                    if alias.name != "*":
                        resultado.append((f"{modulo}.{alias.name}", filho.lineno, no_topo))
            visitar(filho, topo)

    visitar(arvore, True)
    return resultado


def _casa(alvo: str, prefixos) -> bool:
    return any(alvo == p or alvo.startswith(p + ".") for p in prefixos)


def _raiz(alvo: str) -> str:
    return alvo.split(".")[0]


def _arquivos(pasta: Path):
    return sorted(p for p in pasta.rglob("*.py") if "__pycache__" not in p.parts)


def _executar(codigo: str):
    """Executa código em ``python -S`` a partir da raiz do projeto."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, "-S", "-c", codigo],
        cwd=RAIZ, env=env, capture_output=True, text=True, encoding="utf-8",
        timeout=60, stdin=subprocess.DEVNULL,  # nunca herdar terminal (D016)
    )


SONDA = r'''
import io, json, sys, contextlib
BLOQUEAR = {bloquear!r}
for nome in BLOQUEAR:
    sys.modules[nome] = None
saida, erro = io.StringIO(), io.StringIO()
codigo = None
with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
    try:
{corpo}
    except SystemExit as e:
        codigo = e.code
carregados = sorted(n for n, m in sys.modules.items()
                    if m is not None and (n == "jinja2" or n.startswith("jinja2.")
                                          or n == "biocompiler" or n.startswith("biocompiler.")))
print(json.dumps({{"codigo": codigo, "stdout": saida.getvalue(),
                  "stderr": erro.getvalue(), "carregados": carregados,
                  "extra": globals().get("EXTRA")}}))
'''


def _sondar(corpo: str, bloquear=()):
    corpo = "\n".join("        " + linha for linha in corpo.strip().splitlines())
    proc = _executar(SONDA.format(bloquear=list(bloquear), corpo=corpo))
    if proc.returncode != 0:
        raise AssertionError(f"sonda falhou (rc={proc.returncode}):\n{proc.stderr}")
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ------------------------------------------------------------ estrutura base

class TestEstruturaM0(unittest.TestCase):
    def test_arquivos_obrigatorios_existem(self):
        obrigatorios = [
            "biocompiler/__init__.py", "biocompiler/__main__.py",
            "biocompiler/cli.py", "biocompiler/servicos.py",
            "biocompiler/webserver.py", "biocompiler/core/__init__.py",
            "biocompiler/core/at1.py", "biocompiler/core/at2.py",
            "biocompiler/core/at3.py", "biocompiler/core/at4.py",
            "biocompiler/core/pipeline.py",
        ]
        faltando = [a for a in obrigatorios if not (RAIZ / a).is_file()]
        self.assertEqual(faltando, [])

    def test_requirements_web_declara_somente_jinja2(self):
        linhas = [
            l.strip() for l in (RAIZ / "requirements-web.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")
        ]
        self.assertEqual(len(linhas), 1)
        self.assertTrue(linhas[0].lower().startswith("jinja2"), linhas)


# ------------------------------------------------------- regras estáticas AST

class TestImportacoesEstaticas(unittest.TestCase):
    def _violacoes(self, pasta, regra):
        erros = []
        for arquivo in _arquivos(pasta):
            for msg in regra(arquivo, _nome_modulo(arquivo)):
                erros.append(f"{arquivo.relative_to(RAIZ)}: {msg}")
        return erros

    def test_core_somente_stdlib_pura_e_sem_dependencia_entre_ats(self):
        def regra(arquivo, nome):
            if not nome.startswith("biocompiler.core"):
                return
            permitidos_internos = {"biocompiler.modelos", "biocompiler.core.genetic_code"}
            if nome == "biocompiler.core.pipeline":
                permitidos_internos |= {f"biocompiler.core.{a}" for a in ATS}
            for alvo, linha, _ in _importacoes(arquivo):
                if _raiz(alvo) == "biocompiler":
                    # "from biocompiler.core import x" gera alvo pai + filho;
                    # o pai exato é aceito, o filho é verificado na entrada seguinte.
                    if alvo in ("biocompiler", "biocompiler.core") or _casa(alvo, permitidos_internos):
                        continue
                    yield f"linha {linha}: importa {alvo}"
                elif _raiz(alvo) not in STDLIB_CORE:
                    yield f"linha {linha}: importa {alvo} (fora da stdlib permitida em core)"

        self.assertEqual(self._violacoes(PACOTE / "core", regra), [])

    def test_core_sem_chamadas_de_io(self):
        erros = []
        for arquivo in _arquivos(PACOTE / "core"):
            arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
            for no in ast.walk(arvore):
                if (isinstance(no, ast.Call) and isinstance(no.func, ast.Name)
                        and no.func.id in CHAMADAS_PROIBIDAS_CORE):
                    erros.append(f"{arquivo.relative_to(RAIZ)}:{no.lineno}: {no.func.id}()")
        self.assertEqual(erros, [])

    def test_nada_fora_da_web_importa_terceiros_ou_web(self):
        def regra(arquivo, nome):
            if _casa(nome, ("biocompiler.webserver", "biocompiler.web")):
                return
            for alvo, linha, topo in _importacoes(arquivo):
                raiz = _raiz(alvo)
                if raiz != "biocompiler" and raiz not in sys.stdlib_module_names:
                    yield f"linha {linha}: dependência externa {alvo}"
                if _casa(alvo, WEB):
                    # Única exceção: __main__ importa webserver dentro de função.
                    if nome == "biocompiler.__main__" and alvo.startswith("biocompiler.webserver") and not topo:
                        continue
                    yield f"linha {linha}: importa camada web {alvo}"

        self.assertEqual(self._violacoes(PACOTE, regra), [])

    def test_camadas_de_aplicacao_nao_carregam_ats_no_topo(self):
        alvos_proibidos_no_topo = tuple(f"biocompiler.core.{a}" for a in ATS) + (
            "biocompiler.core.pipeline",)

        def regra(arquivo, nome):
            if nome not in ("biocompiler", "biocompiler.__main__", "biocompiler.cli",
                            "biocompiler.servicos", "biocompiler.io_formats",
                            "biocompiler.exports", "biocompiler.modelos"):
                return
            for alvo, linha, topo in _importacoes(arquivo):
                if topo and _casa(alvo, alvos_proibidos_no_topo):
                    yield f"linha {linha}: importa {alvo} no topo do módulo"

        self.assertEqual(self._violacoes(PACOTE, regra), [])

    def test_init_e_main_nao_importam_pacote_no_topo(self):
        erros = []
        for rel in ("biocompiler/__init__.py", "biocompiler/__main__.py"):
            for alvo, linha, topo in _importacoes(RAIZ / rel):
                if topo and _raiz(alvo) == "biocompiler":
                    erros.append(f"{rel}:{linha}: importa {alvo} no topo")
        self.assertEqual(erros, [])

    def test_servicos_e_modelos_nao_dependem_de_cli_nem_main(self):
        def regra(arquivo, nome):
            if nome not in ("biocompiler.servicos", "biocompiler.modelos",
                            "biocompiler.io_formats", "biocompiler.exports"):
                return
            for alvo, linha, _ in _importacoes(arquivo):
                if _casa(alvo, ("biocompiler.cli", "biocompiler.__main__")):
                    yield f"linha {linha}: importa {alvo}"

        self.assertEqual(self._violacoes(PACOTE, regra), [])

    def test_modelos_nao_importa_core_nem_aplicacao(self):
        def regra(arquivo, nome):
            if nome != "biocompiler.modelos":
                return
            for alvo, linha, _ in _importacoes(arquivo):
                if _raiz(alvo) == "biocompiler":
                    yield f"linha {linha}: importa {alvo}"

        self.assertEqual(self._violacoes(PACOTE, regra), [])

    def test_webserver_nao_chama_cli_nem_subprocesso(self):
        def regra(arquivo, nome):
            if not _casa(nome, ("biocompiler.webserver", "biocompiler.web")):
                return
            for alvo, linha, _ in _importacoes(arquivo):
                if _casa(alvo, ("biocompiler.cli", "biocompiler.__main__", "subprocess")):
                    yield f"linha {linha}: importa {alvo}"
                if _casa(alvo, tuple(f"biocompiler.core.{a}" for a in ATS)):
                    yield f"linha {linha}: importa {alvo} diretamente (usar servicos)"

        self.assertEqual(self._violacoes(PACOTE, regra), [])

    def test_testes_obrigatorios_nao_importam_web(self):
        def regra(arquivo, nome):
            if arquivo.name.startswith("test_web"):
                return
            for alvo, linha, _ in _importacoes(arquivo):
                if _casa(alvo, WEB):
                    yield f"linha {linha}: importa {alvo}"

        self.assertEqual(self._violacoes(TESTES, regra), [])


# ------------------------------------------------- isolamento em tempo de execução

class TestIsolamentoDinamico(unittest.TestCase):
    def assertSemWebNemAts(self, carregados, permitir_ats=()):
        for proibido in ("jinja2", "biocompiler.webserver", "biocompiler.core.pipeline"):
            self.assertNotIn(proibido, carregados)
        for at in ATS:
            if at not in permitir_ats:
                self.assertNotIn(f"biocompiler.core.{at}", carregados)

    def test_importar_pacote_nao_carrega_submodulos(self):
        r = _sondar("import biocompiler")
        self.assertEqual(r["carregados"], ["biocompiler"])

    def test_help_global_sem_web_nem_ats(self):
        r = _sondar("from biocompiler.__main__ import main\ncodigo = main(['--help'])",
                    bloquear=["jinja2"])
        self.assertEqual(r["codigo"], 0)
        self.assertIn("usage: python -m biocompiler", r["stdout"])
        for sub in ("at1", "at2", "at3", "at4", "all", "serve", "examples", "test"):
            self.assertIn(sub, r["stdout"])
        self.assertSemWebNemAts(r["carregados"])

    def test_help_de_cada_subcomando_sem_web_nem_ats(self):
        for sub in ("at1", "at2", "at3", "at4", "all", "serve", "examples", "test"):
            with self.subTest(subcomando=sub):
                r = _sondar(f"from biocompiler.__main__ import main\ncodigo = main([{sub!r}, '--help'])",
                            bloquear=["jinja2"])
                self.assertEqual(r["codigo"], 0, r["stderr"])
                self.assertIn(sub, r["stdout"])
                self.assertSemWebNemAts(r["carregados"])

    def test_serve_help_mostra_host_e_porta(self):
        r = _sondar("from biocompiler.__main__ import main\ncodigo = main(['serve', '--help'])",
                    bloquear=["jinja2"])
        self.assertEqual(r["codigo"], 0)
        self.assertIn("--host", r["stdout"])
        self.assertIn("--port", r["stdout"])

    def test_cli_python_S_help_real(self):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        proc = subprocess.run([sys.executable, "-S", "-m", "biocompiler", "--help"],
                              cwd=RAIZ, env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=60, stdin=subprocess.DEVNULL)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("serve", proc.stdout)

    def test_import_direto_de_cada_at_carrega_somente_ela(self):
        for at, (funcao, _) in FUNCOES_AT.items():
            with self.subTest(at=at):
                outros = [f"biocompiler.core.{o}" for o in ATS if o != at]
                r = _sondar(f"from biocompiler.core.{at} import {funcao}",
                            bloquear=outros + ["biocompiler.core.pipeline", "jinja2"])
                self.assertIn(f"biocompiler.core.{at}", r["carregados"])
                self.assertSemWebNemAts(r["carregados"], permitir_ats=(at,))
                self.assertNotIn("biocompiler.cli", r["carregados"])
                self.assertNotIn("biocompiler.servicos", r["carregados"])

    def test_assinaturas_publicas_das_ats(self):
        for at, (funcao, parametros) in FUNCOES_AT.items():
            with self.subTest(at=at):
                r = _sondar(
                    "import inspect\n"
                    f"from biocompiler.core.{at} import {funcao} as f\n"
                    "EXTRA = list(inspect.signature(f).parameters)"
                )
                self.assertEqual(r["extra"], parametros)

    def test_pipeline_expoe_executar_fluxo(self):
        r = _sondar(
            "import inspect\n"
            "from biocompiler.core.pipeline import executar_fluxo as f\n"
            "EXTRA = list(inspect.signature(f).parameters)[:2]"
        )
        self.assertEqual(r["extra"], ["seq1", "seq2"])

    def test_servicos_importa_sem_carregar_ats(self):
        r = _sondar("from biocompiler import servicos", bloquear=["jinja2"])
        self.assertSemWebNemAts(r["carregados"])
        self.assertNotIn("biocompiler.cli", r["carregados"])

    def test_servicos_despacho_preguicoso_com_outras_ats_bloqueadas(self):
        for at, (funcao, _) in FUNCOES_AT.items():
            with self.subTest(at=at):
                outros = [f"biocompiler.core.{o}" for o in ATS if o != at]
                r = _sondar(
                    "from biocompiler import servicos\n"
                    f"f = servicos.carregar_atividade({at!r})\n"
                    "EXTRA = [f.__module__, f.__name__]",
                    bloquear=outros + ["biocompiler.core.pipeline", "jinja2",
                                       "biocompiler.webserver"],
                )
                self.assertEqual(r["extra"], [f"biocompiler.core.{at}", funcao])
                self.assertSemWebNemAts(r["carregados"], permitir_ats=(at,))
                self.assertNotIn("biocompiler.cli", r["carregados"])

    def test_servicos_despacho_all_carrega_pipeline(self):
        r = _sondar(
            "from biocompiler import servicos\n"
            "f = servicos.carregar_atividade('all')\n"
            "EXTRA = [f.__module__, f.__name__]",
            bloquear=["jinja2", "biocompiler.webserver"],
        )
        self.assertEqual(r["extra"], ["biocompiler.core.pipeline", "executar_fluxo"])

    def test_servicos_atividade_desconhecida(self):
        for nome in ("at5", "AT1", "", "serve", "pipeline"):
            with self.subTest(nome=nome):
                r = _sondar(
                    "from biocompiler import servicos\n"
                    "try:\n"
                    f"    servicos.carregar_atividade({nome!r})\n"
                    "except ValueError as e:\n"
                    "    EXTRA = str(e)\n"
                )
                self.assertEqual(r["extra"], f"atividade desconhecida: {nome!r}")
                self.assertSemWebNemAts(r["carregados"])

    def test_serve_sem_jinja2_orienta_instalacao(self):
        r = _sondar("from biocompiler.__main__ import main\ncodigo = main(['serve'])",
                    bloquear=["jinja2"])
        self.assertEqual(r["codigo"], 1)
        self.assertIn("python -m pip install -r requirements-web.txt", r["stderr"])
        self.assertEqual(r["stdout"], "")
        self.assertNotIn("biocompiler.cli", r["carregados"])
        for at in ATS:
            self.assertNotIn(f"biocompiler.core.{at}", r["carregados"])

    def test_serve_com_jinja2_despacha_para_webserver(self):
        r = _sondar(
            "import types\n"
            "sys.modules['jinja2'] = types.ModuleType('jinja2')\n"
            "from biocompiler.__main__ import main\n"
            "codigo = main(['serve', '--port', '9000'])"
        )
        self.assertIn("biocompiler.webserver", r["carregados"])
        self.assertNotIn("biocompiler.cli", r["carregados"])
        self.assertEqual(r["codigo"], 1)
        self.assertIn("marco M7", r["stderr"])

    def test_outros_comandos_funcionam_sem_jinja2(self):
        # M5 (D015): sem entrada, at1–at4 falham com código 1 antes de carregar
        # qualquer AT; `all` segue provisório (3) até o M6; `examples` e
        # `test --help` funcionam. `test` sem argumentos não é chamado aqui
        # porque executaria esta própria suíte.
        casos = [(["at1"], 1, "informe --input ou --seq"),
                 (["at2"], 1, "informe --input ou --seq"),
                 (["at3"], 1, "informe --input ou --seq"),
                 (["at4"], 1, "informe --input ou --seq1 e --seq2"),
                 (["all"], 3, "comando 'all' ainda não implementado"),
                 (["examples"], 0, ""),
                 (["test", "--help"], 0, "")]
        for argv, codigo, mensagem in casos:
            with self.subTest(argv=argv):
                r = _sondar(f"from biocompiler.__main__ import main\ncodigo = main({argv!r})",
                            bloquear=["jinja2"])
                self.assertEqual(r["codigo"], codigo, r["stderr"])
                self.assertIn(mensagem, r["stderr"])
                self.assertSemWebNemAts(r["carregados"])


if __name__ == "__main__":
    unittest.main()
