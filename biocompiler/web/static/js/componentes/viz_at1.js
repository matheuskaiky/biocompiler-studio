/* Visualização SVG interativa e coreografia da AT1 (Transcrição DNA -> pré-mRNA). */

import { el, limpar } from "../dom.js";
import { animar, cancelarTudo, movimentoReduzido } from "../motor/orquestrador.js";
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

function lerToken(nome, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  return v || fallback;
}

function duracaoDidaticaMs(nomeToken, fallbackMs) {
  const bruto = lerToken(nomeToken, "");
  const n = bruto ? parseFloat(bruto) : NaN;
  const base = Number.isFinite(n) ? (bruto.endsWith("ms") ? n : n * 1000) : fallbackMs;
  const sel = document.querySelector('[data-componente="player"] select[data-campo="velocidade"]');
  const vel = sel && Number(sel.value) > 0 ? Number(sel.value) : 1;
  return Math.max(80, Math.round(base / vel));
}

export function criarVizAT1(conteiner, onInspecionar) {

  let registro = null;
  let passoAtual = 1;
  let passoAnterior = 0;
  let passos = [];
  let janelaIdx = 0;

  let registroRenderizado = null;
  let janelaRenderizada = -1;
  let refs = null;

  const yMarcas = 6;
  const yDna = 44;
  const yPre = 110;

  function construirPalco() {
    limpar(conteiner);
    refs = null;
    if (!registro) return;

    const dados = registro.dados || {};
    const seq = (registro.entrada && registro.entrada.sequencia) || "";
    const pre = dados.pre_mrna || "";
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
      construirPalco();
      sincronizarEstado(true);
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

    // Regiões UTR (no fundo)
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

    const grupoCodons = svgEl("g", { "data-regiao": "codons-at1" });
    svg.appendChild(grupoCodons);

    const grupoDna = svgEl("g", { "data-fita": "dna" });
    preencherFitaBases(grupoDna, seq, ini, fim, yDna, { onInspecionar, comRegua: true });
    svg.appendChild(grupoDna);

    const grupoMarcas = svgEl("g", { "data-regiao": "marcas-at1" });
    svg.appendChild(grupoMarcas);

    const grupoPre = svgEl("g", { "data-fita": "pre-mrna" });
    svg.appendChild(grupoPre);

    const cursor = el("div", {
      class: "at1-cursor cursor-inativo",
      "data-cursor": "",
      "aria-hidden": "true",
    });
    cursor.style.top = `${yDna - 4}px`;
    cursor.style.height = "34px";
    cursor.style.width = `${LARG_BASE}px`;
    cursor.style.transform = "translateX(12px)";

    const palcoFita = el("div", { class: "at1-palco-fita" }, [svg, cursor]);
    raiz.appendChild(el("div", { class: "fita-scroll" }, [palcoFita]));

    const diagnostico = el("div", {
      class: "at1-diagnostico",
      "data-regiao": "diagnostico",
      "data-status": "neutro",
    });
    raiz.appendChild(diagnostico);

    conteiner.appendChild(raiz);
    registroRenderizado = registro;
    janelaRenderizada = janelaIdx;
    refs = {
      raiz,
      svg,
      cursor,
      grupoCodons,
      grupoDna,
      grupoMarcas,
      grupoPre,
      diagnostico,
      ini,
      fim,
      preAtivo: false,
      xCursorAnterior: 12,
      wCursorAnterior: LARG_BASE,
      codonsRenderizados: new Set(),
      marcasRenderizadas: new Set(),
    };
  }

  function sincronizarEstado(semAnimar) {
    if (!refs || !registro) return;
    const dados = registro.dados || {};
    const seq = (registro.entrada && registro.entrada.sequencia) || "";
    const pre = dados.pre_mrna || "";
    const { ini, fim } = refs;

    const feitos = passos.slice(0, passoAtual);
    const eventoAtual = passos[passoAtual - 1] || null;
    const tipos = new Set(feitos.map((e) => e.tipo));

    const durCurta = duracaoDidaticaMs("--dur-curta", 200);
    const durMedia = duracaoDidaticaMs("--dur-media", 300);
    const durLonga = duracaoDidaticaMs("--dur-longa", 450);
    const curvaPadrao = lerToken("--curva-padrao", "cubic-bezier(0.25, 0.1, 0.25, 1)");
    refs.raiz.style.setProperty("--dur-at1-curta", `${durCurta}ms`);
    refs.raiz.style.setProperty("--dur-at1-media", `${durMedia}ms`);

    if (semAnimar) {
      refs.raiz.classList.add("sem-animacao");
      cancelarTudo(conteiner);
    } else {
      refs.raiz.classList.remove("sem-animacao");
    }

    // 1. Cursor científico deslizante
    const posUltima = ultimoEventoComPosicao(passos, passoAtual);
    const posEv = eventoAtual && eventoAtual.posicao !== null && eventoAtual.posicao !== undefined
      ? eventoAtual.posicao
      : null;
    const posCursor = posEv !== null ? posEv : (posUltima !== null ? posUltima : ini);
    const posClamped = Math.max(ini, Math.min(Math.max(ini, fim - 1), posCursor));
    const xCursor = 12 + (posClamped - ini) * PASSO_X;
    const ehTrinca = eventoAtual && (
      eventoAtual.tipo === "START_ENCONTRADO" ||
      eventoAtual.tipo === "CODON_LIDO" ||
      eventoAtual.tipo === "STOP_EM_FASE" ||
      eventoAtual.tipo === "STOP_FORA_DE_FASE"
    );
    const wCursor = ehTrinca ? (2 * PASSO_X + LARG_BASE) : LARG_BASE;
    const xAnt = refs.xCursorAnterior;
    const wAnt = refs.wCursorAnterior;
    refs.cursor.style.width = `${wCursor}px`;
    refs.cursor.style.transform = `translateX(${xCursor}px)`;
    refs.cursor.classList.toggle("cursor-inativo", posEv === null);
    if (semAnimar) {
      void refs.cursor.offsetWidth;
      if (!movimentoReduzido()) {
        refs.raiz.classList.remove("sem-animacao");
      }
    } else if (xCursor !== xAnt || wCursor !== wAnt) {
      animar(refs.cursor, [
        { transform: `translateX(${xAnt}px)`, width: `${wAnt}px` },
        { transform: `translateX(${xCursor}px)`, width: `${wCursor}px` },
      ], {
        duration: durMedia,
        easing: curvaPadrao,
      });
    }
    refs.xCursorAnterior = xCursor;
    refs.wCursorAnterior = wCursor;

    // 2. Trincas (códons) surgem apenas a partir de START_ENCONTRADO
    const pStart = dados.posicao_start;
    const pStop = dados.posicao_stop;
    const codons = dados.codons || [];
    const mostrarCodons = tipos.has("START_ENCONTRADO") && pStart !== null && pStart !== undefined;

    if (!mostrarCodons) {
      limpar(refs.grupoCodons);
      refs.codonsRenderizados.clear();
    } else {
      const revelarTodos = tipos.has("STOP_EM_FASE") || tipos.has("STOP_ENCONTRADO")
        || tipos.has("T_PARA_U") || tipos.has("RESULTADO");
      let maxPosCodon = pStart;
      for (const e of feitos) {
        if ((e.tipo === "START_ENCONTRADO" || e.tipo === "CODON_LIDO" || e.tipo === "STOP_EM_FASE")
            && e.posicao !== null && e.posicao !== undefined) {
          if (e.posicao > maxPosCodon) maxPosCodon = e.posicao;
        }
      }

      const desejados = new Set();
      codons.forEach((_, idx) => {
        const cIni = pStart + idx * 3;
        const cFim = cIni + 3;
        if (cFim <= ini || cIni >= fim) return;
        if (revelarTodos || cIni <= maxPosCodon) {
          desejados.add(idx);
        }
      });

      // Remover excedentes caso o usuário tenha voltado no player
      for (const idx of Array.from(refs.codonsRenderizados)) {
        if (!desejados.has(idx)) {
          const elCod = refs.grupoCodons.querySelector(`[data-codon="${idx}"]`);
          if (elCod) elCod.remove();
          refs.codonsRenderizados.delete(idx);
        }
      }

      codons.forEach((_, idx) => {
        if (!desejados.has(idx)) return;
        const cIni = pStart + idx * 3;
        const cFim = cIni + 3;
        const vIni = Math.max(ini, cIni);
        const vFim = Math.min(fim, cFim);
        const ehAtual = eventoAtual && eventoAtual.posicao === cIni;
        let rect = refs.grupoCodons.querySelector(`[data-codon="${idx}"]`);
        if (!rect) {
          rect = svgEl("rect", {
            x: 10 + (vIni - ini) * PASSO_X,
            y: yDna - 4,
            width: Math.max(LARG_BASE, (vFim - vIni) * PASSO_X - 2),
            height: 34,
            class: `svg-codon-caixa at1-codon${ehAtual ? " atual" : ""}`,
            "data-codon": String(idx),
          });
          refs.grupoCodons.appendChild(rect);
          refs.codonsRenderizados.add(idx);
        } else {
          rect.setAttribute("class", `svg-codon-caixa at1-codon${ehAtual ? " atual" : ""}`);
        }
      });
    }

    // 3. Marcadores sincronizados
    const marcasDesejadas = [];
    if (tipos.has("START_ENCONTRADO") && pStart !== null && pStart !== undefined && pStart >= ini && pStart < fim) {
      marcasDesejadas.push({ chave: `start:${pStart}`, x: 12 + (pStart - ini) * PASSO_X + 12, rotulo: "START", classe: "svg-marca-start", tipo: "start", pos: pStart });
    }
    if ((tipos.has("STOP_EM_FASE") || tipos.has("STOP_ENCONTRADO"))
        && pStop !== null && pStop !== undefined && pStop >= ini && pStop < fim) {
      marcasDesejadas.push({ chave: `stop:${pStop}`, x: 12 + (pStop - ini) * PASSO_X + 12, rotulo: "STOP", classe: "svg-marca-stop", tipo: "stop", pos: pStop });
    }
    const stopsForaVisiveis = new Set(
      feitos.filter((e) => e.tipo === "STOP_FORA_DE_FASE" && e.posicao !== null).map((e) => e.posicao)
    );
    for (const pos of stopsForaVisiveis) {
      if (pos >= ini && pos < fim) {
        marcasDesejadas.push({ chave: `stop-fora:${pos}`, x: 12 + (pos - ini) * PASSO_X + 12, rotulo: "STOP*", classe: "svg-marca-stop-fora", tipo: "stop-fora", pos });
      }
    }
    const invalidasVisiveis = new Set(
      feitos.filter((e) => e.tipo === "BASE_INVALIDA" && e.posicao !== null).map((e) => e.posicao)
    );
    for (const pos of invalidasVisiveis) {
      if (pos >= ini && pos < fim) {
        marcasDesejadas.push({ chave: `invalida:${pos}`, x: 12 + (pos - ini) * PASSO_X + 12, rotulo: "INV", classe: "svg-marca-invalida", tipo: "invalida", pos });
      }
    }
    const chaveMarcas = marcasDesejadas.map((m) => m.chave).join("|");
    if (chaveMarcas !== refs.chaveMarcas) {
      limpar(refs.grupoMarcas);
      for (const m of marcasDesejadas) {
        refs.grupoMarcas.appendChild(criarMarcaSvg(m.x, yMarcas, m.rotulo, m.classe, {
          "data-marca": m.tipo,
          "data-indice": String(m.pos),
        }, () => onInspecionar && onInspecionar(m.pos)));
      }
      refs.chaveMarcas = chaveMarcas;
    }

    // 4. Foco de erro só em posições determinadas pela API (bases_invalidas)
    const invalidasApi = new Set((dados.bases_invalidas || []).map(([idx]) => idx));
    const mostrarFoco = (tipos.has("BASE_INVALIDA") || tipos.has("RESULTADO")) && invalidasApi.size > 0;
    for (const gBase of refs.grupoDna.querySelectorAll("[data-base]")) {
      const idx = Number(gBase.getAttribute("data-indice"));
      if (mostrarFoco && invalidasApi.has(idx)) {
        gBase.setAttribute("data-foco", "");
        gBase.classList.add("at1-base-foco");
      } else {
        gBase.removeAttribute("data-foco");
        gBase.classList.remove("at1-base-foco");
      }
    }

    // 5. Pré-mRNA nasce da fita de DNA a partir de T_PARA_U
    const temPre = Boolean(pre && tipos.has("T_PARA_U"));
    if (!temPre) {
      if (refs.preAtivo) {
        limpar(refs.grupoPre);
        refs.preAtivo = false;
      }
    } else if (!refs.preAtivo) {
      const trocasSet = new Set();
      for (let i = ini; i < Math.min(fim, pre.length); i += 1) {
        if (seq[i] !== pre[i]) trocasSet.add(i);
      }
      preencherFitaBases(refs.grupoPre, pre, ini, Math.min(fim, pre.length), yPre, {
        onInspecionar,
        trocasSet,
        comRegua: false,
      });
      refs.preAtivo = true;
      if (!semAnimar) {
        animar(refs.grupoPre, [
          { transform: `translateY(${yDna - yPre}px)`, opacity: 0.72 },
          { transform: "translateY(0px)", opacity: 1 },
        ], {
          duration: durLonga,
          easing: curvaPadrao,
        });
      }
    }

    // 6. Painel de diagnóstico com o rótulo exato da API
    const resultadoApi = dados.resultado || registro.resultado || "";
    const statusOk = dados.status === "CORRETO" || resultadoApi === "CORRETO";
    refs.diagnostico.setAttribute("data-status", resultadoApi ? (statusOk ? "ok" : "erro") : "neutro");
    limpar(refs.diagnostico);
    refs.diagnostico.appendChild(el("span", { class: "at1-diagnostico-rotulo" }, [
      el("span", { class: `selo ${statusOk ? "selo-ok" : "selo-erro"}`, text: statusOk ? "OK" : "Diagnóstico" }),
      el("span", { class: "mono", text: resultadoApi || "Em análise" }),
    ]));
    const detalheDiag = invalidasApi.size > 0
      ? `${invalidasApi.size} base(s) inválida(s) destacada(s) na fita`
      : (statusOk ? `${codons.length} códon(s) lido(s)` : "Sem posição de erro individualizada");
    refs.diagnostico.appendChild(el("span", { class: "at1-diagnostico-detalhe", text: detalheDiag }));
  }

  function definirRegistro(novoReg) {
    registro = novoReg;
    passos = (registro && registro.passos) || [];
    janelaIdx = 0;
    passoAnterior = 0;
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
