/* Orquestrador de animações cancelável (requestAnimationFrame / Web Animations). */

import { movimentoReduzido } from "../app.js";

export { movimentoReduzido };

const ativas = new Set();

export function animar(alvo, keyframes, opcoes = {}) {
  const reduzido = movimentoReduzido();
  const duracao = reduzido ? 0 : (opcoes.duration ?? 220);

  if (typeof alvo === "function") {
    if (duracao <= 0) {
      alvo(1);
      return { cancel() {} };
    }
    let rafId = null;
    let cancelado = false;
    const inicio = performance.now();
    const handle = {
      cancel() {
        cancelado = true;
        if (rafId !== null) window.cancelAnimationFrame(rafId);
        ativas.delete(handle);
      },
    };
    ativas.add(handle);

    function quadro(agora) {
      if (cancelado) return;
      const frac = Math.min(1, (agora - inicio) / duracao);
      alvo(frac);
      if (frac < 1) {
        rafId = window.requestAnimationFrame(quadro);
      } else {
        ativas.delete(handle);
      }
    }
    rafId = window.requestAnimationFrame(quadro);
    return handle;
  }

  if (!alvo || typeof alvo.animate !== "function" || duracao <= 0) {
    return { cancel() {} };
  }

  const anim = alvo.animate(keyframes, {
    duration: duracao,
    easing: opcoes.easing || "cubic-bezier(0.25, 0.1, 0.25, 1)",
    fill: opcoes.fill || "none",
  });
  const handle = {
    cancel() {
      try {
        anim.cancel();
      } catch (e) {
        // ignora se já finalizada
      }
      ativas.delete(handle);
    },
  };
  ativas.add(handle);
  if (anim.finished && typeof anim.finished.finally === "function") {
    anim.finished.catch(() => {}).finally(() => ativas.delete(handle));
  }
  return handle;
}

export function cancelarTudo(raiz = document) {
  for (const h of Array.from(ativas)) {
    h.cancel();
  }
  ativas.clear();

  if (raiz && typeof raiz.getAnimations === "function") {
    for (const anim of raiz.getAnimations()) {
      const timing = anim.effect && typeof anim.effect.getTiming === "function"
        ? anim.effect.getTiming()
        : null;
      if (!timing || timing.iterations !== Infinity) {
        try {
          anim.cancel();
        } catch (e) {
          // ignora
        }
      }
    }
  }
}
