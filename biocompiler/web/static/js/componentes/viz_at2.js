/* Visualização SVG interativa da AT2 (SpliceLab: íntrons, régua D009, splicing e maturação). */

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

export function criarVizAT2(conteiner, onInspecionar) {
  let registro = null;
  let passoAtual = 1;
  let passos = [];
  let janelaIdx = 0;
  let caudaExpandida = false;

  function calcularEstadoGlobal(feitos) {
    const tipos = new Set(feitos.map((e) => e.tipo));
    if (tipos.has("POLIA_ADICIONADA")) return "maduro";
    if (tipos.has("CAP_ADICIONADA")) return "com-cap";
    if (tipos.has("EXONS_UNIDOS")) return "unido";
    if (tipos.has("INTRON_SELECIONADO")) return "selecionado";
    return "antes";
  }

  function desenhar() {
    limpar(conteiner);
    if (!registro) return;
    const dados = registro.dados || {};
    const seq = (registro.entrada && registro.entrada.sequencia) || "";
    const feitos = passos.slice(0, passoAtual);
    const tipos = new Set(feitos.map((e) => e.tipo));
    const estadoGlobal = calcularEstadoGlobal(feitos);
    const gusSelecionados = new Set(
      feitos.filter((e) => e.tipo === "INTRON_SELECIONADO" && e.posicao !== null).map((e) => e.posicao)
    );

    const total = seq.length;
    const ini = janelaIdx * TAM_JANELA;
    const fim = Math.min(total, ini + TAM_JANELA);

    const raiz = el("div", {
      class: "viz-palco",
      "data-viz": "at2",
      "data-estado": estadoGlobal,
    });

    raiz.appendChild(el("div", { class: "viz-legenda" }, [
      el("span", { class: "chip", text: `Estado: ${estadoGlobal}` }),
      el("span", { class: "chip", text: "GU (doador 5')" }),
      el("span", { class: "chip", text: "A (branch point)" }),
      el("span", { class: "chip", text: "AG (aceptor 3')" }),
    ]));

    const barraJanela = criarBarraJanela(total, janelaIdx, (novoIdx) => {
      janelaIdx = novoIdx;
      desenhar();
    });
    if (barraJanela) raiz.appendChild(barraJanela);

    const temProcessado = Boolean(tipos.has("EXONS_UNIDOS") && dados.rna_processado);
    const largura = Math.max(320, (fim - ini) * PASSO_X + 24);
    const altura = temProcessado ? 194 : 128;
    const svg = svgEl("svg", {
      class: "viz-svg",
      width: largura,
      height: altura,
      viewBox: `0 0 ${largura} ${altura}`,
      role: "img",
      "aria-label": "SpliceLab: pré-mRNA, íntrons e sítios de splicing",
    });

    const yMarcas = 6;
    const yFita = 46;
    const yProc = 136;

    // Blocos de íntrons
    const introns = dados.introns || [];
    for (const intr of introns) {
      const estIntron = tipos.has("EXONS_UNIDOS")
        ? "removido"
        : gusSelecionados.has(intr.posicao_gu)
          ? "selecionado"
          : "pendente";
      const iIni = Math.max(ini, intr.posicao_gu);
      const iFim = Math.min(fim, intr.posicao_ag + 2);
      const gIntron = svgEl("g", {
        class: "intron-bloco",
        "data-intron": "",
        "data-gu": String(intr.posicao_gu),
        "data-branch": String(intr.posicao_branch),
        "data-ag": String(intr.posicao_ag),
        "data-estado": estIntron,
      });
      if (iFim > iIni) {
        const xIntr = 10 + (iIni - ini) * PASSO_X;
        const wIntr = (iFim - iIni) * PASSO_X;
        gIntron.appendChild(svgEl("rect", {
          x: xIntr,
          y: yFita - 6,
          width: wIntr,
          height: 38,
          rx: 8,
          fill: "transparent",
          stroke: "var(--cor-splicing)",
          "stroke-width": 1.5,
        }));
        if (estIntron === "removido") {
          gIntron.appendChild(svgEl("line", {
            x1: xIntr + 2,
            y1: yFita + 13,
            x2: xIntr + wIntr - 2,
            y2: yFita + 13,
            stroke: "var(--cor-erro)",
            "stroke-width": 2,
            "stroke-dasharray": "4 3",
          }));
        }
      }
      svg.appendChild(gIntron);
    }

    // Fita pré-mRNA
    const grupoFita = svgEl("g", { "data-fita": "pre-mrna" });
    preencherFitaBases(grupoFita, seq, ini, fim, yFita, { onInspecionar, comRegua: true });
    svg.appendChild(grupoFita);

    // Sítios GU e AG
    const grupoSitios = svgEl("g", { "data-regiao": "sitios-at2" });
    for (const pos of dados.sitios_gu || []) {
      if (pos >= ini && pos < fim) {
        const x = 12 + (pos - ini) * PASSO_X + 12;
        grupoSitios.appendChild(criarMarcaSvg(x, yMarcas, "GU", "svg-marca-gu", {
          "data-marca": "gu",
          "data-indice": String(pos),
        }, () => onInspecionar && onInspecionar(pos)));
      }
    }
    for (const pos of dados.sitios_ag || []) {
      if (pos >= ini && pos < fim) {
        const x = 12 + (pos - ini) * PASSO_X + 12;
        grupoSitios.appendChild(criarMarcaSvg(x, yFita + 40, "AG", "svg-marca-ag", {
          "data-marca": "ag",
          "data-indice": String(pos),
        }, () => onInspecionar && onInspecionar(pos)));
      }
    }
    svg.appendChild(grupoSitios);

    if (temProcessado) {
      const proc = dados.rna_processado;
      const pIni = Math.min(proc.length, ini);
      const pFim = Math.min(proc.length, pIni + TAM_JANELA);
      svg.appendChild(svgEl("text", {
        x: 12,
        y: yProc - 12,
        class: "svg-regua-texto",
        text: "RNA processado (éxons unidos)",
      }));
      const grupoProc = svgEl("g", { class: "fita-unida", "data-fita": "rna-processado" });
      preencherFitaBases(grupoProc, proc, pIni, pFim, yProc, { comRegua: false });
      svg.appendChild(grupoProc);
    }

    raiz.appendChild(el("div", { class: "fita-scroll" }, [svg]));

    // Réguas D009 por íntron
    if (introns.length) {
      const reguasEl = el("div", { class: "barra-ferramentas" });
      for (const intr of introns) {
        const dist = intr.posicao_ag - intr.posicao_branch - 1;
        reguasEl.appendChild(el("div", {
          class: "regua-d009",
          "data-regua": "",
          "data-distancia": String(dist),
        }, [
          el("span", { text: "Branch → AG:" }),
          el("strong", { class: "mono", "data-campo": "distancia", text: String(dist) }),
          el("span", { class: "texto-suave", text: "(faixa 10–30 nt)" }),
        ]));
      }
      raiz.appendChild(reguasEl);
    }

    // Maturação: CAP + RNA processado + Cauda poli-A expansível
    if (tipos.has("CAP_ADICIONADA") || tipos.has("POLIA_ADICIONADA") || dados.cap || dados.cauda_adicionada) {
      const faixaMat = el("div", { class: "maturacao-faixa" });
      if (dados.cap && (tipos.has("CAP_ADICIONADA") || tipos.has("POLIA_ADICIONADA"))) {
        faixaMat.appendChild(el("span", { class: "cap-selo", "data-cap": "", text: dados.cap }));
      }
      if (dados.rna_processado && tipos.has("EXONS_UNIDOS")) {
        faixaMat.appendChild(el("span", {
          class: "chip mono",
          text: `Éxons: ${dados.rna_processado.length} nt`,
        }));
      }
      if (dados.cauda_adicionada && tipos.has("POLIA_ADICIONADA")) {
        const tam = dados.cauda_adicionada.length;
        faixaMat.appendChild(el("span", {
          class: "cauda-selo",
          "data-cauda": "",
          "data-tamanho": String(tam),
          text: caudaExpandida ? dados.cauda_adicionada : `A×${tam}`,
        }));
        faixaMat.appendChild(el("button", {
          type: "button",
          class: "btn btn-pequeno",
          "data-acao": "expandir-cauda",
          text: caudaExpandida ? "Comprimir cauda" : "Expandir cauda",
          onClick: () => {
            caudaExpandida = !caudaExpandida;
            desenhar();
          },
        }));
      }
      if (faixaMat.childNodes.length) raiz.appendChild(faixaMat);
    }

    conteiner.appendChild(raiz);
  }

  function definirRegistro(novoReg) {
    registro = novoReg;
    passos = (registro && registro.passos) || [];
    janelaIdx = 0;
    caudaExpandida = false;
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
