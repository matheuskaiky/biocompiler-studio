/* Linha do tempo paginada (<= 500 itens) sincronizada com o player de eventos. */

import { el, limpar } from "../dom.js";

const TAM_PAGINA = 500;

export function criarEtapas(conteiner, onSelecionarPasso) {
  let itens = [];
  let tituloAtual = "Linha do tempo de eventos";
  let passoAtual = 1;
  let paginaAtual = 0;

  function desenhar() {
    limpar(conteiner);
    if (!itens.length) {
      conteiner.appendChild(el("div", { class: "vazio", text: "Nenhum evento disponível." }));
      return;
    }

    const total = itens.length;
    const totalPaginas = Math.ceil(total / TAM_PAGINA);
    if (paginaAtual >= totalPaginas) paginaAtual = totalPaginas - 1;
    if (paginaAtual < 0) paginaAtual = 0;

    const ini = paginaAtual * TAM_PAGINA;
    const fim = Math.min(total, ini + TAM_PAGINA);

    const card = el("div", { class: "cartao" }, [
      el("h2", { text: tituloAtual }),
    ]);

    if (total > TAM_PAGINA) {
      const btnAnt = el("button", {
        type: "button",
        class: "btn btn-pequeno",
        text: "Eventos anteriores",
        disabled: paginaAtual === 0,
        onClick: () => {
          paginaAtual = Math.max(0, paginaAtual - 1);
          desenhar();
        },
      });
      const btnProx = el("button", {
        type: "button",
        class: "btn btn-pequeno",
        text: "Próximos eventos",
        disabled: paginaAtual >= totalPaginas - 1,
        onClick: () => {
          paginaAtual = Math.min(totalPaginas - 1, paginaAtual + 1);
          desenhar();
        },
      });
      card.appendChild(el("div", { class: "viz-janela-barra" }, [
        el("span", { "data-regiao": "janela-eventos", text: `Eventos ${ini + 1}–${fim} de ${total}` }),
        el("div", { class: "barra-ferramentas" }, [btnAnt, btnProx]),
      ]));
    }

    const lista = el("ol", { class: "timeline" });
    for (let idx = ini; idx < fim; idx += 1) {
      const ev = itens[idx];
      const k = idx + 1;
      const pos = ev.posicao !== null && ev.posicao !== undefined ? ` · índice ${ev.posicao}` : "";
      const det = ev.detalhe ? ` — ${ev.detalhe}` : "";
      const attrs = {
        class: "timeline-item",
        "data-passo": String(k),
        tabindex: "0",
        onClick: () => {
          if (onSelecionarPasso) onSelecionarPasso(k);
        },
        onKeydown: (evKey) => {
          if (evKey.key === "Enter" || evKey.key === " ") {
            evKey.preventDefault();
            if (onSelecionarPasso) onSelecionarPasso(k);
          }
        },
      };
      if (k === passoAtual) attrs["aria-current"] = "step";
      lista.appendChild(el("li", attrs, [
        el("strong", { class: "mono", text: `${k}. ${ev.tipo}` }),
        el("span", { class: "mono", text: `${pos}${det}` }),
      ]));
    }
    card.appendChild(lista);
    conteiner.appendChild(card);
  }

  function definirDados(novosItens, titulo = "Linha do tempo de eventos", kInicial = 1) {
    itens = novosItens || [];
    tituloAtual = titulo;
    passoAtual = kInicial;
    paginaAtual = Math.floor(Math.max(0, passoAtual - 1) / TAM_PAGINA);
    desenhar();
  }

  function atualizarPasso(k) {
    passoAtual = k;
    const pagEsperada = Math.floor(Math.max(0, k - 1) / TAM_PAGINA);
    if (pagEsperada !== paginaAtual) {
      paginaAtual = pagEsperada;
      desenhar();
      return;
    }
    const anterior = conteiner.querySelector('[aria-current="step"]');
    if (anterior) anterior.removeAttribute("aria-current");
    const alvo = conteiner.querySelector(`[data-passo="${k}"]`);
    if (alvo) alvo.setAttribute("aria-current", "step");
  }

  return { definirDados, atualizarPasso };
}

export function renderizarEtapas(conteiner, itens, titulo = "Linha do tempo de eventos") {
  const inst = criarEtapas(conteiner, null);
  inst.definirDados(itens, titulo, 1);
  return inst;
}
