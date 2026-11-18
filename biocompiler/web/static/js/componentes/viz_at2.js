/* Visualização SVG interativa e coreografia da AT2 (splicing na mesma fita, CAP, cauda e maturação). */

import { el, limpar } from "../dom.js";
import { cancelarTudo, movimentoReduzido } from "../motor/orquestrador.js";
import {
  LARG_BASE,
  PASSO_X,
  TAM_JANELA,
  criarBarraJanela,
  criarMarcaSvg,
  preencherFitaBases,
  svgEl,
  ultimoEventoComPosicao,
} from "./viz_comum.js";

function duracaoDidaticaMs(nomeToken, fallbackMs) {
  const bruto = getComputedStyle(document.documentElement).getPropertyValue(nomeToken).trim();
  const n = bruto ? parseFloat(bruto) : NaN;
  const base = Number.isFinite(n) ? (bruto.endsWith("ms") ? n : n * 1000) : fallbackMs;
  const sel = document.querySelector('[data-componente="player"] select[data-campo="velocidade"]');
  const vel = sel && Number(sel.value) > 0 ? Number(sel.value) : 1;
  return Math.max(80, Math.round(base / vel));
}

export function criarVizAT2(conteiner, onInspecionar) {

  let registro = null;
  let passoAtual = 1;
  let passoAnterior = 0;
  let passos = [];
  let janelaIdx = 0;
  let caudaExpandida = false;

  let registroRenderizado = null;
  let janelaRenderizada = -1;
  let refs = null;

  const xOffset = 84;
  const yMarcas = 4;
  const yFita = 84;
  const yProc = 172;

  function calcularEstadoGlobal(feitos) {
    const tipos = new Set(feitos.map((e) => e.tipo));
    if (tipos.has("POLIA_ADICIONADA")) return "maduro";
    if (tipos.has("CAP_ADICIONADA")) return "com-cap";
    if (tipos.has("EXONS_UNIDOS")) return "unido";
    if (tipos.has("INTRON_SELECIONADO")) return "selecionado";
    return "antes";
  }

  function construirPalco() {
    limpar(conteiner);
    refs = null;
    if (!registro) return;

    const dados = registro.dados || {};
    const seq = (registro.entrada && registro.entrada.sequencia) || "";
    const introns = dados.introns || [];
    const total = seq.length;
    const ini = janelaIdx * TAM_JANELA;
    const fim = Math.min(total, ini + TAM_JANELA);

    const raiz = el("div", {
      class: "viz-palco",
      "data-viz": "at2",
      "data-estado": "antes",
    });

    const chipEstado = el("span", { class: "chip", text: "Estado: antes" });
    raiz.appendChild(el("div", { class: "viz-legenda" }, [
      chipEstado,
      el("span", { class: "chip", text: "GU (doador 5')" }),
      el("span", { class: "chip", text: "A (branch point)" }),
      el("span", { class: "chip", text: "AG (aceptor 3')" }),
    ]));

    const barraJanela = criarBarraJanela(total, janelaIdx, (novoIdx) => {
      janelaIdx = novoIdx;
      construirPalco();
      sincronizarEstado(true);
    });
    if (barraJanela) raiz.appendChild(barraJanela);

    const largura = Math.max(360, xOffset + (fim - ini) * PASSO_X + 60);
    const altura = dados.rna_processado ? 228 : 156;
    const svg = svgEl("svg", {
      class: "viz-svg",
      width: largura,
      height: altura,
      viewBox: `0 0 ${largura} ${altura}`,
      role: "img",
      "aria-label": "SpliceLab: pré-mRNA, íntrons e sítios de splicing",
    });

    const grupoIntrons = svgEl("g", { "data-regiao": "introns-at2" });
    for (const intr of introns) {
      const iIni = Math.max(ini, intr.posicao_gu);
      const iFim = Math.min(fim, intr.posicao_ag + 2);
      const gIntron = svgEl("g", {
        class: "intron-bloco at2-intron-bloco",
        "data-intron": "",
        "data-gu": String(intr.posicao_gu),
        "data-branch": String(intr.posicao_branch),
        "data-ag": String(intr.posicao_ag),
        "data-estado": "pendente",
      });
      if (iFim > iIni) {
        const xIntr = xOffset - 2 + (iIni - ini) * PASSO_X;
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
      }
      grupoIntrons.appendChild(gIntron);
    }
    svg.appendChild(grupoIntrons);

    const grupoFita = svgEl("g", { "data-fita": "pre-mrna" });
    preencherFitaBases(grupoFita, seq, ini, fim, yFita, {
      onInspecionar,
      xOffset,
      comRegua: true,
    });
    for (const gBase of grupoFita.querySelectorAll("[data-base]")) {
      gBase.classList.add("at2-base-movel");
    }
    svg.appendChild(grupoFita);

    const grupoSitios = svgEl("g", { "data-regiao": "sitios-at2" });
    for (const pos of dados.sitios_gu || []) {
      if (pos >= ini && pos < fim) {
        const x = xOffset + (pos - ini) * PASSO_X + 12;
        grupoSitios.appendChild(criarMarcaSvg(x, yMarcas, "GU", "svg-marca-gu", {
          "data-marca": "gu",
          "data-indice": String(pos),
        }, () => onInspecionar && onInspecionar(pos)));
      }
    }
    for (const pos of dados.sitios_ag || []) {
      if (pos >= ini && pos < fim) {
        const x = xOffset + (pos - ini) * PASSO_X + 12;
        grupoSitios.appendChild(criarMarcaSvg(x, yFita + 40, "AG", "svg-marca-ag", {
          "data-marca": "ag",
          "data-indice": String(pos),
        }, () => onInspecionar && onInspecionar(pos)));
      }
    }
    svg.appendChild(grupoSitios);

    const grupoProc = svgEl("g", { "data-regiao": "proc-at2" });
    svg.appendChild(grupoProc);

    const palcoFita = el("div", { class: "at2-palco-fita" }, [svg]);

    let capEl = null;
    if (dados.cap) {
      capEl = el("span", {
        class: "at2-cap",
        "data-cap": "",
        "data-visivel": "false",
        text: dados.cap,
      });
      capEl.style.top = `${yFita}px`;
      capEl.style.left = `${xOffset - 68}px`;
      capEl.style.width = "64px";
      palcoFita.appendChild(capEl);
    }

    let caudaGrupo = null;
    let caudaEl = null;
    let btnExpandir = null;
    if (dados.cauda_adicionada) {
      const tam = dados.cauda_adicionada.length;
      caudaEl = el("span", {
        class: "at2-cauda",
        "data-cauda": "",
        "data-tamanho": String(tam),
        text: `A×${tam}`,
      });
      caudaGrupo = el("div", {
        class: "at2-cauda-grupo",
        "data-visivel": "false",
      }, [caudaEl]);
      caudaGrupo.style.top = `${yFita}px`;
      palcoFita.appendChild(caudaGrupo);

      btnExpandir = el("button", {
        type: "button",
        class: "btn btn-pequeno",
        "data-acao": "expandir-cauda",
        text: "Expandir cauda",
        hidden: true,
        onClick: () => {
          caudaExpandida = !caudaExpandida;
          sincronizarEstado(true);
        },
      });
    }

    raiz.appendChild(el("div", { class: "fita-scroll" }, [palcoFita]));

    if (introns.length || btnExpandir) {
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
      if (btnExpandir) reguasEl.appendChild(btnExpandir);
      raiz.appendChild(reguasEl);
    }

    // Legenda de maturação (removido / preservado / adicionado)
    const removidoNt = introns.reduce((acc, it) => acc + (it.posicao_ag + 2 - it.posicao_gu), 0);
    const preservadoNt = (dados.rna_processado || "").length;
    const capTxt = dados.cap || "—";
    const caudaTam = dados.cauda_adicionada ? dados.cauda_adicionada.length : 0;
    const legendaMat = el("div", {
      class: "at2-legenda-maturacao",
      "data-legenda-maturacao": "",
    }, [
      el("div", { class: "at2-legenda-item", "data-categoria": "removido" }, [
        el("span", { class: "at2-legenda-titulo", text: "Removido (íntrons)" }),
        el("span", { class: "at2-legenda-valor", text: `${removidoNt} nt` }),
      ]),
      el("div", { class: "at2-legenda-item", "data-categoria": "preservado" }, [
        el("span", { class: "at2-legenda-titulo", text: "Preservado (éxons)" }),
        el("span", { class: "at2-legenda-valor", text: `${preservadoNt} nt` }),
      ]),
      el("div", { class: "at2-legenda-item", "data-categoria": "adicionado" }, [
        el("span", { class: "at2-legenda-titulo", text: "Adicionado (maturação)" }),
        el("span", { class: "at2-legenda-valor", text: `${capTxt} + ${caudaTam} A` }),
      ]),
    ]);
    raiz.appendChild(legendaMat);

    conteiner.appendChild(raiz);
    registroRenderizado = registro;
    janelaRenderizada = janelaIdx;
    refs = {
      raiz,
      chipEstado,
      svg,
      palcoFita,
      grupoIntrons,
      grupoFita,
      grupoSitios,
      grupoProc,
      capEl,
      caudaGrupo,
      caudaEl,
      btnExpandir,
      ini,
      fim,
      procAtivo: false,
    };
  }

  function sincronizarEstado(semAnimar) {
    if (!refs || !registro) return;
    const dados = registro.dados || {};
    const introns = dados.introns || [];
    const { ini, fim } = refs;

    const feitos = passos.slice(0, passoAtual);
    const tipos = new Set(feitos.map((e) => e.tipo));
    const estadoGlobal = calcularEstadoGlobal(feitos);
    const gusSelecionados = new Set(
      feitos.filter((e) => e.tipo === "INTRON_SELECIONADO" && e.posicao !== null).map((e) => e.posicao)
    );
    const unido = tipos.has("EXONS_UNIDOS");

    refs.raiz.style.setProperty("--dur-at2-curta", `${duracaoDidaticaMs("--dur-curta", 200)}ms`);
    refs.raiz.style.setProperty("--dur-at2-media", `${duracaoDidaticaMs("--dur-media", 300)}ms`);
    refs.raiz.style.setProperty("--dur-at2-longa", `${duracaoDidaticaMs("--dur-longa", 450)}ms`);

    if (semAnimar) {
      refs.raiz.classList.add("sem-animacao");
      cancelarTudo(conteiner);
    } else {
      refs.raiz.classList.remove("sem-animacao");
    }

    refs.raiz.setAttribute("data-estado", estadoGlobal);
    refs.chipEstado.textContent = `Estado: ${estadoGlobal}`;

    // 1. Estados dos blocos de íntrons
    for (const gIntron of refs.grupoIntrons.querySelectorAll("[data-intron]")) {
      const gu = Number(gIntron.getAttribute("data-gu"));
      const estIntron = unido
        ? "removido"
        : gusSelecionados.has(gu)
          ? "selecionado"
          : "pendente";
      gIntron.setAttribute("data-estado", estIntron);
    }

    // 2. Splicing na mesma fita: íntron sobe e esmaece; éxons deslizam até se encostar
    const ehIntron = (idx) => introns.some((it) => idx >= it.posicao_gu && idx < it.posicao_ag + 2);
    const intronSelecionadoDe = (idx) => introns.some(
      (it) => gusSelecionados.has(it.posicao_gu) && idx >= it.posicao_gu && idx < it.posicao_ag + 2
    );
    const removidosAntesDe = (idx) => {
      let soma = 0;
      for (const it of introns) {
        if (it.posicao_ag + 2 <= idx) {
          soma += (it.posicao_ag + 2 - it.posicao_gu);
        }
      }
      return soma;
    };

    let ultimaVisivelIdx = Math.max(ini, fim - 1);
    for (const gBase of refs.grupoFita.querySelectorAll("[data-base]")) {
      const idx = Number(gBase.getAttribute("data-indice"));
      const noIntron = ehIntron(idx);
      gBase.classList.toggle("at2-base-intron-selecionada", !unido && intronSelecionadoDe(idx));
      gBase.classList.toggle("at2-base-intron-removida", unido && noIntron);
      if (unido) {
        if (noIntron) {
          gBase.style.transform = "translateY(-50px)";
        } else {
          const dx = -removidosAntesDe(idx) * PASSO_X;
          gBase.style.transform = `translateX(${dx}px)`;
          ultimaVisivelIdx = idx;
        }
      } else {
        gBase.style.transform = "translate(0px, 0px)";
        ultimaVisivelIdx = idx;
      }
    }

    // 3. Fita resumo RNA processado (M8)
    const temProcessado = Boolean(unido && dados.rna_processado);
    if (!temProcessado && refs.procAtivo) {
      limpar(refs.grupoProc);
      refs.procAtivo = false;
    } else if (temProcessado && !refs.procAtivo) {
      const proc = dados.rna_processado;
      const pIni = Math.min(proc.length, ini);
      const pFim = Math.min(proc.length, pIni + TAM_JANELA);
      refs.grupoProc.appendChild(svgEl("text", {
        x: xOffset,
        y: yProc - 12,
        class: "svg-regua-texto",
        text: "RNA processado (éxons unidos)",
      }));
      const grupoFitaProc = svgEl("g", { class: "fita-unida", "data-fita": "rna-processado" });
      preencherFitaBases(grupoFitaProc, proc, pIni, pFim, yProc, { xOffset, comRegua: false });
      refs.grupoProc.appendChild(grupoFitaProc);
      refs.procAtivo = true;
    }

    // 4. CAP 5' encaixada na extremidade esquerda
    if (refs.capEl) {
      const capVisivel = tipos.has("CAP_ADICIONADA") || tipos.has("POLIA_ADICIONADA");
      refs.capEl.setAttribute("data-visivel", capVisivel ? "true" : "false");
    }

    // 5. Cauda poli-A encostada na extremidade 3'
    if (refs.caudaGrupo && refs.caudaEl && refs.btnExpandir && dados.cauda_adicionada) {
      const caudaVisivel = tipos.has("POLIA_ADICIONADA");
      refs.caudaGrupo.setAttribute("data-visivel", caudaVisivel ? "true" : "false");
      refs.btnExpandir.hidden = !caudaVisivel;
      const dxUltima = unido ? -removidosAntesDe(ultimaVisivelIdx) * PASSO_X : 0;
      const xUltimaDireita = xOffset + (ultimaVisivelIdx - ini) * PASSO_X + dxUltima + LARG_BASE;
      refs.caudaGrupo.style.left = `${xUltimaDireita + 4}px`;
      const tam = dados.cauda_adicionada.length;
      refs.caudaEl.textContent = caudaExpandida ? dados.cauda_adicionada : `A×${tam}`;
      refs.btnExpandir.textContent = caudaExpandida ? "Comprimir cauda" : "Expandir cauda";
      refs.palcoFita.style.minWidth = caudaExpandida ? `${xUltimaDireita + 880}px` : "100%";
    }
  }

  function definirRegistro(novoReg) {
    registro = novoReg;
    passos = (registro && registro.passos) || [];
    janelaIdx = 0;
    passoAnterior = 0;
    caudaExpandida = false;
    registroRenderizado = null;
    refs = null;
  }

  function atualizar(k, novosPassos) {
    passoAtual = k;
    passos = novosPassos || passos;
    const pos = ultimoEventoComPosicao(passos, k);
    janelaIdx = pos !== null ? Math.floor(pos / TAM_JANELA) : 0;

    const semAnimar = movimentoReduzido() || passoAnterior === 0 || Math.abs(k - passoAnterior) > 1;
    if (!refs || registro !== registroRenderizado || janelaIdx !== janelaRenderizada) {
      construirPalco();
    }
    sincronizarEstado(semAnimar);
    passoAnterior = k;
  }

  return { definirRegistro, atualizar };
}
