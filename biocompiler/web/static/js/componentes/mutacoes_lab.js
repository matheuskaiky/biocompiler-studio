import { el, limpar } from "../dom.js";

function aplicarOperacao(seq, operacao, pos, base) {
  if (operacao === "substituir") {
    return seq.slice(0, pos) + base + seq.slice(pos + 1);
  }
  if (operacao === "inserir") {
    return seq.slice(0, pos) + base + seq.slice(pos);
  }
  return seq.slice(0, pos) + seq.slice(pos + 1);
}

function validarIndice(seq, operacao, pos) {
  if (!Number.isInteger(pos) || pos < 0) return false;
  if (operacao === "inserir") return pos <= seq.length;
  return pos < seq.length;
}

export function criarLabMutacoes(conteiner, { obterSeq, definirSeq, aoAlterar }) {
  limpar(conteiner);

  const origens = { seq1: null, seq2: null };
  const historico = [];
  let ultimoAlvo = "seq2";

  const selAlvo = el("select", { id: "mut-alvo", "data-campo": "mut-alvo" }, [
    el("option", { value: "seq2", text: "Seq 2 (variante)" }),
    el("option", { value: "seq1", text: "Seq 1 (referência)" }),
  ]);

  const selOp = el("select", { id: "mut-operacao", "data-campo": "mut-operacao" }, [
    el("option", { value: "substituir", text: "Substituir base" }),
    el("option", { value: "inserir", text: "Inserir base" }),
    el("option", { value: "remover", text: "Remover base" }),
  ]);

  const inpPos = el("input", {
    id: "mut-posicao",
    type: "number",
    min: "0",
    step: "1",
    value: "0",
    "data-campo": "mut-posicao",
  });

  const selBase = el("select", { id: "mut-base", "data-campo": "mut-base" }, [
    el("option", { value: "A", text: "A" }),
    el("option", { value: "T", text: "T" }),
    el("option", { value: "C", text: "C" }),
    el("option", { value: "G", text: "G" }),
  ]);

  const btnAplicar = el("button", {
    type: "button",
    class: "btn btn-primario",
    "data-acao": "aplicar-mutacao",
    text: "Aplicar mutação",
  });

  const btnReverter = el("button", {
    type: "button",
    class: "btn",
    "data-acao": "reverter",
    disabled: true,
    text: "Reverter",
  });

  const linkAlinhar = el("a", {
    class: "btn",
    href: "/at4",
    "data-acao": "alinhar-com-origem",
    text: "Alinhar com origem",
  });

  const regErro = el("p", {
    class: "mut-erro",
    role: "alert",
    "data-regiao": "mutacoes-erro",
    text: "",
  });

  const regHist = el("ol", {
    class: "mut-historico",
    "data-regiao": "mutacoes-historico",
  });

  function atualizarControles() {
    selBase.disabled = selOp.value === "remover";
    btnReverter.disabled = historico.length === 0;
    const origem = origens[ultimoAlvo];
    if (origem !== null) {
      const atual = obterSeq(ultimoAlvo);
      const q = new URLSearchParams({
        seq1: origem,
        seq2: atual,
        executar: "1",
      });
      linkAlinhar.setAttribute("href", `/at4?${q.toString()}`);
    } else {
      linkAlinhar.setAttribute("href", "/at4");
    }
  }

  function renderizarHistorico() {
    limpar(regHist);
    for (let i = 0; i < historico.length; i += 1) {
      const item = historico[i];
      const desc = item.operacao === "remover"
        ? `${item.alvo} · -${item.anterior} @ ${item.pos}`
        : item.operacao === "inserir"
          ? `${item.alvo} · +${item.base} @ ${item.pos}`
          : `${item.alvo} · ${item.anterior}→${item.base} @ ${item.pos}`;
      regHist.appendChild(
        el("li", { class: "mut-item mono", "data-mutacao": String(i + 1), text: desc })
      );
    }
  }

  selOp.addEventListener("change", atualizarControles);

  btnAplicar.addEventListener("click", async () => {
    const alvo = selAlvo.value === "seq1" ? "seq1" : "seq2";
    const operacao = selOp.value;
    const rawPos = inpPos.value.trim();
    const pos = rawPos === "" ? NaN : Number(rawPos);
    const seqAtual = String(obterSeq(alvo) || "");

    if (!validarIndice(seqAtual, operacao, pos)) {
      regErro.textContent = "Índice fora do intervalo";
      return;
    }

    regErro.textContent = "";
    if (origens[alvo] === null) {
      origens[alvo] = seqAtual;
    }

    const base = selBase.value || "A";
    const anterior = seqAtual[pos] || "";
    const novaSeq = aplicarOperacao(seqAtual, operacao, pos, base);

    definirSeq(alvo, novaSeq);
    historico.push({ alvo, operacao, pos, base, anterior, seqAnterior: seqAtual });
    ultimoAlvo = alvo;

    renderizarHistorico();
    atualizarControles();
    await aoAlterar();
  });

  btnReverter.addEventListener("click", async () => {
    if (!historico.length) return;
    regErro.textContent = "";
    const ultimo = historico.pop();
    definirSeq(ultimo.alvo, ultimo.seqAnterior);
    if (!historico.some((h) => h.alvo === ultimo.alvo)) {
      origens[ultimo.alvo] = null;
    }
    ultimoAlvo = historico.length ? historico[historico.length - 1].alvo : "seq2";
    renderizarHistorico();
    atualizarControles();
    await aoAlterar();
  });

  const painel = el("section", {
    class: "cartao mut-painel",
    "data-componente": "mutacoes",
  }, [
    el("h2", { text: "Laboratório de mutações" }),
    el("div", { class: "mut-controles" }, [
      el("div", { class: "campo" }, [
        el("label", { for: "mut-alvo", text: "Alvo" }),
        selAlvo,
      ]),
      el("div", { class: "campo" }, [
        el("label", { for: "mut-operacao", text: "Operação" }),
        selOp,
      ]),
      el("div", { class: "campo" }, [
        el("label", { for: "mut-posicao", text: "Índice (0 = primeira base)" }),
        inpPos,
      ]),
      el("div", { class: "campo" }, [
        el("label", { for: "mut-base", text: "Base" }),
        selBase,
      ]),
    ]),
    el("div", { class: "acoes" }, [btnAplicar, btnReverter, linkAlinhar]),
    regErro,
    regHist,
  ]);

  conteiner.appendChild(painel);
  atualizarControles();

  return {
    limparOrigens() {
      origens.seq1 = null;
      origens.seq2 = null;
      historico.length = 0;
      regErro.textContent = "";
      renderizarHistorico();
      atualizarControles();
    },
  };
}
