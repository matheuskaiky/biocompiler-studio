"""Acessibilidade por teclado (OS-M7-02 R2), com Chrome real via CDP.

- Ajuda: abre como modal, o foco fica preso dentro do diálogo com Tab e Shift+Tab,
  Esc fecha e o foco volta ao botão de ajuda.
- Abas: ←/→/Home/End movem o foco e selecionam a aba, mostrando o painel dela.
- "Pular para o conteúdo" é o primeiro Tab da página e fica visível ao receber foco.
"""
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_interface import CHROME, TEM_JINJA  # noqa: E402

TECLAS = {
    "Tab": ("Tab", 9), "Escape": ("Escape", 27), "ArrowRight": ("ArrowRight", 39),
    "ArrowLeft": ("ArrowLeft", 37), "Home": ("Home", 36), "End": ("End", 35),
}
FOCO = ("(() => { const a = document.activeElement;"
        " return {tag: a ? a.tagName : null, id: a ? a.id : null,"
        " acao: a ? a.getAttribute('data-acao') : null,"
        " noDialogo: !!(a && a.closest('#dialogo-ajuda')),"
        " aberto: !!document.querySelector('#dialogo-ajuda[open]')}; })()")


@unittest.skipUnless(TEM_JINJA and CHROME, "Jinja2 ou Chrome/Edge indisponível")
class TestAcessibilidade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from biocompiler import webserver
        from cdp import Navegador
        cls.srv = webserver.criar_servidor("127.0.0.1", 0)
        cls.porta = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.nav = Navegador(CHROME)

    @classmethod
    def tearDownClass(cls):
        cls.nav.fechar()
        cls.srv.shutdown()
        cls.srv.server_close()

    def tecla(self, nome, shift=False):
        chave, codigo = TECLAS[nome]
        mod = 8 if shift else 0
        for tipo in ("rawKeyDown", "keyUp"):
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key=chave, code=chave,
                         windowsVirtualKeyCode=codigo, nativeVirtualKeyCode=codigo,
                         modifiers=mod)
        self.nav.avaliar("new Promise(r => setTimeout(() => r(true), 120))")

    def abrir(self, caminho):
        self.assertTrue(self.nav.abrir(f"http://127.0.0.1:{self.porta}{caminho}", 1280, 860))

    def test_ajuda_prende_foco_e_esc_devolve(self):
        for caminho in ("/", "/at1", "/at4", "/sobre"):
            with self.subTest(pagina=caminho):
                self.abrir(caminho)
                self.nav.avaliar("document.querySelector('[data-acao=ajuda]').focus(),"
                                 " document.querySelector('[data-acao=ajuda]').click(), true")
                self.nav.avaliar("new Promise(r => setTimeout(() => r(true), 200))")
                f = self.nav.avaliar(FOCO)
                self.assertTrue(f["aberto"], "a ajuda não abriu")
                self.assertTrue(f["noDialogo"], f"foco fora do diálogo ao abrir: {f}")
                for i in range(6):
                    self.tecla("Tab")
                    f = self.nav.avaliar(FOCO)
                    self.assertTrue(f["noDialogo"], f"Tab #{i + 1} tirou o foco do diálogo: {f}")
                for i in range(6):
                    self.tecla("Tab", shift=True)
                    f = self.nav.avaliar(FOCO)
                    self.assertTrue(f["noDialogo"],
                                    f"Shift+Tab #{i + 1} tirou o foco do diálogo: {f}")
                self.tecla("Escape")
                f = self.nav.avaliar(FOCO)
                self.assertFalse(f["aberto"], "Esc não fechou a ajuda")
                self.assertEqual(f["acao"], "ajuda", f"foco não voltou ao botão de ajuda: {f}")

    def test_abas_por_teclado(self):
        for caminho in ("/at1", "/at4", "/"):
            with self.subTest(pagina=caminho):
                self.abrir(caminho)
                ids = self.nav.avaliar("Array.from(document.querySelectorAll('[role=tab]'))"
                                       ".map(a => a.id)")
                self.assertGreaterEqual(len(ids), 4)
                self.nav.avaliar(f"document.getElementById({ids[0]!r}).focus(), true")
                estado = ("(() => { const a = document.activeElement;"
                          " const p = document.getElementById(a.getAttribute('aria-controls'));"
                          " return {id: a.id, sel: a.getAttribute('aria-selected'),"
                          " visivel: !!p && p.offsetParent !== null && !p.hidden,"
                          " selecionadas: document.querySelectorAll("
                          "'[role=tab][aria-selected=true]').length}; })()")
                for tecla, esperado in (("ArrowRight", ids[1]), ("End", ids[-1]),
                                        ("ArrowRight", ids[0]), ("ArrowLeft", ids[-1]),
                                        ("Home", ids[0])):
                    self.tecla(tecla)
                    e = self.nav.avaliar(estado)
                    self.assertEqual(e["id"], esperado, f"{tecla}: foco em {e}")
                    self.assertEqual(e["sel"], "true", f"{tecla}: aba não selecionada {e}")
                    self.assertTrue(e["visivel"], f"{tecla}: painel não visível {e}")
                    self.assertEqual(e["selecionadas"], 1)

    def test_pular_para_conteudo(self):
        self.abrir("/at2")
        self.nav.avaliar("document.activeElement && document.activeElement.blur(), true")
        self.tecla("Tab")
        r = self.nav.avaliar("(() => { const a = document.activeElement;"
                             " const q = a.getBoundingClientRect();"
                             " return {href: a.getAttribute('href'), x: q.left, w: q.width,"
                             " dentro: q.left >= 0 && q.right <= innerWidth && q.top >= 0}; })()")
        self.assertEqual(r["href"], "#conteudo")
        self.assertTrue(r["dentro"] and r["w"] > 0, f"link de salto não visível ao focar: {r}")


if __name__ == "__main__":
    unittest.main()
