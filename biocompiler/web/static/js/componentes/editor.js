/* Contadores ao vivo e importação de arquivo (clique ou arrastar e soltar). */

import { el, limpar } from "../dom.js";

const CHIPS = [
  ["A", "chip-a"],
  ["C", "chip-c"],
  ["G", "chip-g"],
  ["T", "chip-t"],
  ["U", "chip-u"],
];

export function atualizarContadores(texto, container, alfabetoPermitido) {
  if (!container) return;
  limpar(container);
  const contagens = { A: 0, C: 0, G: 0, T: 0, U: 0 };
  let outros = 0;
  for (const ch of texto) {
    if (ch === "\n" || ch === "\r") continue;
    if (ch in contagens) contagens[ch] += 1;
    else outros += 1;
  }
  const total = texto.replace(/[\r\n]/g, "").length;
  container.appendChild(el("span", { class: "chip", text: `Comprimento: ${total}` }));
  for (const [base, cls] of CHIPS) {
    if (alfabetoPermitido.includes(base) || contagens[base] > 0) {
      container.appendChild(el("span", { class: `chip ${cls}`, text: `${base}: ${contagens[base]}` }));
    }
  }
  if (outros > 0) {
    container.appendChild(el("span", {
      class: "chip chip-erro",
      text: `Fora de ${alfabetoPermitido}: ${outros}`,
    }));
  }
}

export function conectarZonaArquivo(zona, inputArquivo, aoLerTexto) {
  if (inputArquivo) {
    inputArquivo.addEventListener("change", async () => {
      const arq = inputArquivo.files && inputArquivo.files[0];
      if (!arq) return;
      const texto = await arq.text();
      aoLerTexto(texto, arq.name);
    });
  }
  if (zona) {
    zona.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      zona.classList.add("arrastando");
    });
    zona.addEventListener("dragleave", () => zona.classList.remove("arrastando"));
    zona.addEventListener("drop", async (ev) => {
      ev.preventDefault();
      zona.classList.remove("arrastando");
      const arq = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
      if (!arq) return;
      const texto = await arq.text();
      aoLerTexto(texto, arq.name);
    });
  }
}
