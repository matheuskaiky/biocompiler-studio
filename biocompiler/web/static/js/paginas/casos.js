/* Controlador da página Casos de Teste (/casos): carrega /api/exemplos e cria links profundos. */

import { definirStatus } from "../app.js";
import { obterExemplos } from "../api.js";
import { el, limpar, qs } from "../dom.js";

function criarGrupo(titulo, links) {
  return el("section", { class: "cartao" }, [
    el("h2", { text: titulo }),
    el("div", { class: "grade-casos" }, links),
  ]);
}

function cardLink(titulo, subtitulo, href) {
  return el("a", { class: "caso-link", href }, [
    el("span", { class: "caso-link-info" }, [
      el("strong", { text: titulo }),
      el("span", { class: "mono", text: subtitulo }),
    ]),
    el("span", { class: "caso-link-seta", "aria-hidden": "true", text: "›" }),
  ]);
}

document.addEventListener("DOMContentLoaded", async () => {
  const cont = qs('[data-regiao="casos"]');
  if (!cont) return;
  try {
    const ex = await obterExemplos();
    limpar(cont);

    const linksAt1 = ex.at1.map((seq, i) => cardLink(
      `AT1 · Caso ${i + 1}`,
      seq,
      `/at1?${new URLSearchParams({ seq, executar: "1" }).toString()}`,
    ));
    const linksAt2 = ex.at2.map((seq, i) => cardLink(
      `AT2 · Caso ${i + 1}`,
      seq.slice(0, 32) + (seq.length > 32 ? "…" : ""),
      `/at2?${new URLSearchParams({ seq, executar: "1" }).toString()}`,
    ));
    const linksAt3 = ex.at3.map((seq, i) => cardLink(
      `AT3 · Caso ${i + 1}`,
      `${seq.slice(0, 28)}… (${seq.length} nt)`,
      `/at3?${new URLSearchParams({ seq, executar: "1" }).toString()}`,
    ));
    const linksAt4 = [
      cardLink(
        "AT4 · Exemplo do enunciado (Global/Local)",
        `${ex.at4.seq1} × ${ex.at4.seq2}`,
        `/at4?${new URLSearchParams({ seq1: ex.at4.seq1, seq2: ex.at4.seq2, metodo: "both", executar: "1" }).toString()}`,
      ),
    ];
    const linksLab = [
      cardLink(
        "Laboratório Completo · SPEC §11.1",
        `${ex.all.seq1.slice(0, 20)}… × ${ex.all.seq2.slice(0, 20)}…`,
        `/?${new URLSearchParams({ seq1: ex.all.seq1, seq2: ex.all.seq2, executar: "1" }).toString()}`,
      ),
    ];

    cont.appendChild(criarGrupo("Laboratório Completo", linksLab));
    cont.appendChild(criarGrupo("AT1 — DNA → pré-mRNA (6 casos)", linksAt1));
    cont.appendChild(criarGrupo("AT2 — pré-mRNA → mRNA maduro (4 casos)", linksAt2));
    cont.appendChild(criarGrupo("AT3 — mRNA maduro → proteína (6 casos)", linksAt3));
    cont.appendChild(criarGrupo("AT4 — Alinhamento de DNA", linksAt4));
    definirStatus("Casos de teste carregados.", "ok");
  } catch (err) {
    definirStatus(err.message, "erro");
  }
});
