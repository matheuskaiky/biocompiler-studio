/* Controlador do Laboratório Completo (/). */

import { ativarAba, definirStatus, registrarHistorico } from "../app.js";
import { executarAll, exportarZip, obterExemplos } from "../api.js";
import { atualizarContadores, conectarZonaArquivo } from "../componentes/editor.js";
import { renderizarSequencia } from "../componentes/sequencia.js";
import { el, limpar, qs } from "../dom.js";

let textoArquivo = null;

function renderizarCadeia(cadeia) {
  const card = el("article", { class: "cartao" }, [
    el("div", { class: "barra-ferramentas" }, [
      el("h2", { text: cadeia.origem }),
      el("span", {
        class: `selo ${cadeia.ok ? "selo-ok" : "selo-erro"}`,
        text: cadeia.ok ? "Cadeia OK" : `Falha em ${cadeia.etapa_falha}`,
      }),
    ]),
    el("p", { class: "mono", text: `AT1: ${cadeia.at1.resultado}` }),
  ]);
  if (cadeia.at1.pre_mrna) {
    card.appendChild(el("div", { class: "bloco-produto", text: `pré-mRNA: ${cadeia.at1.pre_mrna}` }));
  }
  if (cadeia.at2) {
    card.appendChild(el("p", { class: "mono", text: `AT2: ${cadeia.at2.resultado}` }));
    if (cadeia.at2.rna_processado) {
      card.appendChild(el("div", { class: "bloco-produto", text: `RNA processado: ${cadeia.at2.rna_processado}` }));
    }
  } else {
    card.appendChild(el("p", { class: "mono", text: "AT2: NÃO EXECUTADO" }));
  }
  if (cadeia.at3) {
    card.appendChild(el("p", { class: "mono", text: `AT3: ${cadeia.at3.resultado}` }));
    if (cadeia.at3.proteina) {
      card.appendChild(el("div", { class: "bloco-produto", text: `Proteína: ${cadeia.at3.proteina}` }));
    }
  } else {
    card.appendChild(el("p", { class: "mono", text: "AT3: NÃO EXECUTADO" }));
  }
  return card;
}

function renderizarComparador(conteiner, dados) {
  limpar(conteiner);
  const s1 = dados.seq1;
  const s2 = dados.seq2;
  const card = el("div", { class: "cartao" }, [
    el("h2", { text: "Comparador molecular (Seq1 × Seq2)" }),
    el("p", { text: "Diferenças observadas entre as duas amostras (sem diagnóstico clínico)." }),
    el("div", { class: "grade-dupla" }, [
      el("div", {}, [el("strong", { text: "Seq1 — DNA" }), renderizarSequencia(s1.dna)]),
      el("div", {}, [el("strong", { text: "Seq2 — DNA" }), renderizarSequencia(s2.dna)]),
    ]),
  ]);
  if (s1.at3 && s1.at3.proteina && s2.at3 && s2.at3.proteina) {
    const p1 = s1.at3.aminoacidos || [];
    const p2 = s2.at3.aminoacidos || [];
    const diffs = [];
    const maxLen = p1.length > p2.length ? p1.length : p2.length;
    for (let i = 0; i < maxLen; i += 1) {
      if (p1[i] !== p2[i]) {
        diffs.push(`Posição ${i + 1}: ${p1[i] || "—"} × ${p2[i] || "—"} (diferença observada)`);
      }
    }
    card.appendChild(el("h3", { text: "Proteínas comparadas" }));
    card.appendChild(el("p", { class: "mono", text: `Seq1: ${s1.at3.proteina} | Seq2: ${s2.at3.proteina}` }));
    card.appendChild(el("p", {
      text: diffs.length ? diffs.join("; ") : "Nenhuma diferença observada nos aminoácidos.",
    }));
  }
  conteiner.appendChild(card);
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
  const regComp = qs('[data-regiao="comparador"]');
  const regRel = qs('[data-regiao="relatorio-final"]');

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
        s1El.value = ex.all.seq1;
        s2El.value = ex.all.seq2;
        atualizar();
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
      limpar(regRes);
      regRes.appendChild(el("div", { class: "grade-dupla" }, [
        renderizarCadeia(d.seq1),
        renderizarCadeia(d.seq2),
      ]));

      const trilhaAt4 = el("div", { class: "cartao" }, [
        el("h2", { text: "Alinhamento dos DNAs originais (AT4)" }),
      ]);
      for (const al of d.alinhamentos) {
        trilhaAt4.appendChild(el("p", { class: "mono" }, [
          `${al.metodo.toUpperCase()}: `,
          al.ok ? "Score " : al.resultado,
          al.ok ? el("strong", { "data-campo": "score", text: String(al.score) }) : "",
          al.ok ? ` (Matches: ${al.matches}, Mismatches: ${al.mismatches}, Gaps: ${al.gaps})` : "",
        ]));
      }
      regRes.appendChild(trilhaAt4);

      renderizarComparador(regComp, d);

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
