/* Utilitário de conexão SVG animada entre elementos relacionados do DOM. */

import { limpar } from "../dom.js";
import { animar, movimentoReduzido } from "./orquestrador.js";

const NS_SVG = "http:" + "//www.w3.org/2000/svg";

export function limparConexoes(camadaSvg) {
  if (camadaSvg) limpar(camadaSvg);
}

export function desenharConexao(camadaSvg, origemEl, destinoEl, opcoes = {}) {
  if (!camadaSvg || !origemEl || !destinoEl) return null;
  limpar(camadaSvg);

  const caixaSvg = camadaSvg.getBoundingClientRect();
  const r1 = origemEl.getBoundingClientRect();
  const r2 = destinoEl.getBoundingClientRect();

  const x1 = r1.left + r1.width / 2 - caixaSvg.left;
  const y1 = r1.bottom - caixaSvg.top;
  const x2 = r2.left + r2.width / 2 - caixaSvg.left;
  const y2 = r2.top - caixaSvg.top;
  const dy = Math.max(24, Math.abs(y2 - y1) * 0.55);

  const d = `M ${x1.toFixed(1)} ${y1.toFixed(1)} C ${x1.toFixed(1)} ${(y1 + dy).toFixed(1)}, ${x2.toFixed(1)} ${(y2 - dy).toFixed(1)}, ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  const path = document.createElementNS(NS_SVG, "path");
  path.setAttribute("d", d);
  path.setAttribute("class", opcoes.classe || "conexao-svg-curva");
  path.setAttribute("data-conexao", opcoes.id || "true");
  path.setAttribute("fill", "none");
  camadaSvg.appendChild(path);

  if (!movimentoReduzido() && typeof path.getTotalLength === "function") {
    const comp = path.getTotalLength() || 120;
    path.style.strokeDasharray = `${comp}`;
    path.style.strokeDashoffset = `${comp}`;
    animar(path, [
      { strokeDashoffset: comp, opacity: 0.4 },
      { strokeDashoffset: 0, opacity: 1 },
    ], { duration: 240, fill: "forwards" });
  }

  return path;
}
