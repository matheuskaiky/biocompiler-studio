/* Player de eventos sincronizado com linha do tempo acessível, vidro e orquestrador. */

import { movimentoReduzido, obterModoAtual } from "../app.js";
import { el, limpar } from "../dom.js";
import { estadoGlobal } from "../motor/estado.js";
import { cancelarTudo } from "../motor/orquestrador.js";
import { descreverEvento } from "./inspetor.js";

const BASE_MS = 800;
const NS_SVG = "http:" + "//www.w3.org/2000/svg";

function criarIcone(nome) {
  const svg = document.createElementNS(NS_SVG, "svg");
  svg.setAttribute("viewBox", "0 0 20 20");
  svg.setAttribute("width", "16");
  svg.setAttribute("height", "16");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("data-icone", nome);

  const add = (tag, attrs) => {
    const node = document.createElementNS(NS_SVG, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
    svg.appendChild(node);
  };

  if (nome === "reproduzir") {
    add("polygon", { points: "6,4 16,10 6,16", fill: "currentColor", stroke: "none" });
  } else if (nome === "pausar") {
    add("line", { x1: 7, y1: 4.5, x2: 7, y2: 15.5 });
    add("line", { x1: 13, y1: 4.5, x2: 13, y2: 15.5 });
  } else if (nome === "inicio") {
    add("line", { x1: 5, y1: 4.5, x2: 5, y2: 15.5 });
    add("polyline", { points: "14,4.5 8.5,10 14,15.5" });
  } else if (nome === "anterior") {
    add("polyline", { points: "12.5,4.5 7,10 12.5,15.5" });
  } else if (nome === "proximo") {
    add("polyline", { points: "7.5,4.5 13,10 7.5,15.5" });
  } else if (nome === "fim") {
    add("polyline", { points: "6,4.5 11.5,10 6,15.5" });
    add("line", { x1: 15, y1: 4.5, x2: 15, y2: 15.5 });
  }
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
  let trilha = null;
  let barraProg = null;
  let alca = null;
  let marcosEl = null;
  let selReg = null;
  let selVel = null;

  function parar() {
    if (timer) {
      window.clearTimeout(timer);
      timer = null;
    }
    tocando = false;
    cancelarTudo(document);
    atualizarBotaoRep();
  }

  function atualizarBotaoRep() {
    if (!btnRep) return;
    btnRep.setAttribute("aria-pressed", tocando ? "true" : "false");
    btnRep.setAttribute("aria-label", tocando ? "Pausar" : "Reproduzir");
    limpar(btnRep);
    btnRep.appendChild(criarIcone(tocando ? "pausar" : "reproduzir"));
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

  function atualizarMarcos() {
    if (!marcosEl) return;
    limpar(marcosEl);
    const n = passos.length;
    if (!n) return;
    const vistos = new Set();
    for (let idx = 0; idx < n; idx += 1) {
      const tipo = passos[idx]?.tipo;
      if (!tipo || vistos.has(tipo)) continue;
      vistos.add(tipo);
      const passo = idx + 1;
      const pct = n > 1 ? ((passo - 1) / (n - 1)) * 100 : 0;
      const marco = el("span", {
        class: "linha-tempo-marco",
        "data-marco": "",
        "data-tipo": tipo,
        "data-passo": String(passo),
        title: `${tipo} (passo ${passo})`,
      });
      marco.style.left = `${pct}%`;
      marcosEl.appendChild(marco);
    }
  }

  function notificar() {
    const n = passos.length;
    const ev = n ? passos[k - 1] : null;
    if (regPasso) {
      regPasso.textContent = n ? `Passo ${k} de ${n}` : "Passo 0 de 0";
    }
    const pct = n > 1 ? ((k - 1) / (n - 1)) * 100 : (n === 1 ? 100 : 0);
    if (barraProg) {
      barraProg.style.width = `${pct}%`;
    }
    if (alca) {
      alca.style.left = `${pct}%`;
    }
    if (trilha) {
      trilha.setAttribute("aria-valuemin", "1");
      trilha.setAttribute("aria-valuemax", String(Math.max(1, n)));
      trilha.setAttribute("aria-valuenow", String(k));
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
    estadoGlobal.definir({ registro: indiceRegistro, passo: k });
    if (callbacks.onPasso) {
      callbacks.onPasso(k, passos, ev);
    }
  }

  function irPara(novoK, interromper = true, cancelarDepois = false) {
    if (interromper && tocando) parar();
    const n = passos.length;
    if (!n) return;
    if (interromper) cancelarTudo(document);
    const limitado = Math.max(1, Math.min(n, novoK));
    k = limitado;
    notificar();
    if (cancelarDepois) cancelarTudo(document);
  }

  function passoPorPosicaoX(clientX) {
    const n = passos.length;
    if (!n || !trilha) return 1;
    const ret = trilha.getBoundingClientRect();
    const frac = Math.max(0, Math.min(1, (clientX - ret.left) / (ret.width || 1)));
    return 1 + Math.round(frac * (n - 1));
  }

  function montarEstrutura() {
    limpar(conteiner);
    const raiz = el("section", {
      class: "player-barra",
      "data-componente": "player",
      "data-superficie": "vidro",
      "aria-label": "Player de eventos",
      onKeydown: (ev) => {
        if (ev.target === trilha) return;
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

    const regValue = (reg, idx) => {
      if (reg && reg.dados && reg.dados.metodo) return String(reg.dados.metodo);
      if (reg && reg.entrada) return String(idx);
      return String(idx);
    };

    selReg = el("select", {
      "data-campo": "registro",
      "aria-label": "Selecionar sequência ou método",
      onChange: () => {
        const novoIdx = registros.findIndex((r, idx) => regValue(r, idx) === selReg.value);
        if (novoIdx >= 0 && novoIdx !== indiceRegistro) {
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
      const rotulo = reg.dados && reg.dados.metodo
        ? String(reg.dados.metodo).toUpperCase()
        : `Linha ${linhaNum}${rot}`;
      selReg.appendChild(el("option", { value: regValue(reg, idx), text: rotulo }));
    });
    selReg.value = regValue(registros[indiceRegistro], indiceRegistro);

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
    }, [criarIcone("inicio")]);

    const btnAnt = el("button", {
      type: "button",
      class: "btn btn-icone",
      "data-acao": "anterior",
      "aria-label": "Passo anterior",
      title: "Anterior (←)",
      onClick: () => irPara(k - 1),
    }, [criarIcone("anterior")]);

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
    }, [criarIcone("proximo")]);

    const btnFim = el("button", {
      type: "button",
      class: "btn btn-pequeno",
      "data-acao": "fim",
      "aria-label": "Pular para o resultado",
      title: "Ir para o fim (End)",
      onClick: () => irPara(passos.length, true, true),
    }, [criarIcone("fim"), el("span", { text: "Pular para o resultado" })]);

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
    alca = el("span", { class: "linha-tempo-alca", "aria-hidden": "true" });
    marcosEl = el("div", { class: "linha-tempo-marcos", "aria-hidden": "true" });

    trilha = el("div", {
      class: "player-progresso-trilha linha-tempo",
      "data-componente": "linha-tempo",
      role: "slider",
      tabindex: "0",
      "aria-label": "Linha do tempo dos eventos",
      "aria-valuemin": "1",
      "aria-valuemax": String(Math.max(1, passos.length)),
      "aria-valuenow": String(k),
      onMousedown: (ev) => {
        if (!passos.length) return;
        ev.preventDefault();
        trilha.focus();
        trilha.classList.add("arrastando");
        irPara(passoPorPosicaoX(ev.clientX));
        const aoMover = (mev) => {
          irPara(passoPorPosicaoX(mev.clientX));
        };
        const aoSoltar = () => {
          trilha.classList.remove("arrastando");
          document.removeEventListener("mousemove", aoMover);
          document.removeEventListener("mouseup", aoSoltar);
        };
        document.addEventListener("mousemove", aoMover);
        document.addEventListener("mouseup", aoSoltar);
      },
      onKeydown: (ev) => {
        const n = passos.length;
        if (!n) return;
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
          irPara(n);
        } else if (ev.key === "PageDown") {
          ev.preventDefault();
          irPara(Math.min(n, k + 10));
        } else if (ev.key === "PageUp") {
          ev.preventDefault();
          irPara(Math.max(1, k - 10));
        } else if (ev.key === " ") {
          ev.preventDefault();
          alternarReproducao();
        }
      },
    }, [barraProg, marcosEl, alca]);

    atualizarMarcos();

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
    if (selReg) {
      const regSel = registros[indiceRegistro];
      selReg.value = regSel && regSel.dados && regSel.dados.metodo
        ? String(regSel.dados.metodo)
        : String(indiceRegistro);
    }
    const reg = registros[indiceRegistro];
    passos = (reg && reg.passos) || [];
    const modo = obterModoAtual();
    const reduzido = movimentoReduzido();
    k = modo === "rapido" ? Math.max(1, passos.length) : 1;
    atualizarMarcos();
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
