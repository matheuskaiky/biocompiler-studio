/* Linha do tempo vertical dos eventos estruturados retornados pela API. */

import { el, limpar } from "../dom.js";

export function renderizarEtapas(conteiner, itens, titulo = "Linha do tempo de eventos") {
  limpar(conteiner);
  if (!itens || !itens.length) {
    conteiner.appendChild(el("div", { class: "vazio", text: "Nenhum evento disponível." }));
    return;
  }
  const lista = el("ol", { class: "timeline" });
  itens.forEach((ev, idx) => {
    const pos = ev.posicao !== null && ev.posicao !== undefined ? ` · índice ${ev.posicao}` : "";
    const det = ev.detalhe ? ` — ${ev.detalhe}` : "";
    lista.appendChild(el("li", { class: "timeline-item" }, [
      el("strong", { class: "mono", text: `${idx + 1}. ${ev.tipo}` }),
      el("span", { class: "mono", text: `${pos}${det}` }),
    ]));
  });
  conteiner.appendChild(el("div", { class: "cartao" }, [
    el("h2", { text: titulo }),
    lista,
  ]));
}
