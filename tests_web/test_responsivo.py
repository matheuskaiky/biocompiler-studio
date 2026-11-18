"""Responsividade real (OS-M7-02 R1): viewport emulada por CDP, sem texto cortado.

Em 390×844 e 1440×900, para cada página e cada aba (inclusive após execução com
sequências longas), nenhum texto ou elemento pode passar da borda visível, a não ser
dentro de um contêiner com rolagem própria (overflow auto/scroll). Conteúdo
escondido por `overflow: hidden` conta como cortado.
"""
import os
import sys
import threading
import unittest
import urllib.parse
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_interface import CHROME, TEM_JINJA  # noqa: E402

LONGA_DNA = "ATG" + "GCT" * 100 + "TAA"
LONGA_PRE = "AUGGCU" + "GCU" * 30 + "GUAAGU" + "C" * 30 + "A" + "C" * 20 + "AG" + "GCU" * 30 + "UAA"
LONGA_MRNA = "m7Gppp" + "AUG" + "GCU" * 100 + "UAA" + "A" * 100
AT4_1 = "ACGT" + "ACGTTG" * 12
AT4_2 = "ACGA" + "ACGTAG" * 12

CASOS = [
    ("/at1", {"seq": LONGA_DNA + "\nATGCCC\nACGTXX", "executar": "1"}),
    ("/at2", {"seq": LONGA_PRE, "executar": "1"}),
    ("/at3", {"seq": LONGA_MRNA, "executar": "1"}),
    ("/at4", {"seq1": AT4_1, "seq2": AT4_2, "metodo": "both", "executar": "1"}),
    ("/", {"seq1": "CC" + LONGA_DNA + "GG", "seq2": "CC" + LONGA_DNA[:-6] + "GCATAAGG",
           "executar": "1"}),
    ("/casos", {}),
    ("/historico", {}),
    ("/sobre", {}),
]

MEDIR = r"""(() => {
  const W = document.documentElement.clientWidth;
  const rola = (el) => {
    for (let a = el; a && a !== document.documentElement; a = a.parentElement) {
      const o = getComputedStyle(a).overflowX;
      if (o === 'auto' || o === 'scroll') return true;
    }
    return false;
  };
  const visivel = (el) => !el.closest('.pular-conteudo, [hidden], dialog:not([open])');
  const problemas = [];
  const andar = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (andar.nextNode()) {
    const t = andar.currentNode, p = t.parentElement;
    if (!p || !t.textContent.trim() || !visivel(p) || rola(p)) continue;
    let limite = W;
    for (let a = p; a && a !== document.documentElement; a = a.parentElement) {
      const o = getComputedStyle(a).overflowX;
      if (o === 'hidden' || o === 'clip') limite = Math.min(limite, a.getBoundingClientRect().right);
    }
    const r = document.createRange();
    r.selectNodeContents(t);
    for (const q of r.getClientRects()) {
      if (q.width > 0 && q.right > limite + 1) {
        problemas.push('texto <' + p.tagName.toLowerCase() + ' class="' + p.className + '">'
          + t.textContent.trim().slice(0, 40) + ' (direita ' + Math.round(q.right)
          + ' > ' + Math.round(limite) + ')');
        break;
      }
    }
  }
  for (const e of document.querySelectorAll('main *')) {
    if (!visivel(e) || rola(e.parentElement || e)) continue;
    const q = e.getBoundingClientRect();
    if (q.width > 0 && q.right > W + 1) {
      problemas.push('caixa <' + e.tagName.toLowerCase() + ' class="' + e.className
        + '"> direita ' + Math.round(q.right) + ' > ' + W);
    }
  }
  return {W: W, scroll: document.documentElement.scrollWidth, problemas: problemas.slice(0, 8),
          total: problemas.length};
})()"""

ABAS = "Array.from(document.querySelectorAll('[role=tab]')).map(a => a.id)"
ESPERA_EXEC = ("(() => { const s = document.querySelector('[data-regiao=status]');"
               " const r = document.querySelector('[data-regiao=resultados]');"
               " return !!s && !/Executando/.test(s.textContent)"
               " && !!r && r.textContent.trim().length > 0; })()")


@unittest.skipUnless(TEM_JINJA and CHROME, "Jinja2 ou Chrome/Edge indisponível")
class TestResponsivo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from biocompiler import webserver
        from cdp import Navegador
        cls.srv = webserver.criar_servidor("127.0.0.1", 0)
        cls.porta = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.nav = Navegador(CHROME)
        cls.capturas = os.environ.get("BIOCOMPILER_CAPTURAS")

    @classmethod
    def tearDownClass(cls):
        cls.nav.fechar()
        cls.srv.shutdown()
        cls.srv.server_close()

    def _verificar(self, largura, altura):
        for caminho, params in CASOS:
            url = f"http://127.0.0.1:{self.porta}{caminho}"
            if params:
                url += "?" + urllib.parse.urlencode(params)
            espera = ESPERA_EXEC if params.get("executar") else "true"
            with self.subTest(pagina=caminho, largura=largura):
                self.assertTrue(self.nav.abrir(url, largura, altura, espera),
                                f"{caminho} não concluiu a execução a tempo")
                abas = self.nav.avaliar(ABAS) or [None]
                for aba in abas:
                    if aba:
                        self.nav.avaliar(f"document.getElementById({aba!r}).click(), true")
                        self.nav.avaliar("new Promise(r => setTimeout(() => r(true), 400))")
                    m = self.nav.avaliar(MEDIR)
                    if self.capturas:
                        nome = (caminho.strip("/") or "lab") + f"_{aba or 'pagina'}_{largura}.png"
                        self.nav.captura(os.path.join(self.capturas, nome))
                    self.assertLessEqual(m["scroll"], m["W"],
                                         f"{caminho} aba {aba}: rolagem horizontal da página")
                    self.assertEqual(m["total"], 0,
                                     f"{caminho} aba {aba} em {largura}px: conteúdo cortado: "
                                     + "; ".join(m["problemas"]))

    def test_390_sem_conteudo_cortado(self):
        self._verificar(390, 844)

    def test_1440_sem_conteudo_cortado(self):
        self._verificar(1440, 900)


if __name__ == "__main__":
    unittest.main()
