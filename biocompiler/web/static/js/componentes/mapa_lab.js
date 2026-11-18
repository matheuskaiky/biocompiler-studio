import { el, limpar } from "../dom.js";
import { movimentoReduzido } from "../app.js";
import { criarInspetor } from "./inspetor.js";

const LIMITE_JANELA = 600;

function abreviarProduto(texto, limite = 72) {
  const s = String(texto || "");
  if (s.length <= limite) return s;
  return `${s.slice(0, 36)}…${s.slice(-24)} (${s.length})`;
}

function extrairMarcasAt1(at1) {
  const marcas = [];
  if (Number.isInteger(at1.posicao_start)) {
    marcas.push({ tipo: "start", indice: at1.posicao_start, rotulo: `START @ ${at1.posicao_start}` });
  }
  if (Number.isInteger(at1.posicao_stop)) {
    marcas.push({ tipo: "stop", indice: at1.posicao_stop, rotulo: `STOP @ ${at1.posicao_stop}` });
  }
  return marcas;
}

function extrairMarcasAt2(at2) {
  const marcas = [];
  const introns = Array.isArray(at2.introns) ? at2.introns : [];
  for (let idx = 0; idx < introns.length; idx += 1) {
    const intr = introns[idx];
    if (Number.isInteger(intr?.posicao_gu)) {
      marcas.push({
        tipo: "intron",
        indice: intr.posicao_gu,
        rotulo: `Íntron ${idx + 1} (GU @ ${intr.posicao_gu})`,
      });
    }
  }
  return marcas;
}

function extrairMarcasAt3(at3) {
  const marcas = [];
  if (Number.isInteger(at3.posicao_start)) {
    marcas.push({ tipo: "start", indice: at3.posicao_start, rotulo: `START @ ${at3.posicao_start}` });
  }
  if (Number.isInteger(at3.posicao_stop)) {
    marcas.push({ tipo: "stop", indice: at3.posicao_stop, rotulo: `STOP @ ${at3.posicao_stop}` });
  }
  return marcas;
}

function criarBlocoFase(faseId, titulo, faseObj, campoProduto, sequenciaCtx, marcas, aoInspecionar) {
  if (!faseObj) {
    return el("article", {
      class: "mapa-fase mapa-fase-nao-executada",
      "data-fase": faseId,
      "data-status": "nao-executado",
    }, [
      el("div", { class: "mapa-fase-topo" }, [
        el("strong", { text: titulo }),
        el("span", { class: "selo selo-neutro", text: "Não executado" }),
      ]),
      el("p", {
        class: "mapa-fase-msg",
        text: "NÃO EXECUTADO — dependência inválida",
      }),
    ]);
  }

  if (!faseObj.ok) {
    return el("article", {
      class: "mapa-fase mapa-fase-erro",
      "data-fase": faseId,
      "data-status": "erro",
    }, [
      el("div", { class: "mapa-fase-topo" }, [
        el("strong", { text: titulo }),
        el("span", { class: "selo selo-erro", text: faseObj.status || "ERRO" }),
      ]),
      el("p", { class: "mapa-fase-msg mono", text: faseObj.resultado || "Erro na etapa" }),
    ]);
  }

  const valorProduto = String(faseObj[campoProduto] ?? "");
  const botoesMarcas = marcas.map((m) =>
    el("button", {
      type: "button",
      class: `btn btn-marca btn-marca-${m.tipo}`,
      "data-marca": m.tipo,
      "data-indice": String(m.indice),
      text: m.rotulo,
      onClick: () => aoInspecionar(sequenciaCtx, faseObj.eventos || [], m.indice, `${titulo} — ${m.rotulo}`),
    })
  );

  return el("article", {
    class: "mapa-fase mapa-fase-ok",
    "data-fase": faseId,
    "data-status": "ok",
  }, [
    el("div", { class: "mapa-fase-topo" }, [
      el("strong", { text: titulo }),
      el("span", { class: "selo selo-ok", text: faseObj.status || "OK" }),
    ]),
    el("p", {
      class: "mapa-fase-produto mono",
      "data-campo": "produto",
      "data-valor": valorProduto,
      text: abreviarProduto(valorProduto),
    }),
    botoesMarcas.length > 0
      ? el("div", { class: "mapa-marcas" }, botoesMarcas)
      : el("p", { class: "ajuda", text: "Sem marcos posicionais nesta etapa." }),
  ]);
}

function criarTrilhaCadeia(chave, titulo, cadeia, aoInspecionar) {
  const attrs = {
    class: `cartao mapa-trilha ${cadeia.ok ? "mapa-trilha-ok" : "mapa-trilha-falha"}`,
    "data-trilha": chave,
  };
  if (!cadeia.ok && cadeia.etapa_falha) {
    attrs["data-etapa-falha"] = cadeia.etapa_falha;
  }

  const fases = [
    criarBlocoFase(
      "at1",
      "AT1 · Transcrição",
      cadeia.at1,
      "pre_mrna",
      cadeia.at1?.sequencia || cadeia.dna || "",
      cadeia.at1?.ok ? extrairMarcasAt1(cadeia.at1) : [],
      aoInspecionar
    ),
    criarBlocoFase(
      "at2",
      "AT2 · Splicing",
      cadeia.at2,
      "mrna_maduro",
      cadeia.at2?.sequencia || "",
      cadeia.at2?.ok ? extrairMarcasAt2(cadeia.at2) : [],
      aoInspecionar
    ),
    criarBlocoFase(
      "at3",
      "AT3 · Tradução",
      cadeia.at3,
      "proteina",
      cadeia.at3?.regiao_transcrita || "",
      cadeia.at3?.ok ? extrairMarcasAt3(cadeia.at3) : [],
      aoInspecionar
    ),
  ];

  return el("section", attrs, [
    el("div", { class: "mapa-trilha-cabecalho" }, [
      el("h2", { text: `${titulo} (${cadeia.origem || chave})` }),
      el("span", {
        class: `selo ${cadeia.ok ? "selo-ok" : "selo-erro"}`,
        text: cadeia.ok ? "Cadeia completa" : `Falha em ${(cadeia.etapa_falha || "etapa").toUpperCase()}`,
      }),
    ]),
    el("p", {
      class: "mapa-dna-resumo mono",
      text: `DNA (${(cadeia.dna || "").length} nt): ${abreviarProduto(cadeia.dna || "", 64)}`,
    }),
    el("div", { class: "mapa-fases" }, fases),
  ]);
}

function renderizarDiferencasAlinhamento(al) {
  const a1 = String(al.alinhado1 || "");
  const mk = String(al.marcadores || "");
  const a2 = String(al.alinhado2 || "");
  const total = mk.length;
  const inicio = 0;
  const fim = Math.min(total, LIMITE_JANELA);

  const filhos = [];
  for (let i = inicio; i < fim; i += 1) {
    const c1 = a1[i] || " ";
    const m = mk[i] || " ";
    const c2 = a2[i] || " ";
    const ehDif = m !== "|";
    filhos.push(
      el("span", {
        class: `alin-col ${ehDif ? "alin-col-dif" : "alin-col-match"}`,
        ...(ehDif ? { "data-diferenca": "true", "data-indice": String(i) } : {}),
      }, [
        el("span", { class: "alin-c", text: c1 }),
        el("span", { class: "alin-m", text: m }),
        el("span", { class: "alin-c", text: c2 }),
      ])
    );
  }

  return el("div", { class: "alin-faixa-wrap" }, [
    el("span", {
      "data-campo": "alinhado1",
      "data-valor": a1,
      hidden: true,
    }),
    el("span", {
      "data-campo": "marcadores",
      "data-valor": mk,
      hidden: true,
    }),
    el("span", {
      "data-campo": "alinhado2",
      "data-valor": a2,
      hidden: true,
    }),
    total > LIMITE_JANELA
      ? el("p", {
          class: "ajuda",
          text: `Mostrando janela visual 0–${fim - 1} de ${total} colunas alinhadas.`,
        })
      : null,
    el("div", { class: "alin-faixa mono" }, filhos),
  ]);
}

function criarTrilhaAlinhamento(alinhamentos) {
  const cards = (alinhamentos || []).map((al) => {
    const tipo = al.metodo === "local" ? "local" : "global";
    const titulo = tipo === "local" ? "Smith–Waterman (Local)" : "Needleman–Wunsch (Global)";
    if (!al.ok) {
      return el("article", {
        class: "mapa-alinhamento-card",
        "data-alinhamento": tipo,
      }, [
        el("div", { class: "mapa-fase-topo" }, [
          el("strong", { text: titulo }),
          el("span", {
            class: "selo selo-erro",
            "data-campo": "score",
            "data-metodo": al.metodo,
            text: "Erro",
          }),
        ]),
        el("p", { class: "mapa-fase-msg mono", text: al.resultado || "Erro no alinhamento" }),
      ]);
    }

    return el("article", {
      class: "mapa-alinhamento-card",
      "data-alinhamento": tipo,
    }, [
      el("div", { class: "mapa-fase-topo" }, [
        el("strong", { text: titulo }),
        el("span", { class: "mono" }, [
          "Score ",
          el("strong", {
            "data-campo": "score",
            "data-metodo": al.metodo,
            text: String(al.score),
          }),
          ` · Matches: ${al.matches} · Mismatches: ${al.mismatches} · Gaps: ${al.gaps}`,
        ]),
      ]),
      renderizarDiferencasAlinhamento(al),
    ]);
  });

  return el("section", {
    class: "cartao mapa-trilha",
    "data-trilha": "alinhamento",
  }, [
    el("div", { class: "mapa-trilha-cabecalho" }, [
      el("h2", { text: "Convergência AT4 · Alinhamento dos DNAs originais" }),
    ]),
    el("div", { class: "mapa-alinhamentos-lista" }, cards),
  ]);
}

function animarTrilhasSequencialmente(raiz) {
  if (movimentoReduzido()) return;
  const fases = raiz.querySelectorAll("[data-fase]");
  fases.forEach((fase, idx) => {
    if (typeof fase.animate === "function") {
      fase.animate(
        [
          { opacity: 0.45, transform: "translateY(4px)" },
          { opacity: 1, transform: "translateY(0)" },
        ],
        {
          duration: 180,
          delay: Math.min(idx * 45, 220),
          easing: "ease-out",
        }
      );
    }
  });
}

export function renderizarMapaLab(conteiner, dados) {
  limpar(conteiner);

  const inspetorBox = el("section", {
    class: "cartao mapa-inspetor",
    "data-regiao": "inspetor",
  }, [
    el("p", {
      class: "ajuda",
      text: "Selecione um marco (START, STOP ou Íntron) em qualquer fase concluída para inspecionar posição, base e eventos.",
    }),
  ]);

  const inspetor = criarInspetor(inspetorBox);

  function aoInspecionar(sequencia, eventos, indice) {
    inspetor.definirContexto(sequencia, eventos || []);
    inspetor.inspecionar(indice);
  }

  const grade = el("div", { class: "grade-dupla mapa-grade" }, [
    criarTrilhaCadeia("seq1", "Cadeia 1", dados.seq1, aoInspecionar),
    criarTrilhaCadeia("seq2", "Cadeia 2", dados.seq2, aoInspecionar),
  ]);

  conteiner.appendChild(grade);
  conteiner.appendChild(inspetorBox);
  conteiner.appendChild(criarTrilhaAlinhamento(dados.alinhamentos));

  animarTrilhasSequencialmente(conteiner);
}
