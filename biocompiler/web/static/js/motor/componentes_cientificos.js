/* Componentes científicos reutilizáveis (nucleotídeo, códon, aminoácido e marcador). */

import { el } from "../dom.js";

export function criarNucleotideo(base, indice, opcoes = {}) {
  const attrs = {
    class: `base-pastilha base-${String(base || "").toLowerCase()}${opcoes.classe ? ` ${opcoes.classe}` : ""}`,
    "data-base": String(base || ""),
    "data-indice": String(indice),
    text: String(base || ""),
  };
  if (opcoes.selecionado) attrs["data-selecionado"] = "true";
  if (opcoes.onClick) attrs.onClick = opcoes.onClick;
  return el("span", attrs);
}

export function criarCodon(trinca, ordem, indice, opcoes = {}) {
  const attrs = {
    type: "button",
    class: `codon-grupo mono${opcoes.selecionado ? " selecionado" : ""}`,
    "data-codon-mrna": "",
    "data-ordem": String(ordem),
    "data-indice": String(indice),
    "aria-pressed": opcoes.selecionado ? "true" : "false",
    "aria-label": `Códon ${trinca} na posição ${indice}`,
    text: trinca,
    onClick: opcoes.onClick,
  };
  if (opcoes.selecionado) attrs["data-selecionado"] = "true";
  return el("button", attrs);
}

export function criarAminoacido(aa, ordem, opcoes = {}) {
  const attrs = {
    type: "button",
    class: `aa-conta${opcoes.selecionado ? " selecionado" : ""}`,
    "data-aminoacido": "",
    "data-ordem": String(ordem),
    "aria-pressed": opcoes.selecionado ? "true" : "false",
    "aria-label": `Aminoácido ${aa} (ordem ${ordem + 1})`,
    text: aa,
    onClick: opcoes.onClick,
  };
  if (opcoes.selecionado) attrs["data-selecionado"] = "true";
  return el("button", attrs);
}

export function criarMarcador(tipo, rotulo, indice, opcoes = {}) {
  const attrs = {
    type: "button",
    class: `marcador-pilula marcador-${tipo}`,
    "data-marca": tipo,
    "data-indice": String(indice),
    text: rotulo,
    onClick: opcoes.onClick,
  };
  return el("button", attrs);
}
