/* Visualização SVG interativa da AT1 (Transcrição DNA -> pré-mRNA). */

import { el, limpar } from "../dom.js";
import {
  PASSO_X,
  TAM_JANELA,
  criarBarraJanela,
  criarMarcaSvg,
  preencherFitaBases,
  svgEl,
  ultimoEventoComPosicao,
} from "./viz_comum.js";

export function criarVizAT1(conteiner, onInspecionar) {
  let registro = null;
  let passoAtual = 1;
  let passos = [];
  let janelaIdx = 0;

  function desenhar() {
    limpar(conteiner);
    if (!registro) return;
    const dados = registro.dados || {};
    const seq = (registro.entrada && registro.entrada.sequencia) || "";
    const pre = dados.pre_mrna || "";
    const feitos = passos.slice(0, passoAtual);
    const eventoAtual = passos[passoAtual - 1] || null;
    const tipos = new Set(feitos.map((e) => e.tipo));

    const total = seq.length;
    const ini = janelaIdx * TAM_JANELA;
    const fim = Math.min(total, ini + TAM_JANELA);

    const raiz = el("div", { class: "viz-palco", "data-viz": "at1" });
    raiz.appendChild(el("div", { class: "viz-legenda" }, [
      el("span", { class: "selo selo-ok", text: "START (início)" }),
      el("span", { class: "selo selo-erro", text: "STOP em fase" }),
      el("span", { class: "chip", text: "STOP fora de fase" }),
      el("span", { class: "chip", text: "Troca T → U" }),
    ]));

    const barraJanela = criarBarraJanela(total, janelaIdx, (novoIdx) => {
      janelaIdx = novoIdx;
      desenhar();
    });
    if (barraJanela) raiz.appendChild(barraJanela);

    const largura = Math.max(320, (fim - ini) * PASSO_X + 24);
    const altura = pre ? 168 : 112;
    const svg = svgEl("svg", {
      class: "viz-svg",
      width: largura,
      height: altura,
      viewBox: `0 0 ${largura} ${altura}`,
      role: "img",
      "aria-label": "Fita de DNA e transcrição para pré-mRNA",
    });

    const yMarcas = 6;
    const yDna = 44;
    const yPre = 110;

    // Regiões UTR e caixas de códons (no fundo)
    const pStart = dados.posicao_start;
    const pStop = dados.posicao_stop;
    if (pStart !== null && pStart !== undefined && pStart > 0) {
      const uIni = Math.max(ini, 0);
      const uFim = Math.min(fim, pStart);
      if (uFim > uIni) {
        svg.appendChild(svgEl("rect", {
          x: 10 + (uIni - ini) * PASSO_X,
          y: yDna - 4,
          width: (uFim - uIni) * PASSO_X,
          height: 34,
          class: "svg-utr",
          "data-regiao-fita": "utr5",
        }));
      }
    }
    if (pStop !== null && pStop !== undefined && pStop + 3 < total) {
      const uIni = Math.max(ini, pStop + 3);
      const uFim = Math.min(fim, total);
      if (uFim > uIni) {
        svg.appendChild(svgEl("rect", {
          x: 10 + (uIni - ini) * PASSO_X,
          y: yDna - 4,
          width: (uFim - uIni) * PASSO_X,
          height: 34,
          class: "svg-utr",
          "data-regiao-fita": "utr3",
        }));
      }
    }

    const codons = dados.codons || [];
    if (pStart !== null && pStart !== undefined) {
      codons.forEach((_, idx) => {
        const cIni = pStart + idx * 3;
        const cFim = cIni + 3;
        if (cFim <= ini || cIni >= fim) return;
        const vIni = Math.max(ini, cIni);
        const vFim = Math.min(fim, cFim);
        const ehAtual = eventoAtual && eventoAtual.posicao === cIni;
        svg.appendChild(svgEl("rect", {
          x: 10 + (vIni - ini) * PASSO_X,
          y: yDna - 4,
          width: (vFim - vIni) * PASSO_X,
          height: 34,
          class: `svg-codon-caixa${ehAtual ? " atual" : ""}`,
          "data-codon": String(idx),
        }));
      });
    }

    // Fita DNA
    const grupoDna = svgEl("g", { "data-fita": "dna" });
    preencherFitaBases(grupoDna, seq, ini, fim, yDna, { onInspecionar, comRegua: true });
    svg.appendChild(grupoDna);

    // Marcadores sincronizados com os eventos já reproduzidos
    const grupoMarcas = svgEl("g", { "data-regiao": "marcas-at1" });
    if (tipos.has("START_ENCONTRADO") && pStart !== null && pStart !== undefined && pStart >= ini && pStart < fim) {
      const x = 12 + (pStart - ini) * PASSO_X + 12;
      grupoMarcas.appendChild(criarMarcaSvg(x, yMarcas, "START", "svg-marca-start", {
        "data-marca": "start",
        "data-indice": String(pStart),
      }, () => onInspecionar && onInspecionar(pStart)));
    }
    if ((tipos.has("STOP_EM_FASE") || tipos.has("STOP_ENCONTRADO"))
        && pStop !== null && pStop !== undefined && pStop >= ini && pStop < fim) {
      const x = 12 + (pStop - ini) * PASSO_X + 12;
      grupoMarcas.appendChild(criarMarcaSvg(x, yMarcas, "STOP", "svg-marca-stop", {
        "data-marca": "stop",
        "data-indice": String(pStop),
      }, () => onInspecionar && onInspecionar(pStop)));
    }
    const stopsForaVisiveis = new Set(
      feitos.filter((e) => e.tipo === "STOP_FORA_DE_FASE" && e.posicao !== null).map((e) => e.posicao)
    );
    for (const pos of stopsForaVisiveis) {
      if (pos >= ini && pos < fim) {
        const x = 12 + (pos - ini) * PASSO_X + 12;
        grupoMarcas.appendChild(criarMarcaSvg(x, yMarcas, "STOP*", "svg-marca-stop-fora", {
          "data-marca": "stop-fora",
          "data-indice": String(pos),
        }, () => onInspecionar && onInspecionar(pos)));
      }
    }
    const invalidasVisiveis = new Set(
      feitos.filter((e) => e.tipo === "BASE_INVALIDA" && e.posicao !== null).map((e) => e.posicao)
    );
    for (const pos of invalidasVisiveis) {
      if (pos >= ini && pos < fim) {
        const x = 12 + (pos - ini) * PASSO_X + 12;
        grupoMarcas.appendChild(criarMarcaSvg(x, yMarcas, "INV", "svg-marca-invalida", {
          "data-marca": "invalida",
          "data-indice": String(pos),
        }, () => onInspecionar && onInspecionar(pos)));
      }
    }
    svg.appendChild(grupoMarcas);

    // Fita pré-mRNA (quando existir)
    if (pre) {
      const trocasSet = new Set();
      if (tipos.has("T_PARA_U")) {
        for (let i = ini; i < Math.min(fim, pre.length); i += 1) {
          if (seq[i] !== pre[i]) trocasSet.add(i);
        }
      }
      const grupoPre = svgEl("g", { "data-fita": "pre-mrna" });
      preencherFitaBases(grupoPre, pre, ini, Math.min(fim, pre.length), yPre, {
        onInspecionar,
        trocasSet,
        comRegua: false,
      });
      svg.appendChild(grupoPre);
    }

    raiz.appendChild(el("div", { class: "fita-scroll" }, [svg]));
    conteiner.appendChild(raiz);
  }

  function definirRegistro(novoReg) {
    registro = novoReg;
    passos = (registro && registro.passos) || [];
    janelaIdx = 0;
  }

  function atualizar(k, novosPassos) {
    passoAtual = k;
    passos = novosPassos || passos;
    const pos = ultimoEventoComPosicao(passos, k);
    janelaIdx = pos !== null ? Math.floor(pos / TAM_JANELA) : 0;
    desenhar();
  }

  return { definirRegistro, atualizar };
}
