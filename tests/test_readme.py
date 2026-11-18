"""M9 — o README e o roteiro de demonstração são verificáveis.

Todo comando `python3 main.py ...` ou `python3 -m biocompiler ...` dentro de blocos
```bash do README.md é executado numa cópia limpa do projeto (sem `serve`, que abre
servidor). O código de saída esperado é 0, salvo comentário final `# saída N`.
"""
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"
DEMO = RAIZ / "docs" / "DEMONSTRACAO.md"

SECOES = ["Instalação", "Uso rápido", "Comandos", "Formatos", "Exportações", "Interface web",
          "Testes", "Estrutura", "Demonstração", "Critérios dos enunciados", "Limites"]


def comandos_do_readme(texto):
    cmds = []
    for bloco in re.findall(r"```bash\n(.*?)```", texto, re.S):
        for linha in bloco.splitlines():
            linha = linha.strip()
            if not re.match(r"python3? (?:-S )?(?:main\.py|-m biocompiler)\b", linha):
                continue
            if " serve" in linha or "<" in linha.split("#")[0]:
                continue
            esperado = 0
            m = re.search(r"#\s*saída\s+(\d)\s*$", linha)
            if m:
                esperado = int(m.group(1))
            cmd = linha.split("#")[0].strip()
            cmds.append((cmd, esperado))
    return cmds


class TestReadme(unittest.TestCase):
    def test_readme_existe_com_secoes(self):
        self.assertTrue(README.exists(), "README.md ausente na raiz")
        texto = README.read_text(encoding="utf-8")
        titulos = re.findall(r"^#{1,3}\s+(.+)$", texto, re.M)
        for s in SECOES:
            self.assertTrue(any(s.lower() in t.lower() for t in titulos), f"seção ausente: {s}")
        self.assertIn("python3 -m unittest discover -s tests", texto)
        self.assertIn("requirements-web.txt", texto)

    def test_comandos_do_readme_executam(self):
        texto = README.read_text(encoding="utf-8")
        cmds = comandos_do_readme(texto)
        self.assertGreaterEqual(len(cmds), 12, "o README deve trazer exemplos reais de uso")
        for at in ("at1", "at2", "at3", "at4", "all"):
            self.assertTrue(any(re.search(rf"\b{at}\b", c) for c, _ in cmds), f"sem exemplo {at}")
        tmp = Path(tempfile.mkdtemp(prefix="biocompiler_readme_"))
        try:
            for item in RAIZ.iterdir():
                if item.name in (".git", "tests_web", "saidas", "__pycache__") or \
                        item.name.startswith("."):
                    continue
                if item.is_dir():
                    shutil.copytree(item, tmp / item.name,
                                    ignore=shutil.ignore_patterns("__pycache__"))
                else:
                    shutil.copy(item, tmp / item.name)
            for cmd, esperado in cmds:
                argv = shlex.split(cmd)
                argv[0] = sys.executable
                with self.subTest(cmd=cmd):
                    p = subprocess.run(argv, cwd=tmp, capture_output=True, text=True,
                                       stdin=subprocess.DEVNULL, timeout=180)
                    self.assertEqual(p.returncode, esperado,
                                     f"{cmd}\nstdout: {p.stdout[-400:]}\nstderr: {p.stderr[-400:]}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_arquivos_citados_existem(self):
        texto = README.read_text(encoding="utf-8")
        for caminho in set(re.findall(r"\b(exemplos/[\w.\-/]+\.(?:txt|fasta))\b", texto)):
            self.assertTrue((RAIZ / caminho).exists(), f"arquivo citado no README: {caminho}")


class TestDemonstracao(unittest.TestCase):
    def test_roteiro(self):
        self.assertTrue(DEMO.exists(), "docs/DEMONSTRACAO.md ausente")
        t = DEMO.read_text(encoding="utf-8")
        self.assertIn("CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAAACCGTAAGG", t)
        self.assertIn("CCATGGCTGTCCCCCCCCCCACCCCCCCCCCCCCCCAGAATCCGTAAGG", t)
        self.assertIn("Met-Ala-Lys-Pro", t)
        self.assertIn("Met-Ala-Asn-Pro", t)
        self.assertRegex(t, r"score\s*\**\s*9")
        passos = re.findall(r"^\s*\d+\.\s", t, re.M)
        self.assertGreaterEqual(len(passos), 7, "roteiro com ao menos 7 passos (SPEC §11.3)")
        self.assertIn("http://127.0.0.1:8765/", t)


if __name__ == "__main__":
    unittest.main()
