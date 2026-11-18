/* Visualizador de sequência: bases coloridas 10 em 10, régua e cauda poli-A comprimida. */

import { el, limpar } from "../dom.js";

function classeBase(b) {
  if (b === "A" || b === "C" || b === "G" || b === "T" || b === "U") return `b-${b}`;
  return "b-X";
}

export function renderizarSequencia(texto) {
  const conteiner = el("div", { class: "visor-bases" });
  if (!texto) {
    conteiner.appendChild(el("span", { class: "regua-pos", text: "(vazia)" }));
    return conteiner;
  }

  let corpo = texto;
  let caudaLonga = 0;
  const m = texto.match(/A{20,}$/);
  if (m && m[0].length >= 20) {
    caudaLonga = m[0].length;
    corpo = texto.slice(0, texto.length - caudaLonga);
  }

  const montarGrupos = (seq, alvo) => {
    for (let i = 0; i < seq.length; i += 10) {
      const fatia = seq.slice(i, i + 10);
      const linhaBases = el("div", { class: "mono" });
      for (const ch of fatia) {
        linhaBases.appendChild(el("span", { class: classeBase(ch), text: ch }));
      }
      alvo.appendChild(el("div", { class: "grupo-10" }, [
        el("span", { class: "regua-pos", text: String(i + 1) }),
        linhaBases,
      ]));
    }
  };

  montarGrupos(corpo, conteiner);

  if (caudaLonga > 0) {
    const resumo = el("span", { class: "chip chip-a", text: `A×${caudaLonga}` });
    const expandido = el("div", { class: "visor-bases painel-oculto" });
    let aberto = false;
    const btn = el("button", {
      type: "button",
      class: "btn btn-pequeno",
      text: "Expandir poli-A",
      onclick: () => {
        aberto = !aberto;
        if (aberto && !expandido.firstChild) {
          montarGrupos("A".repeat(caudaLonga), expandido);
        }
        expandido.classList.toggle("painel-oculto", !aberto);
        btn.textContent = aberto ? "Recolher poli-A" : "Expandir poli-A";
      },
    });
    conteiner.appendChild(el("div", { class: "grupo-10" }, [resumo, btn]));
    conteiner.appendChild(expandido);
  }

  return conteiner;
}

export function criarBlocoProduto(rotulo, valor) {
  const copiar = el("button", {
    type: "button",
    class: "btn btn-pequeno",
    text: "Copiar",
    onclick: async () => {
      try {
        await navigator.clipboard.writeText(valor);
        copiar.textContent = "Copiado";
      } catch (e) {
        copiar.textContent = "Copiado localmente";
      }
    },
  });
  return el("div", { class: "cartao" }, [
    el("div", { class: "barra-ferramentas" }, [
      el("strong", { text: rotulo }),
      copiar,
    ]),
    el("div", { class: "bloco-produto", text: valor }),
    renderizarSequencia(valor),
  ]);
}
