/* Casca da interface: tema, menu responsivo, abas WAI-ARIA, ajuda, status e histórico. */

import { qs, qsa } from "./dom.js";

const CHAVE_TEMA = "biocompiler_tema";
const CHAVE_MODO = "biocompiler_modo";
const CHAVE_HISTORICO = "biocompiler_historico_sessao";

let timerStatus = null;

export function definirStatus(mensagem, tipo = "") {
  const reg = qs('[data-regiao="status"]');
  if (!reg) return;
  reg.textContent = mensagem;
  reg.className = "barra-status" + (tipo ? ` ${tipo}` : "");
  if (timerStatus) window.clearTimeout(timerStatus);
  if (tipo !== "erro") {
    timerStatus = window.setTimeout(() => {
      reg.classList.add("esmaecida");
    }, 4500);
  }
}

export function ativarAba(alvoId) {
  const abas = qsa('[role="tab"]');
  if (!abas.length) return;
  const alvo = abas.find((a) => a.id === alvoId || a.getAttribute("aria-controls") === alvoId);
  if (!alvo) return;
  for (const aba of abas) {
    const selecionada = aba === alvo;
    aba.setAttribute("aria-selected", selecionada ? "true" : "false");
    aba.setAttribute("tabindex", selecionada ? "0" : "-1");
    const painelId = aba.getAttribute("aria-controls");
    const painel = painelId ? document.getElementById(painelId) : null;
    if (painel) {
      const estavaOculto = painel.classList.contains("painel-oculto");
      painel.classList.toggle("painel-oculto", !selecionada);
      if (selecionada && estavaOculto && !movimentoReduzido() && typeof painel.animate === "function") {
        painel.animate([
          { opacity: 0, transform: "translateY(4px)" },
          { opacity: 1, transform: "translateY(0)" },
        ], {
          duration: 200,
          easing: "cubic-bezier(0.16, 1, 0.3, 1)",
        });
      }
    }
  }
}

export function ativarAbaPorNome(nome) {
  if (!nome) return;
  const norm = nome.toLowerCase();
  const abas = qsa('[role="tab"]');
  const alvo = abas.find((a) =>
    a.id.toLowerCase().includes(norm)
    || a.textContent.trim().toLowerCase().includes(norm)
  );
  if (alvo) ativarAba(alvo.id);
}

function inicializarAbas() {
  const lista = qs('[role="tablist"]');
  if (!lista) return;
  const abas = qsa('[role="tab"]', lista);
  for (const aba of abas) {
    aba.addEventListener("click", () => ativarAba(aba.id));
    aba.addEventListener("keydown", (ev) => {
      const idx = abas.indexOf(aba);
      let prox = -1;
      if (ev.key === "ArrowRight") prox = (idx + 1) % abas.length;
      else if (ev.key === "ArrowLeft") prox = (idx - 1 + abas.length) % abas.length;
      else if (ev.key === "Home") prox = 0;
      else if (ev.key === "End") prox = abas.length - 1;
      else if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        ativarAba(aba.id);
        return;
      }
      if (prox >= 0) {
        ev.preventDefault();
        abas[prox].focus();
        ativarAba(abas[prox].id);
      }
    });
  }
}

function inicializarTema() {
  const btn = qs('[data-acao="tema"]');
  if (!btn) return;
  const atualizarRotulo = () => {
    const atual = document.documentElement.getAttribute("data-tema") || "escuro";
    btn.textContent = atual === "escuro" ? "Tema claro" : "Tema escuro";
  };
  atualizarRotulo();
  btn.addEventListener("click", () => {
    const atual = document.documentElement.getAttribute("data-tema") || "escuro";
    const proximo = atual === "escuro" ? "claro" : "escuro";
    const aplicar = () => {
      document.documentElement.setAttribute("data-tema", proximo);
      try {
        window.localStorage.setItem(CHAVE_TEMA, proximo);
      } catch (e) {
        // ignora indisponibilidade de storage
      }
      atualizarRotulo();
    };
    if (!movimentoReduzido() && typeof document.startViewTransition === "function") {
      document.startViewTransition(aplicar);
    } else {
      aplicar();
    }
  });
}

function inicializarMenu() {
  const btn = qs('[data-acao="menu"]');
  const lateral = qs("#barra-lateral");
  if (!btn || !lateral) return;
  btn.addEventListener("click", () => {
    const aberta = lateral.classList.toggle("aberta");
    btn.setAttribute("aria-expanded", aberta ? "true" : "false");
  });
}

function inicializarModo() {
  const grupo = qs('[data-campo="modo-reproducao"]');
  if (!grupo) return;
  const opcoes = Array.from(grupo.querySelectorAll('[role="radio"][data-modo]'));
  const validos = ["rapido", "guiado", "animado"];

  const aplicarModo = (valor, salvar = false) => {
    const modo = validos.includes(valor) ? valor : "rapido";
    grupo.setAttribute("data-valor", modo);
    for (const btn of opcoes) {
      const ativo = btn.getAttribute("data-modo") === modo;
      btn.setAttribute("aria-checked", ativo ? "true" : "false");
      btn.tabIndex = ativo ? 0 : -1;
    }
    if (salvar) {
      try {
        window.localStorage.setItem(CHAVE_MODO, modo);
      } catch (e) {
        // ignora
      }
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("modo", modo);
        window.history.replaceState(null, "", url.pathname + url.search + url.hash);
      } catch (e) {
        // ignora
      }
      grupo.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };

  const paramModo = new URLSearchParams(window.location.search).get("modo");
  if (paramModo && validos.includes(paramModo)) {
    aplicarModo(paramModo, false);
  } else {
    try {
      const salvo = window.localStorage.getItem(CHAVE_MODO);
      aplicarModo(salvo && validos.includes(salvo) ? salvo : "rapido", false);
    } catch (e) {
      aplicarModo("rapido", false);
    }
  }

  opcoes.forEach((btn, idx) => {
    btn.addEventListener("click", () => aplicarModo(btn.getAttribute("data-modo"), true));
    btn.addEventListener("keydown", (ev) => {
      let prox = -1;
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") {
        prox = (idx + 1) % opcoes.length;
      } else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") {
        prox = (idx - 1 + opcoes.length) % opcoes.length;
      }
      if (prox >= 0) {
        ev.preventDefault();
        opcoes[prox].focus();
        aplicarModo(opcoes[prox].getAttribute("data-modo"), true);
      }
    });
  });
}

export function obterModoAtual() {
  const validos = ["rapido", "guiado", "animado"];
  const grupo = qs('[data-campo="modo-reproducao"]');
  const valorControle = grupo && (grupo.getAttribute("data-valor") || grupo.value);
  if (valorControle && validos.includes(valorControle)) {
    return valorControle;
  }
  const paramModo = new URLSearchParams(window.location.search).get("modo");
  if (paramModo && validos.includes(paramModo)) {
    return paramModo;
  }
  return "rapido";
}

export function movimentoReduzido() {
  return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
}

function inicializarAjuda() {
  const btn = qs('[data-acao="ajuda"]');
  const dlg = qs("#dialogo-ajuda");
  const fechar = qs('[data-acao="fechar-ajuda"]');
  if (!btn || !dlg) return;

  const focaveis = () => Array.from(dlg.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )).filter((item) => !item.hasAttribute("hidden") && item.offsetParent !== null);

  const fecharDialogo = () => {
    if (typeof dlg.close === "function" && dlg.open) {
      dlg.close();
    } else {
      dlg.removeAttribute("open");
      btn.focus();
    }
  };

  btn.addEventListener("click", () => {
    if (typeof dlg.showModal === "function") {
      if (!dlg.open) dlg.showModal();
    } else {
      dlg.setAttribute("open", "");
    }
    const lista = focaveis();
    if (!dlg.contains(document.activeElement) && lista.length) {
      lista[0].focus();
    }
  });

  if (fechar) {
    fechar.addEventListener("click", fecharDialogo);
  }

  dlg.addEventListener("close", () => {
    btn.focus();
  });

  dlg.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      fecharDialogo();
      return;
    }
    if (e.key !== "Tab") return;
    const lista = focaveis();
    if (!lista.length) {
      e.preventDefault();
      return;
    }
    const primeiro = lista[0];
    const ultimo = lista[lista.length - 1];
    const atual = document.activeElement;
    if (!dlg.contains(atual)) {
      e.preventDefault();
      (e.shiftKey ? ultimo : primeiro).focus();
    } else if (e.shiftKey && atual === primeiro) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && atual === ultimo) {
      e.preventDefault();
      primeiro.focus();
    }
  });
}

export function lerHistorico() {
  try {
    const bruto = window.sessionStorage.getItem(CHAVE_HISTORICO);
    return bruto ? JSON.parse(bruto) : [];
  } catch (e) {
    return [];
  }
}

export function registrarHistorico(item) {
  const lista = lerHistorico();
  lista.unshift({ ...item, dataHora: new Date().toLocaleString("pt-BR") });
  try {
    window.sessionStorage.setItem(CHAVE_HISTORICO, JSON.stringify(lista.slice(0, 40)));
  } catch (e) {
    // ignora
  }
}

export function limparHistorico() {
  try {
    window.sessionStorage.removeItem(CHAVE_HISTORICO);
  } catch (e) {
    // ignora
  }
}

function inicializarApresentacao() {
  const btn = qs('[data-acao="apresentacao"]');
  const rodape = qs('[data-regiao="rodape-apresentacao"]');
  if (!btn) return;

  const atualizarRodape = (ativo) => {
    if (!rodape) return;
    rodape.hidden = !ativo;
    if (!ativo) return;
    const atalhos = [];
    if (qs('[data-componente="player"]')) {
      atalhos.push("←/→: passo", "Espaço: reproduzir/pausar", "F: resultado final");
    }
    if (qs('[data-acao="exportar"]')) {
      atalhos.push("E: exportar .zip");
    }
    atalhos.push("Esc: sair");
    rodape.textContent = `Modo apresentação · ${atalhos.join(" · ")}`;
  };

  const sair = () => {
    document.documentElement.removeAttribute("data-apresentacao");
    btn.setAttribute("aria-pressed", "false");
    atualizarRodape(false);
    try {
      if (document.fullscreenElement && document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    } catch (e) {
      // ignora
    }
  };

  const entrar = () => {
    document.documentElement.setAttribute("data-apresentacao", "true");
    btn.setAttribute("aria-pressed", "true");
    atualizarRodape(true);
    try {
      if (document.documentElement.requestFullscreen) {
        document.documentElement.requestFullscreen().catch(() => {});
      }
    } catch (e) {
      // ignora indisponibilidade de fullscreen em headless
    }
  };

  btn.addEventListener("click", () => {
    if (document.documentElement.getAttribute("data-apresentacao") === "true") {
      sair();
    } else {
      entrar();
    }
  });

  document.addEventListener("keydown", (ev) => {
    if (document.documentElement.getAttribute("data-apresentacao") !== "true") return;
    const ativo = document.activeElement;
    const tag = ativo ? ativo.tagName : "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (ativo && ativo.isContentEditable)) {
      if (ev.key === "Escape") sair();
      return;
    }
    if (ev.key === "Escape") {
      ev.preventDefault();
      sair();
      return;
    }
    if (ev.key === "ArrowRight") {
      const b = qs('[data-componente="player"] [data-acao="proximo"]');
      if (b) { ev.preventDefault(); b.click(); }
    } else if (ev.key === "ArrowLeft") {
      const b = qs('[data-componente="player"] [data-acao="anterior"]');
      if (b) { ev.preventDefault(); b.click(); }
    } else if (ev.key === " ") {
      const b = qs('[data-componente="player"] [data-acao="reproduzir"]');
      if (b) { ev.preventDefault(); b.click(); }
    } else if (ev.key === "f" || ev.key === "F") {
      const b = qs('[data-componente="player"] [data-acao="fim"]');
      if (b) { ev.preventDefault(); b.click(); }
    } else if (ev.key === "e" || ev.key === "E") {
      const b = qs('[data-acao="exportar"]');
      if (b) { ev.preventDefault(); b.click(); }
    }
  });
}

function conectarIndicadorSegmentado(grupo, seletorAtivo) {
  if (!grupo || grupo.querySelector("[data-indicador-segmento]")) return;
  const ind = document.createElement("span");
  ind.className = "indicador-segmento";
  ind.setAttribute("data-indicador-segmento", "");
  ind.setAttribute("aria-hidden", "true");
  grupo.insertBefore(ind, grupo.firstChild);

  const posicionar = () => {
    const ativo = grupo.querySelector(seletorAtivo);
    if (!ativo) {
      ind.style.opacity = "0";
      return;
    }
    const gRect = grupo.getBoundingClientRect();
    const aRect = ativo.getBoundingClientRect();
    if (aRect.width === 0) return;
    const dx = aRect.left - gRect.left - grupo.clientLeft;
    ind.style.opacity = "1";
    ind.style.width = `${aRect.width}px`;
    ind.style.transform = `translateX(${dx}px)`;
  };

  posicionar();
  grupo.addEventListener("click", () => window.requestAnimationFrame(posicionar));
  grupo.addEventListener("change", posicionar);
  window.addEventListener("resize", posicionar);
  if (typeof MutationObserver === "function") {
    const obs = new MutationObserver(posicionar);
    obs.observe(grupo, {
      subtree: true,
      attributes: true,
      attributeFilter: ["aria-checked", "aria-pressed"],
    });
  }
}

function inicializarIndicadoresSegmentados() {
  conectarIndicadorSegmentado(qs(".modo-segmentado"), '[aria-checked="true"]');
  for (const seg of qsa("[data-segmento-metodo]")) {
    conectarIndicadorSegmentado(seg, '[aria-pressed="true"]');
  }
}

document.addEventListener("DOMContentLoaded", () => {
  inicializarTema();
  inicializarMenu();
  inicializarModo();
  inicializarAjuda();
  inicializarAbas();
  inicializarApresentacao();
  inicializarIndicadoresSegmentados();
  const params = new URLSearchParams(window.location.search);
  const abaParam = params.get("aba");
  if (abaParam) ativarAbaPorNome(abaParam);
});
