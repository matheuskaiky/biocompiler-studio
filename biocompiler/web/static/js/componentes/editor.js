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

export function extrairParSequencias(texto) {
  const bruto = String(texto || "").replace(/\\n/g, "\n").replace(/\r\n/g, "\n");
  const linhas = bruto.split("\n").map((l) => l.trim()).filter(Boolean);
  if (!linhas.length) return ["", ""];
  if (linhas[0].startsWith(">")) {
    const seqs = [];
    let atual = [];
    for (const l of linhas) {
      if (l.startsWith(">")) {
        if (atual.length) seqs.push(atual.join(""));
        atual = [];
      } else {
        atual.push(l);
      }
    }
    if (atual.length) seqs.push(atual.join(""));
    return [seqs[0] || "", seqs[1] || ""];
  }
  return [linhas[0] || "", linhas[1] || ""];
}

export function conectarSegmentoMetodo(segmento, selectEl) {
  if (!segmento || !selectEl) return;
  const botoes = Array.from(segmento.querySelectorAll("[data-valor]"));
  const sincronizar = (valor) => {
    for (const b of botoes) {
      const ativo = b.getAttribute("data-valor") === valor;
      b.setAttribute("aria-pressed", ativo ? "true" : "false");
    }
  };
  sincronizar(selectEl.value || "both");
  for (const b of botoes) {
    b.addEventListener("click", () => {
      const val = b.getAttribute("data-valor");
      if (!val) return;
      selectEl.value = val;
      sincronizar(val);
      selectEl.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
  selectEl.addEventListener("change", () => sincronizar(selectEl.value));
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
    const btnImportar = zona.querySelector('[data-acao="importar"]');
    if (btnImportar && inputArquivo) {
      btnImportar.addEventListener("click", () => inputArquivo.click());
    }
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
