/* Visualização SVG interativa da AT3 (Ribossomo deslizante, códons sincronizados e cadeia polipeptídica). */

import { el, limpar } from "../dom.js";
import { criarAminoacido, criarCodon } from "../motor/componentes_cientificos.js";
import { desenharConexao, limparConexoes } from "../motor/conexao.js";
import { estadoGlobal } from "../motor/estado.js";
import { animar, movimentoReduzido } from "../motor/orquestrador.js";
import {
  PASSO_X,
  TAM_JANELA,
  criarBarraJanela,
  criarMarcaSvg,
  preencherFitaBases,
  svgEl,
  ultimoEventoComPosicao,
} from "./viz_comum.js";

const NS_SVG = "http:" + "//www.w3.org/2000/svg";

export function criarVizAT3(conteiner, onInspecionar, onCodonsPercorridos) {
  let registro = null;
  let passoAtual = 1;
  let passos = [];
  let janelaIdx = 0;
  let xRiboAnterior = null;

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
      xRiboAnterior = null;
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
    const jaStop = tipos.has("STOP_ENCONTRADO") || tipos.has("STOP_EM_FASE");
    const concluida = jaStop && (tipos.has("PROTEINA_GERADA") || tipos.has("RESULTADO") || passoAtual >= passos.length);

    let posRibo = pStart !== null && pStart !== undefined ? pStart : 0;
    if (jaStop && pStop !== null && pStop !== undefined) {
      posRibo = pStop;
    } else if (codonAtualIdx !== null && traduzidos[codonAtualIdx].posicao !== null) {
      posRibo = traduzidos[codonAtualIdx].posicao;
    }
    const localRibo = Math.max(0, Math.min(Math.max(0, fim - ini - 3), posRibo - ini));
    const xRibo = 10 + localRibo * PASSO_X;
    const yRibo = yFita - 32;

    const gRibo = svgEl("g", {
      class: "ribossomo-grupo",
      "data-ribossomo": "",
      "data-codon-atual": codonAtualIdx === null ? "" : String(codonAtualIdx),
      "data-parado": jaStop ? "true" : "false",
      transform: `translate(${xRibo}, ${yRibo})`,
    }, [
      svgEl("rect", {
        class: "ribossomo-janela",
        x: 0,
        y: 0,
        width: PASSO_X * 3 - 4,
        height: 78,
        rx: 14,
      }),
      svgEl("path", {
        class: "ribossomo-subunidade-maior",
        d: `M 2 22 C 2 5, ${Math.round((PASSO_X * 3 - 4) * 0.25)} 1, ${Math.round((PASSO_X * 3 - 4) / 2)} 1 C ${Math.round((PASSO_X * 3 - 4) * 0.75)} 1, ${PASSO_X * 3 - 6} 5, ${PASSO_X * 3 - 6} 22 Z`,
      }),
      svgEl("rect", {
        class: "ribossomo-subunidade-menor",
        x: 6,
        y: 62,
        width: PASSO_X * 3 - 16,
        height: 12,
        rx: 6,
      }),
      svgEl("text", {
        x: (PASSO_X * 3 - 4) / 2,
        y: 12,
        class: "svg-regua-texto",
        "text-anchor": "middle",
        "dominant-baseline": "central",
        text: jaStop ? "STOP" : (codonAtualCodigo || "Ribossomo"),
      }),
    ]);
    svg.appendChild(gRibo);

    if (!movimentoReduzido() && xRiboAnterior !== null && xRiboAnterior !== xRibo) {
      animar(gRibo, [
        { transform: `translate(${xRiboAnterior}px, ${yRibo}px)` },
        { transform: `translate(${xRibo}px, ${yRibo}px)` },
      ], { duration: 240, easing: "cubic-bezier(0.22, 1, 0.36, 1)" });
    }
    xRiboAnterior = xRibo;

    // Fita de mRNA
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
    if (jaStop && pStop !== null && pStop !== undefined && pStop >= ini && pStop < fim) {
      const x = 12 + (pStop - ini) * PASSO_X + 12;
      grupoMarcas.appendChild(criarMarcaSvg(x, yMarcas, "STOP", "svg-marca-stop", {
        "data-marca": "stop",
        "data-indice": String(pStop),
      }, () => onInspecionar && onInspecionar(pStop)));
    }
    svg.appendChild(grupoMarcas);

    // Códons traduzidos alinhados sob a fita (dentro de .fita-scroll para manter centro idêntico)
    const palcoTrad = el("div", { class: "at3-palco-traducao" });
    const camadaConexao = document.createElementNS(NS_SVG, "svg");
    camadaConexao.setAttribute("class", "at3-conexao-svg");
    camadaConexao.setAttribute("aria-hidden", "true");

    const faixaCodons = el("div", { class: "codons-faixa-alinhada", "data-regiao": "codons-mrna" });
    faixaCodons.style.width = `${largura}px`;

    const cadeia = el("div", {
      class: "cadeia-aa",
      "data-cadeia": "",
      ...(concluida ? { "data-concluida": "true" } : {}),
    });

    const codonEls = [];
    const aaEls = [];

    function aplicarSelecao(ordem) {
      const selValida = Number.isInteger(ordem) && ordem >= 0 && ordem < codonEls.length ? ordem : null;
      estadoGlobal.definir({ selecao: selValida });
      for (let idx = 0; idx < codonEls.length; idx += 1) {
        const ativo = idx === selValida;
        codonEls[idx].classList.toggle("selecionado", ativo);
        aaEls[idx].classList.toggle("selecionado", ativo);
        codonEls[idx].setAttribute("aria-pressed", ativo ? "true" : "false");
        aaEls[idx].setAttribute("aria-pressed", ativo ? "true" : "false");
        if (ativo) {
          codonEls[idx].setAttribute("data-selecionado", "true");
          aaEls[idx].setAttribute("data-selecionado", "true");
        } else {
          codonEls[idx].removeAttribute("data-selecionado");
          aaEls[idx].removeAttribute("data-selecionado");
        }
      }
      if (selValida !== null) {
        desenharConexao(camadaConexao, codonEls[selValida], aaEls[selValida], {
          id: `aa-codon-${selValida}`,
        });
      } else {
        limparConexoes(camadaConexao);
      }
    }

    traduzidos.forEach((ev, idx) => {
      const partes = (ev.detalhe || "").split(":");
      const trinca = (partes[0] || "").trim();
      const aa = (partes[1] || partes[0] || "").trim();
      const posCodon = ev.posicao !== null && ev.posicao !== undefined ? ev.posicao : idx * 3;

      const onToggle = () => {
        const atual = estadoGlobal.obter().selecao;
        aplicarSelecao(atual === idx ? null : idx);
        if (onInspecionar) onInspecionar(posCodon);
      };

      const codonEl = criarCodon(trinca, idx, posCodon, { onClick: onToggle });
      const leftPos = 10 + Math.max(0, posCodon - ini) * PASSO_X;
      codonEl.style.left = `${leftPos}px`;
      codonEl.style.width = `${PASSO_X * 3 - 4}px`;

      const aaEl = criarAminoacido(aa, idx, { onClick: onToggle });
      codonEls.push(codonEl);
      aaEls.push(aaEl);
      faixaCodons.appendChild(codonEl);
      cadeia.appendChild(aaEl);
    });

    if (!traduzidos.length) {
      cadeia.appendChild(el("span", { class: "texto-suave", text: "Nenhum aminoácido traduzido até este passo." }));
    }

    palcoTrad.appendChild(camadaConexao);
    palcoTrad.appendChild(el("div", { class: "fita-scroll" }, [svg, traduzidos.length ? faixaCodons : null]));
    palcoTrad.appendChild(el("div", { class: "at3-subbloco" }, [
      el("h3", { text: "Cadeia polipeptídica" }),
      cadeia,
    ]));

    raiz.appendChild(palcoTrad);
    conteiner.appendChild(raiz);

    const selAtual = estadoGlobal.obter().selecao;
    if (Number.isInteger(selAtual) && selAtual >= 0 && selAtual < codonEls.length) {
      aplicarSelecao(selAtual);
    }
  }

  function definirRegistro(novoReg) {
    registro = novoReg;
    passos = (registro && registro.passos) || [];
    janelaIdx = 0;
    xRiboAnterior = null;
    estadoGlobal.limparSelecao();
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
