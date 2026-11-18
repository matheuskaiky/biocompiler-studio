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
INTRON = "GU" + "C" * 10 + "A" + "C" * 15 + "AG"
PRE_2INT = "CCAUGG" + INTRON + "CUAAA" + "GUCCCCCAUCCCCCCCCCCCCAG" + "CCGUAAGG"  # dois íntrons
PRE_D10 = "CCAUGG" + "GU" + "CCC" + "A" + "C" * 10 + "AG" + "CUAAACCGUAAGG"   # D009 = 10
PRE_D30 = "CCAUGG" + "GU" + "CCC" + "A" + "C" * 30 + "AG" + "CUAAACCGUAAGG"   # D009 = 30
PRE_LONGO = "CCAUGG" + "GCU" * 1000 + INTRON + "UAAGG"
MRNA_LONGO = "m7Gppp" + "CC" + "AUG" + "GCU" * 1000 + "UAA" + "GG" + "A" * 100

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
        for _ in range(20):  # aguarda o player ser montado (asserção inalterada)
            ok = self.js("(() => { const b = document.querySelector("
                         f"'[data-componente=player] [data-acao={acao}]');"
                         " if (!b) return false; b.click(); return true; })()")
            if ok:
                break
            self.pausa(150)
        self.assertTrue(ok, f"botão data-acao={acao} ausente no player")
        self.pausa(150)

    def ir_para(self, k):
        self.clicar("inicio")
        for _ in range(k - 1):
            self.clicar("proximo")
        self.assertEqual(self.estado()["k"], k)

    def tecla(self, nome):
        codigos = {"ArrowRight": 39, "ArrowLeft": 37, "Home": 36, "End": 35, " ": 32,
                   "Enter": 13}
        code = {" ": "Space", "Enter": "Enter"}.get(nome, nome)
        for tipo in ("rawKeyDown", "char", "keyUp"):
            if tipo == "char" and nome not in (" ", "Enter"):
                continue
            extra = {"text": " " if nome == " " else "\r"} if tipo == "char" else {}
            self.nav.cmd("Input.dispatchKeyEvent", type=tipo, key=nome, code=code,
                         windowsVirtualKeyCode=codigos[nome], **extra)
        self.pausa(150)

    def texto(self, seletor):
        return self.js(f"(document.querySelector({seletor!r}) || {{}}).textContent || ''")

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
        n = self.estado()["n"]
        self.tecla("End")
        self.assertEqual(self.estado()["k"], n, "End deve ir ao último passo")
        self.tecla("Home")
        self.assertEqual(self.estado()["k"], 1, "Home deve ir ao primeiro passo")
        self.js("document.querySelector('[data-componente=player] [data-acao=proximo]')"
                ".focus(), true")
        self.tecla(" ")
        self.assertEqual(self.estado()["tocando"], "true", "Espaço deve iniciar a reprodução")
        self.tecla(" ")
        self.assertEqual(self.estado()["tocando"], "false", "Espaço deve pausar")

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
        self.assertEqual(self.contar("[data-viz=at1] [data-fita=dna] [data-base]"), len(DNA_OK))
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
        visiveis = self.js("Array.from(document.querySelectorAll('[data-viz=at2] [data-regua] "
                           "[data-campo=distancia]')).map(e => e.textContent.trim())")
        self.assertEqual(visiveis, reguas, "o número mostrado deve ser a distância D009")
        self.assertIn("10–30", self.texto("[data-viz=at2] [data-regua]"))
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

    def test_codigos_percorridos_seguem_o_passo(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        marcados = ("Array.from(document.querySelectorAll('[data-codon].percorrido'))"
                    ".map(e => e.getAttribute('data-codon')).sort()")
        atual = ("Array.from(document.querySelectorAll('[data-codon].atual'))"
                 ".map(e => e.getAttribute('data-codon'))")
        for k in range(1, len(r.eventos) + 1):
            self.ir_para(k) if k == 1 else self.clicar("proximo")
            feitos = [e.detalhe.split(":")[0] for e in r.eventos[:k]
                      if e.tipo == "CODON_TRADUZIDO"]
            self.assertEqual(self.js(marcados), sorted(set(feitos)), f"passo {k}")
            esperado_atual = ([feitos[-1]] if feitos and r.eventos[k - 1].tipo == "CODON_TRADUZIDO"
                              else None)
            if esperado_atual:
                self.assertEqual(self.js(atual), esperado_atual, f"passo {k}: códon atual")


class TestSemBiologiaNoJS(unittest.TestCase):
    def test_js_nao_transcreve_nem_traduz(self):
        raiz = Path(__file__).resolve().parents[1] / "biocompiler" / "web" / "static" / "js"
        proibidos = [r"replace\(\s*/T/g", r"replaceAll\(\s*['\"]T['\"]",
                     r"['\"]GCU['\"]\s*:", r"['\"]AUG['\"]\s*:\s*['\"]Met",
                     r"(?:<=?|>=?)\s*30\b.*branch|branch.*(?:<=?|>=?)\s*(?:10|30)\b",
                     r"(?:indexOf|includes|lastIndexOf|startsWith|endsWith|search|match)\(\s*"
                     r"['\"/](?:ATG|AUG|TAA|TAG|TGA|UAA|UAG|UGA|GU|AG)['\"/]",
                     r"/(?:ATG|AUG|TAA|TAG|TGA|UAA|UAG|UGA)/",
                     r"['\"](?:UUU|UUC|GCU|GGG)['\"]\s*[:,]\s*['\"](?:Phe|Ala|Gly)",
                     r"m7Gppp", r"\.repeat\(\s*100\b"]
        for arq in raiz.rglob("*.js"):
            texto = arq.read_text(encoding="utf-8")
            for p in proibidos:
                self.assertIsNone(re.search(p, texto), f"{arq.name}: padrão proibido {p}")


class TestFidelidadeTraco(BaseViz):
    """A2: cada passo k mostra exatamente passos[k-1], em ordem, sem omissões."""

    def _percorrer(self, caminho, at, seq):
        r = servicos.processar_lote(at, [seq])[0]
        self.executar(caminho, {"seq": seq, "modo": "guiado"})
        for k, ev in enumerate(r.eventos, start=1):
            if k > 1:
                self.clicar("proximo")
            e = self.estado()
            with self.subTest(at=at, k=k):
                self.assertEqual((e["k"], e["n"]), (k, len(r.eventos)))
                self.assertEqual(e["tipo"], ev.tipo)
                self.assertEqual(e["posicao"], "" if ev.posicao is None else str(ev.posicao))
                if ev.detalhe:
                    self.assertIn(ev.detalhe, e["evTexto"])
        self.aba("Etapas")
        itens = self.js("Array.from(document.querySelectorAll('[data-passo]'))"
                        ".map(e => [e.getAttribute('data-passo'), e.textContent])")
        self.assertEqual([i[0] for i in itens], [str(k) for k in range(1, len(r.eventos) + 1)])
        for (_, txt), ev in zip(itens, r.eventos):
            self.assertIn(ev.tipo, txt)
        self.assertEqual(self.js("document.querySelector('[aria-current=step]')"
                                 ".getAttribute('data-passo')"), str(len(r.eventos)))

    def test_at1(self):
        self._percorrer("/at1", "at1", DNA_OK)

    def test_at2_dois_introns(self):
        self._percorrer("/at2", "at2", PRE_2INT)

    def test_at3(self):
        self._percorrer("/at3", "at3", MRNA_OK)


class TestCoordenadas(BaseViz):
    """A1/A7: cada fita tem [data-base][data-indice] no referencial dos índices da API."""

    def bases(self, fita, ini, n):
        return self.js("Array.from(document.querySelectorAll("
                       f"'[data-fita={fita}] [data-base]')).filter(e => "
                       f"+e.getAttribute('data-indice') >= {ini} && "
                       f"+e.getAttribute('data-indice') < {ini + n})"
                       ".map(e => e.textContent.trim()).join('')")

    def test_at1_start_aponta_atg(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        self.assertEqual(self.bases("dna", r.posicao_start, 3), "ATG")
        self.assertEqual(self.bases("dna", r.posicao_stop, 3), r.codon_stop)

    def test_at2_indices_no_pre_mrna(self):
        r = servicos.processar_lote("at2", [PRE_2INT])[0]
        self.executar("/at2", {"seq": PRE_2INT, "modo": "rapido"})
        self.assertEqual(self.contar("[data-viz=at2] [data-fita=pre-mrna] [data-base]"),
                         len(PRE_2INT))
        for i in r.introns:
            self.assertEqual(self.bases("pre-mrna", i.posicao_gu, 2), "GU")
            self.assertEqual(self.bases("pre-mrna", i.posicao_branch, 1), "A")
            self.assertEqual(self.bases("pre-mrna", i.posicao_ag, 2), "AG")

    def test_at3_indices_na_regiao_transcrita(self):
        r = servicos.processar_lote("at3", [MRNA_OK])[0]
        self.executar("/at3", {"seq": MRNA_OK, "modo": "rapido"})
        self.assertEqual(self.contar("[data-viz=at3] [data-fita=mrna] [data-base]"),
                         len(r.regiao_transcrita))
        self.assertEqual(self.bases("mrna", r.posicao_start, 3), "AUG")
        self.assertEqual(self.bases("mrna", r.posicao_stop, 3), r.codon_stop)
        # CAP e cauda são blocos à parte, sem data-indice de base
        self.assertEqual(self.js("document.querySelectorAll('[data-viz=at3] [data-cap] "
                                 "[data-base], [data-viz=at3] [data-cauda] [data-base]').length"), 0)


class TestLote(BaseViz):
    """A3: com lote, o seletor de registro troca player, visualização e etapas juntos."""

    def test_trocar_registro(self):
        seqs = [DNA_OK, "ATGCCCTGA", DNA_INV]
        rs = servicos.processar_lote("at1", seqs)
        self.executar("/at1", {"seq": "\n".join(seqs), "modo": "rapido"})
        opcoes = self.js("Array.from(document.querySelectorAll('[data-componente=player] "
                         "select[data-campo=registro] option')).map(o => o.value)")
        self.assertEqual(len(opcoes), 3)
        for idx in (1, 2, 0, 2):
            self.js("(() => { const s = document.querySelector('[data-componente=player] "
                    f"select[data-campo=registro]'); s.value = {opcoes[idx]!r};"
                    " s.dispatchEvent(new Event('change', {bubbles: true})); return true; })()")
            self.pausa(250)
            e = self.estado()
            with self.subTest(registro=idx):
                n = len(rs[idx].eventos)
                self.assertEqual((e["k"], e["n"]), (n, n), "modo rápido: abre no fim")
                self.assertEqual(e["tipo"], rs[idx].eventos[-1].tipo)
                self.assertEqual(self.contar("[data-viz=at1] [data-fita=dna] [data-base]"),
                                 len(seqs[idx]))
                self.assertEqual(self.contar("[data-viz=at1] [data-marca=invalida]"),
                                 len(rs[idx].bases_invalidas))


class TestAT2Estados(BaseViz):
    """A4: estado global e por íntron do SpliceLab, com dois íntrons."""

    def test_estados(self):
        r = servicos.processar_lote("at2", [PRE_2INT])[0]
        self.executar("/at2", {"seq": PRE_2INT, "modo": "guiado"})
        glob = "document.querySelector('[data-viz=at2]').getAttribute('data-estado')"
        por = ("Array.from(document.querySelectorAll('[data-viz=at2] [data-intron]'))"
               ".map(e => e.getAttribute('data-estado'))")
        gus = [i.posicao_gu for i in r.introns]
        for k, ev in enumerate(r.eventos, start=1):
            if k > 1:
                self.clicar("proximo")
            feitos = r.eventos[:k]
            tipos = [e.tipo for e in feitos]
            sel = {e.posicao for e in feitos if e.tipo == "INTRON_SELECIONADO"}
            if "POLIA_ADICIONADA" in tipos:
                g = "maduro"
            elif "CAP_ADICIONADA" in tipos:
                g = "com-cap"
            elif "EXONS_UNIDOS" in tipos:
                g = "unido"
            elif sel:
                g = "selecionado"
            else:
                g = "antes"
            esperado = [("removido" if "EXONS_UNIDOS" in tipos else
                         "selecionado" if gu in sel else "pendente") for gu in gus]
            with self.subTest(k=k, evento=ev.tipo):
                self.assertEqual(self.js(glob), g)
                self.assertEqual(self.js(por), esperado)

    def test_fita_processada_mostra_os_exons_unidos(self):
        """R1: SPEC §7.3 — o íntron sai e as extremidades exônicas se aproximam."""
        r = servicos.processar_lote("at2", [PRE_2INT])[0]
        tipos = [e.tipo for e in r.eventos]
        self.executar("/at2", {"seq": PRE_2INT, "modo": "guiado"})
        sel = "[data-viz=at2] [data-fita=rna-processado] [data-base]"
        self.assertEqual(self.contar(sel), 0, "antes da união não há fita processada")
        self.ir_para(tipos.index("EXONS_UNIDOS"))
        self.assertEqual(self.contar(sel), 0, "ainda não unido no passo anterior")
        self.clicar("proximo")  # EXONS_UNIDOS
        letras = self.js(f"Array.from(document.querySelectorAll({sel!r}))"
                         ".map(e => e.textContent.trim()).join('')")
        self.assertEqual(letras, r.rna_processado)
        removidos = self.js("Array.from(document.querySelectorAll('[data-viz=at2] "
                            "[data-intron]')).map(e => getComputedStyle(e).opacity)")
        self.assertTrue(all(float(o) < 0.75 for o in removidos),
                        f"íntrons removidos devem ficar esmaecidos/riscados na fita original: {removidos}")
        self.clicar("fim")
        self.assertEqual(self.contar(sel), len(r.rna_processado))

    def test_regua_nos_limites_d009(self):
        for seq, d in ((PRE_D10, "10"), (PRE_D30, "30")):
            r = servicos.processar_lote("at2", [seq])[0]
            self.assertEqual([str(i.posicao_ag - i.posicao_branch - 1) for i in r.introns], [d])
            self.executar("/at2", {"seq": seq, "modo": "rapido"})
            self.assertEqual(self.js("document.querySelector('[data-viz=at2] [data-regua] "
                                     "[data-campo=distancia]').textContent.trim()"), d)


class TestInspetorTeclado(BaseViz):
    """A7: inspetor por teclado, base anunciada e todos os eventos da posição."""

    def test_enter_na_base_lista_todos_os_eventos(self):
        r = servicos.processar_lote("at1", [DNA_OK])[0]
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        i = r.posicao_start
        alvo = (f"document.querySelector('[data-viz=at1] [data-fita=dna] "
                f"[data-base][data-indice=\"{i}\"]')")
        self.assertEqual(self.js(f"{alvo}.getAttribute('tabindex') !== null || "
                                 f"{alvo}.closest('[tabindex]') !== null"), True,
                         "a fita precisa ser alcançável por teclado")
        self.js(f"(() => {{ const b = {alvo}; (b.getAttribute('tabindex') !== null ? b :"
                " b.closest('[tabindex]')).focus(); return true; })()")
        self.js(f"(() => {{ const b = {alvo}; if (document.activeElement !== b &&"
                " b.getAttribute('tabindex') !== null) b.focus(); return true; })()")
        self.tecla("Enter")
        txt = self.texto("[data-regiao=inspetor]")
        self.assertIn(f"Posição {i}", txt)
        self.assertIn(f"Base {DNA_OK[i]}", txt)
        for ev in r.eventos:
            if ev.posicao == i:
                self.assertIn(ev.tipo, txt)
        self.assertGreaterEqual(sum(1 for ev in r.eventos if ev.posicao == i), 2)

    def test_setas_movem_na_fita(self):
        self.executar("/at1", {"seq": DNA_OK, "modo": "rapido"})
        self.js("(() => { const b = document.querySelector('[data-viz=at1] [data-fita=dna] "
                "[data-base][data-indice=\"0\"]'); (b.getAttribute('tabindex') !== null ? b :"
                " b.closest('[tabindex]')).focus(); return true; })()")
        self.tecla("Enter")
        self.tecla("ArrowRight")
        self.tecla("ArrowRight")
        self.tecla("Enter")
        self.assertIn("Posição 2", self.texto("[data-regiao=inspetor]"))


class TestVelocidadeEMovimento(BaseViz):
    """A8: 1× entre 400 e 900 ms por passo, parada automática, rótulo e movimento reduzido."""

    def test_intervalo_a_1x_e_parada_no_fim(self):
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"})
        rotulo = ("document.querySelector('[data-componente=player] [data-acao=reproduzir]')"
                  ".getAttribute('aria-label') || document.querySelector("
                  "'[data-componente=player] [data-acao=reproduzir]').textContent.trim()")
        antes = self.js(rotulo)
        self.clicar("reproduzir")
        self.assertNotEqual(self.js(rotulo), antes, "o rótulo deve mudar para Pausar")
        self.pausa(3000)
        k = self.estado()["k"]
        self.assertTrue(4 <= k <= 9, f"a 1×, em 3 s deveria avançar 3–7 passos; está em {k}")
        self.js("(() => { const s = document.querySelector('[data-componente=player] "
                "select[data-campo=velocidade]'); s.value = '4';"
                " s.dispatchEvent(new Event('change', {bubbles: true})); return true; })()")
        self.pausa(4500)
        e = self.estado()
        self.assertEqual(e["k"], e["n"], "a reprodução deve chegar ao fim")
        self.assertEqual(e["tocando"], "false", "ao chegar ao fim a reprodução para")

    def test_movimento_reduzido_sem_animacoes(self):
        self.executar("/at3", {"seq": MRNA_OK, "modo": "guiado"}, reduzir_movimento=True)
        self.clicar("proximo")
        self.clicar("fim")
        durs = self.js("""(() => {
          const s = v => Math.max(...v.split(',').map(x => parseFloat(x) * (x.trim().endsWith('ms') ? 1 : 1000)));
          const els = document.querySelectorAll('[data-viz] *, [data-viz], [data-componente=player] *');
          let m = 0;
          for (const e of els) {
            const c = getComputedStyle(e);
            m = Math.max(m, s(c.transitionDuration), s(c.animationDuration));
          }
          const anims = document.getAnimations().filter(a => a.playState === 'running')
            .map(a => a.effect && a.effect.getTiming().duration || 0);
          return {css: m, js: anims.length ? Math.max(...anims) : 0};
        })()""")
        self.assertLessEqual(durs["css"], 10, f"transições/animações CSS ativas: {durs}")
        self.assertLessEqual(durs["js"], 10, f"animações JS ativas: {durs}")


class TestLongas(BaseViz):
    """A10: janelas contíguas, acompanhamento do passo e limite de DOM em todas as ATs."""

    LIMITE_NOS = 8000

    def janela(self, viz):
        t = self.texto(f"[data-viz={viz}] [data-regiao=janela]")
        m = re.search(r"(\d+)\s*[–-]\s*(\d+)\s+de\s+(\d+)", t)
        self.assertIsNotNone(m, f"texto da janela inesperado: {t!r}")
        return tuple(int(x) for x in m.groups())

    def _verificar(self, caminho, seq, viz, fita, total):
        self.executar(caminho, {"seq": seq, "modo": "rapido"})
        self.assertLess(self.js("document.querySelectorAll('main *').length"), self.LIMITE_NOS)
        self.assertLessEqual(self.contar(f"[data-viz={viz}] [data-fita={fita}] [data-base]"), 600)
        self.clicar("inicio")
        a, b, n = self.janela(viz)
        self.assertEqual((a, n), (1, total))
        vistos = b
        for _ in range(total // 600 + 2):
            ok = self.js(f"(() => {{ const x = document.querySelector('[data-viz={viz}] "
                         "[data-acao=janela-proxima]'); if (!x || x.disabled) return false;"
                         " x.click(); return true; })()")
            if not ok:
                break
            self.pausa(120)
            a2, b2, _ = self.janela(viz)
            self.assertEqual(a2, vistos + 1, "janelas devem ser contíguas, sem lacunas")
            vistos = b2
        self.assertEqual(vistos, total, "a última janela deve terminar na última base")
        self.clicar("fim")
        self.aba("Etapas")
        self.assertLessEqual(self.js("document.querySelectorAll('[data-passo]').length"), 500,
                             "linha do tempo longa deve ser paginada/virtualizada")
        self.assertEqual(self.js("document.querySelectorAll('[aria-current=step]').length"), 1)
        self.assertLess(self.js("document.querySelectorAll('main *').length"), self.LIMITE_NOS)

    def test_at1_longa(self):
        self._verificar("/at1", DNA_LONGO, "at1", "dna", len(DNA_LONGO))

    def test_at2_longa(self):
        self._verificar("/at2", PRE_LONGO, "at2", "pre-mrna", len(PRE_LONGO))

    def test_at3_longa(self):
        r = servicos.processar_lote("at3", [MRNA_LONGO])[0]
        self._verificar("/at3", MRNA_LONGO, "at3", "mrna", len(r.regiao_transcrita))

    def test_janela_acompanha_o_passo(self):
        r = servicos.processar_lote("at1", [DNA_LONGO])[0]
        self.executar("/at1", {"seq": DNA_LONGO, "modo": "rapido"})
        self.clicar("fim")
        pos = [e.posicao for e in r.eventos if e.posicao is not None][-1]
        a, b, _ = self.janela("at1")
        self.assertTrue(a <= pos + 1 <= b, f"janela {a}–{b} não contém a posição {pos}")


class TestParidadeAleatoria(BaseViz):
    """A9: entradas geradas no teste; toda projeção confere com a API."""

    def test_at1_aleatorias(self):
        import random
        rnd = random.Random(20261118)
        for _ in range(4):
            miolo = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(20, 70)))
            seq = "".join(rnd.choice("ACGT") for _ in range(rnd.randint(0, 6))) + "ATG" + miolo
            r = servicos.processar_lote("at1", [seq])[0]
            self.executar("/at1", {"seq": seq, "modo": "rapido"})
            with self.subTest(seq=seq):
                self.assertEqual(self.atributos("[data-viz=at1] [data-marca=start]",
                                                "data-indice"),
                                 [] if r.posicao_start is None else [str(r.posicao_start)])
                self.assertEqual(self.atributos("[data-viz=at1] [data-marca=stop]",
                                                "data-indice"),
                                 [] if r.posicao_stop is None else [str(r.posicao_stop)])
                self.assertEqual(sorted(self.atributos("[data-viz=at1] [data-marca=stop-fora]",
                                                       "data-indice")),
                                 sorted(str(p) for p in r.stops_fora_de_fase))
                self.assertEqual(self.contar("[data-viz=at1] [data-codon]"), len(r.codons))
                self.assertEqual(self.estado()["n"], len(r.eventos))

    def test_at3_aleatorias(self):
        import random
        rnd = random.Random(1118)
        sentido = [a + b + c for a in "ACGU" for b in "ACGU" for c in "ACGU"
                   if a + b + c not in ("UAA", "UAG", "UGA")]
        for _ in range(3):
            corpo = "".join(rnd.choice(sentido) for _ in range(rnd.randint(3, 12)))
            seq = "m7Gppp" + "CC" + "AUG" + corpo + "UGA" + "GG" + "A" * 100
            r = servicos.processar_lote("at3", [seq])[0]
            self.executar("/at3", {"seq": seq, "modo": "rapido"})
            with self.subTest(seq=seq):
                consulta = ("Array.from(document.querySelectorAll('[data-viz=at3] [data-cadeia] "
                            "[data-aminoacido]')).map(e => e.textContent.trim())")
                for _ in range(20):  # aguarda a renderização (sem afrouxar a asserção)
                    aa = self.js(consulta)
                    if aa:
                        break
                    self.pausa(150)
                self.assertEqual(aa, list(r.aminoacidos))
                marcados = self.js("Array.from(document.querySelectorAll("
                                   "'[data-codon].percorrido')).map(e => "
                                   "e.getAttribute('data-codon')).sort()")
                feitos = sorted({e.detalhe.split(":")[0] for e in r.eventos
                                 if e.tipo == "CODON_TRADUZIDO"})
                self.assertEqual(marcados, feitos)


if __name__ == "__main__":
    unittest.main()
