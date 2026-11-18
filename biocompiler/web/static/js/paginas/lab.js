/* Controlador do Laboratório Completo (/). */

import { ativarAba, definirStatus, registrarHistorico } from "../app.js";
import { executarAll, exportarZip, obterExemplos } from "../api.js";
import {
  atualizarContadores,
  conectarSegmentoMetodo,
  conectarZonaArquivo,
  extrairParSequencias,
} from "../componentes/editor.js";
import { renderizarComparadorLab } from "../componentes/comparador_lab.js";
import { renderizarMapaLab } from "../componentes/mapa_lab.js";
import { criarLabMutacoes } from "../componentes/mutacoes_lab.js";
import { el, limpar, qs } from "../dom.js";

let textoArquivo = null;

document.addEventListener("DOMContentLoaded", async () => {
  const s1El = qs('[data-campo="seq1"]');
  const s2El = qs('[data-campo="seq2"]');
  const metEl = qs('[data-campo="metodo"]');
  const maEl = qs('[data-campo="match"]');
  const miEl = qs('[data-campo="mismatch"]');
  const gapEl = qs('[data-campo="gap"]');
  const c1 = qs('[data-regiao="contadores-seq1"]');
  const c2 = qs('[data-regiao="contadores-seq2"]');
  const btnExec = qs('[data-acao="executar"]');
  const btnEx = qs('[data-acao="carregar-exemplo-par"]');
  const btnLimpar = qs('[data-acao="limpar-par"]');
  const btnExp = qs('[data-acao="exportar"]');
  const delimEl = qs('[data-campo="delimitador"]');
  const zonaArq = qs('[data-zona="arquivo-par"]');
  const inputArq = qs('[data-campo="arquivo"]');
  const regRes = qs('[data-regiao="resultados"]');
  const regComp = qs('[data-regiao="comparador"]');
  const regRel = qs('[data-regiao="relatorio-final"]');

  const atualizar = () => {
    atualizarContadores(s1El.value, c1, "ACGT");
    atualizarContadores(s2El.value, c2, "ACGT");
  };
  s1El.addEventListener("input", () => { textoArquivo = null; atualizar(); });
  s2El.addEventListener("input", () => { textoArquivo = null; atualizar(); });

  conectarSegmentoMetodo(qs('[data-segmento-metodo]'), metEl);

  conectarZonaArquivo(zonaArq, inputArq, (texto, nome) => {
    textoArquivo = texto;
    const [a, b] = extrairParSequencias(texto);
    if (a || b) {
      s1El.value = a;
      s2El.value = b;
      atualizar();
    }
    definirStatus(`Arquivo carregado: ${nome}`);
  });

  const compVizEl = el("div", { class: "comp-viz-slot" });
  const mutEl = el("div", { class: "comp-mut-slot" });
  limpar(regComp);
  regComp.appendChild(compVizEl);
  regComp.appendChild(mutEl);

  const mutacoesCtrl = criarLabMutacoes(mutEl, {
    obterSeq: (alvo) => (alvo === "seq1" ? s1El.value : s2El.value),
    definirSeq: (alvo, valor) => {
      if (alvo === "seq1") s1El.value = valor;
      else s2El.value = valor;
      textoArquivo = null;
      atualizar();
    },
    aoAlterar: () => executar(false),
  });

  if (btnEx) {
    btnEx.addEventListener("click", async () => {
      try {
        const ex = await obterExemplos();
        textoArquivo = null;
        s1El.value = ex.all.seq1;
        s2El.value = ex.all.seq2;
        atualizar();
        mutacoesCtrl.limparOrigens();
        definirStatus("Exemplo integrado (SPEC §11.1) carregado.");
      } catch (err) {
        definirStatus(err.message, "erro");
      }
    });
  }

  if (btnLimpar) {
    btnLimpar.addEventListener("click", () => {
      textoArquivo = null;
      s1El.value = "";
      s2El.value = "";
      atualizar();
      mutacoesCtrl.limparOrigens();
      definirStatus("Campos limpos.");
    });
  }

  async function executar(selecionarAba = true) {
    const base = textoArquivo !== null
      ? { texto: textoArquivo }
      : { seq1: s1El.value, seq2: s2El.value };
    btnExec.disabled = true;
    btnExec.setAttribute("aria-busy", "true");
    definirStatus("Executando laboratório completo…");
    try {
      const resp = await executarAll({
        ...base,
        metodo: metEl.value,
        match: maEl.value,
        mismatch: miEl.value,
        gap: gapEl.value,
      });
      const d = resp.dados;
      renderizarMapaLab(regRes, d);
      renderizarComparadorLab(compVizEl, d);

      limpar(regRel);
      const resumoJson = {
        ...d,
        alinhamentos: (d.alinhamentos || []).map((al) => {
          const copia = { ...al };
          if (Array.isArray(copia.matriz)) {
            copia.matriz = `[${copia.matriz.length}x${copia.matriz[0]?.length || 0}]`;
          }
          if (Array.isArray(copia.direcoes)) {
            copia.direcoes = `[${copia.direcoes.length}x${copia.direcoes[0]?.length || 0}]`;
          }
          return copia;
        }),
      };
      regRel.appendChild(el("div", { class: "cartao" }, [
        el("h2", { text: `Status geral: ${resp.status}` }),
        el("pre", { class: "alinhamento-pre", text: JSON.stringify(resumoJson, null, 2) }),
      ]));

      definirStatus(`Laboratório concluído (${resp.status}).`, resp.status === "OK" ? "ok" : "erro");
      registrarHistorico({
        atividade: "all",
        resumo: `Status ${resp.status}`,
        href: `/?${new URLSearchParams({
          seq1: s1El.value, seq2: s2El.value, metodo: metEl.value,
          match: maEl.value, mismatch: miEl.value, gap: gapEl.value, executar: "1",
        }).toString()}`,
      });
      if (selecionarAba) ativarAba("tab-mapa");
    } catch (err) {
      definirStatus(err.message, "erro");
    } finally {
      btnExec.disabled = false;
      btnExec.removeAttribute("aria-busy");
    }
  }

  btnExec.addEventListener("click", () => executar(true));

  if (btnExp) {
    btnExp.addEventListener("click", async () => {
      const base = textoArquivo !== null
        ? { texto: textoArquivo }
        : { seq1: s1El.value, seq2: s2El.value };
      try {
        await exportarZip({
          atividade: "all",
          ...base,
          metodo: metEl.value,
          match: maEl.value,
          mismatch: miEl.value,
          gap: gapEl.value,
          delimitador: delimEl ? delimEl.value : "semicolon",
        });
        definirStatus("Pacote .zip do laboratório exportado.", "ok");
      } catch (err) {
        definirStatus(err.message, "erro");
      }
    });
  }

  const params = new URLSearchParams(window.location.search);
  if (params.get("seq1") !== null) s1El.value = params.get("seq1");
  if (params.get("seq2") !== null) s2El.value = params.get("seq2");
  if (params.get("metodo")) metEl.value = params.get("metodo");
  if (params.get("match") !== null) maEl.value = params.get("match");
  if (params.get("mismatch") !== null) miEl.value = params.get("mismatch");
  if (params.get("gap") !== null) gapEl.value = params.get("gap");
  atualizar();
  if (params.get("executar") === "1") {
    await executar(!params.get("aba"));
  }
});
