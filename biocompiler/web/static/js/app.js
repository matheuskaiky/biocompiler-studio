/* Casca da interface: tema, menu responsivo, abas WAI-ARIA, ajuda, status e histórico. */

import { qs, qsa } from "./dom.js";

const CHAVE_TEMA = "biocompiler_tema";
const CHAVE_MODO = "biocompiler_modo";
const CHAVE_HISTORICO = "biocompiler_historico_sessao";

export function definirStatus(mensagem, tipo = "") {
  const reg = qs('[data-regiao="status"]');
  if (!reg) return;
  reg.textContent = mensagem;
  reg.className = "barra-status" + (tipo ? ` ${tipo}` : "");
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
      painel.classList.toggle("painel-oculto", !selecionada);
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
    document.documentElement.setAttribute("data-tema", proximo);
    try {
      window.localStorage.setItem(CHAVE_TEMA, proximo);
    } catch (e) {
      // ignora indisponibilidade de storage
    }
    atualizarRotulo();
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
  const sel = qs('[data-campo="modo-reproducao"]');
  if (!sel) return;
  try {
    const salvo = window.localStorage.getItem(CHAVE_MODO);
    if (salvo && ["rapido", "guiado", "animado"].includes(salvo)) {
      sel.value = salvo;
    }
  } catch (e) {
    // ignora
  }
  sel.addEventListener("change", () => {
    try {
      window.localStorage.setItem(CHAVE_MODO, sel.value);
    } catch (e) {
      // ignora
    }
  });
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

document.addEventListener("DOMContentLoaded", () => {
  inicializarTema();
  inicializarMenu();
  inicializarModo();
  inicializarAjuda();
  inicializarAbas();
  const params = new URLSearchParams(window.location.search);
  const abaParam = params.get("aba");
  if (abaParam) ativarAbaPorNome(abaParam);
});
