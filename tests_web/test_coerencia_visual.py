"""OS-M10-11 — Coerência visual final: inspetor da AT4 no mesmo material de vidro dos
inspetores de AT1–AT3 (D022, R-4.1) e durações de movimento sempre tokenizadas (plano §7).
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_visualizacao import BaseViz  # noqa: E402

CSS = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "css"


class TestInspetorAT4(BaseViz):
    def test_inspetor_da_at4_em_vidro_sem_cobrir_a_matriz(self):
        self.executar("/at4", {"seq1": "ACGTAC", "seq2": "ACGTTC", "metodo": "global", "modo": "rapido"})
        self.js("document.querySelector('[data-viz=at4] [data-celula][data-i=\"3\"][data-j=\"4\"]')"
                ".dispatchEvent(new MouseEvent('click', {bubbles: true})), true")
        self.pausa(400)
        i = self.js("""(() => {
          const e = document.querySelector('[data-regiao=inspetor-celula]');
          if (!e) return null;
          const m = document.querySelector('[data-viz=at4] .matriz-scroll').getBoundingClientRect();
          const r = e.getBoundingClientRect();
          const cobre = !(r.right <= m.left || r.left >= m.right || r.bottom <= m.top || r.top >= m.bottom);
          return [e.getAttribute('data-superficie'), getComputedStyle(e).backdropFilter, cobre];
        })()""")
        self.assertIsNotNone(i, "[data-regiao=inspetor-celula] ausente")
        self.assertEqual(i[0], "vidro")
        self.assertIn("blur", i[1])
        self.assertFalse(i[2], "o inspetor não se sobrepõe à área matricial (dados ficam visíveis)")


class TestDuracoesTokenizadas(unittest.TestCase):
    def test_transicoes_e_animacoes_usam_tokens(self):
        literais = []
        for arq in sorted(CSS.glob("*.css")):
            if arq.name in ("tokens.css",):
                continue
            for n, linha in enumerate(arq.read_text(encoding="utf-8").splitlines(), 1):
                m = re.search(r"^\s*(transition|animation)(-duration)?\s*:(.*)$", linha)
                if not m:
                    continue
                valor = m.group(3)
                if re.search(r"(?<![\w-])\d*\.?\d+m?s\b", re.sub(r"var\([^)]*\)", "", valor)) \
                        and not re.search(r"(?<![\w-])0m?s\b|0\.01ms|1ms", valor):
                    literais.append(f"{arq.name}:{n}: {linha.strip()}")
        self.assertEqual(literais, [], "durações literais; use os tokens --dur-* de tokens.css")


if __name__ == "__main__":
    unittest.main()
