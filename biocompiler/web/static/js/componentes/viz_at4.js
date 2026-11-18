/* Visualização interativa da AT4 (preenchimento da matriz, inspetor /api/at4/celula, traceback e alinhamento). */

import { inspecionarCelula } from "../api.js";
import { el, limpar } from "../dom.js";
import { animar, movimentoReduzido } from "../motor/orquestrador.js";
import { NS_SVG } from "./viz_comum.js";

const LIMITE_GRADE_DOM = 10000;
const LIMITE_CANVAS_CELULAS = 1000000;

export function criarVizAT4(conteiner) {
  let envelope = null;
  let paramsScore = { match: 2, mismatch: -1, gap: -2 };
  let passoAtual = 1;
  let passos = [];
  let preenchidoCount = 0;
  let ultimaCelula = null;
  let celulaInspecionada = null;
  let cursor = { i: 0, j: 0 };
  let zoom = 1;
  let chaveSeqMontada = null;
  let todosAlinhamentos = [];
  let ladoALadoAtivo = false;
  let coordAtivaLadoALado = null;

  let palcoEl = null;
  let celulasDom = [];
  let gradeEmbrulho = null;
  let scrollMatrizEl = null;
  let ladoALadoEl = null;
  let botaoLadoALadoEl = null;
  let svgSetas = null;
  let svgDeps = null;
  let zoomLabelEl = null;

  let arrasteEstado = null;
  if (typeof window !== "undefined") {
    window.addEventListener("mousemove", (ev) => {
      if (!arrasteEstado) return;
      const dx = ev.clientX - arrasteEstado.x;
      const dy = ev.clientY - arrasteEstado.y;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) arrasteEstado.moveu = true;
      arrasteEstado.el.scrollLeft = arrasteEstado.sl - dx;
      arrasteEstado.el.scrollTop = arrasteEstado.st - dy;
    });
    window.addEventListener("mouseup", () => {
      if (!arrasteEstado) return;
      const { el: sc, moveu } = arrasteEstado;
      arrasteEstado = null;
      sc.classList.remove("arrastando");
      if (moveu) {
        sc.dataset.arrasteRecente = "1";
        setTimeout(() => { delete sc.dataset.arrasteRecente; }, 0);
      }
    });
  }
  let regPreenchimento = null;
  let regCelulaAtual = null;
  let regAlinhamento = null;
  let regInspetor = null;
  let regCursor = null;
  let canvasEl = null;
  let cacheCanvas = null;

  function calcularTamanho(dados) {
    const matriz = dados.matriz || [];
    const linhas = matriz.length;
    const colunas = linhas ? matriz[0].length : 0;
    return { linhas, colunas, total: linhas * colunas };
  }

  function calcularEstadoPasso(k) {
    const feitos = passos.slice(0, k);
    const evAtual = passos[k - 1] || null;
    const idxMat = passos.findIndex((e) => e.tipo === "MATRIZ_PREENCHIDA");
    const emPreenchimento = Boolean(evAtual && evAtual.tipo === "MATRIZ_PREENCHIDA");
    const aposPreenchimento = idxMat >= 0 && k - 1 > idxMat;

    const temInicioTb = feitos.some((e) => e.tipo === "INICIO_TRACEBACK");
    const passosTb = feitos.filter((e) => e.tipo === "TRACEBACK_PASSO").length;
    const colsAlinhamento = feitos.filter(
      (e) => e.tipo === "TRACEBACK_PASSO" && !(e.detalhe || "").endsWith("·")
    ).length;

    return {
      feitos,
      evAtual,
      emPreenchimento,
      aposPreenchimento,
      temInicioTb,
      passosTb,
      colsAlinhamento,
    };
  }

  function celulaEstaRevelada(i, j, colunas, est) {
    if (i === 0 || j === 0) return true;
    if (est.aposPreenchimento) return true;
    if (!est.emPreenchimento) return false;
    const ordem = (i - 1) * (colunas - 1) + j;
    return ordem <= preenchidoCount;
  }

  async function consultarCelula(i, j) {
    celulaInspecionada = [i, j];
    desenharDependencias(i, j);
    if (!envelope || !regInspetor) return;
    const dados = envelope.dados || {};
    limpar(regInspetor);
    regInspetor.appendChild(el("h3", { text: `Inspetor de célula (${dados.metodo || ""})` }));
    regInspetor.appendChild(el("p", { class: "mono", text: `Célula (${i}, ${j}) — consultando API…` }));

    try {
      const resp = await inspecionarCelula({
        seq1: dados.seq1 || "",
        seq2: dados.seq2 || "",
        alinhamento: dados.metodo || "local",
        match: paramsScore.match,
        mismatch: paramsScore.mismatch,
        gap: paramsScore.gap,
        i,
        j,
      });
      limpar(regInspetor);
      regInspetor.appendChild(el("h3", { text: `Inspetor de célula (${resp.metodo})` }));
      regInspetor.appendChild(el("div", { class: "barra-ferramentas" }, [
        el("span", { class: "chip mono", text: `Célula (${resp.i}, ${resp.j})` }),
        el("span", { class: "chip mono", text: `Valor: ${resp.valor}` }),
        el("span", { class: "chip mono", text: `Direção: ${resp.direcao || "·"}` }),
      ]));

      const cands = resp.candidatos || [];
      if (!cands.length) {
        regInspetor.appendChild(el("p", { class: "texto-suave", text: "Célula de borda" }));
        return;
      }

      const lista = el("ul", { class: "timeline" });
      let maxVal = -Infinity;
      for (const c of cands) {
        if (c.valor > maxVal) maxVal = c.valor;
      }
      let qtdMax = 0;
      for (const c of cands) {
        if (c.valor === maxVal) qtdMax += 1;
        lista.appendChild(el("li", { class: "timeline-item" }, [
          el("strong", { class: "mono", text: `${c.nome}: ` }),
          el("span", { class: "mono", text: String(c.valor) }),
        ]));
      }
      regInspetor.appendChild(lista);
      regInspetor.appendChild(el("p", {
        class: "texto-suave",
        text: qtdMax > 1
          ? "Empate resolvido pela regra: diagonal > vertical > horizontal"
          : "Regra de desempate: diagonal > vertical > horizontal",
      }));
    } catch (err) {
      limpar(regInspetor);
      regInspetor.appendChild(el("h3", { text: "Inspetor de célula" }));
      regInspetor.appendChild(el("p", { class: "barra-status erro", text: err.message }));
    }
  }

  function desenharDependencias(i, j, vencedor = null) {
    if (!svgDeps || !gradeEmbrulho) return;
    limpar(svgDeps);
    if (!Number.isInteger(i) || !Number.isInteger(j) || i < 1 || j < 1) return;
    const tdDest = celulasDom[i] && celulasDom[i][j];
    if (!tdDest) return;

    const specs = [
      { tipo: "diagonal", oi: i - 1, oj: j - 1, curva: -10 },
      { tipo: "vertical", oi: i - 1, oj: j, curva: 8 },
      { tipo: "horizontal", oi: i, oj: j - 1, curva: -8 },
    ];

    const x2 = tdDest.offsetLeft + tdDest.offsetWidth / 2;
    const y2 = tdDest.offsetTop + tdDest.offsetHeight / 2;

    for (const sp of specs) {
      const tdOrig = celulasDom[sp.oi] && celulasDom[sp.oi][sp.oj];
      if (!tdOrig) continue;
      const x1 = tdOrig.offsetLeft + tdOrig.offsetWidth / 2;
      const y1 = tdOrig.offsetTop + tdOrig.offsetHeight / 2;
      const mx = (x1 + x2) / 2 + (sp.tipo === "vertical" ? sp.curva : 0);
      const my = (y1 + y2) / 2 + (sp.tipo !== "vertical" ? sp.curva : 0);
      const path = document.createElementNS(NS_SVG, "path");
      path.setAttribute("d", `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`);
      path.setAttribute("class", `at4-dep-curva at4-dep-${sp.tipo}${vencedor === sp.tipo ? " at4-dep-vencedora" : ""}`);
      path.setAttribute("data-dependencia", sp.tipo);
      path.setAttribute("data-de", `${sp.oi},${sp.oj}`);
      svgDeps.appendChild(path);

      if (!movimentoReduzido() && typeof path.getTotalLength === "function") {
        const comp = path.getTotalLength() || 60;
        path.style.strokeDasharray = `${comp}`;
        path.style.strokeDashoffset = `${comp}`;
        animar(path, [
          { strokeDashoffset: comp, opacity: 0.3 },
          { strokeDashoffset: 0, opacity: 0.95 },
        ], { duration: 200, fill: "forwards" });
      }
    }
  }

  function desenharSetas(caminhoVisivel) {
    if (!svgSetas || !gradeEmbrulho) return;
    limpar(svgSetas);
    if (caminhoVisivel.length < 2) return;

    const defs = document.createElementNS(NS_SVG, "defs");
    const marker = document.createElementNS(NS_SVG, "marker");
    marker.setAttribute("id", "seta-at4");
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "7");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "5");
    marker.setAttribute("markerHeight", "5");
    marker.setAttribute("orient", "auto-start-reverse");
    const path = document.createElementNS(NS_SVG, "path");
    path.setAttribute("d", "M 0 1 L 10 5 L 0 9 z");
    path.setAttribute("fill", "var(--cor-alinhamento)");
    marker.appendChild(path);
    defs.appendChild(marker);
    svgSetas.appendChild(defs);

    const usaMedicao = gradeEmbrulho.offsetWidth > 0;
    for (let idx = 1; idx < caminhoVisivel.length; idx += 1) {
      const [i1, j1] = caminhoVisivel[idx - 1];
      const [i2, j2] = caminhoVisivel[idx];
      const di = i1 - i2;
      const dj = j1 - j2;
      const direcao = di === 1 && dj === 1
        ? "diagonal"
        : di === 1 && dj === 0
          ? "vertical"
          : "horizontal";

      const td1 = celulasDom[i1] && celulasDom[i1][j1];
      const td2 = celulasDom[i2] && celulasDom[i2][j2];
      const x1 = usaMedicao && td1 ? td1.offsetLeft + td1.offsetWidth / 2 : (j1 + 1) * 44 + 22;
      const y1 = usaMedicao && td1 ? td1.offsetTop + td1.offsetHeight / 2 : (i1 + 1) * 32 + 16;
      const x2 = usaMedicao && td2 ? td2.offsetLeft + td2.offsetWidth / 2 : (j2 + 1) * 44 + 22;
      const y2 = usaMedicao && td2 ? td2.offsetTop + td2.offsetHeight / 2 : (i2 + 1) * 32 + 16;

      const line = document.createElementNS(NS_SVG, "line");
      line.setAttribute("class", `at4-seta-linha at4-seta-${direcao}`);
      line.setAttribute("data-seta", "");
      line.setAttribute("data-de", `${i1},${j1}`);
      line.setAttribute("data-para", `${i2},${j2}`);
      line.setAttribute("data-direcao", direcao);
      line.setAttribute("x1", String(x1));
      line.setAttribute("y1", String(y1));
      line.setAttribute("x2", String(x2));
      line.setAttribute("y2", String(y2));
      line.setAttribute("marker-end", "url(#seta-at4)");
      svgSetas.appendChild(line);
    }
  }

  function atualizarAlinhamento(dados, est) {
    if (!regAlinhamento) return;
    limpar(regAlinhamento);
    regAlinhamento.appendChild(el("div", { class: "barra-ferramentas" }, [
      el("h3", { text: "Alinhamento reconstruído" }),
      el("span", { class: "chip mono", text: `Score: ${dados.score} ` }),
    ]));

    if (dados.observacao && !(dados.caminho && dados.caminho.length)) {
      regAlinhamento.appendChild(el("p", { class: "texto-suave", text: dados.observacao }));
      return;
    }

    const a1 = dados.alinhado1 || "";
    const mk = dados.marcadores || "";
    const a2 = dados.alinhado2 || "";
    const total = a1.length;
    const t = Math.min(total, est.colsAlinhamento);
    if (t <= 0) {
      regAlinhamento.appendChild(el("p", {
        class: "texto-suave",
        text: "Avance para o traceback para reconstruir o alinhamento coluna a coluna.",
      }));
      return;
    }

    const colsEl = el("div", { class: "alinhamento-colunas" });
    for (let idx = total - t; idx < total; idx += 1) {
      const ca = a1[idx] || "";
      const cm = mk[idx] || " ";
      const cb = a2[idx] || "";
      const clsTipo = cm === "|" ? "col-match" : (ca === "-" || cb === "-" ? "col-gap" : "col-mismatch");
      colsEl.appendChild(el("div", {
        class: `alinhamento-col ${clsTipo}`,
        "data-coluna": "",
        "data-a": ca,
        "data-m": cm,
        "data-b": cb,
      }, [
        el("span", { text: ca }),
        el("span", { text: cm === " " ? "\u00a0" : cm }),
        el("span", { text: cb }),
      ]));
    }
    regAlinhamento.appendChild(colsEl);
  }

  function atualizarCanvas(dados, est) {
    if (!canvasEl) return;
    const { linhas, colunas } = calcularTamanho(dados);
    const passoPx = linhas > 300 || colunas > 300 ? 2 : (linhas > 100 || colunas > 100 ? 4 : 6);
    const w = colunas * passoPx;
    const h = linhas * passoPx;
    if (canvasEl.width !== w || canvasEl.height !== h) {
      canvasEl.width = w;
      canvasEl.height = h;
      cacheCanvas = null;
    }

    const ctx = canvasEl.getContext("2d");
    if (!ctx) return;

    const matriz = dados.matriz || [];
    const caminho = dados.caminho || [];
    const caminhoVis = est.passosTb ? caminho.slice(0, est.passosTb) : [];
    const chaveEstado = `${dados.metodo}-${passoAtual}-${preenchidoCount}`;

    if (!cacheCanvas || cacheCanvas.chave !== chaveEstado) {
      const off = document.createElement("canvas");
      off.width = w;
      off.height = h;
      const octx = off.getContext("2d");
      let maxVal = 1;
      for (let i = 0; i < linhas; i += 1) {
        for (let j = 0; j < colunas; j += 1) {
          if (matriz[i][j] > maxVal) maxVal = matriz[i][j];
        }
      }
      for (let i = 0; i < linhas; i += 1) {
        for (let j = 0; j < colunas; j += 1) {
          const rev = celulaEstaRevelada(i, j, colunas, est);
          if (!rev) {
            octx.fillStyle = "#161b26";
          } else {
            const norm = Math.max(0, Math.min(1, matriz[i][j] / maxVal));
            const alpha = (0.12 + norm * 0.55).toFixed(2);
            octx.fillStyle = `rgba(56, 189, 248, ${alpha})`;
          }
          octx.fillRect(j * passoPx, i * passoPx, passoPx, passoPx);
        }
      }
      octx.fillStyle = "#f59e0b";
      for (const [ci, cj] of caminhoVis) {
        octx.fillRect(cj * passoPx, ci * passoPx, passoPx, passoPx);
      }
      cacheCanvas = { chave: chaveEstado, canvas: off };
    }

    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(cacheCanvas.canvas, 0, 0);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(cursor.j * passoPx, cursor.i * passoPx, passoPx, passoPx);

    if (regCursor) {
      regCursor.textContent = `Linha ${cursor.i}, coluna ${cursor.j}, valor ${matriz[cursor.i][cursor.j]}`;
    }
  }

  function atualizarGradeDom(dados, est) {
    const { linhas, colunas } = calcularTamanho(dados);
    const matriz = dados.matriz || [];
    const direcoes = dados.direcoes || [];
    const caminho = dados.caminho || [];
    const temCaminhoReal = caminho.length > 0;
    const caminhoVisivel = temCaminhoReal && est.passosTb ? caminho.slice(0, est.passosTb) : [];
    const caminhoSet = new Set(caminhoVisivel.map(([ci, cj]) => `${ci},${cj}`));
    const inicioTb = temCaminhoReal && est.temInicioTb && dados.inicio_traceback
      ? `${dados.inicio_traceback[0]},${dados.inicio_traceback[1]}`
      : null;

    let maxPos = 1;
    for (let i = 0; i < linhas; i += 1) {
      for (let j = 0; j < colunas; j += 1) {
        if (matriz[i][j] > maxPos) maxPos = matriz[i][j];
      }
    }

    for (let i = 0; i < linhas; i += 1) {
      for (let j = 0; j < colunas; j += 1) {
        const td = celulasDom[i] && celulasDom[i][j];
        if (!td) continue;
        const rev = celulaEstaRevelada(i, j, colunas, est);
        td.setAttribute("data-revelada", rev ? "true" : "false");
        if (rev) {
          const dir = direcoes[i] && direcoes[i][j] ? direcoes[i][j] : "";
          const mostrarSeta = passoAtual > 1 || (i > 0 && j > 0);
          const setaTxt = mostrarSeta && dir && dir !== " " && dir !== "·" ? ` ${dir}` : "";
          const val = matriz[i][j];
          td.textContent = `${val}${setaTxt}`;
          const calor = val < 0
            ? 0
            : val === 0
              ? 1
              : Math.min(4, 2 + Math.floor((val / Math.max(1, maxPos)) * 2.99));
          for (let c = 0; c <= 4; c += 1) {
            td.classList.toggle(`at4-calor-${c}`, c === calor);
          }
        } else {
          td.textContent = "·";
          for (let c = 0; c <= 4; c += 1) {
            td.classList.remove(`at4-calor-${c}`);
          }
        }
        const key = `${i},${j}`;
        if (inicioTb === key) td.setAttribute("data-traceback-inicio", "");
        else td.removeAttribute("data-traceback-inicio");

        if (caminhoSet.has(key)) td.setAttribute("data-caminho", "");
        else td.removeAttribute("data-caminho");

        const ehAtual = ultimaCelula && ultimaCelula[0] === i && ultimaCelula[1] === j;
        const ehDep = ultimaCelula && (
          (i === ultimaCelula[0] - 1 && j === ultimaCelula[1] - 1)
          || (i === ultimaCelula[0] - 1 && j === ultimaCelula[1])
          || (i === ultimaCelula[0] && j === ultimaCelula[1] - 1)
        );
        td.classList.toggle("at4-celula-atual", Boolean(ehAtual));
        td.classList.toggle("at4-dep", Boolean(ehDep));
      }
    }

    desenharSetas(caminhoVisivel);
  }

  function atualizarControlesPreenchimento(dados, est) {
    if (!regPreenchimento) return;
    const { linhas, colunas } = calcularTamanho(dados);
    const maxInterior = Math.max(0, (linhas - 1) * (colunas - 1));
    const tudoRevelado = est.aposPreenchimento || (maxInterior > 0 && preenchidoCount >= maxInterior);
    regPreenchimento.hidden = !est.emPreenchimento;
    if (regCelulaAtual) {
      if (tudoRevelado) {
        regCelulaAtual.textContent = "Matriz completa";
      } else if (ultimaCelula && est.emPreenchimento) {
        regCelulaAtual.textContent = `Célula (${ultimaCelula[0]}, ${ultimaCelula[1]})`;
      } else {
        regCelulaAtual.textContent = "Bordas inicializadas";
      }
    }
    const btnCel = regPreenchimento.querySelector('[data-acao="celula-proxima"]');
    const btnLin = regPreenchimento.querySelector('[data-acao="linha-proxima"]');
    const btnTudo = regPreenchimento.querySelector('[data-acao="preencher-tudo"]');
    const esgotado = preenchidoCount >= maxInterior;
    if (btnCel) btnCel.disabled = esgotado;
    if (btnLin) btnLin.disabled = esgotado;
    if (btnTudo) btnTudo.disabled = esgotado;
  }

  function obterParLadoALado() {
    const porMetodo = new Map();
    for (const item of todosAlinhamentos) {
      const m = item && item.dados ? item.dados.metodo : null;
      if ((m === "local" || m === "global") && !porMetodo.has(m)) {
        porMetodo.set(m, item);
      }
    }
    if (!porMetodo.has("local") || !porMetodo.has("global")) return null;
    return { local: porMetodo.get("local"), global: porMetodo.get("global") };
  }

  function destacarCoordLadoALado(i, j) {
    coordAtivaLadoALado = { i, j };
    if (!ladoALadoEl) return;
    ladoALadoEl.querySelectorAll("[data-coordenada-ativa]").forEach((td) => {
      td.removeAttribute("data-coordenada-ativa");
    });
    ladoALadoEl.querySelectorAll(`[data-celula][data-i="${i}"][data-j="${j}"]`).forEach((td) => {
      td.setAttribute("data-coordenada-ativa", "true");
    });
  }

  function construirTabelaComparacao(item, metodo) {
    const dados = item && item.dados ? item.dados : {};
    const matriz = dados.matriz || [];
    const seq1 = dados.seq1 || "";
    const seq2 = dados.seq2 || "";
    const total = matriz.length * (matriz[0] ? matriz[0].length : 0);
    const secao = el("section", { class: "at4-grade-comp", "data-grade-metodo": metodo }, [
      el("header", { class: "at4-grade-comp-cab" }, [
        el("strong", { text: metodo === "local" ? "Local (Smith–Waterman)" : "Global (Needleman–Wunsch)" }),
        el("span", { class: "badge", text: `Score ${dados.score ?? "—"}` }),
      ]),
    ]);
    if (total > 10000) {
      secao.appendChild(el("p", {
        class: "texto-suave",
        text: `Grade com ${total.toLocaleString("pt-BR")} células excede o limite de 10 000 células para comparação lado a lado.`,
      }));
      return secao;
    }
    const tbody = el("tbody");
    const trCab = el("tr", {}, [el("th", { text: "" }), el("th", { text: "−" })]);
    for (let j = 0; j < seq2.length; j += 1) {
      trCab.appendChild(el("th", { text: seq2[j] }));
    }
    const thead = el("thead", {}, [trCab]);
    for (let i = 0; i < matriz.length; i += 1) {
      const tr = el("tr");
      tr.appendChild(el("th", { text: i === 0 ? "−" : (seq1[i - 1] || "") }));
      const linha = matriz[i] || [];
      for (let j = 0; j < linha.length; j += 1) {
        const val = linha[j];
        const td = el("td", {
          class: "at4-comp-cel",
          "data-celula": "",
          "data-i": String(i),
          "data-j": String(j),
          text: String(val),
          onClick: () => destacarCoordLadoALado(i, j),
        });
        if (coordAtivaLadoALado && coordAtivaLadoALado.i === i && coordAtivaLadoALado.j === j) {
          td.setAttribute("data-coordenada-ativa", "true");
        }
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    const scroll = el("div", { class: "at4-grade-comp-scroll" }, [
      el("table", { class: "at4-comp-tabela" }, [thead, tbody]),
    ]);
    secao.appendChild(scroll);
    return secao;
  }

  function atualizarLadoALado() {
    if (!ladoALadoEl) return;
    limpar(ladoALadoEl);
    const par = obterParLadoALado();
    if (botaoLadoALadoEl) {
      botaoLadoALadoEl.hidden = !par;
      botaoLadoALadoEl.setAttribute("aria-pressed", String(Boolean(par && ladoALadoAtivo)));
    }
    if (!par || !ladoALadoAtivo) {
      ladoALadoEl.hidden = true;
      if (scrollMatrizEl) scrollMatrizEl.hidden = false;
      return;
    }
    ladoALadoEl.hidden = false;
    if (scrollMatrizEl) scrollMatrizEl.hidden = true;
    ladoALadoEl.appendChild(construirTabelaComparacao(par.local, "local"));
    ladoALadoEl.appendChild(construirTabelaComparacao(par.global, "global"));
  }

  function construirCena() {
    limpar(conteiner);
    celulasDom = [];
    gradeEmbrulho = null;
    scrollMatrizEl = null;
    ladoALadoEl = null;
    botaoLadoALadoEl = null;
    svgSetas = null;
    svgDeps = null;
    palcoEl = null;
    canvasEl = null;
    cacheCanvas = null;

    if (!envelope) return;
    const dados = envelope.dados || {};
    const { linhas, colunas, total } = calcularTamanho(dados);

    const palco = el("div", {
      class: "viz-palco",
      "data-viz": "at4",
      "data-alinhamento": dados.metodo || "",
    });
    palcoEl = palco;

    if (total > LIMITE_CANVAS_CELULAS) {
      palco.appendChild(el("div", { class: "barra-status", "data-regiao": "aviso-matriz" }, [
        `Matriz com ${total} células excede o limite de exibição célula a célula (${LIMITE_CANVAS_CELULAS} células). Score, alinhamento e exportação permanecem disponíveis.`,
      ]));
      regAlinhamento = el("div", { "data-regiao": "alinhamento-viz" });
      palco.appendChild(regAlinhamento);
      conteiner.appendChild(palco);
      return;
    }

    regCelulaAtual = el("span", { class: "chip mono", "data-regiao": "celula-atual" });
    regPreenchimento = el("div", {
      class: "at4-preenchimento-barra",
      "data-componente": "preenchimento",
      hidden: true,
    }, [
      regCelulaAtual,
      el("div", { class: "barra-ferramentas" }, [
        el("button", {
          type: "button",
          class: "btn btn-pequeno",
          "data-acao": "celula-proxima",
          text: "Próxima célula",
          onClick: () => {
            const maxInt = (linhas - 1) * (colunas - 1);
            if (preenchidoCount < maxInt) {
              preenchidoCount += 1;
              const i = Math.floor((preenchidoCount - 1) / (colunas - 1)) + 1;
              const j = ((preenchidoCount - 1) % (colunas - 1)) + 1;
              ultimaCelula = [i, j];
              atualizar(passoAtual, passos);
              consultarCelula(i, j);
            }
          },
        }),
        el("button", {
          type: "button",
          class: "btn btn-pequeno",
          "data-acao": "linha-proxima",
          text: "Completar linha",
          onClick: () => {
            const maxInt = (linhas - 1) * (colunas - 1);
            if (preenchidoCount < maxInt) {
              const linhaAtual = Math.floor(preenchidoCount / (colunas - 1)) + 1;
              preenchidoCount = Math.min(maxInt, linhaAtual * (colunas - 1));
              ultimaCelula = [linhaAtual, colunas - 1];
              atualizar(passoAtual, passos);
              consultarCelula(linhaAtual, colunas - 1);
            }
          },
        }),
        el("button", {
          type: "button",
          class: "btn btn-pequeno",
          "data-acao": "preencher-tudo",
          text: "Preencher tudo",
          onClick: () => {
            preenchidoCount = (linhas - 1) * (colunas - 1);
            ultimaCelula = [linhas - 1, colunas - 1];
            atualizar(passoAtual, passos);
            consultarCelula(linhas - 1, colunas - 1);
          },
        }),
      ]),
    ]);
    palco.appendChild(regPreenchimento);

    if (total > LIMITE_GRADE_DOM) {
      chaveSeqMontada = null;
      regCursor = el("div", {
        class: "chip mono",
        "data-regiao": "cursor-matriz",
        "aria-live": "polite",
      });
      canvasEl = el("canvas", {
        class: "canvas-at4",
        "data-matriz": "",
        "data-linhas": String(linhas),
        "data-colunas": String(colunas),
        tabindex: "0",
        "aria-label": `Matriz ${linhas} por ${colunas} (${dados.metodo})`,
        onKeydown: (ev) => {
          let mudou = false;
          if (ev.key === "ArrowRight") { cursor.j = Math.min(colunas - 1, cursor.j + 1); mudou = true; }
          else if (ev.key === "ArrowLeft") { cursor.j = Math.max(0, cursor.j - 1); mudou = true; }
          else if (ev.key === "ArrowDown") { cursor.i = Math.min(linhas - 1, cursor.i + 1); mudou = true; }
          else if (ev.key === "ArrowUp") { cursor.i = Math.max(0, cursor.i - 1); mudou = true; }
          else if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            consultarCelula(cursor.i, cursor.j);
            return;
          }
          if (mudou) {
            ev.preventDefault();
            atualizarCanvas(dados, calcularEstadoPasso(passoAtual));
          }
        },
      });
      palco.appendChild(regCursor);
      if (obterParLadoALado()) {
        palco.appendChild(el("p", {
          class: "barra-status",
          "data-aviso": "lado-a-lado",
          text: `Vista lado a lado indisponível acima de 10 000 células por método (${total.toLocaleString("pt-BR")} células; modo Canvas ativo).`,
        }));
      }
      palco.appendChild(el("div", { class: "matriz-scroll" }, [canvasEl]));
    } else {
      const seq1 = dados.seq1 || "";
      const seq2 = dados.seq2 || "";
      chaveSeqMontada = `${seq1}|${seq2}`;
      const thead = el("thead", {}, [
        el("tr", {}, [
          el("th", { text: "" }),
          el("th", { text: "—" }),
          ...seq2.split("").map((b) => el("th", { "data-cabecalho-seq": "", text: b })),
        ]),
      ]);
      const tbody = el("tbody");
      celulasDom = Array.from({ length: linhas }, () => Array(colunas).fill(null));

      const focarCelula = (ni, nj) => {
        const alvo = celulasDom[ni] && celulasDom[ni][nj];
        if (!alvo) return;
        for (const row of celulasDom) {
          for (const cell of row) {
            if (cell) cell.setAttribute("tabindex", "-1");
          }
        }
        alvo.setAttribute("tabindex", "0");
        alvo.focus();
      };

      for (let i = 0; i < linhas; i += 1) {
        const tr = el("tr");
        tr.appendChild(el("th", i === 0 ? { text: "—" } : { "data-cabecalho-seq": "", text: seq1[i - 1] }));
        for (let j = 0; j < colunas; j += 1) {
          const td = el("td", {
            role: "gridcell",
            "data-celula": "",
            "data-i": String(i),
            "data-j": String(j),
            "data-revelada": "false",
            tabindex: i === 0 && j === 0 ? "0" : "-1",
            onClick: () => {
              focarCelula(i, j);
              ultimaCelula = [i, j];
              consultarCelula(i, j);
            },
            onKeydown: (ev) => {
              if (ev.key === "ArrowDown") { ev.preventDefault(); focarCelula(Math.min(linhas - 1, i + 1), j); }
              else if (ev.key === "ArrowUp") { ev.preventDefault(); focarCelula(Math.max(0, i - 1), j); }
              else if (ev.key === "ArrowRight") { ev.preventDefault(); focarCelula(i, Math.min(colunas - 1, j + 1)); }
              else if (ev.key === "ArrowLeft") { ev.preventDefault(); focarCelula(i, Math.max(0, j - 1)); }
              else if (ev.key === "Enter" || ev.key === " ") {
                ev.preventDefault();
                ultimaCelula = [i, j];
                consultarCelula(i, j);
              }
            },
          });
          celulasDom[i][j] = td;
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }

      const tabela = el("table", { class: "tabela-matriz", role: "grid" }, [thead, tbody]);
      svgSetas = document.createElementNS(NS_SVG, "svg");
      svgSetas.setAttribute("class", "at4-setas-svg");
      svgDeps = document.createElementNS(NS_SVG, "svg");
      svgDeps.setAttribute("class", "at4-deps-svg");
      svgDeps.setAttribute("aria-hidden", "true");
      gradeEmbrulho = el("div", { class: "at4-grade-embrulho" }, [tabela, svgSetas, svgDeps]);
      gradeEmbrulho.style.setProperty("--at4-zoom", String(zoom));

      const aplicarZoom = (novoZoom) => {
        zoom = Math.max(0.7, Math.min(2.2, Math.round(novoZoom * 100) / 100));
        if (gradeEmbrulho) gradeEmbrulho.style.setProperty("--at4-zoom", String(zoom));
        if (zoomLabelEl) zoomLabelEl.textContent = `${Math.round(zoom * 100)}%`;
        if (envelope) {
          const est = calcularEstadoPasso(passoAtual);
          desenharSetas((envelope.dados.caminho || []).slice(0, est.passosTb));
          if (celulaInspecionada) desenharDependencias(celulaInspecionada[0], celulaInspecionada[1]);
        }
      };

      zoomLabelEl = el("span", { class: "chip mono", text: `${Math.round(zoom * 100)}%` });
      const temPar = Boolean(obterParLadoALado());
      botaoLadoALadoEl = el("button", {
        type: "button",
        class: "btn btn-pequeno",
        "data-acao": "lado-a-lado",
        "aria-pressed": String(ladoALadoAtivo),
        hidden: !temPar,
        text: "Lado a lado",
        onClick: () => {
          ladoALadoAtivo = !ladoALadoAtivo;
          atualizarLadoALado();
        },
      });
      palco.appendChild(el("div", { class: "at4-barra-zoom" }, [
        el("span", { class: "texto-suave", text: "Clique em uma célula para inspecionar dependências ou arraste a grade." }),
        el("div", { class: "at4-zoom-controles" }, [
          botaoLadoALadoEl,
          el("button", {
            type: "button",
            class: "btn btn-pequeno",
            "data-acao": "zoom-menos",
            "aria-label": "Reduzir zoom da matriz",
            text: "−",
            onClick: () => aplicarZoom(zoom - 0.2),
          }),
          zoomLabelEl,
          el("button", {
            type: "button",
            class: "btn btn-pequeno",
            "data-acao": "zoom-mais",
            "aria-label": "Ampliar zoom da matriz",
            text: "+",
            onClick: () => aplicarZoom(zoom + 0.2),
          }),
        ]),
      ]));

      if (typeof window.ResizeObserver === "function") {
        const ro = new window.ResizeObserver(() => {
          if (!envelope) return;
          const est = calcularEstadoPasso(passoAtual);
          const cam = (envelope.dados.caminho || []).slice(0, est.passosTb);
          desenharSetas(cam);
          if (celulaInspecionada) desenharDependencias(celulaInspecionada[0], celulaInspecionada[1]);
        });
        ro.observe(gradeEmbrulho);
      }

      const scrollMatriz = el("div", { class: "matriz-scroll" }, [gradeEmbrulho]);
      scrollMatrizEl = scrollMatriz;
      scrollMatriz.addEventListener("mousedown", (ev) => {
        if (ev.button !== 0) return;
        arrasteEstado = {
          el: scrollMatriz,
          x: ev.clientX,
          y: ev.clientY,
          sl: scrollMatriz.scrollLeft,
          st: scrollMatriz.scrollTop,
          moveu: false,
        };
        scrollMatriz.classList.add("arrastando");
      });
      scrollMatriz.addEventListener("click", (ev) => {
        if (scrollMatriz.dataset.arrasteRecente === "1") {
          ev.stopPropagation();
          ev.preventDefault();
          delete scrollMatriz.dataset.arrasteRecente;
        }
      }, true);
      scrollMatriz.addEventListener("wheel", (ev) => {
        if (!ev.ctrlKey) return;
        ev.preventDefault();
        aplicarZoom(zoom + (ev.deltaY < 0 ? 0.15 : -0.15));
      }, { passive: false });
      palco.appendChild(scrollMatriz);
      ladoALadoEl = el("div", { class: "at4-lado-a-lado", hidden: true });
      palco.appendChild(ladoALadoEl);
      atualizarLadoALado();
    }

    regAlinhamento = el("div", { "data-regiao": "alinhamento-viz" });
    palco.appendChild(regAlinhamento);

    regInspetor = el("aside", { class: "inspetor-painel", "data-regiao": "inspetor-celula", "data-superficie": "vidro" }, [
      el("h3", { text: "Inspetor de célula" }),
      el("p", { class: "texto-suave", text: "Clique ou use as setas e Enter em qualquer célula para consultar /api/at4/celula." }),
    ]);

    conteiner.appendChild(el("div", { class: "viz-grade" }, [palco, regInspetor]));
  }

  function definirAlinhamento(novoEnv, novosParams, novosItens) {
    const dados = novoEnv && novoEnv.dados ? novoEnv.dados : {};
    const { total } = calcularTamanho(dados);
    const novaChave = `${dados.seq1 || ""}|${dados.seq2 || ""}`;
    if (Array.isArray(novosItens) && novosItens.length) {
      todosAlinhamentos = novosItens;
    } else if (!todosAlinhamentos.length && novoEnv) {
      todosAlinhamentos = [novoEnv];
    }
    const podeReusar = Boolean(
      gradeEmbrulho
      && total <= LIMITE_GRADE_DOM
      && chaveSeqMontada === novaChave
      && celulasDom.length === (dados.matriz || []).length
    );
    envelope = novoEnv;
    paramsScore = novosParams || paramsScore;
    passos = (envelope && envelope.passos) || [];
    preenchidoCount = 0;
    ultimaCelula = null;
    celulaInspecionada = null;
    cursor = { i: 0, j: 0 };
    if (podeReusar) {
      if (palcoEl) palcoEl.setAttribute("data-alinhamento", dados.metodo || "");
      if (svgDeps) limpar(svgDeps);
      atualizarLadoALado();
      return;
    }
    ladoALadoAtivo = false;
    coordAtivaLadoALado = null;
    construirCena();
  }

  function atualizar(k, novosPassos) {
    passoAtual = k;
    passos = novosPassos || passos;
    if (!envelope) return;
    const dados = envelope.dados || {};
    const est = calcularEstadoPasso(k);
    if (k <= 1) {
      preenchidoCount = 0;
      ultimaCelula = null;
    } else if (est.aposPreenchimento) {
      const { linhas, colunas } = calcularTamanho(dados);
      preenchidoCount = Math.max(0, (linhas - 1) * (colunas - 1));
    }

    atualizarControlesPreenchimento(dados, est);
    const { total } = calcularTamanho(dados);
    if (total <= LIMITE_GRADE_DOM) {
      atualizarGradeDom(dados, est);
    } else if (total <= LIMITE_CANVAS_CELULAS) {
      atualizarCanvas(dados, est);
    }
    atualizarAlinhamento(dados, est);
  }

  return { definirAlinhamento, atualizar };
}
