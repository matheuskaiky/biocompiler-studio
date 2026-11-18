/* Lente de refração SVG nativa (perfil de bisel + lei de Snell) para superfícies [data-lente]. */

const NS_SVG = "http:" + "//www.w3.org/2000/svg";
const cacheMapas = new Map();
let contadorFiltro = 0;
let defsSvg = null;
let observadorResize = null;

function obterDefs() {
  if (defsSvg && defsSvg.isConnected) return defsSvg;
  const svg = document.createElementNS(NS_SVG, "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.style.cssText = "position:absolute;width:0;height:0;overflow:hidden;pointer-events:none";
  const defs = document.createElementNS(NS_SVG, "defs");
  svg.appendChild(defs);
  document.body.appendChild(svg);
  defsSvg = defs;
  return defsSvg;
}

function gerarMapaLente(largura, altura) {
  const w = Math.max(1, Math.round(largura));
  const h = Math.max(1, Math.round(altura));
  const chave = `${w}x${h}`;
  if (cacheMapas.has(chave)) return cacheMapas.get(chave);

  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";

  const img = ctx.createImageData(w, h);
  const dados = img.data;
  new Uint32Array(dados.buffer).fill(0xFF808080);
  const bisel = Math.min(14, Math.max(6, Math.floor(Math.min(w, h) * 0.2)));
  const nArVidro = 1.0 / 1.48;

  for (let y = 0; y < h; y += 1) {
    const dyTop = y;
    const dyBot = h - 1 - y;
    const dy = Math.min(dyTop, dyBot);
    const naBordaY = dy < bisel;
    for (let x = 0; x < w; x += 1) {
      const dxLeft = x;
      const dxRight = w - 1 - x;
      const dx = Math.min(dxLeft, dxRight);
      if (!naBordaY && dx >= bisel) {
        x = w - bisel - 1;
        continue;
      }
      const d = Math.min(dx, dy);
      if (d >= bisel) continue;

      const idx = (y * w + x) * 4;
      const t = 1 - d / bisel;
      const inc = t * (Math.PI * 0.42);
      const refr = Math.asin(Math.min(1, nArVidro * Math.sin(inc)));
      const mag = Math.sin(inc - refr) * 290;

      let vx = 0;
      let vy = 0;
      if (dx < bisel) vx = (dxLeft < dxRight ? -1 : 1) * (1 - dx / bisel);
      if (dy < bisel) vy = (dyTop < dyBot ? -1 : 1) * (1 - dy / bisel);
      const norm = Math.hypot(vx, vy) || 1;
      dados[idx] = Math.max(0, Math.min(255, Math.round(128 + (vx / norm) * mag)));
      dados[idx + 1] = Math.max(0, Math.min(255, Math.round(128 + (vy / norm) * mag)));
    }
  }

  ctx.putImageData(img, 0, 0);
  const url = canvas.toDataURL("image/png");
  if (cacheMapas.size > 24) cacheMapas.clear();
  cacheMapas.set(chave, url);
  return url;
}

function atualizarLente(el) {
  if (!el || !el.isConnected) return;
  const r = el.getBoundingClientRect();
  const w = Math.round(r.width);
  const h = Math.round(r.height);
  if (w < 4 || h < 4) return;
  if (el.__lenteW !== undefined && Math.abs(el.__lenteW - w) <= 2 && Math.abs(el.__lenteH - h) <= 2) return;

  el.__lenteW = w;
  el.__lenteH = h;

  const defs = obterDefs();
  if (!el.__lenteId) {
    contadorFiltro += 1;
    const id = `lente-vidro-${contadorFiltro}`;
    const filtro = document.createElementNS(NS_SVG, "filter");
    filtro.setAttribute("id", id);
    filtro.setAttribute("x", "0");
    filtro.setAttribute("y", "0");
    filtro.setAttribute("width", "100%");
    filtro.setAttribute("height", "100%");
    filtro.setAttribute("color-interpolation-filters", "sRGB");

    const feImg = document.createElementNS(NS_SVG, "feImage");
    feImg.setAttribute("x", "0");
    feImg.setAttribute("y", "0");
    feImg.setAttribute("preserveAspectRatio", "none");
    feImg.setAttribute("result", "mapa");

    const feDisp = document.createElementNS(NS_SVG, "feDisplacementMap");
    feDisp.setAttribute("in", "SourceGraphic");
    feDisp.setAttribute("in2", "mapa");
    feDisp.setAttribute("scale", "14");
    feDisp.setAttribute("xChannelSelector", "R");
    feDisp.setAttribute("yChannelSelector", "G");

    filtro.appendChild(feImg);
    filtro.appendChild(feDisp);
    defs.appendChild(filtro);

    el.__lenteId = id;
    el.__lenteImg = feImg;
    el.style.setProperty("--vidro-filtro-lente", `url(#${id}) blur(var(--vidro-desfoque)) saturate(175%)`);
  }

  const href = gerarMapaLente(w, h);
  if (href && el.__lenteImg) {
    el.__lenteImg.setAttribute("width", String(w));
    el.__lenteImg.setAttribute("height", String(h));
    el.__lenteImg.setAttribute("href", href);
  }
}

function registrarElemento(el) {
  if (!el || el.__lenteObservado) return;
  el.__lenteObservado = true;
  if (observadorResize) observadorResize.observe(el);
  atualizarLente(el);
}

function varrerLentes(raiz = document) {
  if (!raiz || !raiz.querySelectorAll) return;
  if (raiz.matches && raiz.matches("[data-lente]")) registrarElemento(raiz);
  raiz.querySelectorAll("[data-lente]").forEach(registrarElemento);
}

function iniciarLentes() {
  if (!document.body) return;
  if (typeof ResizeObserver !== "undefined" && !observadorResize) {
    observadorResize = new ResizeObserver((entradas) => {
      for (const ent of entradas) {
        const alvo = ent.target;
        clearTimeout(alvo.__lenteTimer);
        alvo.__lenteTimer = setTimeout(() => atualizarLente(alvo), 140);
      }
    });
  }
  varrerLentes(document);
  if (typeof MutationObserver !== "undefined") {
    const obsDom = new MutationObserver((mutacoes) => {
      for (const mut of mutacoes) {
        for (const no of mut.addedNodes) {
          if (no.nodeType === 1) varrerLentes(no);
        }
      }
    });
    obsDom.observe(document.body, { childList: true, subtree: true });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", iniciarLentes);
} else {
  iniciarLentes();
}
