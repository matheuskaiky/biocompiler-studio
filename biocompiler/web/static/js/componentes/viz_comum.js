/* Utilitários compartilhados de SVG, janelas (<= 600 bases) e navegação por teclado nas fitas. */

import { el } from "../dom.js";

export const NS_SVG = "http:" + "//www.w3.org/2000/svg";
export const TAM_JANELA = 600;
export const PASSO_X = 28;
export const LARG_BASE = 24;

export function svgEl(tag, attrs = {}, children = []) {
  const node = document.createElementNS(NS_SVG, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k.startsWith("on") && typeof v === "function") {
      node.addEventListener(k.slice(2).toLowerCase(), v);
    } else if (k === "text") {
      node.textContent = String(v);
    } else {
      node.setAttribute(k, String(v));
    }
  }
  for (const c of children) {
    if (c) node.appendChild(c);
  }
  return node;
}

export function classeBase(ch) {
  const u = (ch || "").toUpperCase();
  if (u === "A" || u === "C" || u === "G" || u === "T" || u === "U") return u;
  return "X";
}

export function ultimoEventoComPosicao(passos, k) {
  for (let idx = Math.min(k, passos.length) - 1; idx >= 0; idx -= 1) {
    const pos = passos[idx].posicao;
    if (pos !== null && pos !== undefined) return pos;
  }
  return null;
}

export function criarBarraJanela(total, janelaIdx, onMudar) {
  if (total <= TAM_JANELA) return null;
  const totalJanelas = Math.ceil(total / TAM_JANELA);
  const atual = Math.max(0, Math.min(totalJanelas - 1, janelaIdx));
  const ini = atual * TAM_JANELA;
  const fim = Math.min(total, ini + TAM_JANELA);

  const btnAnt = el("button", {
    type: "button",
    class: "btn btn-pequeno",
    "data-acao": "janela-anterior",
    text: "Janela anterior",
    disabled: atual === 0,
    onClick: () => onMudar(atual - 1),
  });
  const btnProx = el("button", {
    type: "button",
    class: "btn btn-pequeno",
    "data-acao": "janela-proxima",
    text: "Próxima janela",
    disabled: atual >= totalJanelas - 1,
    onClick: () => onMudar(atual + 1),
  });

  return el("div", { class: "viz-janela-barra" }, [
    el("span", { "data-regiao": "janela", text: `Bases ${ini + 1}–${fim} de ${total}` }),
    el("div", { class: "barra-ferramentas" }, [btnAnt, btnProx]),
  ]);
}

export function preencherFitaBases(grupoFita, texto, ini, fim, y, opcoes = {}) {
  const {
    onInspecionar,
    trocasSet = null,
    xOffset = 12,
    comRegua = true,
  } = opcoes;

  const nosBases = [];
  for (let i = ini; i < fim; i += 1) {
    const localIdx = i - ini;
    const x = xOffset + localIdx * PASSO_X;
    const letra = texto[i];
    const ehTroca = trocasSet ? trocasSet.has(i) : false;

    if (comRegua && (i % 10 === 0 || i === ini)) {
      grupoFita.appendChild(svgEl("text", {
        x: x + LARG_BASE / 2,
        y: y - 8,
        class: "svg-regua-texto",
        "text-anchor": "middle",
        text: String(i),
      }));
    }

    const attrsGrupo = {
      class: `svg-base-grupo svg-base-${classeBase(letra)}${ehTroca ? " svg-troca" : ""}`,
      "data-base": "",
      "data-indice": String(i),
      tabindex: i === ini ? "0" : "-1",
      role: "button",
      "aria-label": `Base ${letra} na posição ${i}`,
    };
    if (ehTroca) attrsGrupo["data-troca"] = "";

    const gBase = svgEl("g", attrsGrupo, [
      svgEl("rect", { x, y, width: LARG_BASE, height: 26, class: "svg-base-caixa" }),
      svgEl("text", { x: x + LARG_BASE / 2, y: y + 13, class: "svg-base-letra", text: letra }),
    ]);

    gBase.addEventListener("click", () => {
      if (onInspecionar) onInspecionar(i);
    });
    gBase.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowRight") {
        ev.preventDefault();
        const prox = nosBases[localIdx + 1];
        if (prox) {
          gBase.setAttribute("tabindex", "-1");
          prox.setAttribute("tabindex", "0");
          prox.focus();
        }
      } else if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        const ant = nosBases[localIdx - 1];
        if (ant) {
          gBase.setAttribute("tabindex", "-1");
          ant.setAttribute("tabindex", "0");
          ant.focus();
        }
      } else if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        if (onInspecionar) onInspecionar(i);
      }
    });

    nosBases.push(gBase);
    grupoFita.appendChild(gBase);
  }
}

export function criarMarcaSvg(x, y, rotulo, classeTipo, attrsExtras = {}, onClick = null) {
  const w = Math.max(26, rotulo.length * 7 + 10);
  const g = svgEl("g", {
    class: `svg-marca ${classeTipo}`,
    ...attrsExtras,
  }, [
    svgEl("rect", { x: x - w / 2, y, width: w, height: 18, rx: 5 }),
    svgEl("text", { x, y: y + 9, class: "svg-marca-texto", text: rotulo }),
  ]);
  if (onClick) {
    g.addEventListener("click", onClick);
  }
  return g;
}
