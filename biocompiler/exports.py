"""Formatadores puros de relatórios de terminal e exportações CSV/TXT."""

import csv
import dataclasses
import io
import json

_SEP_IGUAL = "=" * 40
_SEP_TRACO = "-" * 40

_ASCII_MAP = str.maketrans({
    "↖": "\\",
    "↑": "^",
    "←": "<",
    "·": "*",
    "×": "x",
})

_TITULOS_LOTE = {
    "at1": "BIOCOMPILER 1.0 - DNA TRANSCRIBER",
    "at2": "BIOCOMPILER 2.0 - RNA PROCESSOR",
    "at3": "RIBOSSOMO - PROTEIN TRANSLATOR",
}

_COLUNAS_CSV = {
    "at1": ("pre_mRNA", "pre_mrna", "NÃO GERADO"),
    "at2": ("mRNA_maduro", "mrna_maduro", "NÃO GERADO"),
    "at3": ("proteina", "proteina", "NÃO GERADA"),
}

_TITULOS_AT4 = {
    "local": "ALINHAMENTO LOCAL (SMITH-WATERMAN)",
    "global": "ALINHAMENTO GLOBAL (NEEDLEMAN-WUNSCH)",
}


def _eh_int(valor: object) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _linha_parametros_at4(match: int, mismatch: int, gap: int) -> str:
    return f"Match: {match:+d}   Mismatch: {mismatch:+d}   Gap: {gap:+d}"


def csv_lote(atividade: str, resultados) -> str:
    """Gera o CSV canônico com delimitador ';' para lotes AT1–AT3."""
    if atividade not in _COLUNAS_CSV:
        raise ValueError(f"atividade inválida para CSV de lote: {atividade!r}")
    coluna, atributo, texto_falha = _COLUNAS_CSV[atividade]
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=";", lineterminator="\n")
    escritor.writerow(["linha", "status", "resultado", coluna])
    for idx, res in enumerate(resultados, start=1):
        if res is None:
            escritor.writerow([
                idx,
                "NÃO EXECUTADO",
                "NÃO EXECUTADO — dependência inválida",
                texto_falha,
            ])
        else:
            produto = getattr(res, atributo) if res.ok else texto_falha
            escritor.writerow([idx, res.status, res.resultado, produto])
    return buf.getvalue()


def cabecalho_lote(atividade: str) -> str:
    """Gera o cabeçalho padrão de um relatório de lote AT1–AT3."""
    if atividade not in _TITULOS_LOTE:
        raise ValueError(f"atividade inválida para relatório de lote: {atividade!r}")
    return f"{_SEP_IGUAL}\n{_TITULOS_LOTE[atividade]}\n{_SEP_IGUAL}\n"


def bloco_lote(atividade: str, n: int, res) -> str:
    """Gera o bloco textual de uma única entrada de lote AT1–AT3."""
    if atividade not in _TITULOS_LOTE:
        raise ValueError(f"atividade inválida para relatório de lote: {atividade!r}")

    linhas: list[str] = [
        f"ENTRADA: {n}",
        f"STATUS: {'CORRETO' if res.ok else 'ERRO'}",
    ]
    if atividade == "at1":
        if res.ok:
            linhas.extend([
                "Bases: OK",
                "START: ATG - OK",
                "Quadro de leitura: OK",
                f"STOP: {res.codon_stop} - OK",
                "Transcrição: OK",
                f"pré-mRNA: {res.pre_mrna}",
            ])
        else:
            linhas.extend([
                f"TIPO: {res.resultado}",
                "pré-mRNA: NÃO GERADO",
            ])
    elif atividade == "at2":
        if res.ok:
            linhas.extend([
                "Sítio 5': OK",
                "Branch point: OK",
                "Sítio 3': OK",
                "Splicing: OK",
                "CAP 5': ADICIONADA",
                f"Cauda poli-A: {len(res.cauda_adicionada)} A",
                f"mRNA MADURO: {res.mrna_maduro}",
            ])
        else:
            linhas.extend([
                f"TIPO: {res.resultado}",
                "mRNA MADURO: NÃO GERADO",
            ])
    else:
        if res.ok:
            linhas.extend([
                "CAP 5': OK",
                "START: AUG - OK",
                "Quadro de leitura: OK",
                f"STOP: {res.codon_stop} - OK",
                f"Cauda poli-A: {res.tamanho_cauda} A - OK",
                "Tradução: OK",
                f"PROTEÍNA: {res.proteina}",
            ])
        else:
            linhas.extend([
                f"TIPO: {res.resultado}",
                "PROTEÍNA: NÃO GERADA",
            ])
    linhas.append(_SEP_TRACO)
    return "\n".join(linhas) + "\n"


def relatorio_lote(atividade: str, resultados) -> str:
    """Gera o relatório textual de lote AT1–AT3 fiel aos enunciados."""
    cabecalho = cabecalho_lote(atividade)
    blocos = "".join(
        bloco_lote(atividade, idx, res) for idx, res in enumerate(resultados, start=1)
    )
    return cabecalho + blocos


def _csv_grade(seq1: str, seq2: str, linhas_matriz, delimitador: str) -> str:
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=delimitador, lineterminator="\n")
    escritor.writerow(["", "-", *seq2])
    rotulos = ["-", *seq1]
    for idx, linha in enumerate(linhas_matriz):
        escritor.writerow([rotulos[idx], *linha])
    return buf.getvalue()


def csv_matriz_pontuacao(r, delimitador: str = ";") -> str:
    """Exporta a matriz de pontuação completa da AT4 em CSV."""
    return _csv_grade(r.seq1, r.seq2, r.matriz, delimitador)


def csv_matriz_traceback(r, delimitador: str = ";") -> str:
    """Exporta a matriz de direções de traceback da AT4 em CSV."""
    return _csv_grade(r.seq1, r.seq2, r.direcoes, delimitador)


def csv_alinhamento(r, delimitador: str = ";") -> str:
    """Exporta as colunas alinhadas e contribuições de score da AT4 em CSV."""
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=delimitador, lineterminator="\n")
    escritor.writerow(["posicao", "seq1", "marcador", "seq2", "contribuicao_score"])
    for pos, (b1, marc, b2) in enumerate(
        zip(r.alinhado1, r.marcadores, r.alinhado2), start=1
    ):
        if marc == "|":
            contrib = r.match
        elif marc == ".":
            contrib = r.mismatch
        else:
            contrib = r.gap
        escritor.writerow([pos, b1, marc, b2, contrib])
    return buf.getvalue()


def _grade_texto(seq1: str, seq2: str, linhas_matriz) -> list[str]:
    grade = [["", "-", *seq2]]
    rotulos = ["-", *seq1]
    for idx, linha in enumerate(linhas_matriz):
        grade.append([rotulos[idx], *(str(v) for v in linha)])
    largura = max(len(celula) for linha in grade for celula in linha)
    return [" ".join(celula.rjust(largura) for celula in linha) for linha in grade]


def relatorio_at4(r) -> str:
    """Gera o relatório textual completo da AT4."""
    titulo = _TITULOS_AT4.get(r.metodo, "ALINHAMENTO")
    linhas: list[str] = [
        _SEP_IGUAL,
        titulo,
        _SEP_IGUAL,
        f"Seq1 original: {r.seq1}",
        f"Seq2 original: {r.seq2}",
    ]
    if _eh_int(r.match) and _eh_int(r.mismatch) and _eh_int(r.gap):
        linhas.append(_linha_parametros_at4(r.match, r.mismatch, r.gap))

    if not r.ok:
        linhas.append("STATUS: ERRO")
        linhas.append(f"TIPO: {r.resultado}")
        for item in r.erros:
            linhas.append(f"- {item}")
        linhas.append(_SEP_TRACO)
        return "\n".join(linhas) + "\n"

    linhas.extend([
        "STATUS: CORRETO",
        "",
        "MATRIZ DE PONTUAÇÃO",
        *_grade_texto(r.seq1, r.seq2, r.matriz),
        "",
        "MATRIZ DE TRACEBACK",
        *_grade_texto(r.seq1, r.seq2, r.direcoes),
        "",
    ])

    if r.inicio_traceback is None:
        linhas.append(
            "Início do traceback: nenhum (sem região de similaridade positiva)"
        )
    else:
        ini_i, ini_j = r.inicio_traceback
        caminho_str = " ".join(f"({ci},{cj})" for ci, cj in r.caminho)
        linhas.extend([
            f"Início do traceback: ({ini_i},{ini_j})",
            f"Caminho: {caminho_str}",
            "",
            "Seq1: " + " ".join(r.alinhado1),
            ("      " + " ".join(r.marcadores)).rstrip(),
            "Seq2: " + " ".join(r.alinhado2),
        ])

    linhas.extend([
        f"Score: {r.score}",
        f"Matches: {r.matches}   Mismatches: {r.mismatches}   Gaps: {r.gaps}   Tamanho: {r.tamanho}",
        _SEP_TRACO,
    ])
    return "\n".join(linhas) + "\n"


def texto_comparacao(local, global_) -> str:
    """Gera o resumo comparativo entre alinhamento local e global (AT4 both)."""
    linhas = [
        "COMPARAÇÃO LOCAL × GLOBAL",
        f"Seq1 original: {local.seq1}",
        f"Seq2 original: {local.seq2}",
        _linha_parametros_at4(local.match, local.mismatch, local.gap),
        (
            f"LOCAL: score={local.score} tamanho={local.tamanho} "
            f"matches={local.matches} mismatches={local.mismatches} gaps={local.gaps}"
        ),
        (
            f"GLOBAL: score={global_.score} tamanho={global_.tamanho} "
            f"matches={global_.matches} mismatches={global_.mismatches} gaps={global_.gaps}"
        ),
    ]
    return "\n".join(linhas) + "\n"


def para_ascii(texto: str) -> str:
    """Converte setas e símbolos visuais Unicode para ASCII puro."""
    return texto.translate(_ASCII_MAP)


def _formatar_evento(k: int, evento) -> str:
    texto = f"  {k}. {evento.tipo}"
    if evento.posicao is not None:
        texto += f" (índice {evento.posicao})"
    if evento.detalhe:
        texto += f": {evento.detalhe}"
    return texto


def passos(r, granularidade: str = "fase") -> list[str]:
    """Formata os eventos (e linhas/células da matriz AT4, se solicitado) numerados."""
    matriz = getattr(r, "matriz", None)
    if granularidade in ("linha", "celula") and matriz is not None:
        eventos = list(r.eventos)
        linhas: list[str] = [_formatar_evento(1, eventos[0])]
        k = 2
        if granularidade == "linha":
            for i, linha in enumerate(matriz):
                linhas.append(f"  {k}. LINHA {i}: " + " ".join(map(str, linha)))
                k += 1
        else:
            for i, (linha_m, linha_d) in enumerate(zip(matriz, r.direcoes)):
                for j, (valor, direcao) in enumerate(zip(linha_m, linha_d)):
                    linhas.append(f"  {k}. CELULA ({i},{j}): {valor} {direcao}")
                    k += 1
        for evento in eventos[1:]:
            linhas.append(_formatar_evento(k, evento))
            k += 1
        return linhas

    return [_formatar_evento(k, evento) for k, evento in enumerate(r.eventos, start=1)]


def _dados_sem_eventos(r) -> dict:
    dados = dataclasses.asdict(r)
    dados.pop("eventos", None)
    return dados


def _passos_json(r) -> list[dict]:
    return [
        {"tipo": e.tipo, "posicao": e.posicao, "detalhe": e.detalhe}
        for e in r.eventos
    ]


def json_lote(atividade: str, sequencias, resultados, saidas: list[str]) -> str:
    """Serializa resultados de lote AT1–AT3 em lista JSON conforme SPEC §8.2/D016."""
    doc = [
        {
            "schema_version": 1,
            "atividade": atividade,
            "entrada": {"linha": idx, "sequencia": seq},
            "configuracao": {},
            "status": res.status,
            "resultado": res.resultado,
            "validacoes": [] if res.ok else [res.resultado],
            "passos": _passos_json(res),
            "dados": _dados_sem_eventos(res),
            "saidas": list(saidas),
            "avisos": [],
        }
        for idx, (seq, res) in enumerate(zip(sequencias, resultados), start=1)
    ]
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def json_at4(
    seq1: str,
    seq2: str,
    match,
    mismatch,
    gap,
    resultados,
    saidas: list[str],
) -> str:
    """Serializa resultados da AT4 em lista JSON conforme SPEC §8.2/D016."""
    doc = [
        {
            "schema_version": 1,
            "atividade": "at4",
            "entrada": {"seq1": seq1, "seq2": seq2},
            "configuracao": {
                "metodo": res.metodo,
                "match": match,
                "mismatch": mismatch,
                "gap": gap,
            },
            "status": res.status,
            "resultado": res.resultado,
            "validacoes": list(res.erros),
            "passos": _passos_json(res),
            "dados": _dados_sem_eventos(res),
            "saidas": list(saidas),
            "avisos": [],
        }
        for res in resultados
    ]
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def relatorio_fluxo(rf) -> str:
    """Gera o relatório mestre do modo `all` (AT1→AT2→AT3 nas duas amostras + AT4)."""
    linhas: list[str] = [
        _SEP_IGUAL,
        "LABORATÓRIO COMPLETO (AT1 → AT2 → AT3 + AT4)",
        _SEP_IGUAL,
    ]
    for idx, cadeia in enumerate((rf.seq1, rf.seq2), start=1):
        linhas.append(f"SEQ{idx}")
        linhas.append(f"DNA: {cadeia.dna}")
        linhas.append(f"AT1: {cadeia.at1.resultado}")
        if cadeia.at1.ok:
            linhas.append(f"  pré-mRNA: {cadeia.at1.pre_mrna}")

        if cadeia.at2 is None:
            linhas.append("AT2: NÃO EXECUTADO — dependência inválida")
        else:
            linhas.append(f"AT2: {cadeia.at2.resultado}")
            if cadeia.at2.ok:
                for n_intr, intr in enumerate(cadeia.at2.introns, start=1):
                    linhas.append(
                        f"  Íntron {n_intr}: GU no índice {intr.posicao_gu}, "
                        f"branch A no índice {intr.posicao_branch}, "
                        f"AG no índice {intr.posicao_ag}"
                    )
                linhas.append(f"  mRNA maduro: {cadeia.at2.mrna_maduro}")

        if cadeia.at3 is None:
            linhas.append("AT3: NÃO EXECUTADO — dependência inválida")
        else:
            linhas.append(f"AT3: {cadeia.at3.resultado}")
            if cadeia.at3.ok:
                linhas.append("  Códons: " + " ".join(cadeia.at3.codons))
                linhas.append(f"  Proteína: {cadeia.at3.proteina}")

        if cadeia.ok:
            linhas.append("CADEIA: OK")
        else:
            linhas.append(f"CADEIA: ERRO (falha em {cadeia.etapa_falha})")
        linhas.append(_SEP_TRACO)

    texto = "\n".join(linhas) + "\n"
    partes = [texto] + [relatorio_at4(r) for r in rf.alinhamentos]
    if len(rf.alinhamentos) == 2 and all(r.ok for r in rf.alinhamentos):
        partes.append(texto_comparacao(rf.alinhamentos[0], rf.alinhamentos[1]))
    return "".join(partes)


def json_fluxo(
    seq1: str,
    seq2: str,
    metodo: str,
    match,
    mismatch,
    gap,
    rf,
    saidas: list[str],
) -> str:
    """Serializa o ResultadoFluxo completo em JSON conforme D017."""
    doc = {
        "schema_version": 1,
        "atividade": "all",
        "entrada": {"seq1": seq1, "seq2": seq2},
        "configuracao": {
            "metodo": metodo,
            "match": match,
            "mismatch": mismatch,
            "gap": gap,
        },
        "status": "OK" if rf.ok else "ERRO",
        "dados": dataclasses.asdict(rf),
        "saidas": list(saidas),
        "avisos": [],
    }
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def artefatos_lote(atividade: str, resultados) -> dict[str, str]:
    """Monta os arquivos de exportação de um lote AT1–AT3 na ordem da CLI."""
    return {f"{atividade}_resultados.txt": csv_lote(atividade, resultados)}


def artefatos_at4(resultados, delimitador: str = ";") -> dict[str, str]:
    """Monta os arquivos de exportação da AT4 para os alinhamentos OK."""
    arquivos: dict[str, str] = {}
    for r in resultados:
        if not r.ok:
            continue
        m = r.metodo
        arquivos[f"alinhamento_{m}.txt"] = relatorio_at4(r)
        arquivos[f"matriz_pontuacao_{m}.csv"] = csv_matriz_pontuacao(r, delimitador)
        arquivos[f"matriz_traceback_{m}.csv"] = csv_matriz_traceback(r, delimitador)
        arquivos[f"alinhamento_{m}.csv"] = csv_alinhamento(r, delimitador)
    if len(resultados) == 2 and all(r.ok for r in resultados):
        arquivos["comparacao.txt"] = texto_comparacao(resultados[0], resultados[1])
    return arquivos


def artefatos_fluxo(rf, delimitador: str = ";") -> dict[str, str]:
    """Monta os arquivos de exportação do modo `all` na ordem da CLI."""
    arquivos: dict[str, str] = {
        "relatorio_mestre.txt": relatorio_fluxo(rf),
        "at1_resultados.txt": csv_lote("at1", [rf.seq1.at1, rf.seq2.at1]),
        "at2_resultados.txt": csv_lote("at2", [rf.seq1.at2, rf.seq2.at2]),
        "at3_resultados.txt": csv_lote("at3", [rf.seq1.at3, rf.seq2.at3]),
    }
    arquivos.update(artefatos_at4(rf.alinhamentos, delimitador))
    return arquivos
