/* Visualização SVG interativa da AT3 (Ribossomo, tradução de códons e cadeia polipeptídica). */

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

export function criarVizAT3(conteiner, onInspecionar, onCodonsPercorridos) {
  let registro = null;
  let passoAtual = 1;
  let passos = [];
  let janelaIdx = 0;

  function desenhar() {
    limpar(conteiner);
    if (!registro) return;
    const dados = registro.dados || {};
    const regiao = dados.regiao_transcrita || "";
    const feitos = passos.slice(0, passoAtual);
    const eventoAtual = passos[passoAtual - 1] || null;
    const tipos = new Set(feitos.map((e) => e.tipo));

    const traduzidos = feitos.filter((e) => e.tipo === "CODON_TRADUZIDO");
    const codonAtualIdx = traduzidos.length ? traduzidos.length - 1 : null;
    const percorridosSet = new Set(
      traduzidos.map((e) => (e.detalhe || "").split(":")[0]).filter(Boolean)
    );
    const codonAtualCodigo = eventoAtual && eventoAtual.tipo === "CODON_TRADUZIDO"
      ? (eventoAtual.detalhe || "").split(":")[0]
      : null;

    if (onCodonsPercorridos) {
      onCodonsPercorridos(percorridosSet, codonAtualCodigo);
    }

    const total = regiao.length;
    const ini = janelaIdx * TAM_JANELA;
    const fim = Math.min(total, ini + TAM_JANELA);

    const raiz = el("div", { class: "viz-palco", "data-viz": "at3" });

    // CAP e cauda como blocos à parte (sem [data-base] dentro)
    const evCap = passos.find((e) => e.tipo === "CAP_VALIDADA");
    const textoCap = dados.cap || (dados.cap_ok && evCap ? evCap.detalhe : "");
    const tamCauda = dados.tamanho_cauda !== undefined && dados.tamanho_cauda !== null
      ? dados.tamanho_cauda
      : (dados.cauda_adicionada ? dados.cauda_adicionada.length : 0);
    raiz.appendChild(el("div", { class: "maturacao-faixa" }, [
      textoCap ? el("span", { class: "cap-selo", "data-cap": "", text: textoCap }) : null,
      el("span", { class: "chip mono", text: `Região: ${total} nt` }),
      el("span", {
        class: "cauda-selo",
        "data-cauda": "",
        "data-tamanho": String(tamCauda),
        text: `A×${tamCauda}`,
      }),
    ]));

    const barraJanela = criarBarraJanela(total, janelaIdx, (novoIdx) => {
      janelaIdx = novoIdx;
      desenhar();
    });
    if (barraJanela) raiz.appendChild(barraJanela);

    const largura = Math.max(320, (fim - ini) * PASSO_X + 24);
    const altura = 158;
    const svg = svgEl("svg", {
      class: "viz-svg",
      width: largura,
      height: altura,
      viewBox: `0 0 ${largura} ${altura}`,
      role: "img",
      "aria-label": "mRNA maduro e ribossomo em tradução",
    });

    const yMarcas = 4;
    const yFita = 64;
    const pStart = dados.posicao_start;
    const pStop = dados.posicao_stop;

    // Ribossomo SVG envolvendo a fita (subunidade maior acima, menor abaixo)
    let posRibo = pStart !== null && pStart !== undefined ? pStart : 0;
    if (codonAtualIdx !== null && traduzidos[codonAtualIdx].posicao !== null) {
      posRibo = traduzidos[codonAtualIdx].posicao;
    }
    const localRibo = Math.max(0, Math.min(Math.max(0, fim - ini - 3), posRibo - ini));
    const xRibo = 10 + localRibo * PASSO_X;
    const gRibo = svgEl("g", {
      class: "ribossomo-grupo",
      "data-ribossomo": "",
      "data-codon-atual": codonAtualIdx === null ? "" : String(codonAtualIdx),
      transform: `translate(${xRibo}, ${yFita - 32})`,
    }, [
      svgEl("rect", {
        x: -2,
        y: 0,
        width: PASSO_X * 3 + 2,
        height: 76,
        rx: 14,
        fill: "color-mix(in srgb, var(--cor-traducao) 9%, transparent)",
        stroke: "var(--cor-traducao)",
        "stroke-width": 1.2,
        "stroke-dasharray": "4 3",
      }),
      svgEl("rect", {
        x: 0,
        y: 2,
        width: PASSO_X * 3 - 2,
        height: 20,
        rx: 10,
        fill: "color-mix(in srgb, var(--cor-traducao) 26%, var(--superficie))",
        stroke: "var(--cor-traducao)",
        "stroke-width": 1.5,
      }),
      svgEl("rect", {
        x: 6,
        y: 62,
        width: PASSO_X * 3 - 14,
        height: 12,
        rx: 6,
        fill: "color-mix(in srgb, var(--cor-traducao) 18%, var(--superficie))",
        stroke: "var(--cor-traducao)",
        "stroke-width": 1,
      }),
      svgEl("text", {
        x: (PASSO_X * 3 - 2) / 2,
        y: 12,
        class: "svg-regua-texto",
        "text-anchor": "middle",
        "dominant-baseline": "central",
        text: codonAtualCodigo || "Ribossomo",
      }),
    ]);
    svg.appendChild(gRibo);

    // Fita de mRNA (regiao_transcrita)
    const grupoMrna = svgEl("g", { "data-fita": "mrna" });
    preencherFitaBases(grupoMrna, regiao, ini, fim, yFita, { onInspecionar, comRegua: true });
    svg.appendChild(grupoMrna);

    // Marcadores START e STOP
    const grupoMarcas = svgEl("g", { "data-regiao": "marcas-at3" });
    if ((tipos.has("AUG_ENCONTRADO") || tipos.has("START_ENCONTRADO"))
        && pStart !== null && pStart !== undefined && pStart >= ini && pStart < fim) {
      const x = 12 + (pStart - ini) * PASSO_X + 12;
      grupoMarcas.appendChild(criarMarcaSvg(x, yMarcas, "START", "svg-marca-start", {
        "data-marca": "start",
        "data-indice": String(pStart),
      }, () => onInspecionar && onInspecionar(pStart)));
    }
    if ((tipos.has("STOP_ENCONTRADO") || tipos.has("STOP_EM_FASE"))
        && pStop !== null && pStop !== undefined && pStop >= ini && pStop < fim) {
      const x = 12 + (pStop - ini) * PASSO_X + 12;
      grupoMarcas.appendChild(criarMarcaSvg(x, yMarcas, "STOP", "svg-marca-stop", {
        "data-marca": "stop",
        "data-indice": String(pStop),
      }, () => onInspecionar && onInspecionar(pStop)));
    }
    svg.appendChild(grupoMarcas);

    raiz.appendChild(el("div", { class: "fita-scroll" }, [svg]));

    // Cadeia polipeptídica em contas encadeadas
    const cadeia = el("div", { class: "cadeia-aa", "data-cadeia": "" });
    for (const ev of traduzidos) {
      const partes = (ev.detalhe || "").split(":");
      const aa = (partes[1] || partes[0] || "").trim();
      cadeia.appendChild(el("span", { class: "aa-conta", "data-aminoacido": "", text: aa }));
    }
    if (!traduzidos.length) {
      cadeia.appendChild(el("span", { class: "texto-suave", text: "Nenhum aminoácido traduzido até este passo." }));
    }
    raiz.appendChild(el("div", {}, [
      el("h3", { text: "Cadeia polipeptídica" }),
      cadeia,
    ]));

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
