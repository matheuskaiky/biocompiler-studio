import { el, limpar } from "../dom.js";

const LIMITE_JANELA = 600;

function abreviarTexto(texto, limite = 80) {
  const s = String(texto || "");
  if (s.length <= limite) return s;
  return `${s.slice(0, 40)}…${s.slice(-24)} (${s.length})`;
}

function extrairLista(valor, modo) {
  if (valor == null) return null;
  const s = String(valor);
  if (modo === "proteina") {
    return s ? s.split("-") : [];
  }
  return Array.from(s);
}

function criarPainelNivel(nivel, titulo, v1, v2, modo) {
  const l1 = extrairLista(v1, modo);
  const l2 = extrairLista(v2, modo);

  const lado1 = el("div", {
    class: "comp-lado",
    "data-lado": "seq1",
    "data-valor": v1 != null ? String(v1) : "",
  }, [
    el("strong", { text: "Seq 1: " }),
    el("span", {
      class: "mono",
      text: v1 != null ? abreviarTexto(v1) : "Indisponível",
    }),
  ]);

  const lado2 = el("div", {
    class: "comp-lado",
    "data-lado": "seq2",
    "data-valor": v2 != null ? String(v2) : "",
  }, [
    el("strong", { text: "Seq 2: " }),
    el("span", {
      class: "mono",
      text: v2 != null ? abreviarTexto(v2) : "Indisponível",
    }),
  ]);

  if (l1 === null || l2 === null) {
    return el("section", {
      class: "secao-plana comp-nivel comp-nivel-indisponivel",
      "data-nivel": nivel,
    }, [
      el("div", { class: "comp-nivel-topo" }, [
        el("h3", { text: titulo }),
        el("span", { class: "selo selo-neutro", text: "Indisponível" }),
      ]),
      el("div", { class: "comp-lados" }, [lado1, lado2]),
    ]);
  }

  const maxLen = Math.max(l1.length, l2.length);
  const comprimentosDiferentes = l1.length !== l2.length;
  let totalDifs = 0;
  for (let i = 0; i < maxLen; i += 1) {
    if (l1[i] !== l2[i]) totalDifs += 1;
  }

  const fim = Math.min(maxLen, LIMITE_JANELA);
  const itens = [];
  for (let i = 0; i < fim; i += 1) {
    const a = l1[i] ?? "∅";
    const b = l2[i] ?? "∅";
    const dif = a !== b;
    itens.push(
      el("span", {
        class: `comp-cel ${dif ? "comp-cel-dif" : "comp-cel-igual"}`,
        ...(dif ? { "data-diferenca": "true", "data-indice": String(i) } : {}),
        title: `Posição ${i}: ${a} vs ${b}`,
      }, [
        el("span", { class: "comp-pos", text: String(i) }),
        el("span", { class: "comp-a mono", text: a }),
        el("span", { class: "comp-b mono", text: b }),
      ])
    );
  }

  const resumoDifs = `${totalDifs} ${totalDifs === 1 ? "diferença observada" : "diferenças observadas"}`;
  const seloTexto = comprimentosDiferentes
    ? `Comprimentos diferentes (${l1.length} vs ${l2.length}) · ${resumoDifs}`
    : resumoDifs;

  return el("section", {
    class: "secao-plana comp-nivel",
    "data-nivel": nivel,
  }, [
    el("div", { class: "comp-nivel-topo" }, [
      el("h3", { text: titulo }),
      el("span", {
        class: `selo ${totalDifs > 0 ? "selo-aviso" : "selo-ok"}`,
        text: seloTexto,
      }),
    ]),
    el("div", { class: "comp-lados" }, [lado1, lado2]),
    maxLen > LIMITE_JANELA
      ? el("p", {
          class: "ajuda",
          text: `Mostrando janela 0–${fim - 1} de ${maxLen} posições.`,
        })
      : null,
    el("div", { class: "comp-grade" }, itens),
  ]);
}

export function renderizarComparadorLab(conteiner, dados) {
  limpar(conteiner);
  const s1 = dados.seq1 || {};
  const s2 = dados.seq2 || {};

  const raiz = el("div", {
    class: "comparador-raiz",
    "data-componente": "comparador",
  }, [
    criarPainelNivel("dna", "1. DNA original", s1.dna ?? null, s2.dna ?? null, "bases"),
    criarPainelNivel(
      "pre-mrna",
      "2. Pré-mRNA (AT1)",
      s1.at1?.ok ? s1.at1.pre_mrna : null,
      s2.at1?.ok ? s2.at1.pre_mrna : null,
      "bases"
    ),
    criarPainelNivel(
      "rna-processado",
      "3. RNA processado (AT2)",
      s1.at2?.ok ? s1.at2.rna_processado : null,
      s2.at2?.ok ? s2.at2.rna_processado : null,
      "bases"
    ),
    criarPainelNivel(
      "proteina",
      "4. Proteína (AT3)",
      s1.at3?.ok ? s1.at3.proteina : null,
      s2.at3?.ok ? s2.at3.proteina : null,
      "proteina"
    ),
  ]);

  conteiner.appendChild(raiz);
}
