/* Renderização de resultados de lote (AT1–AT3) com filtro e cartões. */

import { el, limpar } from "../dom.js";
import { criarBlocoProduto } from "./sequencia.js";

function produtoDe(atividade, dados) {
  if (atividade === "at1") return dados.pre_mrna;
  if (atividade === "at2") return dados.mrna_maduro;
  return dados.proteina;
}

export function renderizarResultadosLote(conteiner, atividade, itens) {
  limpar(conteiner);
  if (!itens || !itens.length) {
    conteiner.appendChild(el("div", { class: "vazio", text: "Nenhum resultado ainda." }));
    return;
  }

  const corretas = itens.filter((i) => i.status === "OK").length;
  const erros = itens.length - corretas;
  let filtro = "todos";

  const resumo = el("p", {
    text: `${itens.length} entrada(s) · ${corretas} correta(s) · ${erros} com diagnóstico`,
  });

  const lista = el("div", { class: "lista-cartoes" });
  const atualizarLista = () => {
    limpar(lista);
    for (const item of itens) {
      if (filtro === "ok" && item.status !== "OK") continue;
      if (filtro === "erro" && item.status === "OK") continue;

      const ok = item.status === "OK";
      const selo = el("span", {
        class: `selo ${ok ? "selo-ok" : "selo-erro"}`,
        text: ok ? "OK · Válida" : "Diagnóstico",
      });
      const cartao = el("article", { class: "cartao" }, [
        el("div", { class: "barra-ferramentas" }, [
          el("strong", { text: `Entrada #${item.entrada.linha}` }),
          selo,
          el("span", { class: "mono", text: item.resultado }),
        ]),
        el("div", { class: "bloco-produto", text: item.entrada.sequencia || "(vazia)" }),
      ]);

      const prod = produtoDe(atividade, item.dados || {});
      if (prod) {
        cartao.appendChild(criarBlocoProduto("Produto gerado", prod));
      }
      lista.appendChild(cartao);
    }
  };

  const barraFiltro = el("div", { class: "barra-ferramentas" }, [
    el("button", { type: "button", class: "btn btn-pequeno", text: "Todos", onclick: () => { filtro = "todos"; atualizarLista(); } }),
    el("button", { type: "button", class: "btn btn-pequeno", text: "Corretos", onclick: () => { filtro = "ok"; atualizarLista(); } }),
    el("button", { type: "button", class: "btn btn-pequeno", text: "Com erro", onclick: () => { filtro = "erro"; atualizarLista(); } }),
  ]);

  atualizarLista();
  conteiner.appendChild(el("div", { class: "cartao" }, [resumo, barraFiltro]));
  conteiner.appendChild(lista);
}
