/* Utilitários DOM seguros (somente createElement/textContent/setAttribute). */

export function el(tag, attrs = {}, filhos = []) {
  const no = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") {
      no.className = v;
    } else if (k === "text") {
      no.textContent = String(v);
    } else if (k.startsWith("on") && typeof v === "function") {
      no.addEventListener(k.slice(2), v);
    } else {
      no.setAttribute(k, v === true ? "" : String(v));
    }
  }
  const lista = Array.isArray(filhos) ? filhos : [filhos];
  for (const f of lista) {
    if (f === null || f === undefined || f === false) continue;
    no.appendChild(typeof f === "string" || typeof f === "number"
      ? document.createTextNode(String(f))
      : f);
  }
  return no;
}

export function limpar(no) {
  while (no && no.firstChild) {
    no.removeChild(no.firstChild);
  }
}

export function qs(seletor, raiz = document) {
  return raiz.querySelector(seletor);
}

export function qsa(seletor, raiz = document) {
  return Array.from(raiz.querySelectorAll(seletor));
}
