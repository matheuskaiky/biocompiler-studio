"""OS-M10-08 — README e roteiro de demonstração atualizados para a interface do M10.

Complementa tests/test_readme.py (comandos executados e seções). Aqui se verifica que a
documentação descreve a interface que de fato existe agora: nomes da navegação, recursos
novos e um roteiro que usa as interações reais. Os ganchos citados são conferidos no
código servido, para que a documentação não prometa o que não existe.
"""
import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"
DEMO = RAIZ / "docs" / "DEMONSTRACAO.md"
WEB = RAIZ / "biocompiler" / "web"


def secao(texto, titulo):
    m = re.search(rf"^##\s+{re.escape(titulo)}.*?$(.*?)(?=^##\s|\Z)", texto, re.M | re.S)
    return m.group(1) if m else ""


class TestReadmeInterface(unittest.TestCase):
    def test_secao_interface_web_descreve_o_m10(self):
        web = secao(README.read_text(encoding="utf-8"), "Interface web")
        self.assertTrue(web, "seção 'Interface web' ausente")
        for termo in ("BioCompiler 1.0", "BioCompiler 2.0", "Ribossomo", "Alinhamento",
                      "Comparador molecular", "Liquid Glass", "linha do tempo",
                      "Enviar para", "lado a lado", "Apresentação", "movimento reduzido",
                      "transparência reduzida", "D021"):
            self.assertIn(termo.lower(), web.lower(), f"README › Interface web não cita: {termo}")
        self.assertIn("docs/FRONTEND_DESIGN_PLAN.md", web)


class TestRoteiroInterface(unittest.TestCase):
    def test_roteiro_usa_as_interacoes_reais(self):
        t = DEMO.read_text(encoding="utf-8")
        for termo in ("Enviar para BioCompiler 2.0", "Enviar para o Ribossomo", "Detalhar",
                      "lado a lado", "linha do tempo", "ribossomo", "Pular para o resultado",
                      "Apresentação"):
            self.assertIn(termo.lower(), t.lower(), f"roteiro não usa: {termo}")

    def test_rotulos_citados_existem_na_interface(self):
        codigo = " ".join(p.read_text(encoding="utf-8")
                          for p in list((WEB / "static" / "js").rglob("*.js"))
                          + list((WEB / "templates").rglob("*.html")))
        for rotulo in ("Enviar para BioCompiler 2.0", "Enviar para o Ribossomo", "Detalhar",
                       "Pular para o resultado", "Apresentação"):
            self.assertIn(rotulo, codigo, f"rótulo citado na documentação não existe: {rotulo}")


if __name__ == "__main__":
    unittest.main()
