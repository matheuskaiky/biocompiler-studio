/* Controlador da página AT4 (alinhamento local e global + inspetor de célula). */

import { ativarAba, definirStatus, registrarHistorico } from "../app.js";
import { executarAt4, exportarZip, obterExemplos } from "../api.js";
import { atualizarContadores, conectarZonaArquivo } from "../componentes/editor.js";
import { renderizarEtapas } from "../componentes/etapas.js";
import { renderizarListaArtefatos } from "../componentes/exportacao.js";
import { renderizarMatrizAT4 } from "../componentes/matriz.js";
import { el, limpar, qs } from "../dom.js";

let textoArquivo = null;

function renderizarResultadosAT4(conteiner, itens) {
  limpar(conteiner);
  if (!itens || !itens.length) {
    conteiner.appendChild(el("div", { class: "vazio", text: "Nenhum resultado ainda." }));
    return;
  }
  const grade = el("div", { class: itens.length > 1 ? "grade-dupla" : "lista-cartoes" });
  for (const item of itens) {
    const d = item.dados || {};
    const ok = item.status === "OK";
    const card = el("article", { class: "cartao" }, [
      el("div", { class: "barra-ferramentas" }, [
        el("h2", { text: `Método: ${(d.metodo || "").toUpperCase()}` }),
        el("span", { class: `selo ${ok ? "selo-ok" : "selo-erro"}`, text: item.resultado }),
      ]),
      el("p", { class: "mono" }, [
        "Seq1: ", d.seq1 || "", "   Seq2: ", d.seq2 || "",
      ]),
    ]);
    if (ok) {
      card.appendChild(el("p", { class: "mono" }, [
        "Score: ",
        el("strong", { "data-campo": "score", text: String(d.score) }),
        `   Matches: ${d.matches}   Mismatches: ${d.mismatches}   Gaps: ${d.gaps}   Tamanho: ${d.tamanho}`,
      ]));
      if (d.observacao) {
        card.appendChild(el("p", { text: d.observacao }));
      } else {
        const bloco = [
          `Seq1: ${d.alinhado1.split("").join(" ")}`,
          `      ${d.marcadores.split("").join(" ")}`,
          `Seq2: ${d.alinhado2.split("").join(" ")}`,
        ].join("\n");
        card.appendChild(el("pre", { class: "alinhamento-pre", text: bloco }));
      }
    } else if (d.erros && d.erros.length) {
      const ul = el("ul");
      for (const e of d.erros) ul.appendChild(el("li", { text: e }));
      card.appendChild(ul);
    }
    grade.appendChild(card);
  }
  conteiner.appendChild(grade);
}

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
  const regEtapas = qs('[data-regiao="etapas"]');
  const regVis = qs('[data-regiao="visualizacao"]');
  const regLista = qs('[data-regiao="lista-artefatos"]');

  renderizarListaArtefatos(regLista, "at4");

  const atualizar = () => {
    atualizarContadores(s1El.value, c1, "ACGT");
    atualizarContadores(s2El.value, c2, "ACGT");
  };
  s1El.addEventListener("input", () => { textoArquivo = null; atualizar(); });
  s2El.addEventListener("input", () => { textoArquivo = null; atualizar(); });

  conectarZonaArquivo(zonaArq, inputArq, (texto, nome) => {
    textoArquivo = texto;
    definirStatus(`Arquivo carregado: ${nome}`);
  });

  if (btnEx) {
    btnEx.addEventListener("click", async () => {
      try {
        const ex = await obterExemplos();
        textoArquivo = null;
        s1El.value = ex.at4.seq1;
        s2El.value = ex.at4.seq2;
        atualizar();
        definirStatus("Exemplo AT4 carregado.");
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
      definirStatus("Campos limpos.");
    });
  }

  async function executar(selecionarAba = true) {
    const base = textoArquivo !== null
      ? { texto: textoArquivo }
      : { seq1: s1El.value, seq2: s2El.value };
    const payload = {
      ...base,
      metodo: metEl.value,
      match: maEl.value,
      mismatch: miEl.value,
      gap: gapEl.value,
    };
    btnExec.disabled = true;
    btnExec.setAttribute("aria-busy", "true");
    definirStatus("Executando alinhamento…");
    try {
      const itens = await executarAt4(payload);
      renderizarResultadosAT4(regRes, itens);
      if (itens.length && regEtapas) {
        renderizarEtapas(regEtapas, itens[0].passos, `Eventos — ${itens[0].dados.metodo}`);
      }
      if (regVis) {
        limpar(regVis);
        for (const item of itens) {
          if (item.status === "OK") {
            renderizarMatrizAT4(regVis, item, {
              seq1: item.dados.seq1,
              seq2: item.dados.seq2,
              match: maEl.value,
              mismatch: miEl.value,
              gap: gapEl.value,
            });
          }
        }
      }
      const ok = itens.every((i) => i.status === "OK");
      definirStatus(ok ? "Alinhamento concluído." : "Alinhamento com diagnóstico.", ok ? "ok" : "erro");
      registrarHistorico({
        atividade: "at4",
        resumo: `${metEl.value}: ${itens.map((i) => `${i.dados.metodo}=${i.dados.score}`).join(", ")}`,
        href: `/at4?${new URLSearchParams({
          seq1: s1El.value, seq2: s2El.value, metodo: metEl.value,
          match: maEl.value, mismatch: miEl.value, gap: gapEl.value, executar: "1",
        }).toString()}`,
      });
      if (selecionarAba) ativarAba("tab-resultados");
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
          atividade: "at4",
          ...base,
          metodo: metEl.value,
          match: maEl.value,
          mismatch: miEl.value,
          gap: gapEl.value,
          delimitador: delimEl ? delimEl.value : "semicolon",
        });
        definirStatus("Pacote .zip exportado.", "ok");
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
