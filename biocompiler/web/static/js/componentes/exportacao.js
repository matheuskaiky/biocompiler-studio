/* Painel de exportação .zip listando os artefatos da D015/D017. */

import { el, limpar } from "../dom.js";

const ARQUIVOS_POR_AT = {
  at1: ["at1_resultados.txt"],
  at2: ["at2_resultados.txt"],
  at3: ["at3_resultados.txt"],
  at4: [
    "alinhamento_local.txt",
    "matriz_pontuacao_local.csv",
    "matriz_traceback_local.csv",
    "alinhamento_local.csv",
    "alinhamento_global.txt",
    "matriz_pontuacao_global.csv",
    "matriz_traceback_global.csv",
    "alinhamento_global.csv",
    "comparacao.txt",
  ],
  all: [
    "relatorio_mestre.txt",
    "at1_resultados.txt",
    "at2_resultados.txt",
    "at3_resultados.txt",
    "alinhamento_<metodo>.txt / matriz_*.csv / comparacao.txt",
  ],
};

export function renderizarListaArtefatos(conteiner, atividade) {
  if (!conteiner) return;
  limpar(conteiner);
  const nomes = ARQUIVOS_POR_AT[atividade] || [];
  const ul = el("ul");
  for (const nome of nomes) {
    ul.appendChild(el("li", { class: "mono", text: nome }));
  }
  conteiner.appendChild(el("p", { text: "Arquivos incluídos no pacote .zip:" }));
  conteiner.appendChild(ul);
}
