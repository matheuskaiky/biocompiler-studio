/* Inspetor "Por que este resultado?" e descrições didáticas dos eventos da API. */

import { el, limpar } from "../dom.js";

const FRASES_EVENTO = {
  BASES_VALIDADAS: "Bases da sequência validadas",
  BASE_INVALIDA: "Caractere fora do alfabeto aceito",
  START_ENCONTRADO: "Códon de início localizado",
  START_AUSENTE: "Nenhum códon de início encontrado",
  AUG_ENCONTRADO: "Códon de início de tradução localizado",
  AUG_AUSENTE: "Códon de início de tradução ausente",
  CODON_LIDO: "Trinca lida na fase de leitura",
  CODON_TRADUZIDO: "Códon traduzido em aminoácido",
  STOP_ENCONTRADO: "Códon de parada em fase localizado",
  STOP_FORA_DE_FASE: "Códon de parada fora da fase de leitura",
  STOP_AUSENTE: "Nenhum códon de parada em fase",
  T_PARA_U: "Base transcrita para uracila",
  GU_CANDIDATO: "Sítio doador 5' candidato",
  AG_CANDIDATO: "Sítio aceptor 3' candidato",
  INTRON_SELECIONADO: "Íntron selecionado para remoção",
  BRANCH_POINT: "Ponto de ramificação selecionado",
  EXONS_UNIDOS: "Éxons unidos após remoção de íntrons",
  CAP_ADICIONADA: "Quepe 5' adicionado",
  CAP_VALIDADA: "Quepe 5' validado",
  CAP_AUSENTE: "Quepe 5' ausente na entrada",
  POLIA_ADICIONADA: "Cauda poli-A adicionada",
  POLIA_VALIDADA: "Cauda poli-A validada",
  CAUDA_VALIDADA: "Cauda poli-A validada",
  CAUDA_AUSENTE: "Cauda poli-A ausente ou incompleta",
  STOP_EM_FASE: "Códon de parada em fase localizado",
  PROTEINA_GERADA: "Proteína gerada pela tradução",
  BORDA_INICIALIZADA: "Bordas da matriz inicializadas",
  MATRIZ_PREENCHIDA: "Matriz de pontuação preenchida",
  INICIO_TRACEBACK: "Início do traceback localizado",
  TRACEBACK_PASSO: "Passo do caminho ótimo de traceback",
  ALINHAMENTO_FINAL: "Alinhamento final reconstruído",
  RESULTADO: "Resultado final da atividade",
};

export function descreverEvento(tipo) {
  return FRASES_EVENTO[tipo] || "Evento registrado pelo núcleo";
}

export function criarInspetor(conteiner) {
  let sequencia = "";
  let passos = [];

  function limparInspetor() {
    limpar(conteiner);
    conteiner.appendChild(el("h3", { text: "Por que este resultado?" }));
    conteiner.appendChild(el("p", {
      class: "texto-suave",
      text: "Clique em qualquer base ou marcador da fita (ou navegue com ←/→ e pressione Enter) para inspecionar os eventos reais daquela posição.",
    }));
  }

  function definirContexto(novaSeq, novosPassos) {
    sequencia = novaSeq || "";
    passos = novosPassos || [];
    limparInspetor();
  }

  function inspecionar(indice) {
    limpar(conteiner);
    const pos = Number(indice);
    const letra = Number.isInteger(pos) && pos >= 0 && pos < sequencia.length ? sequencia[pos] : "—";
    const correspondentes = passos.filter((ev) => ev.posicao === pos);

    conteiner.appendChild(el("h3", { text: "Por que este resultado?" }));
    conteiner.appendChild(el("div", { class: "barra-ferramentas" }, [
      el("span", { class: "chip mono", text: `Posição ${pos}` }),
      el("span", { class: "chip mono", text: `Base ${letra}` }),
    ]));

    if (!correspondentes.length) {
      conteiner.appendChild(el("p", {
        class: "texto-suave",
        text: "Nenhum evento registrado nesta posição.",
      }));
      return;
    }

    const lista = el("ul", { class: "timeline" });
    for (const ev of correspondentes) {
      lista.appendChild(el("li", { class: "timeline-item" }, [
        el("strong", { class: "mono", text: ev.tipo }),
        el("span", { text: ` — ${descreverEvento(ev.tipo)}` }),
        ev.detalhe ? el("div", { class: "mono", text: ev.detalhe }) : "",
      ]));
    }
    conteiner.appendChild(lista);
  }

  limparInspetor();
  return { definirContexto, inspecionar };
}
