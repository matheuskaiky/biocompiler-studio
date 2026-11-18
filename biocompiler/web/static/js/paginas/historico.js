/* Controlador da página Histórico local (/historico). */

import { definirStatus, lerHistorico, limparHistorico } from "../app.js";
import { el, limpar, qs } from "../dom.js";

function renderizar() {
  const cont = qs('[data-regiao="historico"]');
  if (!cont) return;
  limpar(cont);
  const lista = lerHistorico();
  if (!lista.length) {
    cont.appendChild(el("div", { class: "vazio", text: "Nenhum experimento nesta sessão." }));
    return;
  }
  for (const item of lista) {
    cont.appendChild(el("article", { class: "cartao" }, [
      el("div", { class: "barra-ferramentas" }, [
        el("strong", { text: (item.atividade || "").toUpperCase() }),
        el("span", { text: item.dataHora || "" }),
        el("a", { class: "btn btn-pequeno", href: item.href || "/", text: "Reabrir" }),
      ]),
      el("p", { class: "mono", text: item.resumo || "" }),
    ]));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderizar();
  const btnExp = qs('[data-acao="exportar-historico"]');
  const btnLimpar = qs('[data-acao="limpar-historico"]');
  if (btnExp) {
    btnExp.addEventListener("click", () => {
      const dados = JSON.stringify(lerHistorico(), null, 2);
      const blob = new Blob([dados], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "biocompiler_historico.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      definirStatus("Histórico exportado em JSON.", "ok");
    });
  }
  if (btnLimpar) {
    btnLimpar.addEventListener("click", () => {
      limparHistorico();
      renderizar();
      definirStatus("Histórico limpo.");
    });
  }
});
