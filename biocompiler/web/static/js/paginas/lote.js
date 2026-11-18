/* Controlador das páginas de lote AT1, AT2 e AT3 com player, visualizações SVG e inspetor. */

import { ativarAba, definirStatus, registrarHistorico } from "../app.js";
import { executarLote, exportarZip, obterCodigoGenetico, obterExemplos } from "../api.js";
import { atualizarContadores, conectarZonaArquivo } from "../componentes/editor.js";
import { criarEtapas } from "../componentes/etapas.js";
import { renderizarListaArtefatos } from "../componentes/exportacao.js";
import { criarInspetor } from "../componentes/inspetor.js";
import { criarPlayer } from "../componentes/player.js";
import { renderizarResultadosLote } from "../componentes/resultados.js";
import { criarVizAT1 } from "../componentes/viz_at1.js";
import { criarVizAT2 } from "../componentes/viz_at2.js";
import { criarVizAT3 } from "../componentes/viz_at3.js";
import { el, limpar, qs } from "../dom.js";

const ALFABETOS = { at1: "ATCG", at2: "AUCG", at3: "AUCG" };

let ultimoTextoArquivo = null;
let tabelaGenetica = null;
let codonsUsados = new Set();
let codonAtualTabela = null;

function renderizarTabelaCodons() {
  const cont = qs('[data-regiao="tabela-codons"]');
  const filtroEl = qs('[data-campo="filtro-codon"]');
  if (!cont || !tabelaGenetica) return;
  limpar(cont);
  const termo = (filtroEl ? filtroEl.value : "").trim().toLowerCase();
  const stops = new Set(tabelaGenetica.stops || []);
  const entradas = Object.entries(tabelaGenetica.codigos || {}).sort(([a], [b]) => a.localeCompare(b));
  for (const [codon, aa] of entradas) {
    if (termo && !codon.toLowerCase().includes(termo) && !aa.toLowerCase().includes(termo)) {
      continue;
    }
    const cls = ["codon-card"];
    if (stops.has(codon)) cls.push("stop");
    if (codonsUsados.has(codon)) cls.push("percorrido");
    if (codonAtualTabela === codon) cls.push("atual");
    cont.appendChild(el("div", { class: cls.join(" "), "data-codon": codon }, [
      el("strong", { text: codon }),
      el("span", { text: aa }),
    ]));
  }
}

function sequenciaReferencia(at, reg) {
  if (!reg) return "";
  if (at === "at3") {
    return (reg.dados && reg.dados.regiao_transcrita) || "";
  }
  return (reg.entrada && reg.entrada.sequencia) || "";
}

document.addEventListener("DOMContentLoaded", async () => {
  const at = document.body.dataset.pagina;
  const alfabeto = ALFABETOS[at] || "ATCG";
  const textarea = qs('[data-campo="sequencias"]');
  const contadores = qs('[data-regiao="contadores-lote"]');
  const btnExec = qs('[data-acao="executar"]');
  const btnExemplos = qs('[data-acao="carregar-exemplos"]');
  const btnLimpar = qs('[data-acao="limpar"]');
  const btnExportar = qs('[data-acao="exportar"]');
  const zonaArq = qs('[data-zona="arquivo-lote"]');
  const inputArq = qs('[data-campo="arquivo"]');
  const regResultados = qs('[data-regiao="resultados"]');
  const regEtapas = qs('[data-regiao="etapas"]');
  const regVis = qs('[data-regiao="visualizacao"]');
  const regListaArq = qs('[data-regiao="lista-artefatos"]');

  renderizarListaArtefatos(regListaArq, at);

  const atualizar = () => atualizarContadores(textarea.value, contadores, alfabeto);
  textarea.addEventListener("input", () => {
    ultimoTextoArquivo = null;
    atualizar();
  });

  if (at === "at3") {
    const filtro = qs('[data-campo="filtro-codon"]');
    if (filtro) filtro.addEventListener("input", renderizarTabelaCodons);
    try {
      tabelaGenetica = await obterCodigoGenetico();
      renderizarTabelaCodons();
    } catch (err) {
      definirStatus(`Erro ao carregar código genético: ${err.message}`, "erro");
    }
  }

  conectarZonaArquivo(zonaArq, inputArq, (texto, nome) => {
    ultimoTextoArquivo = texto;
    textarea.value = texto.replace(/\r\n/g, "\n").replace(/\n$/, "");
    atualizar();
    definirStatus(`Arquivo carregado: ${nome}`);
  });

  if (btnExemplos) {
    btnExemplos.addEventListener("click", async () => {
      try {
        const ex = await obterExemplos();
        ultimoTextoArquivo = null;
        textarea.value = (ex[at] || []).join("\n");
        atualizar();
        definirStatus("Exemplos carregados.");
      } catch (err) {
        definirStatus(err.message, "erro");
      }
    });
  }

  if (btnLimpar) {
    btnLimpar.addEventListener("click", () => {
      ultimoTextoArquivo = null;
      textarea.value = "";
      atualizar();
      definirStatus("Entrada limpa.");
    });
  }

  let itensAtuais = [];
  let etapasCtrl = null;
  let playerCtrl = null;
  let inspetorCtrl = null;
  let vizCtrl = null;

  function prepararPalcoVisualizacao() {
    if (!regVis) return;
    regVis.classList.remove("vazio");
    limpar(regVis);
    const slotPlayer = el("div");
    const slotViz = el("div");
    const slotInspetor = el("aside", { class: "inspetor-painel", "data-regiao": "inspetor" });
    regVis.appendChild(slotPlayer);
    regVis.appendChild(el("div", { class: "viz-grade" }, [slotViz, slotInspetor]));

    inspetorCtrl = criarInspetor(slotInspetor);
    const onInspecionar = (pos) => inspetorCtrl.inspecionar(pos);

    if (at === "at1") {
      vizCtrl = criarVizAT1(slotViz, onInspecionar);
    } else if (at === "at2") {
      vizCtrl = criarVizAT2(slotViz, onInspecionar);
    } else {
      vizCtrl = criarVizAT3(slotViz, onInspecionar, (percorridos, atualCodon) => {
        codonsUsados = percorridos;
        codonAtualTabela = atualCodon;
        renderizarTabelaCodons();
      });
    }

    etapasCtrl = criarEtapas(regEtapas, (novoK) => {
      if (playerCtrl) playerCtrl.irPara(novoK);
    });

    playerCtrl = criarPlayer(slotPlayer, {
      onTrocarRegistro: (idx) => {
        const reg = itensAtuais[idx];
        if (!reg) return;
        const linha = reg.entrada && reg.entrada.linha ? reg.entrada.linha : idx + 1;
        etapasCtrl.definirDados(reg.passos, `Eventos da entrada #${linha}`, 1);
        inspetorCtrl.definirContexto(sequenciaReferencia(at, reg), reg.passos);
        vizCtrl.definirRegistro(reg);
        playerCtrl.selecionarRegistro(idx);
      },
      onPasso: (k, passos) => {
        if (vizCtrl) vizCtrl.atualizar(k, passos);
        if (etapasCtrl) etapasCtrl.atualizarPasso(k);
      },
    });
  }

  async function executar(selecionarAba = true) {
    const payload = ultimoTextoArquivo !== null
      ? { texto: ultimoTextoArquivo }
      : { sequencias: textarea.value === "" ? [] : textarea.value.replace(/\r\n/g, "\n").split("\n") };

    btnExec.disabled = true;
    btnExec.setAttribute("aria-busy", "true");
    definirStatus("Executando…");
    try {
      const itens = await executarLote(at, payload);
      itensAtuais = itens;
      renderizarResultadosLote(regResultados, at, itens);
      if (itens.length && regVis && regEtapas) {
        prepararPalcoVisualizacao();
        const primeiro = itens[0];
        etapasCtrl.definirDados(primeiro.passos, "Eventos da primeira entrada", 1);
        inspetorCtrl.definirContexto(sequenciaReferencia(at, primeiro), primeiro.passos);
        vizCtrl.definirRegistro(primeiro);
        playerCtrl.definirRegistros(itens, 0);
      }
      const ok = itens.filter((i) => i.status === "OK").length;
      definirStatus(`Concluído: ${itens.length} registro(s), ${ok} correto(s).`, ok === itens.length ? "ok" : "");
      registrarHistorico({
        atividade: at,
        resumo: `${itens.length} registro(s), ${ok} correto(s)`,
        href: `/${at}?${new URLSearchParams({ seq: textarea.value, executar: "1" }).toString()}`,
      });
      if (selecionarAba) ativarAba("tab-resultados");
    } catch (err) {
      definirStatus(err.message, "erro");
    } finally {
      btnExec.disabled = false;
      btnExec.removeAttribute("aria-busy");
    }
  }

  btnExec.addEventListener("click", () => executar(true));
  textarea.addEventListener("keydown", (ev) => {
    if (ev.ctrlKey && ev.key === "Enter") {
      ev.preventDefault();
      executar(true);
    }
  });

  if (btnExportar) {
    btnExportar.addEventListener("click", async () => {
      const payload = ultimoTextoArquivo !== null
        ? { atividade: at, texto: ultimoTextoArquivo }
        : { atividade: at, sequencias: textarea.value === "" ? [] : textarea.value.replace(/\r\n/g, "\n").split("\n") };
      try {
        await exportarZip(payload);
        definirStatus("Pacote .zip exportado.", "ok");
      } catch (err) {
        definirStatus(err.message, "erro");
      }
    });
  }

  const params = new URLSearchParams(window.location.search);
  const seqUrl = params.get("seq");
  if (seqUrl !== null) {
    textarea.value = seqUrl;
  }
  atualizar();
  if (params.get("executar") === "1") {
    await executar(!params.get("aba"));
  }
});
