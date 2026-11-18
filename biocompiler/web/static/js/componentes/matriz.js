/* Renderização da matriz AT4 (tabela sticky ou Canvas) + inspetor de célula via API. */

import { el, limpar } from "../dom.js";
import { inspecionarCelula } from "../api.js";

const LIMITE_DOM_CELULAS = 10000;

export function renderizarMatrizAT4(conteiner, item, cfgEntrada) {
  const dados = item.dados;
  const matriz = dados.matriz;
  const direcoes = dados.direcoes;
  if (!matriz || !direcoes) return;

  const m = dados.seq1.length;
  const n = dados.seq2.length;
  const caminhoSet = new Set((dados.caminho || []).map(([i, j]) => `${i},${j}`));

  const painelInspetor = el("div", { class: "cartao" }, [
    el("h3", { text: `Inspetor de célula (${dados.metodo})` }),
    el("p", { text: "Clique ou use as setas em uma célula para consultar /api/at4/celula." }),
  ]);

  async function carregarCelula(i, j) {
    try {
      const resp = await inspecionarCelula({
        seq1: cfgEntrada.seq1,
        seq2: cfgEntrada.seq2,
        alinhamento: dados.metodo,
        match: cfgEntrada.match,
        mismatch: cfgEntrada.mismatch,
        gap: cfgEntrada.gap,
        i,
        j,
      });
      limpar(painelInspetor);
      painelInspetor.appendChild(el("h3", {
        text: `Célula (${resp.i}, ${resp.j}) — ${resp.metodo}`,
      }));
      painelInspetor.appendChild(el("p", {
        class: "mono",
        text: `Valor: ${resp.valor}   Direção: ${resp.direcao}`,
      }));
      if (!resp.candidatos.length) {
        painelInspetor.appendChild(el("p", { text: "Célula de borda (sem candidatos internos)." }));
      } else {
        const ul = el("ul");
        for (const c of resp.candidatos) {
          ul.appendChild(el("li", { class: "mono", text: `${c.nome}: ${c.valor}` }));
        }
        painelInspetor.appendChild(ul);
      }
    } catch (err) {
      limpar(painelInspetor);
      painelInspetor.appendChild(el("p", { text: `Erro ao inspecionar célula: ${err.message}` }));
    }
  }

  const bloco = el("div", { class: "cartao" }, [
    el("h3", { text: `Matriz completa — ${dados.metodo.toUpperCase()} (${m + 1}×${n + 1})` }),
  ]);

  if ((m + 1) * (n + 1) > LIMITE_DOM_CELULAS) {
    const cel = 26;
    const canvas = el("canvas", {
      width: (n + 2) * cel,
      height: (m + 2) * cel,
    });
    const ctx = canvas.getContext("2d");
    ctx.font = "11px monospace";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let i = 0; i <= m; i += 1) {
      for (let j = 0; j <= n; j += 1) {
        const x = (j + 1) * cel;
        const y = (i + 1) * cel;
        ctx.fillStyle = caminhoSet.has(`${i},${j}`) ? "#92400e" : "#141c2b";
        ctx.fillRect(x, y, cel - 1, cel - 1);
        ctx.fillStyle = "#e6edf7";
        ctx.fillText(String(matriz[i][j]), x + cel / 2, y + cel / 2);
      }
    }
    canvas.addEventListener("click", (ev) => {
      const rect = canvas.getBoundingClientRect();
      const j = Math.floor((ev.clientX - rect.left) / cel) - 1;
      const i = Math.floor((ev.clientY - rect.top) / cel) - 1;
      if (i >= 0 && i <= m && j >= 0 && j <= n) carregarCelula(i, j);
    });
    bloco.appendChild(el("div", { class: "matriz-scroll" }, [canvas]));
  } else {
    const tabela = el("table", { class: "matriz-at4" });
    const thead = el("thead");
    const trHead = el("tr", {}, [el("th", { text: "" }), el("th", { text: "-" })]);
    for (const ch of dados.seq2) trHead.appendChild(el("th", { text: ch }));
    thead.appendChild(trHead);
    tabela.appendChild(thead);

    const tbody = el("tbody");
    const tds = Array.from({ length: m + 1 }, () => Array(n + 1));
    let selecionada = null;

    for (let i = 0; i <= m; i += 1) {
      const rotulo = i === 0 ? "-" : dados.seq1[i - 1];
      const tr = el("tr", {}, [el("th", { scope: "row", text: rotulo })]);
      for (let j = 0; j <= n; j += 1) {
        const noCaminho = caminhoSet.has(`${i},${j}`);
        const td = el("td", {
          class: `celula-btn${noCaminho ? " caminho" : ""}`,
          tabindex: "0",
          text: `${matriz[i][j]} ${direcoes[i][j]}`,
        });
        const selecionar = () => {
          if (selecionada) selecionada.classList.remove("selecionada");
          selecionada = td;
          td.classList.add("selecionada");
          carregarCelula(i, j);
        };
        td.addEventListener("click", selecionar);
        td.addEventListener("keydown", (ev) => {
          let ni = i;
          let nj = j;
          if (ev.key === "ArrowRight") nj = Math.min(n, j + 1);
          else if (ev.key === "ArrowLeft") nj = Math.max(0, j - 1);
          else if (ev.key === "ArrowDown") ni = Math.min(m, i + 1);
          else if (ev.key === "ArrowUp") ni = Math.max(0, i - 1);
          else if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            selecionar();
            return;
          } else {
            return;
          }
          ev.preventDefault();
          tds[ni][nj].focus();
        });
        tds[i][j] = td;
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    tabela.appendChild(tbody);
    bloco.appendChild(el("div", { class: "matriz-scroll" }, [tabela]));
  }

  conteiner.appendChild(bloco);
  conteiner.appendChild(painelInspetor);
}
