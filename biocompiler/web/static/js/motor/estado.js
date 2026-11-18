/* Barramento de estado compartilhado entre player, visualizações e inspetor. */

export function criarEstado() {
  const atual = {
    registro: 0,
    passo: 1,
    selecao: null,
  };
  const ouvintes = new Set();

  function obter() {
    return { ...atual };
  }

  function definir(parcial) {
    let mudou = false;
    for (const chave of ["registro", "passo", "selecao"]) {
      if (chave in parcial && atual[chave] !== parcial[chave]) {
        atual[chave] = parcial[chave];
        mudou = true;
      }
    }
    if (!mudou) return;
    const copia = obter();
    for (const fn of ouvintes) {
      fn(copia);
    }
  }

  function assinar(fn) {
    ouvintes.add(fn);
    return () => ouvintes.delete(fn);
  }

  function limparSelecao() {
    definir({ selecao: null });
  }

  return { obter, definir, assinar, limparSelecao };
}

export const estadoGlobal = criarEstado();
