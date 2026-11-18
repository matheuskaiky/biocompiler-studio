"""OS-M8-01 — player de eventos e visualizações AT1–AT3 (Chrome real via CDP).

As expectativas vêm do núcleo/serviços (mesma fonte da API): o JS só projeta os
eventos e campos já calculados. Nada aqui depende de nomes de casos.
"""
import re
import sys
import threading
import time
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_interface import CHROME, TEM_JINJA  # noqa: E402

from biocompiler import servicos  # noqa: E402

DNA_OK = "CCATGGCTAAACCGTAAGG"            # START 2, STOP em fase 14, STOP fora de fase 7
DNA_INV = "ATGXCTAAZCCGTAA"               # bases inválidas
PRE_OK = "CCAUGGCUGUCCCCCCCCCCACCCCCCCCCCCCCCCCAGAAACCGUAAGG"  # SPEC §11.1 (pré-mRNA)
MRNA_OK = "m7GpppCCAUGGCUAAACCGUAAGG" + "A" * 100
DNA_LONGO = "ATG" + "GCT" * 1000 + "TAA"  # 3006 bases

ESPERA = ("(() => { const s = document.querySelector('[data-regiao=status]');"
          " const r = document.querySelector('[data-regiao=resultados]');"
          " return !!s && !/Executando/.test(s.textContent)"
          " && !!r && r.textContent.trim().length > 0; })()")

ESTADO = r"""(() => {
  const p = document.querySelector('[data-componente=player]');
  if (!p) return null;
  const t = (p.querySelector('[data-regiao=passo]') || {}).textContent || '';
  const m = t.match(/Passo\s+(\d+)\s+de\s+(\d+)/);
  const ev = p.querySelector('[data-regiao=evento-atual]') ||
             document.querySelector('[data-regiao=evento-atual]');
  const rep = p.querySelector('[data-acao=reproduzir]');
  return {k: m ? +m[1] : null, n: m ? +m[2] : null, texto: t,
          tipo: ev ? ev.getAttribute('data-tipo') : null,
          posicao: ev ? ev.getAttribute('data-posicao') : null,
          evTexto: ev ? ev.textContent : '',
          tocando: rep ? rep.getAttribute('aria-pressed') : null};
})()"""

VISIVEIS = ("(sel) => Array.from(document.querySelectorAll(sel)).filter(e => {"
            " const r = e.getBoundingClientRect(); const c = getComputedStyle(e);"
            " return (r.width > 0 || r.height > 0) && c.visibility !== 'hidden'"
            " && c.display !== 'none' && c.opacity !== '0'; })")


@unittest.skipUnless(TEM_JINJA and CHROME, "Jinja2 ou Chrome/Edge indisponível")
class BaseViz(unittest.TestCase):
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

    # ---- utilidades ------------------------------------------------------
    def js(self, expr):
        return self.nav.avaliar(expr)

    def pausa(self, ms):
        self.js(f"new Promise(r => setTimeout(() => r(true), {ms}))")

    def executar(self, caminho, params, reduzir_movimento=False):
        self.nav.cmd("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-reduced-motion", "value": "reduce" if reduzir_movimento else ""}])
        url = (f"http://127.0.0.1:{self.porta}{caminho}?"
               + urllib.parse.urlencode(dict(params, executar="1")))
        self.assertTrue(self.nav.abrir(url, 1366, 900, ESPERA), f"{caminho} não executou")
        self.aba("Visualização")

    def aba(self, rotulo):
        ok = self.js("(() => { const a = Array.from(document.querySelectorAll('[role=tab]'))"
                     f".find(x => x.textContent.trim() === {rotulo!r});"
                     " if (!a) return false; a.click(); return true; })()")
        self.assertTrue(ok, f"aba {rotulo} ausente")
        self.pausa(250)

    def estado(self):
        e = self.js(ESTADO)
        self.assertIsNotNone(e, "player [data-componente=player] ausente")
        return e

    def clicar(self, acao):
        ok = self.js("(() => { const b = document.querySelector("
                     f"'[data-componente=player] [data-acao={acao}]');"
                     " if (!b) return false; b.click(); return true; })()")
        self.assertTrue(ok, f"botão data-acao={acao} ausente no player")
        self.pausa(150)

    def ir_para(self, k):
        self.clicar("inicio")
        for _ in range(k - 1):
            self.clicar("proximo")
        self.assertEqual(self.estado()["k"], k)

    def contar(self, seletor):
        return self.js(f"({VISIVEIS})({seletor!r}).length")

    def atributos(self, seletor, attr):
        return self.js(f"({VISIVEIS})({seletor!r}).map(e => e.getAttribute({attr!r}))")


class TestPlayer(BaseViz):
    def test_controles_e_contagem_igual_aos_passos(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        n = len(r.eventos)
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        e = self.estado()
        self.assertEqual((e["k"], e["n"]), (1, n), e)
        self.assertEqual(e["tipo"], r.eventos[0].tipo)
        for acao in ("inicio", "anterior", "reproduzir", "proximo", "fim"):
            self.assertEqual(self.js(f"document.querySelectorAll('[data-componente=player] "
                                     f"[data-acao={acao}]').length"), 1, acao)
        vel = self.js("Array.from(document.querySelectorAll('[data-componente=player] "
                      "select[data-campo=velocidade] option')).map(o => o.value)")
        self.assertEqual(vel, ["0.5", "1", "2", "4"])
        self.assertEqual(self.js("document.querySelector('[data-componente=player] "
                                 "select[data-campo=velocidade]').value"), "1")
        # próximo / anterior / fim / início, com o evento exato da API
        self.clicar("proximo")
        e = self.estado()
        self.assertEqual(e["k"], 2)
        self.assertEqual(e["tipo"], r.eventos[1].tipo)
        self.assertEqual(e["posicao"], str(r.eventos[1].posicao))
        self.assertIn(r.eventos[1].detalhe, e["evTexto"])
        self.clicar("anterior")
        self.assertEqual(self.estado()["k"], 1)
        self.clicar("anterior")
        self.assertEqual(self.estado()["k"], 1, "anterior no passo 1 deve ficar no 1")
        self.clicar("fim")
        e = self.estado()
        self.assertEqual(e["k"], n)
        self.assertEqual(e["tipo"], "RESULTADO")
        self.assertIn("CORRETO", e["evTexto"])
        self.clicar("proximo")
        self.assertEqual(self.estado()["k"], n, "próximo no último passo deve ficar no último")
        self.clicar("inicio")
        self.assertEqual(self.estado()["k"], 1)

    def test_modo_rapido_mostra_resultado_final(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "rapido"})
        e = self.estado()
        self.assertEqual((e["k"], e["n"]), (len(r.eventos), len(r.eventos)))

    def test_reproduzir_avanca_e_pausar_para(self):
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        self.js("(() => { const s = document.querySelector('[data-componente=player] "
                "select[data-campo=velocidade]'); s.value = '4';"
                " s.dispatchEvent(new Event('change', {bubbles: true})); return true; })()")
        self.clicar("reproduzir")
        self.assertEqual(self.estado()["tocando"], "true")
        self.pausa(1600)
        k1 = self.estado()["k"]
        self.assertGreater(k1, 1, "reprodução a 4× não avançou em 1,6 s")
        self.clicar("reproduzir")  # pausa
        self.assertEqual(self.estado()["tocando"], "false")
        k2 = self.estado()["k"]
        self.pausa(1200)
        self.assertEqual(self.estado()["k"], k2, "continuou avançando após pausar")

    def test_animado_reproduz_sozinho_e_respeita_movimento_reduzido(self):
        self.executar("/at1", {"seq": DNA_OK, "modo": "animado"})
        self.pausa(2600)
        self.assertGreater(self.estado()["k"], 1, "modo animado não iniciou a reprodução")
        self.executar("/at1", {"seq": DNA_OK, "modo": "animado"}, reduzir_movimento=True)
        self.pausa(2000)
        e = self.estado()
        self.assertEqual(e["k"], 1, "com prefers-reduced-motion não deve reproduzir sozinho")
        self.assertNotEqual(e["tocando"], "true")

    def test_teclado_no_player(self):
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        self.js("document.querySelector('[data-componente=player] [data-acao=proximo]')"
                ".focus(), true")
        for _ in range(2):
            for tipo in ("rawKeyDown", "keyUp"):
                self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key="ArrowRight",
                             code="ArrowRight", windowsVirtualKeyCode=39)
            self.pausa(120)
        self.assertEqual(self.estado()["k"], 3, "→ dentro do player deve avançar um passo")
        for tipo in ("rawKeyDown", "keyUp"):
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key="ArrowLeft",
                         code="ArrowLeft", windowsVirtualKeyCode=37)
        self.pausa(120)
        self.assertEqual(self.estado()["k"], 2, "← dentro do player deve voltar um passo")

    def test_etapas_destaca_o_passo_atual_e_permite_saltar(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        self.ir_para(3)
        self.aba("Etapas")
        atual = self.js("Array.from(document.querySelectorAll('[aria-current=step]'))"
                        ".map(e => e.textContent)")
        self.assertEqual(len(atual), 1, "exatamente um evento marcado aria-current=step")
        self.assertIn(r.eventos[2].tipo, atual[0])
        # clicar em outro item da linha do tempo salta para ele
        ok = self.js("(() => { const it = document.querySelectorAll('[data-passo]');"
                     " if (it.length < 5) return false; it[4].click(); return true; })()")
        self.assertTrue(ok, "itens da linha do tempo precisam de [data-passo]")
        self.pausa(150)
        self.assertEqual(self.estado()["k"], 5)


class TestAT1Viz(BaseViz):
    def test_fita_orf_marcadores_e_transcricao(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        self.assertEqual(self.js("document.querySelectorAll('[data-viz=at1] svg').length > 0"),
                         True, "AT1 deve desenhar a fita em SVG")
        self.assertEqual(self.contar("[data-viz=at1] [data-base]"), len(DNA_OK))
        self.assertEqual(self.atributos("[data-viz=at1] [data-marca=start]", "data-indice"),
                         [str(r.posicao_start)])
        self.assertEqual(self.atributos("[data-viz=at1] [data-marca=stop]", "data-indice"),
                         [str(r.posicao_stop)])
        self.assertEqual(sorted(self.atributos("[data-viz=at1] [data-marca=stop-fora]",
                                               "data-indice")),
                         sorted(str(p) for p in r.stops_fora_de_fase))
        self.assertEqual(self.contar("[data-viz=at1] [data-codon]"), len(r.codons))
        self.assertEqual(self.contar("[data-viz=at1] [data-regiao-fita=utr5]"), 1)
        self.assertEqual(self.contar("[data-viz=at1] [data-regiao-fita=utr3]"), 1)
        self.assertEqual(self.contar("[data-viz=at1] [data-fita=pre-mrna] [data-base]"),
                         len(r.pre_mrna))
        trocas = sum(1 for a, b in zip(DNA_OK, r.pre_mrna) if a != b)
        self.assertEqual(self.contar("[data-viz=at1] [data-troca]"), trocas)

    def test_marcadores_seguem_o_passo(self):
        self.executar("/at1", {"seq": DNA_OK, "modo": "guiado"})
        self.assertEqual(self.contar("[data-viz=at1] [data-marca=start]"), 0,
                         "no passo 1 (BASES_VALIDADAS) o START ainda não foi encontrado")
        self.assertEqual(self.contar("[data-viz=at1] [data-troca]"), 0)
        self.clicar("proximo")  # START_ENCONTRADO
        self.assertEqual(self.contar("[data-viz=at1] [data-marca=start]"), 1)
        self.clicar("fim")
        self.assertGreater(self.contar("[data-viz=at1] [data-troca]"), 0)

    def test_bases_invalidas_marcadas(self):
        r = servicos.processar_lote("at1", [DNA_INV])[0]
        self.executar("/at1", {"seq": DNA_INV, "modo": "rapido"})
        self.assertEqual(sorted(self.atributos("[data-viz=at1] [data-marca=invalida]",
                                               "data-indice")),
                         sorted(str(i) for i, _ in r.bases_invalidas))
        self.assertEqual(self.contar("[data-viz=at1] [data-fita=pre-mrna]"), 0,
                         "sem pré-mRNA quando a entrada é inválida")

    def test_sequencia_longa_em_janelas(self):
        self.executar("/at1", {"seq": DNA_LONGO, "modo": "rapido"})
        n = self.js("document.querySelectorAll('[data-viz=at1] [data-fita=dna] [data-base]')"
                    ".length")
        self.assertGreater(n, 0)
        self.assertLessEqual(n, 600, "fitas longas devem ser renderizadas em janelas")
        janela = self.js("(document.querySelector('[data-viz=at1] [data-regiao=janela]')"
                         " || {}).textContent || ''")
        self.assertRegex(janela, r"de\s+3006")
        ok = self.js("(() => { const b = document.querySelector('[data-viz=at1] "
                     "[data-acao=janela-proxima]'); if (!b) return false; b.click();"
                     " return true; })()")
        self.assertTrue(ok)
        self.pausa(200)
        primeiro = self.js("+document.querySelector('[data-viz=at1] [data-fita=dna] "
                           "[data-base]').getAttribute('data-indice')")
        self.assertGreater(primeiro, 0, "a próxima janela deve começar depois da primeira")

    def test_inspetor_por_que(self):
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        ok = self.js("(() => { const m = document.querySelector('[data-viz=at1] "
                     "[data-marca=start]'); if (!m) return false;"
                     " m.dispatchEvent(new MouseEvent('click', {bubbles: true})); return true; })()")
        self.assertTrue(ok)
        self.pausa(150)
        txt = self.js("(document.querySelector('[data-regiao=inspetor]') || {}).textContent"
                      " || ''")
        self.assertIn("START_ENCONTRADO", txt)
        self.assertIn("ATG", txt)
        self.assertIn("2", txt)
        # base sem evento
        self.js("(() => { const b = document.querySelector('[data-viz=at1] [data-fita=dna] "
                "[data-base][data-indice=\"0\"]');"
                " b.dispatchEvent(new MouseEvent('click', {bubbles: true})); return true; })()")
        self.pausa(150)
        txt = self.js("document.querySelector('[data-regiao=inspetor]').textContent")
        self.assertIn("Nenhum evento registrado nesta posição.", txt)


class TestAT2Viz(BaseViz):
    def test_introns_sitios_regua_e_maturacao(self):
        r = servicos.processar_lote("at2", [PRE_OK])[0]
        self.executar("/at2", {"seq": PRE_OK, "modo": "rapido"})
        introns = self.js("Array.from(document.querySelectorAll('[data-viz=at2] [data-intron]'))"
                          ".map(e => [e.getAttribute('data-gu'), e.getAttribute('data-branch'),"
                          " e.getAttribute('data-ag')])")
        self.assertEqual(introns, [[str(i.posicao_gu), str(i.posicao_branch), str(i.posicao_ag)]
                                   for i in r.introns])
        self.assertEqual(sorted(self.atributos("[data-viz=at2] [data-marca=gu]", "data-indice")),
                         sorted(str(p) for p in r.sitios_gu))
        self.assertEqual(sorted(self.atributos("[data-viz=at2] [data-marca=ag]", "data-indice")),
                         sorted(str(p) for p in r.sitios_ag))
        reguas = self.atributos("[data-viz=at2] [data-regua]", "data-distancia")
        # D009: distância = nucleotídeos entre o A do branch point e o AG
        self.assertEqual(reguas, [str(i.posicao_ag - i.posicao_branch - 1) for i in r.introns])
        self.assertIn("10", self.js("document.querySelector('[data-viz=at2] [data-regua]')"
                                    ".textContent"))
        self.assertEqual(self.js("document.querySelector('[data-viz=at2]')"
                                 ".getAttribute('data-estado')"), "maduro")
        self.assertEqual(self.js("document.querySelector('[data-viz=at2] [data-cap]')"
                                 ".textContent.trim()"), r.cap)
        cauda = self.js("document.querySelector('[data-viz=at2] [data-cauda]')")
        self.assertIsNotNone(cauda)
        self.assertEqual(self.js("document.querySelector('[data-viz=at2] [data-cauda]')"
                                 ".getAttribute('data-tamanho')"), str(len(r.cauda_adicionada)))
        self.assertIn("100", self.js("document.querySelector('[data-viz=at2] [data-cauda]')"
                                     ".textContent"))
        self.js("document.querySelector('[data-viz=at2] [data-acao=expandir-cauda]').click(),"
                " true")
        self.pausa(150)
        self.assertEqual(self.js("(document.querySelector('[data-viz=at2] [data-cauda]')"
                                 ".textContent.match(/A/g) || []).length"), 100)

    def test_estado_do_splicing_segue_o_passo(self):
        r = servicos.processar_lote("at2", [PRE_OK])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at2", {"seq": PRE_OK, "modo": "guiado"})
        est = "document.querySelector('[data-viz=at2]').getAttribute('data-estado')"
        self.assertEqual(self.js(est), "antes")
        self.ir_para(tipos.index("EXONS_UNIDOS") + 1)
        self.assertEqual(self.js(est), "unido")
        self.clicar("fim")
        self.assertEqual(self.js(est), "maduro")


class TestAT3Viz(BaseViz):
    def test_ribossomo_cadeia_e_marcadores(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        self.assertEqual(self.contar("[data-viz=at3] svg [data-ribossomo]"), 1,
                         "ribossomo desenhado em SVG")
        self.assertEqual(self.contar("[data-viz=at3] [data-cadeia] [data-aminoacido]"), 0)
        tipos = [e.tipo for e in r.eventos]
        primeiro = tipos.index("CODON_TRADUZIDO") + 1
        self.ir_para(primeiro + 1)  # dois códons traduzidos
        aa = self.js("Array.from(document.querySelectorAll('[data-viz=at3] [data-cadeia] "
                     "[data-aminoacido]')).map(e => e.textContent.trim())")
        self.assertEqual(aa, list(r.aminoacidos[:2]))
        self.assertEqual(self.js("document.querySelector('[data-viz=at3] [data-ribossomo]')"
                                 ".getAttribute('data-codon-atual')"), "1")
        self.clicar("fim")
        aa = self.js("Array.from(document.querySelectorAll('[data-viz=at3] [data-cadeia] "
                     "[data-aminoacido]')).map(e => e.textContent.trim())")
        self.assertEqual(aa, list(r.aminoacidos))
        self.assertEqual(self.atributos("[data-viz=at3] [data-marca=stop]", "data-indice"),
                         [str(r.posicao_stop)])
        self.assertEqual(self.atributos("[data-viz=at3] [data-marca=start]", "data-indice"),
                         [str(r.posicao_start)])
        self.assertEqual(self.js("document.querySelector('[data-viz=at3] [data-cauda]')"
                                 ".getAttribute('data-tamanho')"), str(r.tamanho_cauda))
        self.assertEqual(self.js("document.querySelector('[data-viz=at3] [data-cap]')"
                                 ".textContent.trim()"), "m7Gppp")

    def test_codigos_percorridos_na_tabela(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "rapido"})
        marcados = self.js("Array.from(document.querySelectorAll('[data-codon].percorrido'))"
                           ".map(e => e.getAttribute('data-codon'))")
        traduzidos = {e.detalhe.split(":")[0] for e in r.eventos if e.tipo == "CODON_TRADUZIDO"}
        self.assertTrue(traduzidos <= set(marcados), (traduzidos, marcados))


class TestSemBiologiaNoJS(unittest.TestCase):
    def test_js_nao_transcreve_nem_traduz(self):
        raiz = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "js"
        proibidos = [r"replace\(\s*/T/g", r"replaceAll\(\s*['\"]T['\"]",
                     r"['\"]GCU['\"]\s*:", r"['\"]AUG['\"]\s*:\s*['\"]Met",
                     r"(?:<=?|>=?)\s*30\b.*branch|branch.*(?:<=?|>=?)\s*(?:10|30)\b"]
        for arq in raiz.rglob("*.js"):
            texto = arq.read_text(encoding="utf-8")
            for p in proibidos:
                self.assertIsNone(re.search(p, texto), f"{arq.name}: padrão proibido {p}")


if __name__ == "__main__":
    unittest.main()
