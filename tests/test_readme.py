"""M9 — README, exemplos, roteiro de demonstração e rastreabilidade verificáveis.

- Todo comando `python3 main.py ...`/`python3 -m biocompiler ...` em blocos ```bash do
  README e do roteiro roda numa cópia isolada do projeto (arquivos versionados ou não
  ignorados pelo Git; sem `saidas/` e sem `tests_web/`). Código esperado 0, salvo
  comentário final `# saída N`. `serve` não é executado.
- Comandos obrigatórios têm a saída conferida contra o núcleo.
- Os arquivos de `exemplos/` contêm exatamente os casos de `biocompiler/exemplos.py`.
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
sys.path.insert(0, str(RAIZ))

from biocompiler import exemplos, servicos  # noqa: E402

README = RAIZ / "README.md"
DEMO = RAIZ / "docs" / "DEMONSTRACAO.md"
RASTRO = RAIZ / "docs" / "RASTREABILIDADE.md"

SECOES = ["Instalação", "Uso rápido", "Comandos", "Formatos", "Exportações", "Interface web",
          "Testes", "Estrutura", "Demonstração", "Critérios dos enunciados", "Limites"]
OPCOES = ["--input", "--seq", "--seq1", "--seq2", "--format", "--out-dir", "--output",
          "--no-save", "--force", "--quiet", "--step", "--interactive", "--explain",
          "--method", "--match", "--mismatch", "--gap", "--delimiter"]
EXPORTACOES = ["at1_resultados.txt", "at2_resultados.txt", "at3_resultados.txt",
               "matriz_pontuacao_local.csv", "matriz_traceback_global.csv",
               "alinhamento_local.csv", "comparacao.txt"]
ROTAS = ["/", "/at1", "/at2", "/at3", "/at4", "/casos", "/historico", "/sobre"]
OBRIGATORIOS = {
    "python3 main.py at1 --input exemplos/at1_casos.txt --no-save": 2,
    "python3 main.py at4 --input exemplos/at4_par.fasta --no-save": 0,
    "python3 main.py all --input exemplos/integrado.txt --no-save": 0,
}


def comandos(texto):
    cmds = []
    for bloco in re.findall(r"```bash\n(.*?)```", texto, re.S):
        for linha in bloco.splitlines():
            linha = linha.strip()
            if not re.match(r"python3? (?:-S )?(?:main\.py|-m biocompiler)\b", linha):
                continue
            if " serve" in linha or "<" in linha.split("#")[0]:
                continue
            m = re.search(r"#\s*saída\s+(\d)\s*$", linha)
            cmds.append((linha.split("#")[0].strip(), int(m.group(1)) if m else 0))
    return cmds


def copia_isolada():
    tmp = Path(tempfile.mkdtemp(prefix="biocompiler_doc_"))
    arquivos = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=RAIZ,
                              capture_output=True, text=True, check=True).stdout.splitlines()
    for rel in arquivos:
        if rel.startswith(("saidas/", "tests_web/")) or "__pycache__" in rel:
            continue
        origem = RAIZ / rel
        if origem.is_file():
            destino = tmp / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(origem, destino)
    return tmp


class Base(unittest.TestCase):
    def executar(self, texto, minimo):
        cmds = comandos(texto)
        self.assertGreaterEqual(len(cmds), minimo)
        tmp = copia_isolada()
        saidas = {}
        try:
            for cmd, esperado in cmds:
                argv = shlex.split(cmd)
                argv[0] = sys.executable
                p = subprocess.run(argv, cwd=tmp, capture_output=True, text=True,
                                   stdin=subprocess.DEVNULL, timeout=180)
                with self.subTest(cmd=cmd):
                    self.assertEqual(p.returncode, esperado,
                                     f"{cmd}\nstdout: {p.stdout[-400:]}\nstderr: {p.stderr[-400:]}")
                saidas[cmd] = p.stdout
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return saidas


class TestReadme(Base):
    def setUp(self):
        self.assertTrue(README.exists(), "README.md ausente na raiz")
        self.texto = README.read_text(encoding="utf-8")

    def test_secoes_opcoes_exportacoes_rotas_e_decisoes(self):
        titulos = re.findall(r"^#{1,3}\s+(.+)$", self.texto, re.M)
        for s in SECOES:
            self.assertTrue(any(s.lower() in t.lower() for t in titulos), f"seção ausente: {s}")
        for termo in OPCOES + EXPORTACOES:
            self.assertIn(termo, self.texto, f"README não documenta {termo}")
        for rota in ROTAS:
            self.assertRegex(self.texto, rf"`{re.escape(rota)}`", f"rota não documentada: {rota}")
        for d in ("D009", "D015", "D017", "D019", "D020"):
            self.assertIn(d, self.texto)
        for t in ("python3 -m unittest discover -s tests", "python3 -m unittest discover -s tests_web",
                  "python3 -S", "requirements-web.txt", "docs/DEMONSTRACAO.md",
                  "docs/RASTREABILIDADE.md"):
            self.assertIn(t, self.texto)

    def test_comandos_executam_e_saidas_conferem(self):
        for cmd, cod in OBRIGATORIOS.items():
            linha = rf"^\s*{re.escape(cmd)}\s*(#\s*saída\s+{cod})?\s*$" if cod else \
                rf"^\s*{re.escape(cmd)}\s*$"
            self.assertRegex(self.texto, re.compile(linha, re.M), f"comando obrigatório: {cmd}")
        saidas = self.executar(self.texto, 12)
        for at in ("at1", "at2", "at3", "at4", "all"):
            self.assertTrue(any(re.search(rf"\b{at}\b", c) for c in saidas), f"sem exemplo {at}")
        rotulos = {r.resultado for r in servicos.processar_lote("at1", list(exemplos.AT1_EXEMPLOS))}
        for rot in rotulos:
            self.assertIn(rot, saidas[list(OBRIGATORIOS)[0]])
        self.assertIn("Score: 9", saidas[list(OBRIGATORIOS)[1]])
        for prot in ("Met-Ala-Lys-Pro", "Met-Ala-Asn-Pro"):
            self.assertIn(prot, saidas[list(OBRIGATORIOS)[2]])

    def test_exemplos_tem_exatamente_os_casos(self):
        def linhas(nome):
            return [l.strip() for l in (RAIZ / "exemplos" / nome).read_text(encoding="utf-8")
                    .splitlines() if l.strip()]
        self.assertEqual(linhas("at1_casos.txt"), list(exemplos.AT1_EXEMPLOS))
        self.assertEqual(linhas("at2_casos.txt"), list(exemplos.AT2_EXEMPLOS))
        self.assertEqual(linhas("at3_casos.txt"), list(exemplos.AT3_EXEMPLOS))
        self.assertEqual(linhas("integrado.txt"), list(exemplos.ALL_EXEMPLO))
        fasta = linhas("at4_par.fasta")
        self.assertEqual([l for l in fasta if not l.startswith(">")], list(exemplos.AT4_EXEMPLO))
        self.assertEqual(sum(1 for l in fasta if l.startswith(">")), 2)
        for caminho in set(re.findall(r"\b(exemplos/[\w.\-/]+\.(?:txt|fasta))\b", self.texto)):
            self.assertTrue((RAIZ / caminho).exists(), f"arquivo citado: {caminho}")


class TestDemonstracao(Base):
    def test_roteiro_estruturado_e_executavel(self):
        self.assertTrue(DEMO.exists(), "docs/DEMONSTRACAO.md ausente")
        t = DEMO.read_text(encoding="utf-8")
        passos = re.split(r"^#{2,3}\s*Passo\s+\d+", t, flags=re.M)[1:]
        self.assertGreaterEqual(len(passos), 7, "≥ 7 seções '## Passo N' (SPEC §11.3)")
        for k, p in enumerate(passos, start=1):
            for campo in ("**Ação:**", "**Resultado esperado:**", "**Fala:**"):
                self.assertIn(campo, p, f"passo {k} sem {campo}")
        for termo in ("5–8 min", "Plano B", "30 nt", "16 nt", "Met-Ala-Lys-Pro",
                      "Met-Ala-Asn-Pro", exemplos.ALL_EXEMPLO[0], exemplos.ALL_EXEMPLO[1]):
            self.assertIn(termo, t)
        self.assertRegex(t, r"[Ss]core\W{0,3}9\b")
        for url in re.findall(r"http://127\.0\.0\.1:8765(/[^\s?)`#]*)", t):
            self.assertIn(url, ROTAS, f"rota inexistente no roteiro: {url}")
        plano_b = t[t.index("Plano B"):]
        self.assertTrue(comandos(plano_b), "o Plano B traz comandos de terminal")
        self.executar(t, 3)


class TestRastreabilidade(unittest.TestCase):
    def test_nove_condicoes_com_evidencias_existentes(self):
        self.assertTrue(RASTRO.exists(), "docs/RASTREABILIDADE.md ausente")
        t = RASTRO.read_text(encoding="utf-8")
        nomes_testes = set()
        for arq in list((RAIZ / "tests").glob("test_*.py")) + list((RAIZ / "tests_web").glob("test_*.py")):
            nomes_testes |= set(re.findall(r"def (test_\w+)", arq.read_text(encoding="utf-8")))
        for n in range(1, 10):
            linha = re.search(rf"^\|\s*{n}\s*\|(.+)$", t, re.M)
            self.assertIsNotNone(linha, f"condição {n} da SPEC §12 sem linha na tabela")
            refs = re.findall(r"(tests(?:_web)?/test_\w+\.py)", linha.group(1))
            self.assertTrue(refs or "inspeção" in linha.group(1).lower(),
                            f"condição {n} sem evidência")
            for r in refs:
                self.assertTrue((RAIZ / r).exists(), f"condição {n}: {r} não existe")
            for nome in re.findall(r"\b(test_\w+)\b(?!\.py)", linha.group(1)):
                self.assertIn(nome, nomes_testes, f"condição {n}: teste {nome} não existe")


if __name__ == "__main__":
    unittest.main()
