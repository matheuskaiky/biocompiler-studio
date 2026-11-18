/* Player de eventos sincronizado com visualizações e linha do tempo. */

import { movimentoReduzido, obterModoAtual } from "../app.js";
import { el, limpar } from "../dom.js";
import { descreverEvento } from "./inspetor.js";

const BASE_MS = 800;
const NS_SVG = "http:" + "//www.w3.org/2000/svg";

function iconeSvg(d) {
  const svg = document.createElementNS(NS_SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", "16");
  svg.setAttribute("height", "16");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(NS_SVG, "path");
  path.setAttribute("fill", "currentColor");
  path.setAttribute("d", d);
  svg.appendChild(path);
  return svg;
}

export function criarPlayer(conteiner, callbacks = {}) {
  let registros = [];
  let indiceRegistro = 0;
  let passos = [];
  let k = 1;
  let tocando = false;
  let timer = null;
  let velocidade = 1;

  let regPasso = null;
  let regEvento = null;
  let btnRep = null;
  let barraProg = null;
  let selReg = null;
  let selVel = null;

  function parar() {
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
    tocando = false;
    atualizarBotaoRep();
  }

  function atualizarBotaoRep() {
    if (!btnRep) return;
    btnRep.setAttribute("aria-pressed", tocando ? "true" : "false");
    btnRep.setAttribute("aria-label", tocando ? "Pausar" : "Reproduzir");
    limpar(btnRep);
    btnRep.appendChild(iconeSvg(
      tocando
        ? "M6 5h4v14H6zm8 0h4v14h-4z"
        : "M8 5v14l11-7z"
    ));
  }

  function agendarProximo() {
    if (!tocando) return;
    if (k >= passos.length) {
      parar();
      return;
    }
    const intervalo = Math.max(80, Math.round(BASE_MS / velocidade));
    timer = window.setTimeout(() => {
      if (!tocando) return;
      if (k < passos.length) {
        irPara(k + 1, false);
        agendarProximo();
      } else {
        parar();
      }
    }, intervalo);
  }

  function iniciarReproducao() {
    if (!passos.length) return;
    if (k >= passos.length) k = 1;
    tocando = true;
    atualizarBotaoRep();
    notificar();
    agendarProximo();
  }

  function alternarReproducao() {
    if (tocando) parar();
    else iniciarReproducao();
  }

  function notificar() {
    const n = passos.length;
    const ev = n ? passos[k - 1] : null;
    if (regPasso) {
      regPasso.textContent = n ? `Passo ${k} de ${n}` : "Passo 0 de 0";
    }
    if (barraProg) {
      const pct = n > 1 ? Math.round(((k - 1) / (n - 1)) * 100) : (n === 1 ? 100 : 0);
      barraProg.style.width = `${pct}%`;
    }
    if (regEvento) {
      limpar(regEvento);
      if (ev) {
        const posStr = ev.posicao === null || ev.posicao === undefined ? "" : String(ev.posicao);
        regEvento.setAttribute("data-tipo", ev.tipo);
        regEvento.setAttribute("data-posicao", posStr);
        regEvento.appendChild(el("strong", { class: "mono", text: ev.tipo }));
        if (posStr !== "") {
          regEvento.appendChild(el("span", { class: "chip mono", text: `pos ${posStr}` }));
        }
        if (ev.detalhe) {
          regEvento.appendChild(el("span", { class: "mono", text: ev.detalhe }));
        }
        regEvento.appendChild(el("span", { class: "texto-suave", text: descreverEvento(ev.tipo) }));
      } else {
        regEvento.setAttribute("data-tipo", "");
        regEvento.setAttribute("data-posicao", "");
        regEvento.textContent = "Nenhum evento disponível.";
      }
    }
    if (callbacks.onPasso) {
      callbacks.onPasso(k, passos, ev);
    }
  }

  function irPara(novoK, interromper = true) {
    if (interromper && tocando) parar();
    const n = passos.length;
    if (!n) return;
    const limitado = Math.max(1, Math.min(n, novoK));
    k = limitado;
    notificar();
  }

  function montarEstrutura() {
    limpar(conteiner);
    const raiz = el("section", {
      class: "player-barra",
      "data-componente": "player",
      "aria-label": "Player de eventos",
      onKeydown: (ev) => {
        if (ev.key === "ArrowRight") {
          ev.preventDefault();
          irPara(k + 1);
        } else if (ev.key === "ArrowLeft") {
          ev.preventDefault();
          irPara(k - 1);
        } else if (ev.key === "Home") {
          ev.preventDefault();
          irPara(1);
        } else if (ev.key === "End") {
          ev.preventDefault();
          irPara(passos.length);
        } else if (ev.key === " ") {
          ev.preventDefault();
          alternarReproducao();
        }
      },
    });

    selReg = el("select", {
      "data-campo": "registro",
      "aria-label": "Selecionar sequência do lote",
      onChange: () => {
        const novoIdx = Number(selReg.value) || 0;
        if (novoIdx !== indiceRegistro) {
          parar();
          indiceRegistro = novoIdx;
          if (callbacks.onTrocarRegistro) {
            callbacks.onTrocarRegistro(indiceRegistro);
          }
        }
      },
    });
    registros.forEach((reg, idx) => {
      const linhaNum = reg.entrada && reg.entrada.linha ? reg.entrada.linha : idx + 1;
      const rot = reg.entrada && reg.entrada.rotulo ? ` (${reg.entrada.rotulo})` : "";
      selReg.appendChild(el("option", { value: String(idx), text: `Linha ${linhaNum}${rot}` }));
    });
    selReg.value = String(indiceRegistro);

    regPasso = el("span", {
      class: "player-passo",
      "data-regiao": "passo",
      "aria-live": "polite",
    });

    const topo = el("div", { class: "player-topo" }, [
      el("label", { class: "seletor-inline" }, [
        el("span", { text: "Registro" }),
        selReg,
      ]),
      regPasso,
    ]);

    const btnIni = el("button", {
      type: "button",
      class: "btn btn-icone",
      "data-acao": "inicio",
      "aria-label": "Início",
      title: "Início (Home)",
      onClick: () => irPara(1),
    }, [iconeSvg("M6 6h2v12H6zm3.5 6l8.5 6V6z")]);

    const btnAnt = el("button", {
      type: "button",
      class: "btn btn-icone",
      "data-acao": "anterior",
      "aria-label": "Passo anterior",
      title: "Anterior (←)",
      onClick: () => irPara(k - 1),
    }, [iconeSvg("M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z")]);

    btnRep = el("button", {
      type: "button",
      class: "btn btn-icone btn-icone-principal",
      "data-acao": "reproduzir",
      "aria-pressed": "false",
      "aria-label": "Reproduzir",
      title: "Reproduzir / Pausar (Espaço)",
      onClick: () => alternarReproducao(),
    });
    atualizarBotaoRep();

    const btnProx = el("button", {
      type: "button",
      class: "btn btn-icone",
      "data-acao": "proximo",
      "aria-label": "Próximo passo",
      title: "Próximo (→)",
      onClick: () => irPara(k + 1),
    }, [iconeSvg("M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z")]);

    const btnFim = el("button", {
      type: "button",
      class: "btn btn-pequeno",
      "data-acao": "fim",
      text: "Pular para o resultado",
      title: "Ir para o fim (End)",
      onClick: () => irPara(passos.length),
    });

    selVel = el("select", {
      "data-campo": "velocidade",
      "aria-label": "Velocidade de reprodução",
      onChange: () => {
        velocidade = Number(selVel.value) || 1;
        if (tocando) {
          window.clearTimeout(timer);
          agendarProximo();
        }
      },
    }, [
      el("option", { value: "0.5", text: "0.5×" }),
      el("option", { value: "1", text: "1×", selected: true }),
      el("option", { value: "2", text: "2×" }),
      el("option", { value: "4", text: "4×" }),
    ]);
    selVel.value = String(velocidade);

    const controles = el("div", { class: "player-controles" }, [
      el("div", { class: "player-botoes" }, [btnIni, btnAnt, btnRep, btnProx, btnFim]),
      el("label", { class: "seletor-inline" }, [
        el("span", { text: "Velocidade" }),
        selVel,
      ]),
    ]);

    barraProg = el("div", { class: "player-progresso-preenchimento" });
    const trilha = el("div", {
      class: "player-progresso-trilha",
      onClick: (ev) => {
        if (!passos.length) return;
        const ret = trilha.getBoundingClientRect();
        const frac = Math.max(0, Math.min(1, (ev.clientX - ret.left) / (ret.width || 1)));
        irPara(Math.round(frac * (passos.length - 1)) + 1);
      },
    }, [barraProg]);

    regEvento = el("div", { class: "player-evento", "data-regiao": "evento-atual" });

    raiz.appendChild(topo);
    raiz.appendChild(controles);
    raiz.appendChild(trilha);
    raiz.appendChild(regEvento);
    conteiner.appendChild(raiz);
  }

  function definirRegistros(novosRegistros, idxInicial = 0) {
    parar();
    registros = novosRegistros || [];
    indiceRegistro = Math.max(0, Math.min(registros.length - 1, idxInicial));
    const reg = registros[indiceRegistro];
    passos = (reg && reg.passos) || [];
    const modo = obterModoAtual();
    const reduzido = movimentoReduzido();
    k = modo === "rapido" ? Math.max(1, passos.length) : 1;
    montarEstrutura();
    notificar();
    if (modo === "animado" && !reduzido && passos.length > 1) {
      iniciarReproducao();
    }
  }

  function selecionarRegistro(idx) {
    parar();
    indiceRegistro = Math.max(0, Math.min(registros.length - 1, idx));
    if (selReg) selReg.value = String(indiceRegistro);
    const reg = registros[indiceRegistro];
    passos = (reg && reg.passos) || [];
    const modo = obterModoAtual();
    const reduzido = movimentoReduzido();
    k = modo === "rapido" ? Math.max(1, passos.length) : 1;
    notificar();
    if (modo === "animado" && !reduzido && passos.length > 1) {
      iniciarReproducao();
    }
  }

  return {
    definirRegistros,
    selecionarRegistro,
    irPara,
    parar,
    passoAtual: () => k,
  };
}
