/* Cliente HTTP local para a API JSON e exportação .zip. */

async function requisitarJson(url, opcoes = {}) {
  const resp = await fetch(url, opcoes);
  const texto = await resp.text();
  let dados;
  try {
    dados = JSON.parse(texto);
  } catch (e) {
    throw new Error(`Resposta inválida do servidor (HTTP ${resp.status})`);
  }
  if (!resp.ok) {
    throw new Error((dados && dados.erro) || `Erro HTTP ${resp.status}`);
  }
  return dados;
}

export function obterExemplos() {
  return requisitarJson("/api/exemplos");
}

export function obterCodigoGenetico() {
  return requisitarJson("/api/codigo-genetico");
}

const ROTAS_LOTE = {
  at1: "/api/at1",
  at2: "/api/at2",
  at3: "/api/at3",
};

export function executarLote(atividade, payload) {
  const url = ROTAS_LOTE[atividade];
  return requisitarJson(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function executarAt4(payload) {
  return requisitarJson("/api/at4", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function executarAll(payload) {
  return requisitarJson("/api/all", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function inspecionarCelula(payload) {
  return requisitarJson("/api/at4/celula", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function exportarZip(payload) {
  const resp = await fetch("/api/exportar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    let msg = `Erro HTTP ${resp.status}`;
    try {
      const dados = await resp.json();
      if (dados && dados.erro) msg = dados.erro;
    } catch (e) {
      // ignora corpo não-JSON
    }
    throw new Error(msg);
  }
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `biocompiler_${payload.atividade}.zip`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
